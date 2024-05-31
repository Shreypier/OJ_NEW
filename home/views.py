from django.shortcuts import render,redirect
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth import login,authenticate
from django.contrib import messages
from django.template import loader
from django.contrib.auth.decorators import login_required
from home.models import problem

# Create your views here.
 
@login_required
def starts(request):
    all_problems=problem.objects.all()
    template=loader.get_template("start.html")
    context={
        'all_problems':all_problems,
    }
    return HttpResponse(template.render(context,request))

@login_required
def problem_details(request,id):
    detail=problem.objects.get(id=id)
    template=loader.get_template("detail.html")
    context={
        'detail':detail,
    }
    return HttpResponse(template.render(context,request))


        