from django.shortcuts import render,redirect
from django.http import HttpResponse
from django.contrib.auth import login,authenticate
from django.contrib.auth.models import User
from django.contrib import messages
from django.template import loader

def home (request):
    return render(request, 'home.html')

def register_user(request):
    
    if request.POST:
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user=User.objects.filter(username=username)
        
        if user.exists():
            messages.info(request,'Username already exists')
            return redirect("/accounts/register/")
        
        user=User.objects.create_user(username=username)
        
        user.set_password(password)
        
        user.save()
        
        messages.info(request,'User created successfully')
        return redirect('/accounts/register/')
    
    template=loader.get_template('register.html')
    context={}
    return HttpResponse(template.render(context,request))

def login_user(request):
    if request.POST:
        username=request.POST.get('username')
        password=request.POST.get('password')
        
        if not User.objects.filter(username=username).exists():
            messages.info(request,'Invalid username')
            return redirect('/accounts/login/')
        
        user= authenticate(username=username,password=password)
        
        if user is None:
            messages.info(request,'Invalid password')
            return redirect ('/accounts/login/')
        
        else:
            login(request,user)
            return redirect ('/home/')
    
    template=loader.get_template('login.html')
    context={}
    return HttpResponse(template.render(context,request))

def login_employee(request):
    """Employees are regular Django users with is_staff=True."""
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('/home/employee/')
    if request.method == 'POST':
        employee_id = request.POST.get('employee_id', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=employee_id, password=password)
        if user is not None and user.is_staff:
            login(request, user)
            return redirect('/home/employee/')
        messages.info(request, 'Invalid employee ID or password')
        return redirect('/accounts/employee_login/')
    return render(request, 'employee.html')
