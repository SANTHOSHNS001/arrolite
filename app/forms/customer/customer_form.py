from django import forms
from app.models.customer_model.customer_model import CustomUser, Customer

class CustomerUserRegisterFrom(forms.ModelForm):
    # specify the name of model to use
     
    class Meta:
        model = CustomUser
        fields = "__all__"
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # If updating an existing customer, remove password requirements
        if self.instance and self.instance.pk:
            if 'password' in self.fields:
                self.fields['password'].required = False
    def clean(self):
        cleaned_data = super().clean()
         
class CustomerRegisterFrom(forms.ModelForm):
    # specify the name of model to use
     
    class Meta:
        model = Customer
        fields = ['email', 'phone_number', 'phone_prefix', 'name', 'gst_number']

  