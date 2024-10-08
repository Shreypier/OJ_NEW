from django.contrib import admin
from accounts.models import employee,user_employee
# Register your models here.
admin.site.register(employee)
admin.site.register(user_employee)
