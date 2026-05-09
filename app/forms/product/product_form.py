from django import forms
from app.models.product.product_model import Product
 
class ProductCreateForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category','price', 'fixed_price','unit','subcategory', 'height', 'width', 'description']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fixed_price'].required = False   
        self.fields['subcategory'].required = False   
class ProductUpdateForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category','price', 'fixed_price','unit','subcategory', 'height', 'width', 'description']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fixed_price'].required = False   
        self.fields['subcategory'].required = False
    def clean(self):
        cleaned_data = super().clean() 
        fixed_price = cleaned_data.get("fixed_price") 
        if fixed_price:
            # change None or empty to 0.0
            width = cleaned_data.get("width")
            height = cleaned_data.get("height")

            if width in [None, '', 'None']:
                cleaned_data["width"] = 0.0

            if height in [None, '', 'None']:
                cleaned_data["height"] = 0.0

        return cleaned_data
        
        

