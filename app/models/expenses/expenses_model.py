from django.db import models
from app.models.base_model.basemodel import CustomBase
 
 
 
from django.db import models
from django.core.exceptions import ValidationError


# =======================
# EXPENSE TYPE
# =======================
class ExpensesTypes(CustomBase):
    name = models.CharField(max_length=20, unique=True)
    active = models.BooleanField(default=True)
    description = models.TextField(null=True, blank=True)

    # Recurring fields
 

    def __str__(self):
        return self.name


# =======================
# MAIN EXPENSE (BILL)
# =======================
class Expenses(CustomBase):

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("partial", "Partial"),
        ("paid", "Paid"),
        ("overdue", "Overdue"),
        ("expired", "Expired"),
        ("cancelled", "Cancelled"),
    ]

    PAYMENT_MODE_STATUS = [
        ("transfer", "Transfer"),
        ("cash", "Cash"),
        ("upi", "UPI"),
    ]

    expenses_type = models.ForeignKey(
        "app.ExpensesTypes",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    product_name = models.CharField(max_length=255, null=True, blank=True)
    company_name = models.CharField(max_length=255, null=True, blank=True) 

    due_date = models.DateField(null=True, blank=True)
    invoice_number = models.CharField(max_length=100, null=True, blank=True)
    amount = models.FloatField()  
    description = models.TextField(null=True, blank=True)

    expense_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )
 
    def __str__(self):
        return self.product_name or "Expense"

    # =======================
    # CALCULATIONS
    # =======================
    def total_paid(self):
        return sum(item.amount for item in self.items.all())

    def balance_amount(self):
        return (self.amount or 0) - self.total_paid()

    def update_status(self):
        paid = self.total_paid()

        if paid == 0:
            self.expense_status = "pending"
        elif paid < self.amount:
            self.expense_status = "partial"
        elif paid >= self.amount:
            self.expense_status = "paid"

        self.save(update_fields=["expense_status"])


# =======================
# EXPENSE ITEMS (PAYMENTS)
# =======================
class ExpensesItems(CustomBase):
    expenses = models.ForeignKey(
        "app.Expenses",
        on_delete=models.CASCADE,
        related_name="items"
    )

    amount = models.FloatField(null=True, blank=True)
    invoice_number = models.CharField(max_length=100, null=True, blank=True)

    due_date = models.DateField(null=True, blank=True)

    receipt = models.FileField(
        upload_to="receipts/items/",
        null=True,
        blank=True
    )

    description = models.TextField(null=True, blank=True)

    payment_mode = models.CharField(
        max_length=20,
        choices=Expenses.PAYMENT_MODE_STATUS,
        default="upi",
    ) 

    def __str__(self):
        return f"{self.expenses} - {self.amount}"

    # =======================
    # VALIDATION
    # =======================
    def clean(self):
        # ✅ FIX: check expenses_id (raw FK integer) first.
        # Accessing self.expenses when expenses_id is None raises
        # RelatedObjectDoesNotExist. self.expenses_id is just None — safe.
        if not self.expenses_id:
            return
 
        parent     = self.expenses
        total_paid = sum(item.amount for item in parent.items.all())
 
        # Editing: exclude this item's own amount to avoid double-counting
        if self.pk:
            try:
                old = ExpensesItems.objects.get(pk=self.pk)
                total_paid -= old.amount
            except ExpensesItems.DoesNotExist:
                pass
 
        if total_paid + self.amount > parent.amount:
            raise ValidationError(
                f"Payment ₹{self.amount:.2f} exceeds the remaining balance "
                f"₹{parent.amount - total_paid:.2f}."
            )
 
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Auto-update parent status after every payment save
        self.expenses.update_status() 