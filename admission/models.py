from django.db import models
from course.models import Batch, Course
from student_details.models import Registration
from master.models import Organization, Branch
from django.conf import settings
from staff.models import UserRole

class Admission(models.Model):
    send_email = models.BooleanField(default=False)
    send_text_sms = models.BooleanField(default=False)
    direct = models.BooleanField(default=False)
    cancel_admission = models.BooleanField(default=False)
    #corporate = models.BooleanField(default=False)

    # Cancellation Info
    cancellation_date = models.DateField(null=True, blank=True)
    reason = models.TextField(null=True, blank=True)

    # Linking to Registration
    registration = models.ForeignKey(
        Registration, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='admissions'
    )

    admission_code = models.CharField(max_length=50, unique=True)
    image = models.ImageField(upload_to='admission_images/', null=True, blank=True)
    admission_date = models.DateField()

    # Candidate Details
    candidate_name = models.CharField(max_length=255)
    mobile_no = models.CharField(max_length=15)
    alternate_mobile_no = models.CharField(max_length=15, null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')])
    email = models.EmailField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    role = models.ForeignKey(UserRole, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[('Admitted', 'Admitted'), ('Cancelled', 'Cancelled')]
    )
    father_name = models.CharField(max_length=255, null=True, blank=True)
    mother_name = models.CharField(max_length=255, null=True, blank=True)
    qualification = models.CharField(max_length=255, null=True, blank=True)
    aadhaar_no = models.CharField(max_length=12, null=True, blank=True)

    # Courses (Multiple)
    #courses = models.ManyToManyField(Course, related_name='admissions')
    #batches = models.ManyToManyField('course.Batch', related_name='admissions', blank=True)
    
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='admissions_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='admissions_updated')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.admission_code} - {self.candidate_name}"




class AdmissionCourseBatch(models.Model):
    admission = models.ForeignKey(
        Admission,
        on_delete=models.CASCADE,
        related_name="course_batches"
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE
    )

    batch = models.ForeignKey(
        Batch,
        on_delete=models.CASCADE
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.admission} | {self.course} | {self.batch}"



# class CertificateTemplate(models.Model):
#     template_name = models.CharField(max_length=100)
#     template_path = models.CharField(max_length=500, null=True, blank=True)
#     is_active = models.BooleanField(default=True)

#     def __str__(self):
#         return self.template_name


from django.db import models
from django.core.exceptions import ValidationError


class CertificateTemplate(models.Model):

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="certificate_templates",
        null=True,
        blank=True
    )

    template_name = models.CharField(max_length=100)

    # =====================================
    # LOGO
    # =====================================

    institute_logo = models.ImageField(
        upload_to="certificate/logo/",
        null=True,
        blank=True
    )

    logo_position = models.CharField(
        max_length=20,
        choices=[
            ("top_left","Top Left"),
            ("top_center","Top Center"),
            ("top_right","Top Right")
        ],
        default="top_center"
    )

    # =====================================
    # INSTITUTE NAME
    # =====================================

    institute_name = models.CharField(
        max_length=255,
        blank=True
    )

    institute_name_font_size = models.IntegerField(default=24)

    institute_name_bold = models.BooleanField(default=True)

    institute_name_italic = models.BooleanField(default=False)

    institute_name_color = models.CharField(
        max_length=20,
        default="#000000"
    )

    institute_name_alignment = models.CharField(
        max_length=20,
        default="center"
    )

    # =====================================
    # TITLE
    # =====================================

    certificate_title = models.CharField(
        max_length=255,
        default="Certificate of Completion"
    )

    title_font_size = models.IntegerField(default=36)

    title_bold = models.BooleanField(default=True)

    title_italic = models.BooleanField(default=False)

    title_color = models.CharField(
        max_length=20,
        default="#000000"
    )

    title_alignment = models.CharField(
        max_length=20,
        default="center"
    )

    # =====================================
    # BODY
    # =====================================

    body_text = models.TextField(
        blank=True,
        default=""
    )

    body_font_size = models.IntegerField(default=18)

    body_color = models.CharField(
        max_length=20,
        default="#000000"
    )

    # =====================================
    # SIGNATURE
    # =====================================

    signature_image = models.ImageField(
        upload_to="certificate/signature/",
        null=True,
        blank=True
    )

    signature_label = models.CharField(
        max_length=100,
        blank=True
    )

    # =====================================
    # STAMP
    # =====================================

    stamp_image = models.ImageField(
        upload_to="certificate/stamp/",
        null=True,
        blank=True
    )

    stamp_position = models.CharField(
        max_length=20,
        choices=[
            ("left","Left"),
            ("center","Center"),
            ("right","Right")
        ],
        default="right"
    )

    # =====================================
    # BORDER
    # =====================================

    border_style = models.CharField(
        max_length=20,
        choices=[
            ("none","No Border"),
            ("simple","Simple Line Border"),
            ("decorative","Decorative Border")
        ],
        default="simple"
    )

    border_color = models.CharField(
        max_length=20,
        default="#000000"
    )

    # =====================================
    # BACKGROUND
    # =====================================

    background_type = models.CharField(
        max_length=20,
        choices=[
            ("color","Color"),
            ("image","Image")
        ],
        default="color"
    )

    background_color = models.CharField(
        max_length=20,
        default="#FFFFFF"
    )

    background_image = models.ImageField(
        upload_to="certificate/background/",
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True,null=True,blank=True)

    updated_at = models.DateTimeField(auto_now=True,null=True,blank=True)
    
    is_active = models.BooleanField(default=True)




