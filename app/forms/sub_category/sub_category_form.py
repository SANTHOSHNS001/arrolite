from django import forms

from app.models.sub_category.sub_category_model import SubCategory
 
 

class SubCategoryCreateForm(forms.ModelForm):
    class Meta:
        model = SubCategory
        fields = ['name', 'description','category']