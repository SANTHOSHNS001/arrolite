from django.db import models
from app.models.base_model.basemodel import CustomBase

class ISOSize(CustomBase):
    SERIES_CHOICES = [
        ('A', 'A Series'),
        ('B', 'B Series'),
        ('C', 'C Series'),
    ]

    name = models.CharField(max_length=15, unique=True)  # e.g., A4, A3
    series = models.CharField(max_length=1, choices=SERIES_CHOICES)
    width_mm = models.DecimalField(max_digits=6, decimal_places=2)
    height_mm = models.DecimalField(max_digits=6, decimal_places=2)
    class Meta:
        permissions = [
            ("can_assign_approver_isosize", "Can assign approver ISO-Size"),
            ("can_manage_isosize","Can manage ISO-Size")
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name}"