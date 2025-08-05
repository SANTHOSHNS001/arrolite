
import os
from datetime import datetime

from django.db import models
from django.utils.text import slugify


def user_directory_path(instance: models.Model, filename: str) -> str:
    now = datetime.now()
    date_format = now.strftime("%d%m%y_%H%M")
    user_name = f"{instance.first_name}_{instance.last_name}"
    new_filename = f"{user_name}_{date_format}.png"
    return f"user_pictures/{new_filename}"