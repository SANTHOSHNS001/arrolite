from django.db import models
from app.models.base_model.basemodel import CustomBase

class Unit(CustomBase):
    name = models.CharField(max_length=50, unique=True)
    symbol = models.CharField(max_length=15, unique=True)
    to_mm_factor = models.FloatField(default=1)

    UNIT_TO_MM_MAP = {
        "mm": 1,
        "cm": 10,
        "dm": 100,
        "m": 1000,
        "km": 1_000_000,
        "um": 0.001,
        "µm": 0.001,
        "nm": 0.000001,
        "in": 25.4,
        "ft": 304.8,
        "yd": 914.4,
        "mi": 1_609_344,
        "nmi": 1_852_000,
        "mil": 0.0254,
    }

    def save(self, *args, **kwargs):
        symbol = self.symbol.lower()

        if symbol in self.UNIT_TO_MM_MAP:
            self.to_mm_factor = self.UNIT_TO_MM_MAP[symbol]
        else:
            raise ValueError(f"Unit '{self.symbol}' not supported")

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.symbol}) - {self.to_mm_factor} mm"
