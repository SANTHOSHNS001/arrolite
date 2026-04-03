from django import forms

from app.models.expenses.expenses_model import Expenses, ExpensesItems, ExpensesTypes
 
 

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
            'invoice_number',
            'due_date',
            'amount',
            'description'
        ]

        widgets = {
            'expenses_type': forms.Select(attrs={'class': 'form-control'}),
            'product_name': forms.TextInput(attrs={'class': 'form-control'}),
            'invoice_number': forms.TextInput(attrs={'class': 'form-control'}),
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ Required fields
        self.fields['product_name'].required = True
        self.fields['invoice_number'].required = True
        self.fields['invoice_number'].required = True
        self.fields['due_date'].required = True
        self.fields['amount'].required = True

        # ✅ Optional
        self.fields['company_name'].required = False
        self.fields['description'].required = False

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")

        if amount is None:
            raise forms.ValidationError("Amount is required")

        if amount <= 0:
            raise forms.ValidationError("Amount must be greater than 0")

        return amount
    
    
    
class ExpensesItemsForm(forms.ModelForm):
    class Meta:
        model = ExpensesItems
        fields = [
            'amount',
            'due_date',
            'payment_mode',
            'receipt',
            'description',
        ]
        widgets = {
            'amount':         forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'invoice_number': forms.TextInput(attrs={'class': 'form-control'}),
            'due_date':       forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'payment_mode':   forms.Select(attrs={'class': 'form-control'}),
            'receipt':        forms.FileInput(attrs={'class': 'form-control'}),
            'description':    forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        # Pull the parent Expenses instance out before calling super()
        # so ModelForm doesn't see an unexpected keyword.
        # Pass it from the view like:
        #   form = ExpensesItemsForm(request.POST, request.FILES, expense=expense)
        self.expense = kwargs.pop('expense', None)
        super().__init__(*args, **kwargs)

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')

        # ── Basic sanity ──────────────────────────────────────────
        if amount is None or amount <= 0:
            raise forms.ValidationError("Payment amount must be greater than 0.")

        # ── Balance check (only when parent expense is known) ─────
        if self.expense is not None:
            # If editing an existing item, subtract its current amount
            # from the already-paid total so we don't double-count it.
            already_paid = self.expense.total_paid()
            if self.instance and self.instance.pk:
                already_paid -= (self.instance.amount or 0)

            balance = (self.expense.amount or 0) - already_paid

            if amount > balance:
                raise forms.ValidationError(
                    f"Payment ₹{amount:.2f} exceeds the remaining balance "
                    f"₹{balance:.2f} (total ₹{self.expense.amount:.2f}, "
                    f"paid so far ₹{already_paid:.2f})."
                )

        return amount