from rest_framework import serializers
from staff.models import Attendance
from course.models import CourseTracker

class EnquiryReportSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    enquiry_date = serializers.DateField()
    enquiry_code = serializers.CharField()
    student_name = serializers.CharField()
    mobile_no = serializers.CharField()
    course_interested = serializers.CharField()
    source = serializers.CharField()
    status = serializers.CharField()

class AttendanceReportSerializer(serializers.ModelSerializer):
    # Bringing in the employee name for readability
    employee_name = serializers.ReadOnlyField(source='employee.name')

    class Meta:
        model = Attendance
        fields = ['id', 'employee', 'employee_name', 'date', 'present', 'is_active']

class FollowUpReportSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    followup_date = serializers.DateField()
    student_name = serializers.CharField()
    mobile_no = serializers.CharField()
    medium = serializers.CharField()
    interest_level = serializers.CharField()
    remarks = serializers.CharField()
    next_followup_date = serializers.DateField()

class CourseTrackerReportSerializer(serializers.ModelSerializer):
    # Pulling human-readable names for the report
    organization_name = serializers.ReadOnlyField(source='organization.name')
    branch_name = serializers.ReadOnlyField(source='branch.name')
    trainer_name = serializers.ReadOnlyField(source='trainer.name')
    batch_name = serializers.ReadOnlyField(source='batch.batch_name')
    course_name = serializers.ReadOnlyField(source='course.course_name')

    class Meta:
        model = CourseTracker
        fields = [
            'id', 'date', 'status', 'remark', 
            'organization_name', 'branch_name', 
            'trainer_name', 'batch_name', 'course_name'
        ]


