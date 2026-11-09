"""Code execution and judging engine.

Each submission gets its own temporary workspace that is deleted afterwards.
Programs run with a wall-clock timeout, an output-size cap and (on Linux, e.g.
inside the Docker image) CPU / memory / file-size rlimits.

NOTE: timeouts and rlimits stop runaway programs, not hostile ones. Run the
whole app inside the provided Docker image for real isolation.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field

from django.conf import settings

# Verdict codes
AC = "AC"    # Accepted
WA = "WA"    # Wrong Answer
CE = "CE"    # Compile Error
RE = "RE"    # Runtime Error
TLE = "TLE"  # Time Limit Exceeded
OLE = "OLE"  # Output Limit Exceeded
SE = "SE"    # System Error (judge problem, e.g. compiler missing)

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


def _trim(text):
    return text if len(text) <= MAX_MESSAGE else text[:MAX_MESSAGE] + "\n...[truncated]"


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


def run_code(language, code, stdin_text):
    """Compile (if needed) and run once. Used by the 'Run' button."""
    with Workspace(language, code) as ws:
        failed = ws.compile()
        if failed:
            return failed
        return ws.run(stdin_text)


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

    with Workspace(language, code) as ws:
        failed = ws.compile()
        if failed:
            result.verdict = failed.verdict
            result.message = failed.error
            return result

        for i, case in enumerate(cases, start=1):
            run = ws.run(case.input_data)
            result.time_ms = max(result.time_ms, run.time_ms)
            verdict = run.verdict
            if verdict == AC and not outputs_match(run.output, case.expected_output):
                verdict = WA
            entry = CaseResult(index=i, verdict=verdict, time_ms=run.time_ms,
                               is_sample=case.is_sample)
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
