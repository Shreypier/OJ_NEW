from django.db import models


# Create your models here.
class problem(models.Model):
    Name=models.CharField(max_length=400)
    level=models.CharField(max_length=50)
    desc=models.CharField(max_length=1000)
    
    def __str__(self):
        return f"{self.Name}"
