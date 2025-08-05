from django import forms
from app.models.customer_model.customer_model import CustomUser, Customer

class CustomerUserRegisterFrom(forms.ModelForm):
    # specify the name of model to use
     
    class Meta:
        model = CustomUser
        fields = "__all__"
    def clean(self):
        cleaned_data = super().clean()
        print(cleaned_data)
class CustomerRegisterFrom(forms.ModelForm):
    # specify the name of model to use
     
    class Meta:
        model = Customer
        fields = ['email', 'phone_number', 'phone_prefix', 'name', 'gst_number']
  