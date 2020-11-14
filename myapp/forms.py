# myapp/forms.py
from django import forms

class UIDForm(forms.Form):
    UID = forms.CharField(label='UID', min_length = 10, max_length=10)
    
