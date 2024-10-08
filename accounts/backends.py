from django.contrib.auth.backends import ModelBackend
from .models import user_employee
from django.contrib.auth.hashers import check_password
from django.contrib.auth.hashers import make_password

def hash_pass(employee_id):
    employee=user_employee.objects.get(employee_id=employee_id)
    password=employee.password
    if employee.DoesNotExist:
        return None
    else:
        employee.password = make_password(password)
        employee.save()
    
    
    
class EmployeeAuthBackend(ModelBackend):
    def authenticate(self,employee_id,password):
        try:
                Employee = user_employee.objects.get(employee_id=employee_id)
                hash_pass(employee_id)
                if Employee.password==password:
                    return Employee
                
        except user_employee.DoesNotExist:
                    return None 

    def get_user(self, employee_id):
        try:
            return user_employee.objects.get(employee_id=employee_id)
        except user_employee.DoesNotExist:
            return None