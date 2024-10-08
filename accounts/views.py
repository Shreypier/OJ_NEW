from django.shortcuts import render,redirect
from django.http import HttpResponse
from django.contrib.auth import login,authenticate
from django.contrib.auth.models import User
from accounts.backends import EmployeeAuthBackend
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
    if request.method == 'POST':
        employee_id = request.POST['employee_id']
        password = request.POST['password']
        backend = EmployeeAuthBackend()
        employee = backend.authenticate( employee_id, password)
        if employee:
            login(request, backend.get_user(employee_id))
            return redirect('/home/employee/')  # Redirect to employee dashboard
        else:
                 # Login failed, show error message
            messages.info(request,'')
            return redirect ('/home/employee/')
    else:
          template=loader.get_template('employee.html')
          context={}
          return HttpResponse(template.render(context,request))

        
       
      