

from django.db import models

from app.models.base_model.basemodel import CustomBase


class Unit(CustomBase):
    name = models.CharField(max_length=50, unique=True)
    symbol = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return f"{self.name} ({self.symbol})"