class CertificateApproval(models.Model):
    admission = models.OneToOneField(
        Admission, 
        on_delete=models.CASCADE, 
        related_name='certificate_approval'
    )
    approval_date = models.DateField()
    remarks = models.TextField()
    
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT)
    
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='approvals_granted'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Approved: {self.admission.admission_code}"





class CertificateIssue(models.Model):

    student = models.ForeignKey(
        Admission,
        on_delete=models.PROTECT,
        related_name='issued_certificates'
    )

    # NEW
    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    batch = models.ForeignKey(
        Batch,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    template = models.ForeignKey(
        CertificateTemplate,
        on_delete=models.PROTECT
    )

    certificate_no = models.CharField(
        max_length=50,
        unique=True
    )

    issue_date = models.DateField()

    expiry_date = models.DateField()

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT
    )

    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT
    )

    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='certs_issued'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='certs_updated'
    )

    updated_at = models.DateTimeField(auto_now=True)

    certificate_pdf = models.FileField(
        upload_to="certificates/pdf/",
        null=True,
        blank=True
    )

    pdf_generated_at = models.DateTimeField(
        null=True,
        blank=True
    )




# class Attendance(models.Model):
#     is_active = models.BooleanField(default=True)
#     # Linking to your Admission model (which represents the student/candidate)
#     admission = models.ForeignKey(
#         'Admission', 
#         on_delete=models.CASCADE, 
#         related_name='attendance_records'
#     )
#     date = models.DateField()
#     present = models.BooleanField(default=False)
    
#     class Meta:
#         # Prevents duplicate entries for the same student on the same day
#         unique_together = ('admission', 'date')

#     def __str__(self):
#         status = "Present" if self.present else "Absent"
#         return f"{self.admission.candidate_name} - {self.date} ({status})"



class Attendance(models.Model):

    STATUS_CHOICES = [
        ("present", "Present"),
        ("absent", "Absent"),
        ("half_day", "Half Day"),
        ("on_leave", "On Leave"),
    ]

    is_active = models.BooleanField(default=True)

    admission = models.ForeignKey(
        "Admission",
        on_delete=models.CASCADE,
        related_name="attendance_records"
    )

    date = models.DateField()

    # NEW
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="present"
    )

    time_in = models.TimeField(
        null=True,
        blank=True
    )

    time_out = models.TimeField(
        null=True,
        blank=True
    )

    total_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    remark = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_marked"
    )

    class Meta:
        unique_together = ("admission", "date")

    def save(self, *args, **kwargs):

        if (
            self.time_in and
            self.time_out
        ):
            from datetime import datetime

            start = datetime.combine(
                self.date,
                self.time_in
            )

            end = datetime.combine(
                self.date,
                self.time_out
            )

            diff = end - start

            self.total_hours = round(
                diff.total_seconds() / 3600,
                2
            )

        else:
            self.total_hours = None

        super().save(*args, **kwargs)


