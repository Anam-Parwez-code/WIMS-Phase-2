from django.db import models
import re

from django.contrib.auth.hashers import make_password

from core.models import ClientUser
from django.contrib.auth import get_user_model

User = get_user_model()

class Country(models.Model):
    name = models.CharField(max_length=100)
    country_code = models.CharField(max_length=10, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class State(models.Model):
    name = models.CharField(max_length=100)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)  # soft delete

    def __str__(self):
        return self.name

class City(models.Model):
    name = models.CharField(max_length=100)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    state = models.ForeignKey(State, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Department(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)  # soft delete

    def __str__(self):
        return self.name

class Designation(models.Model):
    name = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)

    # Multi-tenant fields
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.department})"

class FollowUpMedium(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)  # soft delete

    def __str__(self):
        return self.name

class InterestLevel(models.Model):
    level = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.level

class Organization(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    mobile = models.CharField(max_length=20)
    landline = models.CharField(max_length=20, blank=True)
    address = models.TextField()
    zipcode = models.CharField(max_length=10)
    website = models.URLField(blank=True)
    fax = models.CharField(max_length=20, blank=True)

    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True)
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True)

    is_active = models.BooleanField(default=True)   # soft delete

    def __str__(self):
        return self.name

from django.db import models, transaction


class Branch(models.Model):

    is_active = models.BooleanField(default=True)

    # NEW FIELD
    is_main_branch = models.BooleanField(default=False)

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE
    )

    name = models.CharField(max_length=100)

    country = models.ForeignKey(
        Country,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    state = models.ForeignKey(
        State,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    city = models.ForeignKey(
        City,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    address = models.TextField()

    email = models.EmailField()

    mobile = models.CharField(max_length=20)

    landline = models.CharField(max_length=20, blank=True)

    zipcode = models.CharField(max_length=10)

    tin_number = models.CharField(max_length=50, blank=True)

    affiliation_number = models.CharField(max_length=50, blank=True)

    fax = models.CharField(max_length=20, blank=True)

    website = models.URLField(blank=True)

    bank_name = models.CharField(max_length=100, blank=True)

    bank_branch = models.CharField(max_length=100, blank=True)

    account_holder = models.CharField(max_length=100, blank=True)

    account_number = models.CharField(max_length=50, blank=True)

    ifsc_code = models.CharField(max_length=20, blank=True)

    gst_number = models.CharField(max_length=20, blank=True)

    image = models.ImageField(
        upload_to="branch_images/",
        blank=True,
        null=True
    )


    def save(self, *args, **kwargs):

        with transaction.atomic():

            if not self.pk:

                has_main_branch = Branch.objects.filter(
                    organization=self.organization,
                    is_main_branch=True,
                    is_active=True
                ).exists()

                if not has_main_branch:
                    self.is_main_branch = True

            if self.is_main_branch:

                Branch.objects.filter(
                    organization=self.organization,
                    is_main_branch=True
                ).exclude(
                    pk=self.pk
                ).update(
                    is_main_branch=False
                )

            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.organization})"

    # def save(self, *args, **kwargs):

    #     is_new = self._state.adding

    #     with transaction.atomic():

    #         # ======================================
    #         # AUTO SET FIRST BRANCH AS MAIN
    #         # ======================================

    #         if not self.pk:

    #             has_main_branch = Branch.objects.filter(
    #                 organization=self.organization,
    #                 is_main_branch=True,
    #                 is_active=True
    #             ).exists()

    #             if not has_main_branch:

    #                 self.is_main_branch = True

    #         # ======================================
    #         # ENSURE SINGLE MAIN BRANCH
    #         # ======================================

    #         if self.is_main_branch:

    #             Branch.objects.filter(
    #                 organization=self.organization,
    #                 is_main_branch=True
    #             ).exclude(
    #                 pk=self.pk
    #             ).update(
    #                 is_main_branch=False
    #             )

    #         super().save(*args, **kwargs)

    #         # ======================================
    #         # AUTO CREATE BRANCH SUPER ADMIN
    #         # ======================================

    #         if is_new:

    #             from django.db import connections

    #             from core.dbrouter import set_client_db

    #             from core.models import Client

    #             print("Organization ID:", self.organization_id)

    #             from core.models import Client

    #             print(
    #                 "All Client IDs:",
    #                 list(
    #                     Client.objects.values_list(
    #                         "id",
    #                         flat=True
    #                     )
    #                 )
    #             )

    #             client = Client.objects.filter(
    #                 id=self.organization_id
    #             ).first()

    #             print("Client Found:", client)

    #             client = Client.objects.filter(
    #                 id=self.organization_id
    #             ).first()

    #             if client:

    #                 db_key = f"client_{client.client_code}"

    #                 if db_key not in connections.databases:

    #                     connections.databases[db_key] = {
    #                         'ENGINE': 'django.db.backends.postgresql',
    #                         'NAME': client.database_name,
    #                         'USER': client.db_user,
    #                         'PASSWORD': client.db_password,
    #                         'HOST': client.db_host,
    #                         'PORT': client.db_port,
    #                     }

    #                 set_client_db(db_key)

    #                 # ======================================
    #                 # GENERATE USERNAME
    #                 # ======================================

    #                 clean_branch_name = re.sub(
    #                     r'[^a-zA-Z0-9]',
    #                     '',
    #                     self.name.lower()
    #                 )

    #                 username = f"admin_{clean_branch_name}"

    #                 default_password = "Admin@1234"

    #                 # ======================================
    #                 # AVOID DUPLICATES
    #                 # ======================================

    #                 if not ClientUser.objects.using(db_key).filter(
    #                     client_code=client.client_code,
    #                     user_id=username
    #                 ).exists():

    #                     ClientUser.objects.using(db_key).create(

    #                         client_code=client.client_code,

    #                         user_id=username,

    #                         password=make_password(
    #                             default_password
    #                         ),

    #                         role="admin",

    #                         is_admin=True,

    #                         is_branch_super_admin=True,

    #                         is_main_branch_admin=self.is_main_branch,

    #                         employee_name=f"{self.name} Branch Admin",

    #                         branch=self,

    #                         is_active=True
    #                     )

    #                     # ======================================
    #                     # CREATE DJANGO USER
    #                     # ======================================

    #                     if not User.objects.filter(
    #                         email=username
    #                     ).exists():

    #                         User.objects.create_user(

    #                             #username=username,

    #                             email=username,

    #                             password=default_password
    #                         )

    #                 # ======================================
    #                 # STORE TEMP VALUES
    #                 # ======================================

    #                 self.generated_username = username

    #                 self.generated_password = default_password


    # def __str__(self):
    #     return f"{self.name} ({self.organization})"




class Source(models.Model):
    name = models.CharField(max_length=100)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Status(models.Model):
    
    name = models.CharField(max_length=100)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Nationality(models.Model):
    
    name = models.CharField(max_length=100)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class FormDesign(models.Model):
    FORM_TYPES = [
        ("enquiry", "Enquiry"),
        ("admission", "Admission"),
        ("registration", "Registration"),
    ]
    form_type = models.CharField(max_length=20, choices=FORM_TYPES)
    layout_json = models.JSONField()

class EmailConfigurations(models.Model):
    
    smtp_host = models.CharField(max_length=100)
    smtp_port = models.IntegerField()
    username = models.CharField(max_length=100)
    password = models.CharField(max_length=100)
    use_tls = models.BooleanField(default=True)
    sender_email = models.EmailField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.username, self.sender_email

class SMSConfiguration(models.Model):
    api_url = models.URLField()
    username = models.CharField(max_length=100)
    password = models.CharField(max_length=100)

    sender = models.CharField(max_length=50)
    sender_id = models.CharField(max_length=50)
    entity_id = models.CharField(max_length=50)

    total_sms = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)   # Enable / Disable configuration

    def __str__(self):
        return f"{self.sender} ({self.client})"

class PaymentMethod(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
