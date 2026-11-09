from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from Online_Compiler import judge
from Online_Compiler.models import Submission
from home.models import problem

MAX_CODE_LENGTH = 100_000


def _clean_language(value):
    return value if value in judge.LANGUAGES else None


@login_required
@require_POST
def submit_page(request, id):
    """Judge the submitted code against all of the problem's test cases."""
    prob = get_object_or_404(problem, id=id)
    language = _clean_language(request.POST.get("language"))
    code = request.POST.get("code", "")
    if language is None or not code.strip():
        messages.error(request, "Choose a language and write some code before submitting.")
        return redirect("problem-details", id=prob.id)
    if len(code) > MAX_CODE_LENGTH:
        messages.error(request, "Code is too long.")
        return redirect("problem-details", id=prob.id)

    result = judge.judge(language, code, prob.test_cases.all())
    sub = Submission.objects.create(
        user=request.user, problem=prob, language=language, code=code,
        verdict=result.verdict, message=result.message, time_ms=result.time_ms,
        passed=result.passed, total=result.total,
    )
    # Per-case details are only needed for this response, so keep them in the session.
    request.session[f"cases_{sub.id}"] = [vars(c) for c in result.cases]
    return redirect("submission-detail", sub_id=sub.id)


@login_required
def submission_detail(request, sub_id):
    sub = get_object_or_404(Submission, id=sub_id)
    if sub.user_id != request.user.id and not request.user.is_staff:
        messages.error(request, "You can only view your own submissions.")
        return redirect("submission-list")
    cases = request.session.pop(f"cases_{sub.id}", [])
    return render(request, "submit.html", {
        "sub": sub, "cases": cases, "accepted": sub.verdict == judge.AC,
    })


@login_required
def submission_list(request):
    subs = Submission.objects.filter(user=request.user).select_related("problem")
    prob = None
    problem_id = request.GET.get("problem")
    if problem_id and problem_id.isdigit():
        prob = problem.objects.filter(id=problem_id).first()
        if prob:
            subs = subs.filter(problem=prob)
    return render(request, "submissions.html", {"subs": subs[:200], "prob": prob})
