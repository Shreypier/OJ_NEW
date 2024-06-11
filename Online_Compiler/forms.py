from django import  forms
from Online_Compiler.models import submission

LANGUAGE_CHOICES=[
    ("py","python"),
    ("c","c"),
    ("cpp","c++"),
]
class submissionform(forms.ModelForm):
     language=forms.ChoiceField(choices=LANGUAGE_CHOICES)
     class Meta:
         model=submission
         fields=["language","code","input_data"]
    