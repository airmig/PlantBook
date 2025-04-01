from django import forms
from .models import Plant

class PlantForm(forms.ModelForm):
    class Meta:
        model = Plant
        fields = ['name', 'scientific_name', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'scientific_name': forms.TextInput(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'})
        }
        labels = {
            'name': 'Plant Name',
            'scientific_name': 'Scientific Name',
            'image': 'Plant Image'
        }
        help_texts = {
            'scientific_name': 'Optional: Enter the scientific name of your plant',
            'image': 'Upload a clear image of your plant'
        } 