from django.db import connections
from django.conf import settings
from core.models import Client, AuditLog, UserActivityLog, ErrorLog
from elearning_settings.models import ModuleELearning, FormELearning, UserRoleELearning


# def inject_tenant_db_config(client: Client) -> str:
#     """
#     Ensure tenant DB entry exists in settings.DATABASES and return db_key.
#     """
#     db_key = f"tenant_{client.client_code}"
#     if db_key not in settings.DATABASES:
#         settings.DATABASES[db_key] = {
#             "ENGINE": "django.db.backends.postgresql",
#             "NAME": client.database_name,
#             "USER": client.db_user,
#             "PASSWORD": client.db_password,
#             "HOST": client.db_host,
#             "PORT": client.db_port,
#         }
#     return db_key


# def soft_delete_module(module_id: int, user_id: int | None):
#     """
#     Soft-delete a module in the main DB (default only).
#     """
#     try:
#         m = ModuleELearning.objects.using("default").get(pk=module_id)
#         m.is_active = False
#         m.updated_by = user_id
#         m.save(using="default")
#         return True
#     except ModuleELearning.DoesNotExist:
#         return False


# def soft_delete_page(form_id: int, user_id: int | None):
#     """
#     Soft-delete a page in the main DB (default only).
#     """
#     try:
#         f = FormELearning.objects.using("default").get(pk=form_id)
#         f.is_active = False
#         f.updated_by = user_id
#         f.save(using="default")
#         return True
#     except FormELearning.DoesNotExist:
#         return False


# def assign_permission_to_tenant(client: Client, role: int, module_id: int, form_id: int, perms: dict, user_id: int):
#     """
#     Add or update a UserRoleELearning permission in a tenant DB.
#     """
#     db_key = inject_tenant_db_config(client)

#     payload = dict(
#         client_id=client.id,
#         user_role=role,
#         module_id=module_id,
#         form_id=form_id,
#         u_read=perms.get("read", False),
#         u_write=perms.get("write", False),
#         u_delete=perms.get("delete", False),
#         u_view=perms.get("view", False),
#         updated_by=user_id,
#     )

#     qs = UserRoleELearning.objects.using(db_key).filter(
#         user_role=role, module_id=module_id, form_id=form_id
#     )
#     if qs.exists():
#         qs.update(**payload)
#     else:
#         payload["created_by"] = user_id
#         UserRoleELearning.objects.using(db_key).create(**payload)


from django.db import connections
from django.conf import settings
from core.models import Client, AuditLog, UserActivityLog, ErrorLog
from elearning_settings.models import ModuleELearning, FormELearning, UserRoleELearning


def inject_tenant_db_config(client: Client) -> str:
    """
    Ensure tenant DB entry exists in settings.DATABASES and return db_key.
    
    Args:
        client: Client instance
        
    Returns:
        str: Database key to use with .using()
    """
    db_key = f"tenant_{client.client_code}"
    if db_key not in settings.DATABASES:
        settings.DATABASES[db_key] = {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": client.database_name,
            "USER": client.db_user,
            "PASSWORD": client.db_password,
            "HOST": client.db_host,
            "PORT": client.db_port,
        }
    return db_key


def soft_delete_module(module_id: int, user_id: int | None) -> bool:
    """
    Soft-delete a module in the main DB (default only).
    
    Args:
        module_id: ID of the module to delete
        user_id: ID of the user performing the deletion
        
    Returns:
        bool: True if successful, False if module not found
    """
    try:
        m = ModuleELearning.objects.using("default").get(pk=module_id)
        m.is_active = False
        m.updated_by = user_id
        m.save(using="default")
        return True
    except ModuleELearning.DoesNotExist:
        return False


def soft_delete_page(form_id: int, user_id: int | None) -> bool:
    """
    Soft-delete a page in the main DB (default only).
    
    Args:
        form_id: ID of the form/page to delete
        user_id: ID of the user performing the deletion
        
    Returns:
        bool: True if successful, False if form not found
    """
    try:
        f = FormELearning.objects.using("default").get(pk=form_id)
        f.is_active = False
        f.updated_by = user_id
        f.save(using="default")
        return True
    except FormELearning.DoesNotExist:
        return False


def assign_permission_to_tenant(
    client: Client, 
    role: int, 
    module_id: int, 
    form_id: int, 
    perms: dict, 
    user_id: int
) -> None:
    """
    Add or update a UserRoleELearning permission in a tenant DB.
    
    This function creates or updates a permission record for a specific user role,
    module, and form combination in the tenant database.
    
    Args:
        client: Client instance - identifies which tenant DB to use
        role: User role ID (integer) - corresponds to UserRole.id
        module_id: Module ID (integer) - from ModuleELearning.module_id
        form_id: Form ID (integer) - from FormELearning.form_id
        perms: Dictionary containing permission flags:
            {
                "u_read": bool,
                "u_write": bool,
                "u_delete": bool,
                "u_view": bool
            }
        user_id: ID of the user performing this action (for audit trail)
        
    Returns:
        None
        
    Example:
        >>> assign_permission_to_tenant(
        ...     client=client_obj,
        ...     role=5,  # user_role_id
        ...     module_id=1,
        ...     form_id=10,
        ...     perms={
        ...         "u_read": True,
        ...         "u_write": True,
        ...         "u_delete": False,
        ...         "u_view": True
        ...     },
        ...     user_id=42
        ... )
    """
    db_key = inject_tenant_db_config(client)

    payload = dict(
        client_id=client.id,
        user_role_id=role,  # CORRECTED: Changed from user_role to user_role_id
        module_id=module_id,
        form_id=form_id,
        u_read=perms.get("u_read", False),
        u_write=perms.get("u_write", False),
        u_delete=perms.get("u_delete", False),
        u_view=perms.get("u_view", False),
        updated_by=user_id,
    )

    # Try to find existing permission record
    qs = UserRoleELearning.objects.using(db_key).filter(
        user_role_id=role,  # CORRECTED: Changed from user_role to user_role_id
        module_id=module_id, 
        form_id=form_id
    )
    
    if qs.exists():
        # Update existing record
        qs.update(**payload)
    else:
        # Create new record
        payload["created_by"] = user_id
        UserRoleELearning.objects.using(db_key).create(**payload)