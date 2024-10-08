from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.
class employee(models.Model):
      name=models.CharField(max_length=50)
      username=models.CharField(max_length=50)
      employee_id=models.IntegerField(null=True,blank=True)
      password=models.CharField(max_length=50)
      
      def __str__(self):
        return f"{self.name}"
      
class user_employee(models.Model):
      employee_id=models.CharField( max_length=100,unique=True)
      password=models.CharField(max_length=100)
      
      def __str__(self):
        return f"{self.employee_id}"