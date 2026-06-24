from core.models import AuditLog, UserActivityLog, ErrorLog
import traceback
import json

def log_audit(request, action, details="", class_name="", table_name="", pk_id=None, status="Success"):
    """
    Log CRUD operations to AuditLog.
    """
    user = request.user if request and request.user.is_authenticated else None
    ip_address = request.META.get('REMOTE_ADDR') if request else None
    user_agent = request.META.get('HTTP_USER_AGENT') if request else None
    
    AuditLog.objects.create(
        user=user,
        action=action,
        details=json.dumps({
            "description": details,
            "class_name": class_name,
            "table_name": table_name,
            "pk_id": pk_id,
            "status": status
        }) if isinstance(details, (dict, list)) else f"{action}: {details} (Class: {class_name}, Table: {table_name}, PK: {pk_id}, Status: {status})",
        ip_address=ip_address,
        user_agent=user_agent
    )

def log_activity(request, activity, metadata=None):
    """
    Log user interactions to UserActivityLog.
    """
    user = request.user if request and request.user.is_authenticated else None
    ip_address = request.META.get('REMOTE_ADDR') if request else None
    user_agent = request.META.get('HTTP_USER_AGENT') if request else None
    
    UserActivityLog.objects.create(
        user=user,
        activity=activity,
        metadata=json.dumps(metadata) if metadata else "",
        ip_address=ip_address,
        user_agent=user_agent
    )

def log_error(request, location, message, exception=None):
    """
    Log errors and exceptions to ErrorLog.
    """
    user = request.user if request and request.user.is_authenticated else None
    ip_address = request.META.get('REMOTE_ADDR') if request else None
    user_agent = request.META.get('HTTP_USER_AGENT') if request else None
    stack_trace = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__)) if exception else ""
    
    request_body = ""
    if request:
        try:
            request_body = request.body.decode('utf-8')
        except:
            request_body = "Could not decode body"

    ErrorLog.objects.create(
        user=user,
        location=location,
        message=message,
        stack_trace=stack_trace,
        request_body=request_body,
        ip_address=ip_address,
        user_agent=user_agent
    )
