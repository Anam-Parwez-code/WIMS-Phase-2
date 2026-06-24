from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings



User = get_user_model()

class Client(models.Model):
    
 
    client_name = models.CharField(max_length=255)
    client_code = models.CharField(max_length=100, unique=True)

    database_name = models.CharField(max_length=255, unique=True)   
    db_user = models.CharField(max_length=100)                      
    db_password = models.CharField(max_length=100)                  
    db_host = models.CharField(max_length=100, default="localhost") 
    db_port = models.IntegerField(default=5432)                     

    connection_string = models.TextField(blank=True, null=True)  # optional, or auto-generate from above fields

    created_by = models.ForeignKey(User, null=True, blank=True, related_name="created_clients", on_delete=models.SET_NULL)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, null=True, blank=True, related_name="updated_clients", on_delete=models.SET_NULL)
    updated_date = models.DateTimeField(auto_now=True)

    expiry_date = models.DateField(null=True, blank=True)
    client_logo = models.URLField(max_length=500, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    mobile_no = models.CharField(max_length=15, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    website_link = models.URLField(max_length=500, null=True, blank=True)
    password = models.TextField(null=True, blank=True)
    employee_name = models.CharField(max_length=255, null=True, blank=True)
    # ✅ Force always "client_admin"
    role = models.CharField(max_length=20, default="client_admin", editable=False)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.client_name} ({self.client_code})"
    
    def save(self, *args, **kwargs):
        is_new = self._state.adding  # check if this is a new client
        super().save(*args, **kwargs)

        if is_new and self.email and self.password:
            # Auto-create ClientAdmin user in global User model
            if not User.objects.filter(email=self.email).exists():
                User.objects.create_user(
                    email=self.email,
                    password=self.password,
                    first_name=self.client_name,   # or employee_name
                    last_name="Admin",
                    role="client_admin",
                    client_code=self.client_code,
                )

class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=200)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True) #add it while logging in
    user_agent = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class UserActivityLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    activity = models.CharField(max_length=200)
    metadata = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class ErrorLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    location = models.CharField(max_length=200)  # e.g., "SelectClientAPIView"
    message = models.CharField(max_length=500)
    stack_trace = models.TextField(blank=True)
    request_body = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ClientUser(models.Model):
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("user", "User"),
        ("staff", "Staff"),
    ]
    client_code = models.CharField(max_length=50)
    user_id = models.CharField(max_length=100)  # login ID (like username)
    password = models.CharField(max_length=255)  # hashed password (bcrypt)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="user")  
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)

    # =====================================
    # NEW FIELDS
    # =====================================

    is_branch_super_admin = models.BooleanField(
        default=False
    )

    is_main_branch_admin = models.BooleanField(
        default=False
    )



    employee_name = models.CharField(max_length=255, blank=True, null=True) 
    branch = models.ForeignKey(
        'master.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("client_code", "user_id")

    def __str__(self):
        return f"{self.user_id} ({self.client.client_code}) ({'Admin' if self.is_admin else 'User'})"
