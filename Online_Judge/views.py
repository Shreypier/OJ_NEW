from django.shortcuts import render
from django.http import HttpResponse
from django.template import loader

def first(request):
    template=loader.get_template("first.html")
    context={}
    return HttpResponse(template.render(context,request))