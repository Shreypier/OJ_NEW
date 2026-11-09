import os
import shutil
from types import SimpleNamespace
from unittest import skipUnless

from django.contrib.auth.models import User
from django.test import TestCase as DjangoTestCase
from django.urls import reverse

from Online_Compiler import judge
from Online_Compiler.models import Submission
from home.models import problem, TestCase


def case(inp, out, sample=False):
    return SimpleNamespace(input_data=inp, expected_output=out, is_sample=sample)


ADD = "a,b=map(int,input().split())\nprint(a+b)\n"


class JudgeEngineTests(DjangoTestCase):
    def test_accepted(self):
        r = judge.judge("python", ADD, [case("1 2\n", "3\n"), case("5 7\n", "12")])
        self.assertEqual((r.verdict, r.passed, r.total), (judge.AC, 2, 2))

    def test_wrong_answer_stops_at_first_failure(self):
        r = judge.judge("python", ADD, [case("1 2\n", "4\n"), case("1 1\n", "2\n")])
        self.assertEqual(r.verdict, judge.WA)
        self.assertEqual(len(r.cases), 1)
        self.assertEqual(r.passed, 0)

    def test_hidden_case_does_not_leak_data(self):
        r = judge.judge("python", ADD, [case("1 2\n", "4\n", sample=False)])
        self.assertEqual(r.cases[0].expected, "")
        self.assertEqual(r.cases[0].input_data, "")

    def test_whitespace_insensitive(self):
        r = judge.judge("python", "print('1   2')\n", [case("", "1 2\n\n")])
        self.assertEqual(r.verdict, judge.AC)

    def test_runtime_error(self):
        r = judge.judge("python", "raise ValueError('boom')\n", [case("", "x")])
        self.assertEqual(r.verdict, judge.RE)
        self.assertIn("boom", r.message)

    def test_infinite_loop_times_out(self):
        old = judge.TIME_LIMIT
        judge.TIME_LIMIT = 1
        try:
            r = judge.judge("python", "while True: pass\n", [case("", "x")])
        finally:
            judge.TIME_LIMIT = old
        self.assertEqual(r.verdict, judge.TLE)

    def test_output_limit(self):
        old = judge.OUTPUT_LIMIT
        judge.OUTPUT_LIMIT = 1000
        try:
            r = judge.judge("python", "print('a'*5000)\n", [case("", "x")])
        finally:
            judge.OUTPUT_LIMIT = old
        self.assertEqual(r.verdict, judge.OLE)

    def test_no_test_cases_is_system_error(self):
        self.assertEqual(judge.judge("python", "print(1)", []).verdict, judge.SE)

    def test_unsupported_language(self):
        self.assertEqual(judge.run_code("ruby", "puts 1", "").verdict, judge.SE)

    def test_workspace_is_cleaned_up(self):
        with judge.Workspace("python", "print(1)") as ws:
            d = ws.dir
            self.assertTrue(os.path.isdir(d))
        self.assertFalse(os.path.exists(d))

    @skipUnless(shutil.which("g++"), "g++ not installed")
    def test_cpp_accepted_and_compile_error(self):
        src = "#include <iostream>\nint main(){int a,b;std::cin>>a>>b;std::cout<<a+b;}\n"
        self.assertEqual(judge.judge("c++", src, [case("2 3", "5")]).verdict, judge.AC)
        self.assertEqual(judge.judge("c++", "int main(){", [case("", "")]).verdict, judge.CE)

    @skipUnless(shutil.which("gcc"), "gcc not installed")
    def test_c_accepted(self):
        src = '#include <stdio.h>\nint main(){int a,b;scanf("%d %d",&a,&b);printf("%d",a+b);}\n'
        self.assertEqual(judge.judge("c", src, [case("2 3", "5")]).verdict, judge.AC)


