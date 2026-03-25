from django import forms
from app.models.customer_model.customer_model import CustomUser, Customer
from django.contrib.auth.models import Group
class CustomerUserRegisterForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False
    )

    # ✅ Single role selection
    groups = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Designation"
    )

    class Meta:
        model = CustomUser
        fields = "__all__"
        exclude = ["groups"]  # ❗ prevent conflict with default M2M field

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Password required only for create
        if not self.instance.pk:
            self.fields['password'].required = True
            self.fields['confirm_password'].required = True

        # Pre-fill group (edit case)
        if self.instance.pk:
            self.fields['groups'].initial = self.instance.groups.first()

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if not self.instance.pk:
            if not password or not confirm_password:
                raise forms.ValidationError("Password required.")
        if password or confirm_password:
            if password != confirm_password:
                raise forms.ValidationError("Passwords do not match.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)

        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)

        if commit:
            user.save()

            # ✅ enforce ONE group only
            group = self.cleaned_data.get("groups")
            if group:
                user.groups.clear()      # remove old roles
                user.groups.add(group)  # add single role

        return user
         
class CustomerRegisterFrom(forms.ModelForm):
    # specify the name of model to use
    
     
    class Meta:
        model = Customer
        fields = ['email', 'phone_number', 'name', 'address']

  