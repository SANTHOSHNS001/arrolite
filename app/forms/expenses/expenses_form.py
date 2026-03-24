from django import forms

from app.models.expenses.expenses_model import Expenses, ExpensesTypes
 
 

class ExpensesTypesForm(forms.ModelForm):
    class Meta:
        model = ExpensesTypes
        fields = [
            "name",
            "description",
            "active",
            # "is_recurring",
            # "recurrence_type",
            # "recurrence_day",
            # "reminder_start",
            # "reminder_end",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            # "is_recurring": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            # "recurrence_type": forms.Select(attrs={"class": "form-control"}),
            # "recurrence_day": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 31}),
            # "reminder_start": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            # "reminder_end": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }
        

class ExpensesForm(forms.ModelForm):
    class Meta:
        model = Expenses
        fields = [
            'expenses_type',
            'product_name',
            'company_name',
            'due_date',
            'amount',
            'invoice_name',
            'payment_mode',
            'invoice_number',
            'receipt',
            'description'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ Required fields
        self.fields['product_name'].required = True
        self.fields['company_name'].required = False 
        self.fields['amount'].required = True 
        # ✅ Optional fields
        self.fields['invoice_number'].required = False
        self.fields['invoice_name'].required = False
        self.fields['receipt'].required = False
        self.fields['description'].required = False
        self.fields['due_date'].required = False