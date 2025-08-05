from django import forms
from app.models.category.category_model import Category
 

class CategoryCreateForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description','status']