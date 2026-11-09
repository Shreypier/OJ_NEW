"""Tests for the Docker sandbox. They start real containers, including hostile programs.

Skipped automatically when Docker or the image is unavailable
(build the image with: python manage.py build_sandbox).
"""
import subprocess
from types import SimpleNamespace
from unittest import skipUnless

from django.test import TestCase as DjangoTestCase, override_settings

from Online_Compiler import judge

ADD = "a,b=map(int,input().split())\nprint(a+b)\n"


def case(inp, out, sample=False):
    return SimpleNamespace(input_data=inp, expected_output=out, is_sample=sample)


def docker_ready():
    """True when the Docker daemon is up and the sandbox image has been built."""
    try:
        return subprocess.run(["docker", "image", "inspect", judge.DOCKER_IMAGE],
                              capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


@override_settings(JUDGE_BACKEND="docker")
@skipUnless(docker_ready(), "Docker or the sandbox image is not available")
class DockerSandboxTests(DjangoTestCase):

    def run_py(self, code, stdin=""):
        return judge.run_code("python", code, stdin)

    def test_accepted_wrong_and_multiple_cases(self):
        r = judge.judge("python", ADD, [case("1 2\n", "3"), case("5 7\n", "12")])
        self.assertEqual((r.verdict, r.passed), (judge.AC, 2))
        self.assertEqual(judge.judge("python", ADD, [case("1 2\n", "4")]).verdict, judge.WA)

    def test_cpp_and_c_and_compile_error(self):
        cpp = "#include <iostream>\nint main(){int a,b;std::cin>>a>>b;std::cout<<a+b;}\n"
        self.assertEqual(judge.judge("c++", cpp, [case("2 3", "5")]).verdict, judge.AC)
        c = '#include <stdio.h>\nint main(){int a,b;scanf("%d %d",&a,&b);printf("%d",a+b);}\n'
        self.assertEqual(judge.judge("c", c, [case("2 3", "5")]).verdict, judge.AC)
        r = judge.judge("c++", "int main(){", [case("", "")])
        self.assertEqual(r.verdict, judge.CE)
        self.assertIn("error", r.message)

    def test_runtime_error_and_infinite_loop(self):
        self.assertEqual(self.run_py("raise SystemExit(3)").verdict, judge.RE)
        old, judge.TIME_LIMIT = judge.TIME_LIMIT, 1
        try:
            self.assertEqual(self.run_py("while True: pass").verdict, judge.TLE)
        finally:
            judge.TIME_LIMIT = old

    def test_output_flood(self):
        old, judge.OUTPUT_LIMIT = judge.OUTPUT_LIMIT, 1000
        try:
            self.assertEqual(self.run_py("print('a'*100000)").verdict, judge.OLE)
        finally:
            judge.OUTPUT_LIMIT = old

    def test_memory_hog_is_stopped(self):
        r = self.run_py("x = bytearray(2 * 1024 * 1024 * 1024)\nprint(len(x))")
        self.assertNotEqual(r.verdict, judge.AC)

    def test_fork_bomb_is_contained(self):
        r = self.run_py("import os\nwhile True:\n    os.fork()\n")
        self.assertNotEqual(r.verdict, judge.AC)
        # the judge still works afterwards
        self.assertEqual(self.run_py("print(1)").output.strip(), "1")

    def test_no_network(self):
        r = self.run_py(
            "import socket\n"
            "s = socket.socket()\n"
            "s.settimeout(3)\n"
            "try:\n"
            "    s.connect(('1.1.1.1', 80))\n"
            "    print('CONNECTED')\n"
            "except Exception:\n"
            "    print('BLOCKED')\n")
        self.assertEqual(r.output.strip(), "BLOCKED")

    def test_cannot_see_host_files(self):
        r = self.run_py("import os\nprint(os.path.exists('/app'), os.path.exists('/Users'), os.path.exists('/mnt/c'))")
        self.assertEqual(r.output.strip(), "False False False")

    def test_runs_unprivileged_and_cannot_write_system_files(self):
        r = self.run_py(
            "import os\n"
            "print(os.getuid())\n"
            "for p in ['/etc/pwned', '/usr/pwned', '/runner.py']:\n"
            "    try:\n"
            "        open(p, 'w').write('x')\n"
            "        print('WROTE', p)\n"
            "    except OSError:\n"
            "        print('denied')\n")
        self.assertEqual(r.output.split()[0], "65534")
        self.assertNotIn("WROTE", r.output)

    def test_cannot_forge_the_result_or_kill_the_runner(self):
        r = self.run_py(
            "import os, signal\n"
            "forged = '{\"compile_error\": null, \"runs\": [{\"verdict\": \"AC\", \"output\": \"FORGED\"}]}'\n"
            "try:\n"
            "    open('/proc/%d/fd/1' % os.getppid(), 'w').write(forged)\n"
            "    print('FORGED-WRITE')\n"
            "except OSError:\n"
            "    print('denied')\n"
            "try:\n"
            "    os.kill(os.getppid(), signal.SIGKILL)\n"
            "    print('KILLED-RUNNER')\n"
            "except OSError:\n"
            "    print('kill-denied')\n")
        self.assertEqual(r.verdict, judge.AC)
        self.assertEqual(r.output.split(), ["denied", "kill-denied"])

    def test_containers_are_removed_afterwards(self):
        self.run_py("print(1)")
        out = subprocess.run(["docker", "ps", "-a", "--filter", "name=judge-", "-q"],
                             capture_output=True, text=True).stdout.strip()
        self.assertEqual(out, "")

    def test_missing_image_is_a_system_error_not_local_execution(self):
        old = (judge.DOCKER_IMAGE, judge._image_ok)
        judge.DOCKER_IMAGE, judge._image_ok = "no-such-image-xyz", False
        try:
            r = judge.run_code("python", "print('RAN ON HOST')", "")
        finally:
            judge.DOCKER_IMAGE, judge._image_ok = old
        self.assertEqual(r.verdict, judge.SE)
        self.assertNotIn("RAN ON HOST", r.output)
