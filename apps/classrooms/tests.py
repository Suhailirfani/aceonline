from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.academics.models import Subject, Batch, Enrollment
from apps.classrooms.models import LiveClass, ClassAttendance

User = get_user_model()


class LiveClassroomTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create Teacher
        self.teacher = User.objects.create_user(
            username='prof_smith',
            password='password123',
            role='TEACHER',
            first_name='John',
            last_name='Smith'
        )

        # Create Student
        self.student = User.objects.create_user(
            username='alice_student',
            password='password123',
            role='STUDENT',
            first_name='Alice',
            last_name='Green'
        )

        # Create Subject & Batch
        self.subject = Subject.objects.create(name='Mathematics', code='MATH101')
        self.batch = Batch.objects.create(
            name='Grade 10 Algebra',
            subject=self.subject,
            teacher=self.teacher
        )

        # Enroll Student
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            batch=self.batch
        )

        # Create Live Class
        self.live_class = LiveClass.objects.create(
            batch=self.batch,
            teacher=self.teacher,
            title='Quadratic Equations Masterclass',
            meet_link='https://meet.google.com/test-meet-123',
            scheduled_start=timezone.now()
        )

    def test_teacher_can_start_class_via_ajax(self):
        self.client.login(username='prof_smith', password='password123')
        response = self.client.post(f'/classes/{self.live_class.id}/ajax/start/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['status'], 'LIVE')

        self.live_class.refresh_from_db()
        self.assertEqual(self.live_class.status, 'LIVE')
        self.assertIsNotNone(self.live_class.actual_start_time)

    def test_student_join_logs_attendance_via_ajax(self):
        # Teacher starts class
        self.live_class.start_class()

        # Student joins
        self.client.login(username='alice_student', password='password123')
        response = self.client.post(f'/classes/{self.live_class.id}/ajax/join/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['meet_link'], 'https://meet.google.com/test-meet-123')

        # Verify Attendance is recorded
        att = ClassAttendance.objects.filter(live_class=self.live_class, student=self.student).first()
        self.assertIsNotNone(att)
        self.assertIsNotNone(att.joined_at)

    def test_teacher_can_end_class_via_ajax(self):
        self.live_class.start_class()
        self.client.login(username='prof_smith', password='password123')
        response = self.client.post(f'/classes/{self.live_class.id}/ajax/end/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['status'], 'COMPLETED')

        self.live_class.refresh_from_db()
        self.assertEqual(self.live_class.status, 'COMPLETED')
        self.assertIsNotNone(self.live_class.actual_end_time)
