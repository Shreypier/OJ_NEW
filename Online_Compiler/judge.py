"""Code execution and judging engine.

Two execution backends (setting ``JUDGE_BACKEND``):

* ``docker`` (default): every submission runs in its own throwaway container
  (no network, read-only filesystem, memory/CPU/process limits, all capabilities
  dropped, code executed as the unprivileged "nobody" user). See ``sandbox/``.
* ``local``: runs directly on the host with timeouts and (on Linux) rlimits.
  Only for development and tests; it is NOT safe against hostile code.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass, field

from django.conf import settings

# Verdict codes
AC = "AC"    # Accepted
WA = "WA"    # Wrong Answer
CE = "CE"    # Compile Error
RE = "RE"    # Runtime Error
TLE = "TLE"  # Time Limit Exceeded
OLE = "OLE"  # Output Limit Exceeded
SE = "SE"    # System Error (judge problem, e.g. Docker unavailable)

VERDICT_LABELS = {
    AC: "Accepted",
    WA: "Wrong Answer",
    CE: "Compile Error",
    RE: "Runtime Error",
    TLE: "Time Limit Exceeded",
    OLE: "Output Limit Exceeded",
    SE: "System Error",
}

LANGUAGES = ("python", "c", "c++")

COMPILE_TIMEOUT = getattr(settings, "JUDGE_COMPILE_TIMEOUT", 15)
TIME_LIMIT = getattr(settings, "JUDGE_TIME_LIMIT", 3)
MEMORY_LIMIT_MB = getattr(settings, "JUDGE_MEMORY_LIMIT_MB", 256)
OUTPUT_LIMIT = getattr(settings, "JUDGE_OUTPUT_LIMIT_BYTES", 1024 * 1024)
MAX_MESSAGE = 4000  # cap on compiler/stderr text we keep

DOCKER_IMAGE = getattr(settings, "JUDGE_DOCKER_IMAGE", "codelang-sandbox")
CONTAINER_MEMORY_MB = getattr(settings, "JUDGE_CONTAINER_MEMORY_MB", 512)
DOCKER_STARTUP_SLACK = 20  # seconds allowed for container start-up/teardown


@dataclass
class RunResult:
    verdict: str = AC
    output: str = ""
    error: str = ""
    time_ms: int = 0


@dataclass
class CaseResult:
    index: int
    verdict: str
    time_ms: int = 0
    is_sample: bool = False
    input_data: str = ""
    expected: str = ""
    actual: str = ""
    error: str = ""


@dataclass
class JudgeResult:
    verdict: str = AC
    time_ms: int = 0
    message: str = ""
    passed: int = 0
    total: int = 0
    cases: list = field(default_factory=list)


@dataclass
class Execution:
    """Outcome of running a program on a list of inputs."""
    failure: RunResult = None          # compile error / system error: nothing ran
    runs: list = field(default_factory=list)  # one RunResult per input run (stops after a failure)


def _trim(text):
    return text if len(text) <= MAX_MESSAGE else text[:MAX_MESSAGE] + "\n...[truncated]"


# --------------------------------------------------------------------------
# local backend (development / tests only)
# --------------------------------------------------------------------------
def _limit_resources():  # pragma: no cover - runs in the child, posix only
    import resource
    mem = MEMORY_LIMIT_MB * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
    cpu = int(TIME_LIMIT) + 1
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
    resource.setrlimit(resource.RLIMIT_FSIZE, (OUTPUT_LIMIT * 2, OUTPUT_LIMIT * 2))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    os.setsid()


class Workspace:
    """Temporary directory holding one program; compile once, run many times."""

    def __init__(self, language, code):
        self.language = language
        self.code = code
        self.dir = None
        self.cmd = None

    def __enter__(self):
        self.dir = tempfile.mkdtemp(prefix="judge_")
        return self

    def __exit__(self, *exc):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _path(self, name):
        return os.path.join(self.dir, name)

    def compile(self):
        """Prepare the program. Returns None on success, else a RunResult."""
        if self.language not in LANGUAGES:
            return RunResult(SE, error=f"Unsupported language: {self.language}")

        ext = {"python": "py", "c": "c", "c++": "cpp"}[self.language]
        source = self._path(f"main.{ext}")
        with open(source, "w", encoding="utf-8", newline="\n") as f:
            f.write(self.code or "")

        if self.language == "python":
            self.cmd = [sys.executable, "-I", source]
            return None

        exe = self._path("main.exe" if os.name == "nt" else "main")
        compiler = ["gcc"] if self.language == "c" else ["g++"]
        argv = compiler + [source, "-O2", "-o", exe]
        if self.language == "c":
            argv.append("-lm")
        try:
            proc = subprocess.run(
                argv, capture_output=True, text=True, errors="replace",
                timeout=COMPILE_TIMEOUT, cwd=self.dir,
            )
        except FileNotFoundError:
            return RunResult(SE, error=f"{compiler[0]} is not installed on the judge")
        except subprocess.TimeoutExpired:
            return RunResult(CE, error="Compilation timed out")
        if proc.returncode != 0:
            return RunResult(CE, error=_trim(proc.stderr or proc.stdout))
        self.cmd = [exe]
        return None

    def run(self, stdin_text):
        """Run the compiled program on one input."""
        in_path, out_path = self._path("in.txt"), self._path("out.txt")
        with open(in_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(stdin_text or "")

        kwargs = {}
        if os.name == "posix":
            kwargs["preexec_fn"] = _limit_resources

        start = time.perf_counter()
        try:
            with open(in_path, "rb") as fin, open(out_path, "wb") as fout:
                proc = subprocess.run(
                    self.cmd, stdin=fin, stdout=fout, stderr=subprocess.PIPE,
                    timeout=TIME_LIMIT, cwd=self.dir, **kwargs,
                )
        except subprocess.TimeoutExpired:
            return RunResult(TLE, error="Time limit exceeded",
                             time_ms=int(TIME_LIMIT * 1000))
        except OSError as exc:
            return RunResult(SE, error=str(exc))
        elapsed = int((time.perf_counter() - start) * 1000)

        if os.path.getsize(out_path) > OUTPUT_LIMIT:
            return RunResult(OLE, error="Output limit exceeded", time_ms=elapsed)
        with open(out_path, "rb") as f:
            output = f.read().decode("utf-8", errors="replace")

        err = _trim(proc.stderr.decode("utf-8", errors="replace"))
        if proc.returncode != 0:
            return RunResult(RE, output=output, error=err or f"Exited with code {proc.returncode}",
                             time_ms=elapsed)
        return RunResult(AC, output=output, error=err, time_ms=elapsed)


def _execute_local(language, code, inputs):
    with Workspace(language, code) as ws:
        failed = ws.compile()
        if failed:
            return Execution(failure=failed)
        runs = []
        for stdin_text in inputs:
            r = ws.run(stdin_text)
            runs.append(r)
            if r.verdict != AC:
                break
        return Execution(runs=runs)


# --------------------------------------------------------------------------
# docker backend (one throwaway container per submission)
# --------------------------------------------------------------------------
_image_ok = False


def docker_command(name):
    """The `docker run` command line. Every flag here is part of the sandbox."""
    return [
        "docker", "run", "--rm", "-i", "--name", name,
        "--network", "none",                              # no network at all
        "--memory", f"{CONTAINER_MEMORY_MB}m",            # hard RAM cap (OOM-killed beyond)
        "--memory-swap", f"{CONTAINER_MEMORY_MB}m",       # no swap
        "--cpus", "1",
        "--pids-limit", "128",                            # fork bombs
        "--read-only",                                    # immutable root filesystem
        "--tmpfs", "/work:rw,exec,nosuid,nodev,size=64m", # only scratch space, size-capped
        "--cap-drop", "ALL",                              # no Linux capabilities...
        "--cap-add", "SETUID", "--cap-add", "SETGID",     # ...except to drop to "nobody"
        "--security-opt", "no-new-privileges",
        "--ulimit", "core=0",
        DOCKER_IMAGE,
    ]


def _docker_unavailable(msg):
    return Execution(failure=RunResult(SE, error=msg))


def _check_image():
    """Returns an error message, or None if Docker and the sandbox image are ready."""
    global _image_ok
    if _image_ok:
        return None
    try:
        proc = subprocess.run(["docker", "image", "inspect", DOCKER_IMAGE],
                              capture_output=True, timeout=30)
    except FileNotFoundError:
        return "Docker is not installed, so the judge cannot run code safely."
    except subprocess.TimeoutExpired:
        return "Docker did not respond."
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", "replace")
        if "daemon" in err.lower() or "pipe" in err.lower() or "connect" in err.lower():
            return "Docker is not running. Start Docker Desktop and try again."
        return "Sandbox image is missing. Build it with: python manage.py build_sandbox"
    _image_ok = True
    return None


def _execute_docker(language, code, inputs):
    problem = _check_image()
    if problem:
        return _docker_unavailable(problem)

    job = {
        "language": language, "code": code, "inputs": list(inputs),
        "time_limit": TIME_LIMIT, "memory_mb": MEMORY_LIMIT_MB,
        "output_limit": OUTPUT_LIMIT, "compile_timeout": COMPILE_TIMEOUT,
    }
    name = f"judge-{uuid.uuid4().hex[:16]}"
    budget = COMPILE_TIMEOUT + TIME_LIMIT * max(len(inputs), 1) + DOCKER_STARTUP_SLACK
    try:
        proc = subprocess.run(docker_command(name), input=json.dumps(job).encode("utf-8"),
                              capture_output=True, timeout=budget)
    except subprocess.TimeoutExpired:
        subprocess.run(["docker", "kill", name], capture_output=True)
        return _docker_unavailable("The judge took too long and was stopped.")
    except FileNotFoundError:
        return _docker_unavailable("Docker is not installed, so the judge cannot run code safely.")

    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", "replace").strip()
        if proc.returncode == 137:
            return _docker_unavailable("The sandbox ran out of memory and was stopped.")
        return _docker_unavailable("Sandbox error: " + _trim(err or f"exit code {proc.returncode}"))
    try:
        data = json.loads(proc.stdout.decode("utf-8", "replace"))
    except ValueError:
        return _docker_unavailable("Sandbox returned an unreadable result.")

    if data.get("compile_error"):
        ce = data["compile_error"]
        return Execution(failure=RunResult(ce["verdict"], error=ce.get("error", "")))
    return Execution(runs=[RunResult(r["verdict"], r.get("output", ""), r.get("error", ""),
                                     r.get("time_ms", 0)) for r in data["runs"]])


def execute(language, code, inputs):
    """Run `code` on every input using the configured backend."""
    if language not in LANGUAGES:
        return Execution(failure=RunResult(SE, error=f"Unsupported language: {language}"))
    backend = getattr(settings, "JUDGE_BACKEND", "docker")
    if backend == "local":
        return _execute_local(language, code, inputs)
    return _execute_docker(language, code, inputs)


# --------------------------------------------------------------------------
# public API
# --------------------------------------------------------------------------
def run_code(language, code, stdin_text):
    """Compile (if needed) and run once. Used by the 'Run' button."""
    ex = execute(language, code, [stdin_text])
    if ex.failure:
        return ex.failure
    return ex.runs[0] if ex.runs else RunResult(SE, error="Nothing was run")


def outputs_match(actual, expected):
    """Whitespace-insensitive comparison of two outputs."""
    return actual.split() == expected.split()


def judge(language, code, test_cases):
    """Judge code against an iterable of TestCase objects; stops at first failure."""
    cases = list(test_cases)
    result = JudgeResult(total=len(cases))
    if not cases:
        result.verdict = SE
        result.message = "This problem has no test cases yet."
        return result

    ex = execute(language, code, [c.input_data for c in cases])
    if ex.failure:
        result.verdict = ex.failure.verdict
        result.message = ex.failure.error
        return result

    for i, (case, run) in enumerate(zip(cases, ex.runs), start=1):
        result.time_ms = max(result.time_ms, run.time_ms)
        verdict = run.verdict
        if verdict == AC and not outputs_match(run.output, case.expected_output):
            verdict = WA
        entry = CaseResult(index=i, verdict=verdict, time_ms=run.time_ms, is_sample=case.is_sample)
        # Only reveal details of sample cases; hidden cases stay hidden.
        if case.is_sample:
            entry.input_data = case.input_data
            entry.expected = case.expected_output
            entry.actual = run.output
        if verdict != AC:
            entry.error = run.error
        result.cases.append(entry)
        if verdict != AC:
            result.verdict = verdict
            result.message = f"Failed on test case {i} of {len(cases)}"
            if run.error and verdict in (RE, SE):
                result.message += f"\n{run.error}"
            return result
        result.passed += 1

    result.verdict = AC
    result.message = f"Passed all {len(cases)} test cases"
    return result
