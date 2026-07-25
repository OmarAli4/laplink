from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class Action(models.Model):
    """
    Activity stream action model using Django's contenttypes framework.
    Tracks user actions across the entire platform (e.g., purchases,
    cart additions, order placements).
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='actions',
        on_delete=models.CASCADE,
    )
    verb = models.CharField(max_length=255)

    # Generic relation fields for targeting any model instance
    target_ct = models.ForeignKey(
        ContentType,
        blank=True,
        null=True,
        related_name='target_obj',
        on_delete=models.CASCADE,
    )
    target_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_index=True,
    )
    target = GenericForeignKey('target_ct', 'target_id')

    created = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=['-created']),
            models.Index(fields=['target_ct', 'target_id']),
        ]
        ordering = ['-created']

    def __str__(self):
        target_str = f' {self.target}' if self.target else ''
        return f'{self.user} {self.verb}{target_str}'
