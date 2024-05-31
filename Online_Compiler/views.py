from django.shortcuts import render
from Online_Compiler.models import User_Input
from django.http import HttpResponse
from django.template import loader
from pathlib import Path
from django.conf import settings
import uuid
import subprocess
# Create your views here.


def problem_page(request):
    if request.method=='POST':
         language=request.POST['language']
         code=request.POST['code']
         input_data=request.POST['input']
         output_data=run_code(language,code,input_data)
         new=User_Input(language=language, code=code, input_data=input_data,output_data=output_data) 
         new.save()
         sub=new 
         context={
             'sub':sub
         }
         return render(request,'result.html',context)
    
    else:
        
        template=loader.get_template("result.html")
        context={}
        return HttpResponse(template.render(context,request))
    
def run_code(language,code,input):
    project_path=Path(settings.BASE_DIR)
    
    directories =["codes","inputs","outputs"]
    
    for directory in directories:
        dir_path=project_path/directory
        if not dir_path.exists():
            dir_path.mkdir(parents=True,exist_ok=True)
            
    codes_dir=project_path/ "codes"
    inputs_dir=project_path/ "inputs"
    outputs_dir=project_path/ "outputs"
    
    unique=str(uuid.uuid4())
    if(language=="python"):
        code_file_name=f"{unique}.{"py"}"
    else :
        code_file_name=f"{unique}.{language}"
    
    input_file_name=f'{unique}.txt'
    output_file_name=f'{unique}.txt'
    
    code_file_path=codes_dir/code_file_name
    input_file_path=inputs_dir/input_file_name
    output_file_path=outputs_dir/output_file_name
    
    with open(code_file_path,'w') as code_file:
        code_file.write(code)
        
    with open(input_file_path,'w') as input_file:
        input_file.write(input)
    
    with open(output_file_path,'w') as output_file:
        pass
    
    if language =="c++":
        executable_path=codes_dir/unique
        
        compiler_result=subprocess.run(
          ["g++",str(code_file_path),"-o",str(executable_path)]  
        )
        
        if compiler_result.returncode==0:
            with open(input_file_path,'r') as input_file:
                with open(output_file_path,'w') as output_file:
                    subprocess.run(
                       [str(executable_path)], 
                       stdin=input_file,
                       stdout=output_file,
                    )
    if language=="python":
           with open(input_file_path,'r') as input_file:
                with open(output_file_path,'w') as output_file:
                    subprocess.run(
                       ["python3 ",str(code_file_path)], 
                       stdin=input_file,
                       stdout=output_file,
                    )
                    
    if language =="c":
        executable_path=codes_dir/unique
        
        compiler_result=subprocess.run(
          ["gcc",str(code_file_path),"-o",str(executable_path)]  
        )
        
        if compiler_result.returncode==0:
            with open(input_file_path,'r') as input_file:
                with open(output_file_path,'w') as output_file:
                    subprocess.run(
                       [str(executable_path)], 
                       stdin=input_file,
                       stdout=output_file,
                    )
    
    with open(output_file_path,'r') as output_file:
        output_data=output_file.read()
     
    return output_data