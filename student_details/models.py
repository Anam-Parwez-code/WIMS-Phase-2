# student/models.py
from django.db import models
from course.models import Course, Batch
from master.models import InterestLevel, Nationality, FollowUpMedium, Source, Status, Country, State, City, Branch, Organization
from staff.models import Employee
from django.conf import settings


class Enquiry(models.Model):
    enquiry_code = models.CharField(max_length=50, unique=True)
    enquiry_date = models.DateField()
    candidate_name = models.CharField(max_length=100)
    aadhar_card_no = models.CharField(max_length=20, blank=True)
    mobile_no = models.CharField(max_length=15)
    alternate_mobile_no = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    next_followup_date = models.DateField(blank=True, null=True)
    preferred_time = models.CharField(max_length=50, blank=True)
    followup_medium = models.ForeignKey(FollowUpMedium, on_delete=models.SET_NULL, null=True)
    enquiry_source = models.ForeignKey(Source, on_delete=models.SET_NULL, null=True)
    assigned_to = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True)
    status = models.ForeignKey(Status, on_delete=models.SET_NULL, null=True)
    nationality = models.ForeignKey(Nationality, on_delete=models.SET_NULL, null=True)
    remark = models.TextField(blank=True)
    refer_name = models.CharField(max_length=100, blank=True)
    refer_email = models.EmailField(blank=True)
    refer_phone = models.CharField(max_length=15, blank=True)
    courses = models.ManyToManyField(Course)
    send_mail = models.BooleanField(default=False)
    send_sms = models.BooleanField(default=False)
    schedule_demo = models.BooleanField(default=False)
    demo_course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, related_name='demo_course')
    demo_batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True)
    demo_faculty = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='demo_faculty')
    demo_date = models.DateField(blank=True, null=True)
    demo_time = models.CharField(max_length=50, blank=True)
    
    is_active = models.BooleanField(default=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='enquiries_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='enquiries_updated')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.enquiry_code


# models.py

class EnquiryFollowUp(models.Model):

    # =========================================
    # ENQUIRY
    # =========================================

    enquiry = models.ForeignKey(
        Enquiry,
        on_delete=models.CASCADE,
        related_name='followups'
    )

    # =========================================
    # FOLLOWUP DETAILS
    # =========================================

    followup_date = models.DateField()

    next_followup_date = models.DateField(
        null=True,
        blank=True
    )

    preferred_time = models.CharField(
        max_length=50,
        blank=True
    )

    # =========================================
    # TRACKED THROUGH
    # =========================================

    followup_medium = models.ForeignKey(
        FollowUpMedium,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # =========================================
    # INTEREST LEVEL
    # =========================================

    interest_level = models.ForeignKey(
        InterestLevel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # =========================================
    # STATUS
    # =========================================

    status = models.ForeignKey(
        Status,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # =========================================
    # ASSIGNED TO
    # =========================================

    assigned_to = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # =========================================
    # REASON FOR DECLINE / DELAY
    # =========================================

    decline_reason = models.TextField(
        null=True,
        blank=True
    )

    # =========================================
    # FLAGS
    # =========================================

    demo_attended = models.BooleanField(
        default=False
    )

    confirmed_for_joining = models.BooleanField(
        default=False
    )

    schedule_demo_class = models.BooleanField(
        default=False
    )

    # =========================================
    # DEMO DETAILS
    # =========================================

    demo_course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="followup_demo_course"
    )

    demo_batch = models.ForeignKey(
        Batch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    demo_faculty = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="followup_demo_faculty"
    )

    demo_date = models.DateField(
        null=True,
        blank=True
    )

    demo_time = models.CharField(
        max_length=50,
        blank=True
    )

    # =========================================
    # REMARK
    # =========================================

    remark = models.TextField(blank=True)

    # =========================================
    # COMMON FIELDS
    # =========================================

    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='enquiry_followups_created'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='enquiry_followups_updated'
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):

        return (
            f"{self.enquiry.enquiry_code} - "
            f"{self.followup_date}"
        )



class Registration(models.Model):
    enquiry = models.ForeignKey(Enquiry, on_delete=models.SET_NULL, null=True, blank=True)
    registration_code = models.CharField(max_length=50, unique=True)
    registration_date = models.DateField()
    candidate_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10)
    mobile_no = models.CharField(max_length=15)
    email = models.EmailField()
    dob = models.DateField()
    aadhar_no = models.CharField(max_length=20, blank=True, null=True) # Validate 12 digits in serializer
    
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True)
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True)
    address = models.TextField()
    nationality = models.ForeignKey(Nationality, on_delete=models.SET_NULL, null=True)
    
    # 🏢 Organizational fields
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, null=True, blank=True)
    
    registration_fee = models.DecimalField(max_digits=10, decimal_places=2)
    courses = models.ManyToManyField(Course)
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True)
    session_fy = models.CharField(max_length=50, null=True, blank=True) # e.g. "2025-26"
    
    profile_pic = models.ImageField(upload_to='registration_pics/', null=True, blank=True)
    
    send_sms = models.BooleanField(default=False)
    send_mail = models.BooleanField(default=False)
    whatsapp = models.BooleanField(default=False)
    
    is_active = models.BooleanField(default=True) # for soft deletion
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='registrations_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='registrations_updated')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.registration_code} - {self.candidate_name}"











