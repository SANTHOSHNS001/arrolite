from django.db import models
from app.models.base_model.basemodel import CustomBase
 
 
 
class ExpensesTypes(CustomBase):
    name = models.CharField(max_length=20, unique=True)
    active = models.BooleanField(default=True)
    description = models.TextField(null=True, blank=True)

    # New fields for reminders
    is_recurring = models.BooleanField(default=False, help_text="Check if this expense repeats automatically")
    recurrence_type = models.CharField(
        max_length=20,
        choices=[
            ("none", "No Recurrence"),
            ("daily", "Daily"),
            ("weekly", "Weekly"),
            ("monthly", "Monthly"),
            ("yearly", "Yearly"),
        ],
        default="none"
    )
    recurrence_day = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Day of month for recurrence (e.g., 5 = every 5th of the month)"
    )
    reminder_start = models.DateField(null=True, blank=True, help_text="Start date for reminders")
    reminder_end = models.DateField(null=True, blank=True, help_text="Optional end date for reminders")

    def __str__(self):
        return self.name  

    class Meta:
        verbose_name = "Expenses Type"
        verbose_name_plural = "Expenses Types"
        ordering = ["-created_at"]


class Expenses(CustomBase):
    STATUS_CHOICES = [
        ("pending", "Pending"),       
        ("approved", "Approved"),    
        ("paid", "Paid"),            
        ("overdue", "Overdue"),       
        ("expired", "Expired"),     
        ("cancelled", "Cancelled"),   
    ]
    expenses_type = models.ForeignKey(
        "app.ExpensesTypes", 
        on_delete=models.CASCADE, 
        blank=True, 
        null=True
    )
    name = models.CharField(
        max_length=255,    
        unique=True, 
        verbose_name="Name Add"
    )
    due_date = models.DateField(blank=True, null=True)   
    amount = models.FloatField()
    receipt = models.FileField(upload_to="receipts/")    
    description = models.TextField(null=True, blank=True)
    expense_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending" 
    )

    def __str__(self):
        return self.name  

    class Meta:
        verbose_name = "Expense"
        verbose_name_plural = "Expenses"
        permissions = [
            ("expense_manage_permission", "Can manage Expenses"),  
        ]
        ordering = ["-created_at"]