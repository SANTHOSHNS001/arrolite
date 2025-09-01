from django.db import models
from app.models.base_model.basemodel import CustomBase
from app.models.category.category_model import Category
from app.models.product.path import product_image_upload_path
from app.models.unit.unit_model import Unit


class Product(CustomBase):
    
    category = models.ForeignKey(
        "Category", on_delete=models.SET_NULL, null=True, related_name="product_category"
    )
    subcategory = models.ForeignKey(
        "SubCategory", on_delete=models.SET_NULL, null=True, related_name="product_subcategory"        
    )
    name = models.CharField(max_length=255, unique=True)
    width = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    height = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    unit = models.ForeignKey("Unit", on_delete=models.SET_NULL, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fixed_price = models.BooleanField(default=False)
    description = models.TextField(null=True, blank=True)
    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        permissions = [
            ("can_product_approver", "Can Product Approver"),
            ("can_manage_product","Can manage Product")
        ]
        ordering = ["-created_at"]
    def __str__(self):
        return f"{self.name}"
    @property
    def price_cents(self):
       return int(round(self.price * 100)) if self.price else 0
    
class ProductImage(CustomBase):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='product_images'
    )
    image = models.ImageField(upload_to=product_image_upload_path)
    alt_text = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Image for {self.product.name}"
    
 
