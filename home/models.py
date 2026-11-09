from django.db import models


# Create your models here.
class problem(models.Model):
    Name=models.CharField(max_length=400)
    level=models.CharField(max_length=50)
    desc=models.CharField(max_length=1000)
    examples=models.TextField(null=True,blank=True)
    input_constraints=models.TextField(null=True,blank=True)
    output_constraints=models.TextField(null=True,blank=True)
    constraint=models.TextField(null=True,blank=True)
    output_const=models.TextField(null=True,blank=True)
    
    def __str__(self):
        return f"{self.Name}"


class TestCase(models.Model):
    problem = models.ForeignKey(problem, on_delete=models.CASCADE, related_name="test_cases")
    input_data = models.TextField(blank=True)
    expected_output = models.TextField(blank=True)
    is_sample = models.BooleanField(
        default=False, help_text="Sample cases show input/expected/actual output to the user.")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.problem.Name} - case {self.pk}"
