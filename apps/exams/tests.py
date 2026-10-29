import json
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.academics.models import Subject, Batch, Enrollment
from apps.exams.models import Exam, ExamResult

User = get_user_model()


class ExamSystemTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.teacher = User.objects.create_user(
            username='eval_teacher',
            password='password123',
            role='TEACHER'
        )

        self.student = User.objects.create_user(
            username='bob_student',
            password='password123',
            role='STUDENT'
        )

        self.subject = Subject.objects.create(name='Physics', code='PHY101')
        self.batch = Batch.objects.create(
            name='Grade 11 Mechanics',
            subject=self.subject,
            teacher=self.teacher
        )
        self.enrollment = Enrollment.objects.create(student=self.student, batch=self.batch)

        self.exam = Exam.objects.create(
            batch=self.batch,
            subject=self.subject,
            title='Mechanics Unit Test',
            exam_date=timezone.now().date(),
            total_marks=Decimal('50.00'),
            passing_marks=Decimal('20.00'),
            created_by=self.teacher
        )

        self.result = ExamResult.objects.create(
            exam=self.exam,
            student=self.student
        )

    def test_ajax_save_marks_success(self):
        self.client.login(username='eval_teacher', password='password123')
        payload = {
            'student_id': self.student.id,
            'marks_obtained': 42.5,
            'is_absent': False,
            'remarks': 'Outstanding performance in Newton laws.'
        }
        response = self.client.post(
            f'/exams/{self.exam.id}/ajax/save-mark/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['percentage'], 85.0)
        self.assertTrue(data['is_passed'])

        self.result.refresh_from_db()
        self.assertEqual(self.result.marks_obtained, Decimal('42.50'))
        self.assertEqual(self.result.remarks, 'Outstanding performance in Newton laws.')

    def test_ajax_save_marks_rejects_excess_marks(self):
        self.client.login(username='eval_teacher', password='password123')
        payload = {
            'student_id': self.student.id,
            'marks_obtained': 60.0, # exceeds total marks 50
            'is_absent': False
        }
        response = self.client.post(
            f'/exams/{self.exam.id}/ajax/save-mark/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
