# /Users/suganeshr/ROS/ROS-EDMS/ros_app/models/custom_user_models.py
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    Group,
    Permission,
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone
from datetime import datetime
from app.models.base_model.basemodel import CustomBase
from app.models.customer_model.path import user_directory_path

 
class CustomUserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must have is_staff=True.")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser=True.")

        super_admin_role, _ = Group.objects.get_or_create(name="Super Admin")

        # Create the superuser
        user = self.create_user(email, password, **extra_fields)

        # Assign the "Super Admin" group to the user
        user.groups.add(super_admin_role)
        user.save(using=self._db)

        return user


class CustomUser(AbstractBaseUser, PermissionsMixin, CustomBase):
    GENDER_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
        ("prefer_not_say", "Prefer not to say"),
    ]
    MARRIAGE_STATUS_CHOICES = [
        ("single", "Single"),
        ("married", "Married"),
        ("divorced", "Divorced"),
        ("widowed", "Widowed"),
    ]
    email = models.EmailField(unique=True, verbose_name="Email Address")
    first_name = models.CharField(
        max_length=30, verbose_name="First Name", blank=True, null=True
    )
    last_name = models.CharField(
        max_length=30, verbose_name="Last Name", blank=True, null=True
    )
    phone_number = models.TextField(blank=True, null=True)
    phone_prefix = models.CharField(max_length=10, blank=True, null=True)
    picture = models.ImageField(upload_to=user_directory_path, null=True, blank=True)
    blood_group = models.CharField(
        max_length=5, verbose_name="Blood Group", blank=True, null=True
    )
    age = models.PositiveIntegerField(blank=True, null=True)
    date_birth = models.DateTimeField(blank=True, null=True)
    address = models.CharField(
        max_length=150, verbose_name="Address", blank=True, null=True
    )
    father_name = models.CharField(
        max_length=30, verbose_name="Father's Name", blank=True, null=True
    )
    mother_name = models.CharField(
        max_length=30, verbose_name="Mother's Name", blank=True, null=True
    )
    marriage_status = models.CharField(
        max_length=10,
        choices=MARRIAGE_STATUS_CHOICES,
        verbose_name="Marital Status",
        blank=True,
        null=True,
    )
    gender = models.CharField(
        max_length=20,
        choices=GENDER_CHOICES,
        verbose_name="Gender",
        blank=True,
        null=True,
    )
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    latitude = models.DecimalField(max_digits=9, decimal_places=6,blank=True, null=True,)
    longitude= models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True,)
    objects = CustomUserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    permissions = models.ManyToManyField(Permission, related_name="users", blank=True)
 
    def get_full_name(self):
        """Returns the full name of the user."""
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return self.get_full_name()

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        permissions = [
            ("management_role_access", "Can access management-level features"),
            ("client_manege_access", "Can access client-manege features"),
        ]
        ordering = ["-created_at"]
         


class Customer(CustomBase):
    email = models.EmailField(unique=True, verbose_name="Email Address")
    phone_number = models.CharField(max_length=18, unique=True)
    phone_prefix = models.CharField(max_length=5, blank=True, null=True)
    name = models.CharField(max_length=30, verbose_name="Name", blank=True, null=True)
    gst_number = models.CharField(max_length=18, unique=True, null=True, blank=True)
    address = models.TextField(verbose_name="Address", blank=True, null=True)
    active =  models.BooleanField(default=True)

    def __str__(self):
        return self.name or self.email

    class Meta:
        verbose_name = "Customer"
        verbose_name_plural = "Customers"
        permissions = [
            ("client_role_access", "Can access client-level features"),
        ]
        ordering = ["-created_at"]