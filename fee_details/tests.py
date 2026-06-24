from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from admission.models import Admission
from course.models import Course
from .models import FeeGeneration, FeeDeposit
from datetime import date
from decimal import Decimal

class FeeDetailsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Create a course
        self.course = Course.objects.create(course_name="Test Course", course_code="TC01", course_duration=6, course_fee=10000, gst_percentage=18)
        
        # Create an admission
        self.admission = Admission.objects.create(
            admission_code="ADM001",
            candidate_name="Test Student",
            mobile_no="1234567890",
            gender="Male",
            admission_date=date.today(),
            status="Admitted"
        )
        self.admission.courses.add(self.course)
        
        # Create FeeGeneration
        self.fee_gen = FeeGeneration.objects.create(
            candidate=self.admission,
            generated_date=date.today(),
            fee_type='installment',
            course_fee=10000,
            extra_amount=0,
            discount=0,
            gst_percent=18,
            payment_mode='cash',
            advance_amount=1000
        )
        # Total fee should be 10000 + 18% = 11800.
        # Balance should be 11800 - 1000 = 10800.
    
    def test_fee_balance_and_dues_list(self):
        # Check initial balance
        self.fee_gen.refresh_from_db()
        self.assertEqual(self.fee_gen.total_fee, Decimal('11800.00'))
        self.assertEqual(self.fee_gen.balance_amount, Decimal('10800.00'))
        
        # Check Dues List API
        url = reverse('dues-list-list-create') # Check urls.py for name likely 'dues-list-list-create' from previous reading
        # Wait, in urls.py I saw: path('dues-list/', DuesListAPIView.as_view(), name='dues-list-list-create')
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['candidate_name'], "Test Student")
        self.assertEqual(Decimal(response.data[0]['balance_amount']), Decimal('10800.00'))
        
        # Make a deposit
        deposit = FeeDeposit.objects.create(
            fee_generation=self.fee_gen,
            payment_date=date.today(),
            payment_mode='Cash',
            installment_amount=5000
        )
        
        # Check balance updated
        self.fee_gen.refresh_from_db()
        self.assertEqual(self.fee_gen.balance_amount, Decimal('5800.00')) # 10800 - 5000
        
        # Check Dues List API again
        response = self.client.get(url)
        self.assertEqual(Decimal(response.data[0]['balance_amount']), Decimal('5800.00'))
        
        # Make full payment
        deposit2 = FeeDeposit.objects.create(
            fee_generation=self.fee_gen,
            payment_date=date.today(),
            payment_mode='Cash',
            installment_amount=5800
        )
        
        self.fee_gen.refresh_from_db()
        self.assertEqual(self.fee_gen.balance_amount, Decimal('0.00'))
        
        # Check Dues List API - should be empty
        response = self.client.get(url)
        self.assertEqual(len(response.data), 0)
