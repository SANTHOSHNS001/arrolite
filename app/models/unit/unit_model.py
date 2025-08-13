from django.db import models
from app.models.base_model.basemodel import CustomBase

class Unit(CustomBase):
    name = models.CharField(max_length=50, unique=True)  # e.g., Centimeters
    symbol = models.CharField(max_length=15, unique=True)  # e.g., cm, in, ft
    class Meta:
        verbose_name = "unit"
        verbose_name_plural = "units"
        ordering = ["-created_at"]
        permissions = [("manage_unit", "Can manage unit")]
                       
    def __str__(self):
        return f"{self.name} ({self.symbol})"
