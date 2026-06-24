from django.db import models
from django.conf import settings
from core.models import Client
from staff.models import UserRole
from django.db import transaction, models
from django.db.models import F



class ModuleELearning(models.Model):
    module_id = models.AutoField(primary_key=True)
    module_name = models.CharField(max_length=255)  # unique globally
    description = models.TextField(null=True, blank=True)
    icon = models.CharField(max_length=100, null=True, blank=True)
    order = models.IntegerField(default=0)

    created_by = models.IntegerField(null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_by = models.IntegerField(null=True, blank=True)
    updated_date = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        # We use a transaction to ensure all updates happen together
        with transaction.atomic():
            if not self.pk:  # CREATION
                # Shift others up to make room
                ModuleELearning.objects.filter(order__gte=self.order).update(order=models.F('order') + 1)
            else:  # UPDATE
                old_instance = ModuleELearning.objects.get(pk=self.pk)
                if old_instance.order != self.order:
                    if self.order < old_instance.order:
                        # Moving "up" the list (e.g., from 5 to 2)
                        # Shift records between the new and old order down
                        ModuleELearning.objects.filter(
                            order__gte=self.order, 
                            order__lt=old_instance.order
                        ).exclude(pk=self.pk).update(order=models.F('order') + 1)
                    else:
                        # Moving "down" the list (e.g., from 2 to 5)
                        # Shift records between the old and new order up
                        ModuleELearning.objects.filter(
                            order__gt=old_instance.order, 
                            order__lte=self.order
                        ).exclude(pk=self.pk).update(order=models.F('order') - 1)
            
            super().save(*args, **kwargs)

    def __str__(self):
        return self.module_name

class FormELearning(models.Model):
    form_id = models.AutoField(primary_key=True)
    module = models.ForeignKey(
        ModuleELearning,
        on_delete=models.PROTECT,
        db_column="module_id",
        related_name="forms",
    )
    form_name = models.CharField(max_length=255)           # unique per module
    route = models.CharField(max_length=255)               # e.g., "/manage-enquiries"
    description = models.TextField(null=True, blank=True)
    icon = models.CharField(max_length=100, null=True, blank=True)
    order = models.IntegerField(default=0)

    created_by = models.IntegerField(null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_by = models.IntegerField(null=True, blank=True)
    updated_date = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        #db_table = "Setting_FormELearning"
        unique_together = (("module", "form_name"),)
    
    def save(self, *args, **kwargs):
        with transaction.atomic():
            # Filter by module so we only reorder forms within the same module
            base_qs = FormELearning.objects.filter(module=self.module)
            
            if not self.pk:
                base_qs.filter(order__gte=self.order).update(order=models.F('order') + 1)
            else:
                old_instance = FormELearning.objects.get(pk=self.pk)
                if old_instance.order != self.order:
                    if self.order < old_instance.order:
                        base_qs.filter(
                            order__gte=self.order, 
                            order__lt=old_instance.order
                        ).exclude(pk=self.pk).update(order=models.F('order') + 1)
                    else:
                        base_qs.filter(
                            order__gt=old_instance.order, 
                            order__lte=self.order
                        ).exclude(pk=self.pk).update(order=models.F('order') - 1)
            
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.form_name} ({self.module.module_name})"

class ClientPermissionControl(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    
    can_create = models.BooleanField(default=False)
    can_read = models.BooleanField(default=True)
    can_update = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.client.client_name} Permissions"
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['client'], name='unique_client_permission')
        ]



# class ModuleFormPermission(models.Model):
#     # module = models.ForeignKey(ModuleELearning, on_delete=models.CASCADE)
#     # form = models.ForeignKey(FormELearning, on_delete=models.CASCADE)
#     # role = models.ForeignKey(UserRole,on_delete=models.CASCADE, null=True, blank=True)
#     module_id = models.IntegerField(null=True, blank=True)
#     form_id = models.IntegerField(null=True, blank=True)
#     role_id = models.IntegerField(null=True, blank=True)

#     can_create = models.BooleanField(default=False)
#     can_read = models.BooleanField(default=True)
#     can_update = models.BooleanField(default=False)
#     can_delete = models.BooleanField(default=False)

#     is_active = models.BooleanField(default=True)

#     created_at = models.DateTimeField(auto_now_add=True)


import json

class ModuleFormPermission(models.Model):
    role_id = models.IntegerField(unique=True)

    # 🔥 Store all permissions in JSON
    permissions = models.JSONField(default=list)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


    
class UserRoleELearning(models.Model):
    permission_id = models.AutoField(primary_key=True)
    client_id = models.IntegerField()
    branch_id = models.IntegerField(null=True, blank=True)
    user_role = models.ForeignKey(UserRole, on_delete=models.PROTECT)

    module_id = models.IntegerField()
    form_id = models.IntegerField()

    u_read = models.BooleanField(default=False)
    u_write = models.BooleanField(default=False)
    u_delete = models.BooleanField(default=False)
    u_view = models.BooleanField(default=False)

    created_by = models.IntegerField(null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_by = models.IntegerField(null=True, blank=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "Setting_UserRoleELearning"

    def __str__(self):
        return f"Perm[{self.user_role_id}] M{self.module_id} F{self.form_id}"

class RolePermission(models.Model):
    role = models.ForeignKey('staff.UserRole', on_delete=models.CASCADE)
    form = models.ForeignKey(FormELearning, on_delete=models.CASCADE)
    can_create = models.BooleanField(default=False)
    can_read = models.BooleanField(default=True)
    can_update = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)

    class Meta:
        unique_together = ('role', 'form')
    
