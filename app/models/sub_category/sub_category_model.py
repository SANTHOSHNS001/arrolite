from django.db import models
from app.models.base_model.basemodel import CustomBase
from app.models.category.category_model import Category

 
class SubCategory(CustomBase):
    name = models.CharField(max_length=255, unique=True)
    category = models.ForeignKey(
        "Category", on_delete=models.SET_NULL, null=True, related_name="subcategorys"
    )
    description = models.TextField(blank=True, null=True)
    code = models.CharField(max_length=255, blank=True, null=True)
    is_consumable = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Sub-Category"
        verbose_name_plural = "Sub-Categorys"
        ordering = ["-created_at"]
        permissions = [("manage_subcategory", "Can manage Subcategories"),
                       ("manage_subcategory_approver", "Can SubCategorie Approver")
                       ]
         
        
        

    def __str__(self):
        return f"{self.name}"