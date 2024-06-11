from django.db import models

# Create your models here.
class employee(models.Model):
      name=models.CharField(max_length=50)
      username=models.CharField(max_length=50)
      employee_id=models.IntegerField(null=True,blank=True)
      password=models.CharField(max_length=50)
      
      def __str__(self):
        return f"{self.name}"