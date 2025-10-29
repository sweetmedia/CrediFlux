"""
Core abstract models for reusability across apps
"""
from django.db import models
from django.contrib.auth import get_user_model
import uuid


class TimeStampedModel(models.Model):
    """
    Abstract model providing created_at and updated_at timestamps
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    """
    Abstract model using UUID as primary key
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class AuditModel(TimeStampedModel):
    """
    Abstract model providing audit fields (who created/modified)
    """
    created_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        related_name='%(class)s_created',
        editable=False
    )
    updated_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        related_name='%(class)s_updated',
        editable=False
    )

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """
    Abstract model providing soft delete functionality
    """
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        """Soft delete the object"""
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        """Restore soft deleted object"""
        self.is_deleted = False
        self.deleted_at = None
        self.save()
