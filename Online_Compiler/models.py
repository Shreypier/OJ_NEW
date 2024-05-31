from django.db import models

# Create your models here.
class submission(models.Model):
    language=models.CharField(max_length=50)
    code=models.TextField(null=True,blank=True)
    input_data=models.TextField(null=True,blank=True)
    output_data=models.TextField(null=True,blank=True)
    time_stamp=models.DateTimeField(auto_now_add=True)

class User_Input(models.Model):
    language=models.CharField(max_length=50)
    code=models.TextField(null=True,blank=True)
    input_data=models.TextField(null=True,blank=True)
    output_data=models.TextField(null=True,blank=True)
    time_stamp=models.DateTimeField(auto_now_add=True)