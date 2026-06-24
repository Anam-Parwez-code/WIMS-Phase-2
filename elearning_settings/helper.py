# elearning_settings/helpers.py

from django.conf import settings
from django.db import connections
from rest_framework.response import Response
from rest_framework import status

from core.models import Client
from .models import ModuleELearning, FormELearning, UserRoleELearning


# ===== DATABASE CONFIGURATION =====
def inject_tenant_db_config(client: Client) -> str:
    """
    Ensure tenant DB entry exists in settings.DATABASES and return db_key.
    
    Args:
        client: Client instance
        
    Returns:
        str: Database key to use with .using()
        
    Example:
        >>> client = Client.objects.get(id=1)
        >>> db_key = inject_tenant_db_config(client)
        >>> UserRoleELearning.objects.using(db_key).all()
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


# ===== CLIENT & DATABASE RESOLUTION =====
def get_client_and_db(request):
    """
    Get client and database key from request.
    
    Handles:
    - SuperAdmin: Uses X-Client-Code header
    - ClientAdmin/User: Uses user.client_code from profile
    
    Args:
        request: HTTP request object
        
    Returns:
        tuple: (client, db_key, error)
            - client: Client instance or None
            - db_key: Database key string or None
            - error: Response error or None
            
    Example:
        >>> client, db_key, error = get_client_and_db(request)
        >>> if error:
        ...     return error
        >>> UserRoleELearning.objects.using(db_key).all()
    """
    user = request.user
    
    # Determine client code
    if user.role == "super_admin":
        # SuperAdmin must provide X-Client-Code header
        client_code = request.headers.get("X-Client-Code")
    else:
        # Regular users get client from their profile
        client_code = getattr(user, 'client_code', None)
    
    # Validate client code provided
    if not client_code:
        error_msg = "Missing X-Client-Code header" if user.role == "super_admin" else "User client not set"
        return None, None, Response(
            {"error": error_msg},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get client from database
    try:
        client = Client.objects.get(client_code=client_code, is_active=True)
    except Client.DoesNotExist:
        return None, None, Response(
            {"error": f"Invalid client: {client_code}"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Inject tenant database config
    db_key = inject_tenant_db_config(client)
    
    return client, db_key, None


# ===== SOFT DELETE OPERATIONS =====
def soft_delete_module(module_id: int, user_id: int = None) -> bool:
    """
    Soft-delete a module in the main DB.
    Sets is_active=False instead of deleting.
    
    Args:
        module_id: ID of the module to delete
        user_id: ID of the user performing the deletion (for audit)
        
    Returns:
        bool: True if successful, False if module not found
        
    Example:
        >>> soft_delete_module(1, request.user.id)
        True
    """
    try:
        module = ModuleELearning.objects.using("default").get(pk=module_id)
        module.is_active = False
        module.updated_by = user_id
        module.save(using="default")
        return True
    except ModuleELearning.DoesNotExist:
        return False


def soft_delete_page(form_id: int, user_id: int = None) -> bool:
    """
    Soft-delete a form/page in the main DB.
    Sets is_active=False instead of deleting.
    
    Args:
        form_id: ID of the form to delete
        user_id: ID of the user performing the deletion (for audit)
        
    Returns:
        bool: True if successful, False if form not found
        
    Example:
        >>> soft_delete_page(1, request.user.id)
        True
    """
    try:
        form = FormELearning.objects.using("default").get(pk=form_id)
        form.is_active = False
        form.updated_by = user_id
        form.save(using="default")
        return True
    except FormELearning.DoesNotExist:
        return False


# ===== PERMISSION MANAGEMENT =====
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
    
    Creates or updates a permission record for a specific user role,
    module, and form combination in the tenant database.
    
    Args:
        client: Client instance - identifies which tenant DB to use
        role: User role ID (integer) - corresponds to UserRole.id
        module_id: Module ID (integer) - from ModuleELearning.module_id
        form_id: Form ID (integer) - from FormELearning.form_id
        perms: Dictionary containing permission flags:
            {
                "u_read": bool,
                "u_create": bool,
                "u_edit": bool,
                "u_delete": bool
            }
        user_id: ID of the user performing this action (for audit trail)
        
    Returns:
        None
        
    Example:
        >>> assign_permission_to_tenant(
        ...     client=client_obj,
        ...     role=5,
        ...     module_id=1,
        ...     form_id=10,
        ...     perms={
        ...         "u_read": True,
        ...         "u_create": True,
        ...         "u_edit": False,
        ...         "u_delete": False
        ...     },
        ...     user_id=42
        ... )
    """
    db_key = inject_tenant_db_config(client)

    # Prepare payload for create/update
    payload = dict(
        client_id=client.id,
        user_role_id=role,  # ← Important: use _id suffix!
        module_id=module_id,
        form_id=form_id,
        u_read=perms.get("u_read", False),
        u_create=perms.get("u_create", False),
        u_edit=perms.get("u_edit", False),
        u_delete=perms.get("u_delete", False),
        updated_by=user_id,
    )

    # Try to find existing permission record
    qs = UserRoleELearning.objects.using(db_key).filter(
        user_role_id=role,  # ← Important: use _id suffix!
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


# ===== PERMISSION QUERIES =====
def get_user_permissions(user_role_id: int, client: Client, db_key: str, branch_id: int = None):
    """
    Get all permissions for a user role.
    
    Args:
        user_role_id: ID of the role
        client: Client instance
        db_key: Database key for tenant DB
        branch_id: Optional branch ID filter
        
    Returns:
        QuerySet: All permissions for this role
        
    Example:
        >>> perms = get_user_permissions(5, client, db_key)
        >>> for perm in perms:
        ...     print(f"Module {perm.module_id}, Form {perm.form_id}")
    """
    perms = UserRoleELearning.objects.using(db_key).filter(
        user_role_id=user_role_id,
        client_id=client.id
    )
    
    if branch_id:
        perms = perms.filter(branch_id=branch_id)
    
    return perms


def user_has_permission(user_role_id: int, module_id: int, form_id: int, 
                       client: Client, db_key: str, permission_type: str = "u_read") -> bool:
    """
    Check if user has a specific permission for a form.
    
    Args:
        user_role_id: ID of the role
        module_id: ID of the module
        form_id: ID of the form
        client: Client instance
        db_key: Database key for tenant DB
        permission_type: Type of permission to check ("u_read", "u_create", "u_edit", "u_delete")
        
    Returns:
        bool: True if user has the permission, False otherwise
        
    Example:
        >>> if user_has_permission(5, 1, 10, client, db_key, "u_read"):
        ...     allow_read()
    """
    try:
        perm = UserRoleELearning.objects.using(db_key).get(
            user_role_id=user_role_id,
            module_id=module_id,
            form_id=form_id,
            client_id=client.id
        )
        return getattr(perm, permission_type, False)
    except UserRoleELearning.DoesNotExist:
        return False


def build_permission_map(permissions_qs):
    """
    Build a quick lookup dictionary for permissions.
    
    Args:
        permissions_qs: QuerySet of UserRoleELearning objects
        
    Returns:
        dict: {(module_id, form_id): {u_read, u_create, u_edit, u_delete}}
        
    Example:
        >>> perms = UserRoleELearning.objects.using(db_key).filter(user_role_id=5)
        >>> perm_map = build_permission_map(perms)
        >>> flags = perm_map.get((1, 10))
        >>> if flags and flags["u_read"]:
        ...     allow_read()
    """
    perm_map = {}
    for p in permissions_qs:
        perm_map[(p.module_id, p.form_id)] = {
            "u_read": p.u_read,
            "u_create": p.u_create,
            "u_edit": p.u_edit,
            "u_delete": p.u_delete,
        }
    return perm_map


# ===== VALIDATION HELPERS =====
def validate_module_exists(module_id: int) -> bool:
    """
    Check if a module exists and is active.
    
    Args:
        module_id: ID of the module
        
    Returns:
        bool: True if module exists and is active
    """
    return ModuleELearning.objects.using("default").filter(
        module_id=module_id,
        is_active=True
    ).exists()


def validate_form_exists(form_id: int, module_id: int = None) -> bool:
    """
    Check if a form exists and is active.
    
    Args:
        form_id: ID of the form
        module_id: Optional module ID to verify form is in correct module
        
    Returns:
        bool: True if form exists and is active
    """
    qs = FormELearning.objects.using("default").filter(
        form_id=form_id,
        is_active=True
    )
    
    if module_id:
        qs = qs.filter(module_id=module_id)
    
    return qs.exists()


def validate_role_exists(role_id: int) -> bool:
    """
    Check if a user role exists and is active.
    
    Args:
        role_id: ID of the role
        
    Returns:
        bool: True if role exists and is active
    """
    from staff.models import UserRole
    
    return UserRole.objects.filter(
        id=role_id,
        is_active=True
    ).exists()