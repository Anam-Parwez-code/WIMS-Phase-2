from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from admission.models import Admission
from users.models import User
from course.models import Course
from master.models import Organization
from datetime import date

class AdmissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.course = Course.objects.create(course_name="Test Course", course_code="TC01", course_duration=6, course_fee=10000, gst_percentage=18)
        self.organization = Organization.objects.create(name="Test Org", client="CLIENT123", is_active=True)
        # Assuming we need a 'client' header or logic. The view logic checks request.user.client_code if not superadmin.
        # But for creation, it uses request.user context if available.
        # Let's bypass auth for now or mock user if needed. View uses `request.user` to set creator and client logic.
        # Ideally we should force authenticate.
        self.user = User.objects.create_user(email="admin@test.com", password="password", role="super_admin")
        self.client.force_authenticate(user=self.user)

    def test_create_admission_and_user_credentials(self):
        url = '/api/admission/admissions/' # Assuming URL structure based on previous reads
        data = {
            "candidate_name": "New Student",
            "mobile_no": "9876543210",
            "gender": "Male",
            "email": "student@test.com",
            "admission_date": "2024-01-01",
            "status": "Admitted",
            "courses": [self.course.id]
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('credentials', response.data)
        self.assertEqual(response.data['credentials']['email'], "student@test.com")
        self.assertTrue(len(response.data['credentials']['password']) > 0)
        
        # Verify User created
        user = User.objects.get(email="student@test.com")
        self.assertTrue(user.is_active)
        self.assertEqual(user.first_name, "New Student")
        
    def test_edit_admission(self):
        # Create initial admission
        adm = Admission.objects.create(
            candidate_name="Old Name",
            mobile_no="1234567890",
            gender="Male",
            email="edit@test.com",
            admission_code="ADM_EDIT",
            admission_date=date.today(),
            status="Admitted"
        )
        adm.courses.add(self.course)
        
        url = f'/api/admission/admissions/{adm.id}/'
        data = {
            "candidate_name": "New Name"
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        adm.refresh_from_db()
        self.assertEqual(adm.candidate_name, "New Name")

    def test_soft_delete_admission_deactivates_user(self):
        # Setup: Admission with linked User
        user = User.objects.create_user(email="delete@test.com", password="password", is_active=True)
        adm = Admission.objects.create(
            candidate_name="To Delete",
            mobile_no="1112223334",
            gender="Female",
            email="delete@test.com",
            admission_code="ADM_DEL",
            admission_date=date.today(),
            status="Admitted",
            is_active=True
        )
        
        url = f'/api/admission/admissions/{adm.id}/'
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify Admission Inactive
        adm.refresh_from_db()
        self.assertFalse(adm.is_active)
        
        # Verify User Inactive
        user.refresh_from_db()
        self.assertFalse(user.is_active)
