from django.db import models
from django.utils import timezone
 
from django.conf import settings
 
 
 
class ActiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def soft_deleted(self):
        return super().get_queryset().filter(is_deleted=True)

    def inactive(self):
        return super().get_queryset().filter(status=False)

    def active(self):
        return super().get_queryset().filter(status=True, is_deleted=False)

class CustomBase(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='%(class)s_creator')
    updater = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='%(class)s_updater')
 
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)
    deleted_by = models.ForeignKey(
       settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="deleted_%(class)s_set"
    )
    status = models.BooleanField(default=True)
    slug = models.SlugField(max_length=255, blank=True, null=True)

    objects = models.Manager()
    active_objects = ActiveManager()

    class Meta:
        abstract = True


    def delete(self, user=None):
        non_deleted_related_objects = self.get_non_deleted_related_objects()
        if non_deleted_related_objects:
            raise ValueError(
                f"Cannot delete {self.__class__.__name__} instance because it is mapped to non-deleted related objects: {non_deleted_related_objects}. Please delete them first."
            )

        if not self.is_deleted:
            for field in self._meta.fields:
                if field.unique and field.name != self._meta.pk.name:
                    original_value = getattr(self, field.name)
                    if original_value:
                        counter = self.__class__.objects.filter(
                            **{f"{field.name}__startswith": f"{original_value}-deleted-"}
                        ).count() + 1
                        new_value = f"{original_value}-deleted-{counter}"
                        setattr(self, field.name, new_value)

            self.is_deleted = True
            self.deleted_at = timezone.now()
            self.deleted_by = user
            self.save()

    def get_non_deleted_related_objects(self):
        related_fields = [
            field for field in self._meta.get_fields()
            if (field.one_to_many or field.one_to_one) and not field.auto_created
        ]

        non_deleted_objects = []

        for field in related_fields:
            related_manager = getattr(self, field.get_accessor_name())
            if hasattr(related_manager, 'all'):
                for obj in related_manager.all():
                    if hasattr(obj, 'is_deleted') and not obj.is_deleted:
                        non_deleted_objects.append(obj)
            else:
                obj = related_manager
                if obj and hasattr(obj, 'is_deleted') and not obj.is_deleted:
                    non_deleted_objects.append(obj)
        return non_deleted_objects


    def hard_delete(self):
        non_deleted_related_objects = self.get_non_deleted_related_objects()
        if non_deleted_related_objects:
            raise ValueError(
                f"Cannot hard delete {self.__class__.__name__} instance because it is mapped to non-deleted related objects: {non_deleted_related_objects}."
            )
        super().delete()

    def restore(self):
        if self.is_deleted:
            for field in self._meta.fields:
                # Check for unique fields excluding the primary key.
                if field.unique and field.name != self._meta.pk.name:
                    current_value = getattr(self, field.name)
                    # If the value contains the deletion suffix, remove it.
                    if current_value and '-deleted-' in current_value:
                        original_value = current_value.rsplit('-deleted-', 1)[0]
                        setattr(self, field.name, original_value)
            self.is_deleted = False
            self.deleted_at = None
            self.deleted_by = None  # Clear deleted_by on restore
            self.save()

    def deactivate(self):
        if self.is_deleted:
            raise ValueError("Cannot deactivate a soft-deleted item. Restore it first.")
        if self.status:
            self.status = False
            self.save()

    def activate(self):
        if self.is_deleted:
            raise ValueError("Cannot activate a soft-deleted item. Restore it first.")
        if not self.status:
            self.status = True
            self.save()

    def is_active(self):
        return self.status and not self.is_deleted