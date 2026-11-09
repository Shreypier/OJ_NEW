from django.shortcuts import render,redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth import login,authenticate,logout
from django.contrib import messages
from django.template import loader
from django.contrib.auth.decorators import login_required, user_passes_test
from home.models import problem, TestCase
from Online_Compiler import judge
from Online_Compiler.models import Submission
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

def is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


@login_required
def start(request):
    all_problems = list(problem.objects.all())
    subs = Submission.objects.filter(user=request.user)
    solved_ids = set(subs.filter(verdict=judge.AC).values_list("problem_id", flat=True))
    attempted_ids = set(subs.values_list("problem_id", flat=True))
    for p in all_problems:
        p.level_class = (p.level or "").strip().lower()
        p.status = "solved" if p.id in solved_ids else "attempted" if p.id in attempted_ids else "todo"
    total_subs = subs.count()
    context = {
        "username": request.user.username,
        "all_problems": all_problems,
        "solved_count": len(solved_ids),
        "total_problems": len(all_problems),
        "total_subs": total_subs,
        "accepted_subs": subs.filter(verdict=judge.AC).count(),
        "recent": subs.select_related("problem")[:5],
    }
    return render(request, "start.html", context)


@login_required
def problem_details(request, id):
    detail = get_object_or_404(problem, id=id)
    detail.level_class = (detail.level or "").strip().lower()
    context = {
        "detail": detail,
        "sample_cases": detail.test_cases.filter(is_sample=True),
        "languages": judge.LANGUAGES,
        "history": Submission.objects.filter(user=request.user, problem=detail)[:10],
    }
    if request.method == "POST":
        language = request.POST.get("language", "")
        code = request.POST.get("code", "")
        input_data = request.POST.get("input", "")
        if language not in judge.LANGUAGES:
            if is_ajax(request):
                return JsonResponse({"error": "Choose a supported language."}, status=400)
            messages.error(request, "Choose a supported language.")
            result = None
        else:
            result = judge.run_code(language, code, input_data)
        if is_ajax(request):
            return JsonResponse({
                "verdict": result.verdict,
                "label": judge.VERDICT_LABELS.get(result.verdict, ""),
                "output": result.output,
                "error": result.error,
                "time_ms": result.time_ms,
            })
        output = ""
        if result is not None:
            output = result.output or result.error
        context["sub"] = {
            "language": language, "code": code, "input_data": input_data,
            "output_data": output,
            "verdict": judge.VERDICT_LABELS.get(result.verdict, "") if result else "",
            "time_ms": result.time_ms if result else 0,
        }
    return render(request, "detail.html", context)


def staff_required(view):
    """Only logged-in staff (employees) may use the problem management panel."""
    return user_passes_test(lambda u: u.is_active and u.is_staff,
                            login_url="/accounts/employee_login/")(view)


@staff_required
def manage_problem(request):
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "create":
            name = request.POST.get("Name", "").strip()
            level = request.POST.get("level", "").strip()
            desc = request.POST.get("desc", "").strip()
            input_test = request.POST.get("input_test", "")
            output_test = request.POST.get("output_test", "")
            if not all([name, level, desc, output_test.strip()]):
                messages.error(request, "Name, level, description and expected output are required.")
                return redirect("manage_problem")
            new_problem = problem.objects.create(Name=name, level=level, desc=desc)
            # The first test case is a sample, so users can see an example.
            TestCase.objects.create(problem=new_problem, input_data=input_test,
                                    expected_output=output_test, is_sample=True, order=1)
            messages.success(request, "Problem added successfully")

        elif action == "update":
            problem_id = request.POST.get("update_id")
            if not problem_id:
                messages.error(request, "No problem ID provided for update.")
                return redirect("manage_problem")
            instance = get_object_or_404(problem, id=problem_id)
            # Blank fields keep their current value instead of wiping it.
            instance.Name = request.POST.get("Name") or instance.Name
            instance.level = request.POST.get("level") or instance.level
            instance.desc = request.POST.get("desc") or instance.desc
            instance.save()
            messages.success(request, "Problem updated successfully")

        elif action == "delete":
            problem_id = request.POST.get("delete_id")
            if not problem_id:
                messages.error(request, "No problem ID provided for deletion.")
                return redirect("manage_problem")
            get_object_or_404(problem, id=problem_id).delete()
            messages.success(request, "Problem deleted successfully")

        elif action == "add_case":
            instance = get_object_or_404(problem, id=request.POST.get("problem_id"))
            expected = request.POST.get("expected_output", "")
            if not expected.strip():
                messages.error(request, "Expected output is required for a test case.")
                return redirect("manage_problem")
            order = instance.test_cases.count() + 1
            TestCase.objects.create(
                problem=instance, input_data=request.POST.get("input_data", ""),
                expected_output=expected, is_sample=bool(request.POST.get("is_sample")),
                order=order)
            messages.success(request, "Test case added")

        elif action == "delete_case":
            get_object_or_404(TestCase, id=request.POST.get("case_id")).delete()
            messages.success(request, "Test case deleted")

        return redirect("manage_problem")

    all_problems = problem.objects.prefetch_related("test_cases")
    return render(request, "problem_form.html", {"all_problems": all_problems})


def logout_user(request):
    logout(request)
    messages.info(request,'Logged Out Succesfully')
    return redirect('/accounts/login/')

def logout_employee(request):
    logout(request)
    messages.info(request,'Logged Out Succesfully')
    return redirect('/accounts/employee_login/')