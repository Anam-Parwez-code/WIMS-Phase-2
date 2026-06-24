# client_management/utils.py
from cryptography.fernet import Fernet
import base64
from django.conf import settings

# Generate a key once: Fernet.generate_key()
SECRET_KEY = settings.SECRET_KEY[:32].encode()  # simple demo, better use separate env var
fernet = Fernet(base64.urlsafe_b64encode(SECRET_KEY))

def encrypt_value(value: str) -> str:
    return fernet.encrypt(value.encode()).decode()

def decrypt_value(value: str) -> str:
    return fernet.decrypt(value.encode()).decode()


from django.core.management import call_command
from django.conf import settings

def migrate_client_db(client):
    db_config = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': client.db_name,
        'USER': client.db_user,
        'PASSWORD': client.db_password,
        'HOST': client.db_host,
        'PORT': client.db_port,
    }

    db_key = f"tenant_{client.code}"
    if db_key not in settings.DATABASES:
        settings.DATABASES[db_key] = db_config

    # Run all migrations for this tenant
    call_command('migrate', database=db_key, interactive=False, run_syncdb=True)



# Client Selection and Audit Log Utils
from django.conf import settings
from django.db import connections
from django.db.utils import OperationalError
from .models import AuditLog, UserActivityLog, ErrorLog

def inject_tenant_db_config(client):
    """
    Add/refresh tenant DB config in settings.DATABASES under key tenant_{client_code}.
    """
    db_key = f"tenant_{client.client_code}"
    settings.DATABASES[db_key] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": client.database_name,
        "USER": client.db_user,
        "PASSWORD": client.db_password,
        "HOST": client.db_host,
        "PORT": client.db_port,
        "OPTIONS": {"options": settings.DATABASES["default"].get("OPTIONS", {}).get("options", "")},
    }
    return db_key

def test_db_connection(db_key) -> bool:
    try:
        connections[db_key].ensure_connection()
        return True
    except OperationalError:
        return False

def get_ip(request):
    return request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR")

def get_ua(request):
    return request.META.get("HTTP_USER_AGENT", "")

# def log_audit(request, action, details=""):
#     AuditLog.objects.create(
#         user=getattr(request, "user", None) if getattr(request, "user", None) and request.user.is_authenticated else None,
#         action=action, details=details, ip_address=get_ip(request), user_agent=get_ua(request)
#     )

# def log_activity(request, activity, metadata=""):
#     UserActivityLog.objects.create(
#         user=getattr(request, "user", None) if getattr(request, "user", None) and request.user.is_authenticated else None,
#         activity=activity, metadata=metadata, ip_address=get_ip(request), user_agent=get_ua(request)
#     )

# def log_error(request, location, message, stack_trace="", request_body=""):
#     ErrorLog.objects.create(
#         user=getattr(request, "user", None) if getattr(request, "user", None) and request.user.is_authenticated else None,
#         location=location, message=message, stack_trace=stack_trace,
#         request_body=request_body, ip_address=get_ip(request), user_agent=get_ua(request)
#     )
from django.contrib.auth import get_user_model
UserModel = get_user_model()

def log_audit(request, action, details=""):
    user_obj = getattr(request, "user", None)
    if user_obj and isinstance(user_obj, UserModel) and user_obj.is_authenticated:
        user = user_obj
    else:
        user = None
    AuditLog.objects.create(
        user=user,
        action=action, details=details, ip_address=get_ip(request), user_agent=get_ua(request)
    )

def log_activity(request, activity, metadata=""):
    user_obj = getattr(request, "user", None)
    if user_obj and isinstance(user_obj, UserModel) and user_obj.is_authenticated:
        user = user_obj
    else:
        user = None
    UserActivityLog.objects.create(
        user=user,
        activity=activity, metadata=metadata, ip_address=get_ip(request), user_agent=get_ua(request)
    )

def log_error(request, location, message, stack_trace="", request_body=""):
    user_obj = getattr(request, "user", None)
    if user_obj and isinstance(user_obj, UserModel) and user_obj.is_authenticated:
        user = user_obj
    else:
        user = None
    ErrorLog.objects.create(
        user=user,
        location=location, message=message, stack_trace=stack_trace,
        request_body=request_body, ip_address=get_ip(request), user_agent=get_ua(request)
    )

# core/utils.py
def get_client_ip(request):
    """
    Extract the real client IP address from request headers.
    Works behind proxies/load balancers.
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip



from rest_framework.exceptions import PermissionDenied


def get_requested_branch(request):

    user = request.client_user

    requested_branch_id = request.GET.get("branch_id")

    # =====================================
    # DEFAULT TO USER BRANCH
    # =====================================

    if not requested_branch_id:

        return user.branch_id

    requested_branch_id = int(requested_branch_id)

    # =====================================
    # MAIN BRANCH ADMIN
    # =====================================

    if user.is_main_branch_admin:

        return requested_branch_id

    # =====================================
    # REGULAR USERS
    # =====================================

    if requested_branch_id != user.branch_id:

        raise PermissionDenied(
            "You cannot access another branch data."
        )

    return requested_branch_id