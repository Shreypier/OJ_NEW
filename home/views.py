from django.shortcuts import render,redirect
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth import login,authenticate,logout
from django.contrib import messages
from django.template import loader
from django.contrib.auth.decorators import login_required
from home.models import problem
from Online_Compiler.models import User_Input
from Online_Compiler.views import run_code
# Create your views here.
@login_required
def starts(request):
    user=User.objects.filter()
    template=loader.get_template("start.html")
    context={
        'user':user,
    }
    return HttpResponse(template.render(context,request))  

@login_required
def problems(request):
    all_problems=problem.objects.all()
    template=loader.get_template("problem.html")
    context={
        'all_problems':all_problems,
    }
    return HttpResponse(template.render(context,request))

@login_required
def problem_details(request,id):
     if request.method=='POST':
         language=request.POST['language']
         code=request.POST['code']
         input_data=request.POST['input']
         output_data=run_code(language,code,input_data)
         new=User_Input(language=language, code=code, input_data=input_data,output_data=output_data) 
         new.save()
         sub=new 
         detail=problem.objects.get(id=id)
         context={
             'sub':sub,
             'detail':detail,
        }
         return render(request,'detail.html',context)
     detail=problem.objects.get(id=id)
     template=loader.get_template("detail.html")
     context={
        'detail':detail,
     }
     return HttpResponse(template.render(context,request))

@login_required
def add_problem(request):
    if request.method=='POST':
        Name=request.POST['Name']
        level=request.POST['level']
        desc=request.POST['desc']
        input_test=request.POST['input_test']
        output_test=request.POST['output_test']
            
        new=problem(Name=Name,level=level,desc=desc,input_test=input_test,output_test=output_test)
        new.save()
        context={}
        return render(request,'problem_form.html',context)
    
    else:
        
        template=loader.get_template("problem_form.html")
        context={}
        return HttpResponse(template.render(context,request))
    

def logout_user(request):
    logout(request)
    messages.info(request,'Logged Out Succesfully')
    return redirect('/accounts/login/')