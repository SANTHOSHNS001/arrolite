from django import forms
from app.models.product.product_model import Product
 
class ProductCreateForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category','price', 'unit','subcategory', 'height', 'width', 'description']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['subcategory'].required = False  # make it optional in form
        

