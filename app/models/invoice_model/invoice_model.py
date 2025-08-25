from decimal import Decimal
from django.db import models
from app.models.base_model.basemodel import CustomBase
from app.models.category.category_model import Category
from app.models.customer_model.customer_model import CustomUser
from app.models.iso_series.iso_series_model import ISOSize
from app.models.product.path import product_image_upload_path
from app.models.product.product_model import Product
from app.models.unit.unit_model import Unit


class Invoice(CustomBase):
    STATUS_CHOICES = [
            ("draft", "Draft"),
            ("sent", "Sent to Customer"),
            ("pending", "Pending"),
            ("waiting_manager_confirmation", "Waiting Manager Confirmation"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
            ("expired", "Expired"),
            ("unpaid", "Unpaid"),
            ("pending_payment", "Pending Payment"),
            ("advance_paid", "Advance Paid"),   
            ("partially_paid", "Partially Paid"),
            ("paid", "Paid"),
            ("overdue", "Overdue"),
            ("refunded", "Refunded"),
            ("payment_failed", "Payment Failed"),
        ]
    customer = models.ForeignKey(
        "Customer",
        related_name="invoice_customers",
         on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    approver = models.ForeignKey(
        "CustomUser",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='invoice_approvers'
    )
    request_date = models.DateTimeField(null=True, blank=True)
    invoice_number = models.CharField(max_length=20, unique=True)
    description = models.TextField(null=True, blank=True)
    approver_status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="pending"
    )
    discount = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0.00,
        null=True,
        blank=True,
        help_text="Discount amount or percentage to apply"
    )
    is_percentage = models.BooleanField(
    default=False,
    help_text="If true, discount_value is a percentage instead of a fixed amount"
)
    isosize = models.ForeignKey("ISOSize", on_delete=models.SET_NULL, null=True, blank=True)
    advance_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    class Meta:
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"
        permissions = [
            ("can_approve_invoice", "Can approve Invoice"),
            ("can_manage_invoice","Can manage Invoice")
        ]
        ordering = ["-created_at"]
    def __str__(self):
        return f"{self.invoice_number}"
    @property
    def to_json(self):
        return {
            "id": self.id,
            "invoice_number": self.invoice_number,
            "request_date": self.request_date.strftime("%Y-%m-%d %H:%M:%S") if self.request_date else None,
            "description": self.description,
            "customers": [user.name for user in self.customer.all()],
            "items": [item.to_json for item in self.invoiceitems.all()]
        }
    @property
    def items_to_json(self):
        return {
            "items": [item.to_json for item in self.invoiceitems.all()]
        }

    @property
    def total_cost(self):
        """
        Sum of all item costs (before discount).
        IMPORTANT: multiply unit_cost * quantity (this was missing before).
        """
        return sum(
            (item.unit_cost or Decimal("0.00"))  
            for item in self.invoiceitems.all()
        ) or Decimal("0.00")

    @property
    def discount_amount(self):
        """
        If is_percentage == True: discount% of total
        Else: fixed discount amount
        """
        total = self.total_cost or Decimal("0.00")
        discount = Decimal(str(self.discount or 0))
        if self.is_percentage:
            return (discount / Decimal("100.00")) * total
        return discount

    @property
    def payable_total(self):
        """Total after discount (before payments)."""
        total = self.total_cost or Decimal("0.00")
        return total - (self.discount_amount or Decimal("0.00"))

    @property
    def total_paid(self):
        """Total received from customer (advance + later payments)."""
        return (self.advance_amount or Decimal("0.00")) + (self.amount_paid or Decimal("0.00"))

    @property
    def balance_due(self):
        """Remaining amount customer still owes (can go negative if overpaid)."""
        return (self.payable_total or Decimal("0.00")) - self.total_paid
        
            
class InvoiceItem(CustomBase):  # Singular name is conventional
    invoice = models.ForeignKey(
        "Invoice", on_delete=models.CASCADE, related_name='invoiceitems'
    )
    product = models.ForeignKey(  # changed from ManyToManyField to ForeignKey
        "Product",
        on_delete=models.CASCADE,
        related_name="invoice_items"
    )
    quantity = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    unit = models.ForeignKey("Unit", on_delete=models.SET_NULL, null=True, blank=True)
    width = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    height = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    
    class Meta:
            ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.name}-status={self.is_deleted}"
    @property
    def to_json(self):
        return {
            "id": self.id,
            "product_name": self.product.name,
            "product_code": self.product.code if hasattr(self.product, "code") else "",
            "quantity": self.quantity,
            "unit_cost": float(self.unit_cost or 0),
            "total_cost": float((self.unit_cost or 0) * self.quantity),
            "unit": self.unit.symbol if self.unit else None,
            "width": float(self.width or 0),
            "height": float(self.height or 0),
            "description": self.description,
        }
        