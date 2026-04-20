
from django.db import models
from app.models.base_model.basemodel import CustomBase


class Category(CustomBase):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    product_code = models.CharField(max_length=255, blank=True, null=True)
    is_consumable = models.BooleanField(default=False)
    is_tagged = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Product Category"
        verbose_name_plural = "Product Categories"
        permissions = [("manage_category", "Can manage categories"),
                       ("manage_category_approver", "Can categorie Approver")
                       ]
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "is_deleted"],
                name="unique_category_name_is_deleted",
            )
        ]

    def __str__(self):
        return f"{self.name}"