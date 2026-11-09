"""In-container runner. Reads one JSON job on stdin, prints one JSON result on stdout.

job    = {language, code, inputs: [str], time_limit, memory_mb, output_limit,
          compile_timeout}
result = {compile_error: null | {verdict, error},
          runs: [{verdict, output, error, time_ms}]}

Submitted code runs as uid/gid 65534 ("nobody") in its own process group, so it
cannot signal, ptrace or read /proc entries of this root-owned runner, and it
never inherits the runner's stdout (where the result is written).
"""
import json
import os
import resource
import signal
import subprocess
import sys
import time

NOBODY = 65534
CODE_DIR = "/work/code"   # world-writable scratch: source + binary
IO_DIR = "/work/io"       # owned by root: stdin/stdout/stderr files
TMP_DIR = "/work/tmp"     # compiler scratch space
MAX_MESSAGE = 4000


def trim(text):
    return text if len(text) <= MAX_MESSAGE else text[:MAX_MESSAGE] + "\n...[truncated]"


def demote(mem_bytes, cpu_seconds, fsize):
    def fn():
        os.setsid()
        if mem_bytes:
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        resource.setrlimit(resource.RLIMIT_FSIZE, (fsize, fsize))
        resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        os.setgroups([])
        os.setgid(NOBODY)
        os.setuid(NOBODY)
    return fn


def kill_group(proc):
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def read_capped(path, limit):
    with open(path, "rb") as f:
        return f.read(limit + 1)


def setup_dirs():
    os.makedirs(CODE_DIR, exist_ok=True)
    os.makedirs(IO_DIR, exist_ok=True)
    os.makedirs(TMP_DIR, exist_ok=True)
    # No chown (CAP_CHOWN is dropped): these tmpfs dirs are simply world-writable.
    os.chmod(CODE_DIR, 0o777)
    os.chmod(TMP_DIR, 0o777)
    os.chmod(IO_DIR, 0o700)   # submitted code only ever uses the fds we hand it


def compile_program(job):
    """Returns (command, error_dict_or_None)."""
    lang, code = job["language"], job["code"]
    ext = {"python": "py", "c": "c", "c++": "cpp"}.get(lang)
    if ext is None:
        return None, {"verdict": "SE", "error": "Unsupported language: %s" % lang}
    src = os.path.join(CODE_DIR, "main." + ext)
    with open(src, "w", encoding="utf-8", newline="\n") as f:
        f.write(code)
    os.chmod(src, 0o644)

    if lang == "python":
        return ["python3", "-I", src], None

    exe = os.path.join(CODE_DIR, "main")
    argv = ["gcc" if lang == "c" else "g++", src, "-O2", "-o", exe]
    if lang == "c":
        argv.append("-lm")
    env = dict(os.environ, TMPDIR=TMP_DIR, HOME=TMP_DIR)
    try:
        proc = subprocess.run(
            argv, capture_output=True, timeout=job["compile_timeout"], cwd=CODE_DIR, env=env,
            preexec_fn=demote(0, int(job["compile_timeout"]) + 2, 64 * 1024 * 1024),
        )
    except subprocess.TimeoutExpired:
        return None, {"verdict": "CE", "error": "Compilation timed out"}
    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout).decode("utf-8", "replace")
        return None, {"verdict": "CE", "error": trim(msg)}
    return [exe], None


def run_one(cmd, stdin_text, job, index):
    in_path = os.path.join(IO_DIR, "in%d.txt" % index)
    out_path = os.path.join(IO_DIR, "out%d.txt" % index)
    err_path = os.path.join(IO_DIR, "err%d.txt" % index)
    with open(in_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(stdin_text or "")

    limit = job["output_limit"]
    mem = job["memory_mb"] * 1024 * 1024
    tl = job["time_limit"]
    start = time.perf_counter()
    timed_out = False
    with open(in_path, "rb") as fin, open(out_path, "wb") as fout, open(err_path, "wb") as ferr:
        proc = subprocess.Popen(
            cmd, stdin=fin, stdout=fout, stderr=ferr, cwd=CODE_DIR, close_fds=True,
            env={"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": TMP_DIR, "LANG": "C.UTF-8"},
            preexec_fn=demote(mem, int(tl) + 1, limit * 2),
        )
        try:
            proc.wait(timeout=tl)
        except subprocess.TimeoutExpired:
            timed_out = True
        kill_group(proc)       # also reaps any leftover children
        proc.wait()
    elapsed = int((time.perf_counter() - start) * 1000)

    if timed_out:
        return {"verdict": "TLE", "output": "", "error": "Time limit exceeded", "time_ms": int(tl * 1000)}
    raw = read_capped(out_path, limit)
    if len(raw) > limit:
        return {"verdict": "OLE", "output": "", "error": "Output limit exceeded", "time_ms": elapsed}
    output = raw.decode("utf-8", "replace")
    err = trim(read_capped(err_path, MAX_MESSAGE).decode("utf-8", "replace"))
    if proc.returncode != 0:
        if proc.returncode < 0:
            err = (err + "\nTerminated by signal %d" % -proc.returncode).strip()
        return {"verdict": "RE", "output": output, "error": err or "Exited with code %d" % proc.returncode,
                "time_ms": elapsed}
    return {"verdict": "AC", "output": output, "error": err, "time_ms": elapsed}


def main():
    job = json.load(sys.stdin)
    setup_dirs()
    cmd, failure = compile_program(job)
    if failure:
        result = {"compile_error": failure, "runs": []}
    else:
        runs = []
        for i, stdin_text in enumerate(job["inputs"]):
            r = run_one(cmd, stdin_text, job, i)
            runs.append(r)
            if r["verdict"] != "AC":   # TLE / RE / OLE: no point running further cases
                break
        result = {"compile_error": None, "runs": runs}
    sys.stdout.write(json.dumps(result))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
