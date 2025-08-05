from decimal import Decimal
from django.db import models
from app.models.base_model.basemodel import CustomBase
from app.models.category.category_model import Category
from app.models.customer_model.customer_model import CustomUser
from app.models.product.path import product_image_upload_path
from app.models.product.product_model import Product
from app.models.unit.unit_model import Unit


class Quotation(CustomBase):
    STATUS_CHOICES = [
            ("draft", "Draft"),
            ("sent", "Sent to Customer"),
            ("pending", "Pending"),
            ("waiting_manager_confirmation", "Waiting Manager Confirmation"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
            ("accepted_by_customer", "Accepted by Customer"),
            ("expired", "Expired"),
        ]
    customer = models.ManyToManyField(
        "Customer",
        related_name="quotation_customers",
        blank=True,
    )

    approver = models.ForeignKey(
        "CustomUser",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='quotation_approvers'
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
    class Meta:
        verbose_name = "Quotation"
        verbose_name_plural = "Quotations"
        permissions = [
            ("can_approve_quotation", "Can approve quotation"),
            ("can_assign_approver_quotation", "Can assign approver"),
            ("can_manage_quotaion","Can manage Quotaions")
        ]
        ordering = ["-created_at"]
    def __str__(self):
        return f"Quotation #{self.invoice_number}-{self.id}"
    @property
    def to_json(self):
        return {
            "id": self.id,
            "invoice_number": self.invoice_number,
            "request_date": self.request_date.strftime("%Y-%m-%d %H:%M:%S") if self.request_date else None,
            "description": self.description,
            "customers": [user.name for user in self.customer.all()],
            "items": [item.to_json for item in self.items.all()]
        }
    @property
    def items_to_json(self):
        return {
            "items": [item.to_json for item in self.items.all()]
        }

    @property
    def total_cost(self):
        """Sum of all item costs (before discount)"""
        return sum(
            (item.unit_cost or Decimal("0.00")) 
            for item in self.items.all()
        )

    @property
    def discount_amount(self):
        total = self.total_cost or Decimal("0.00")
        discount = Decimal(str(self.discount or 0))
        return (discount / Decimal("100.00")) * total
      

    @property
    def payable_total(self):
        """Total after subtracting discount"""
        return self.total_cost - self.discount_amount
        
        
    
    
class QuotationItem(CustomBase):  # Singular name is conventional
    quotation = models.ForeignKey(
        Quotation, on_delete=models.CASCADE, related_name='items'
    )

    product = models.ForeignKey(  # changed from ManyToManyField to ForeignKey
        "Product",
        on_delete=models.CASCADE,
        related_name="quotation_items"
    )
    request_date = models.DateTimeField(null=True, blank=True)
    quantity = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    unit = models.ForeignKey("Unit", on_delete=models.SET_NULL, null=True, blank=True)
    width = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    height = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    
    class Meta:
            ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.name} (x{self.quantity})"
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
        
    
     
        
 
    
 
