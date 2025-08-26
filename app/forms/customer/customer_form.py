from django import forms
from app.models.customer_model.customer_model import CustomUser, Customer

class CustomerUserRegisterForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=False
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput,
        required=False
    )

    class Meta:
        model = CustomUser
        fields = "__all__"  # include your model's password field

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Require passwords if creating a new user
        if not self.instance.pk:
            self.fields['password'].required = True
            self.fields['confirm_password'].required = True

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")

        confirm_password = cleaned_data.get("confirm_password")

        if self.instance.pk is None:  # Creating new user
            if not password or not confirm_password:
                raise forms.ValidationError("Password and Confirm Password are required.")
            if password != confirm_password:
                raise forms.ValidationError("Passwords do not match.")
        else:  # Updating existing user
            if password or confirm_password:  # changing password
                if not password or not confirm_password:
                    raise forms.ValidationError("Both password fields are required to change the password.")
                if password != confirm_password:
                    raise forms.ValidationError("Passwords do not match.")

        return cleaned_data

    def save(self, commit=True):
        self.cleaned_data.pop("confirm_password", None)  # ensure not saved
        return super().save(commit=commit)

         
class CustomerRegisterFrom(forms.ModelForm):
    # specify the name of model to use
    gst_number = forms.CharField(required=False)  # <--- not required
     
    class Meta:
        model = Customer
        fields = ['email', 'phone_number', 'phone_prefix', 'name', 'address','gst_number']

  