class SubmitViewTests(DjangoTestCase):
    def setUp(self):
        self.user = User.objects.create_user("u1", password="pw12345!")
        self.other = User.objects.create_user("u2", password="pw12345!")
        self.p = problem.objects.create(Name="Sum", level="easy", desc="add")
        TestCase.objects.create(problem=self.p, input_data="1 2", expected_output="3", is_sample=True)
        TestCase.objects.create(problem=self.p, input_data="4 5", expected_output="9")
        self.client.login(username="u1", password="pw12345!")

    def submit(self, code):
        return self.client.post(reverse("submit-page", args=[self.p.id]),
                                {"language": "python", "code": code}, follow=True)

    def test_correct_submission_saved(self):
        resp = self.submit(ADD)
        sub = Submission.objects.get()
        self.assertEqual((sub.verdict, sub.user, sub.problem, sub.passed), ("AC", self.user, self.p, 2))
        self.assertContains(resp, "Accepted")

    def test_wrong_submission(self):
        self.submit("print(0)")
        self.assertEqual(Submission.objects.get().verdict, "WA")

    def test_submit_requires_post_and_login(self):
        url = reverse("submit-page", args=[self.p.id])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.post(url, {"language": "python", "code": "x"}).status_code, 302)
        self.assertEqual(Submission.objects.count(), 0)

    def test_bad_language_rejected(self):
        self.client.post(reverse("submit-page", args=[self.p.id]), {"language": "ruby", "code": "x"})
        self.assertEqual(Submission.objects.count(), 0)

    def test_cannot_view_other_users_submission(self):
        sub = Submission.objects.create(user=self.other, problem=self.p, language="python",
                                        code="print(1)", verdict="AC")
        resp = self.client.get(reverse("submission-detail", args=[sub.id]))
        self.assertEqual(resp.status_code, 302)

    def test_run_button_uses_custom_input(self):
        resp = self.client.post(reverse("problem-details", args=[self.p.id]),
                                {"language": "python", "code": ADD, "input": "20 22"})
        self.assertContains(resp, "42")

    def test_submission_list_only_own(self):
        self.submit(ADD)
        Submission.objects.create(user=self.other, problem=self.p, language="python", code="x", verdict="WA")
        resp = self.client.get(reverse("submission-list"))
        self.assertEqual(len(resp.context["subs"]), 1)


class EmployeeTests(DjangoTestCase):
    def setUp(self):
        User.objects.create_user("emp1", password="pw12345!", is_staff=True)
        User.objects.create_user("plain", password="pw12345!")
        self.p = problem.objects.create(Name="P", level="easy", desc="d")

    def test_panel_requires_staff(self):
        url = reverse("manage_problem")
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.login(username="plain", password="pw12345!")
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.post(url, {"action": "delete", "delete_id": self.p.id})
        self.assertTrue(problem.objects.filter(id=self.p.id).exists())

    def test_employee_login(self):
        url = reverse("login-employee")
        self.client.post(url, {"employee_id": "plain", "password": "pw12345!"})
        self.assertNotIn("_auth_user_id", self.client.session)
        self.client.post(url, {"employee_id": "emp1", "password": "wrong"})
        self.assertNotIn("_auth_user_id", self.client.session)
        resp = self.client.post(url, {"employee_id": "emp1", "password": "pw12345!"})
        self.assertRedirects(resp, "/home/employee/", fetch_redirect_response=False)

    def test_staff_can_manage_problems_and_cases(self):
        self.client.login(username="emp1", password="pw12345!")
        url = reverse("manage_problem")
        self.client.post(url, {"action": "create", "Name": "N", "level": "easy", "desc": "d",
                               "input_test": "1", "output_test": "2"})
        n = problem.objects.get(Name="N")
        self.assertEqual(n.test_cases.count(), 1)
        self.client.post(url, {"action": "add_case", "problem_id": n.id,
                               "input_data": "3", "expected_output": "4"})
        self.assertEqual(n.test_cases.count(), 2)
        self.client.post(url, {"action": "update", "update_id": n.id, "Name": "", "level": "hard"})
        n.refresh_from_db()
        self.assertEqual((n.Name, n.level), ("N", "hard"))
        self.client.post(url, {"action": "delete_case", "case_id": n.test_cases.first().id})
        self.assertEqual(n.test_cases.count(), 1)
