from django.db import models

class CodePrefix(models.Model):
    client = models.CharField(max_length=36, null=True, blank=True)

    module = models.CharField(max_length=100)   # app name (staff, students)
    form = models.CharField(max_length=100)     # model name (Employee, Student)

    prefix = models.CharField(max_length=10)
    current_number = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Code Prefix"
        verbose_name_plural = "Code Prefixes"

    def __str__(self):
        return f"{self.module}.{self.form} → {self.prefix}"
