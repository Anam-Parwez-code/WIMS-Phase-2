from django.db import models
#from admission.models import Admission
from master.models import Department, Designation, Country, State, City
from django.contrib.auth import get_user_model

class Employee(models.Model):    
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ]
    MARITAL_CHOICES = [
        ('single', 'Single'),
        ('married', 'Married')
    ]

    
    organization = models.ForeignKey(
        'master.Organization', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    branch = models.ForeignKey(
        'master.Branch', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    is_active = models.BooleanField(default=True)

    employee_code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True, null=True)

    dob = models.DateField()
    date_of_joining = models.DateField()
    mobile = models.CharField(max_length=15)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    email = models.EmailField()
    phone = models.CharField(max_length=15, blank=True, null=True)

    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    designation = models.ForeignKey(Designation, on_delete=models.SET_NULL, null=True)

    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True)
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True)

    marital_status = models.CharField(max_length=10, choices=MARITAL_CHOICES)

    resume = models.FileField(upload_to='resumes/', null=True, blank=True)
    profile_photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)

    salary = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name





class UserRole(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class StaffUser(models.Model):
    is_active = models.BooleanField(default=True)
    # STAFF LOGIN
    employee = models.ForeignKey(
        "staff.Employee",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    # STUDENT LOGIN
    admission = models.ForeignKey(
        "admission.Admission",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    username = models.CharField(max_length=150)
    password = models.CharField(max_length=128)
    raw_password_store = models.CharField(max_length=128, null=True, blank=True)

    role = models.ForeignKey(UserRole, on_delete=models.SET_NULL, null=True)
    expiry_date = models.DateField()

    def __str__(self):
        return self.username


class Attendance(models.Model):
    is_active = models.BooleanField(default=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.DateField()
    present = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.employee.name} - {self.date}"




# staff/models.py

from admission.models import Admission
from master.models import Branch, Organization

class StudentLoginHistory(models.Model):

    admission = models.ForeignKey(
        Admission,
        on_delete=models.CASCADE,
        related_name="login_histories"
    )

    login_datetime = models.DateTimeField(
        auto_now_add=True
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    is_active = models.BooleanField(
        default=True
    )

    class Meta:
        ordering = ["-login_datetime"]




