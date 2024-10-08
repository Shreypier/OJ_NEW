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
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

@login_required
def start(request):
    all_problems = problem.objects.all()  # Fetch all problems
    context = {
        'username': request.user.username,
        'all_problems': all_problems,
    }
    return render(request, 'start.html', context)


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


def manage_problem(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create':
            # Extract form data from POST request
            name = request.POST.get('Name')
            level = request.POST.get('level')
            desc = request.POST.get('desc')
            input_test = request.POST.get('input_test')
            output_test = request.POST.get('output_test')

            # Check if any field is empty
            if not all([name, level, desc, input_test, output_test]):
                messages.error(request, "All fields are required for creating a problem.")
                return redirect('manage_problems')

            # Create a new Problem instance and save it
            new_problem = problem(
                Name=name,
                level=level,
                desc=desc,
                input_test=input_test,
                output_test=output_test
            )
            new_problem.save()
            messages.success(request, "Problem added successfully")

        elif action == 'update':
            problem_id = request.POST.get('update_id')
            if not problem_id:
                messages.error(request, "No problem ID provided for update.")
                return redirect('manage_problems')

            problem_instance = get_object_or_404(problem, id=problem_id)

            # Update the problem instance with new data
            problem_instance.Name = request.POST.get('Name', problem_instance.Name)
            problem_instance.level = request.POST.get('level', problem_instance.level)
            problem_instance.desc = request.POST.get('desc', problem_instance.desc)
            problem_instance.input_test = request.POST.get('input_test', problem_instance.input_test)
            problem_instance.output_test = request.POST.get('output_test', problem_instance.output_test)
            problem_instance.save()
            messages.success(request, "Problem updated successfully")

        elif action == 'delete':
            problem_id = request.POST.get('delete_id')
            if not problem_id:
                messages.error(request, "No problem ID provided for deletion.")
                return redirect('manage_problem')

            problem_instance = get_object_or_404(problem, id=problem_id)
            problem_instance.delete()
            messages.success(request, "Problem deleted successfully")

        return redirect('manage_problem')

    else:
        all_problems = problem.objects.all()

        context = {
            'all_problems': all_problems,
        }
        return render(request, 'problem_form.html', context)
    

def logout_user(request):
    logout(request)
    messages.info(request,'Logged Out Succesfully')
    return redirect('/accounts/login/')

def logout_employee(request):
    logout(request)
    messages.info(request,'Logged Out Succesfully')
    return redirect('/accounts/employee_login/')