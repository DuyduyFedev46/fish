"""Kho (V1: đúng 1 kho)."""
from django.db import models


class Warehouse(models.Model):
    """V1: đúng 1 kho duy nhất."""

    name = models.CharField("Tên kho", max_length=120, unique=True)
    is_group = models.BooleanField("Là nhóm kho", default=False)

    class Meta:
        verbose_name = "Kho"
        verbose_name_plural = "Kho"

    def __str__(self):
        return self.name
