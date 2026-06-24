import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wims_project.settings')
django.setup()

from course.models import Batch, Course
from admission.models import Admission
from assignment.models import Mst_Assignment, Mst_AssignmentSubmission
from assignment.serializers import AssignmentRowSerializer

# get batch 1
try:
    batch = Batch.objects.get(id=1)
    print(f"Batch found: {batch}")
    
    # get teacher (Employee) 
    # Batch 1 has no trainer, let's assign one or just pick one for the assignment
    from staff.models import Employee
    teacher = Employee.objects.first()
    if not teacher:
        print("No employees found! Creating one...")
        # create valid employee if needed
    else:
        print(f"Using Teacher: {teacher}")

    # Create dummy assignment
    if not Mst_Assignment.objects.filter(batch=batch).exists():
        print("Creating dummy assignment...")
        assignment = Mst_Assignment.objects.create(
            teacher=teacher,
            batch=batch,
            course=batch.course,
            assignment_name="Test Assignment 1",
            assignment_date="2025-01-01"
        )
    else:
        assignment = Mst_Assignment.objects.filter(batch=batch).first()
        print(f"Using existing assignment: {assignment}")

    # Simulate View Logic
    assignments = Mst_Assignment.objects.filter(batch=batch)
    students = Admission.objects.filter(courses=batch.course)
    
    data_list = []
    print(f"Looping {assignments.count()} assignments and {students.count()} students")
    
    for ass in assignments:
        for stud in students:
            sub = Mst_AssignmentSubmission.objects.filter(assignment=ass, student=stud).first()
            data_list.append({
                'assignment': ass,
                'student': stud,
                'submission': sub
            })
            
    print(f"Data list size: {len(data_list)}")
    
    # Serialize
    print("Serializing...")
    serializer = AssignmentRowSerializer(data_list, many=True)
    print("Serialized Data:", serializer.data)

except Exception as e:
    print(f"CRASH: {e}")
    import traceback
    traceback.print_exc()
