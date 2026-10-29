import os
import django
from decimal import Decimal
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.accounts.models import StudentProfile, TeacherProfile
from apps.academics.models import Subject, Batch, Enrollment
from apps.classrooms.models import LiveClass, ClassAttendance
from apps.exams.models import Exam, ExamResult

User = get_user_model()


def seed():
    print("== Seeding Demo Data for Online Tuition App... ==")

    # 1. Admin
    admin_user, _ = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@edulive.com',
            'role': 'ADMIN',
            'first_name': 'Principal',
            'last_name': 'Administrator',
            'is_staff': True,
            'is_superuser': True,
        }
    )
    admin_user.set_password('admin123')
    admin_user.save()
    print("  -> Admin created: admin / admin123")

    # 2. Teacher
    teacher_user, _ = User.objects.get_or_create(
        username='sarah_teacher',
        defaults={
            'email': 'sarah@edulive.com',
            'role': 'TEACHER',
            'first_name': 'Sarah',
            'last_name': 'Jenkins',
            'phone': '+1 555-0199',
        }
    )
    teacher_user.set_password('teacher123')
    teacher_user.save()
    TeacherProfile.objects.get_or_create(
        user=teacher_user,
        defaults={
            'qualification': 'M.Sc. Mathematics & Education',
            'subject_specialization': 'Pure Mathematics & Calculus',
            'bio': 'Passionate senior mathematics tutor with 8+ years of online teaching experience.'
        }
    )
    print("  -> Teacher created: sarah_teacher / teacher123")

    # 3. Students
    students_data = [
        ('alex_student', 'Alex', 'Morgan', 'Grade 10', 'David Morgan', '+1 555-0101'),
        ('emma_student', 'Emma', 'Watson', 'Grade 10', 'Claire Watson', '+1 555-0102'),
        ('noah_student', 'Noah', 'Taylor', 'Grade 10', 'Robert Taylor', '+1 555-0103'),
    ]

    student_objs = []
    for uname, fname, lname, grade, parent, pphone in students_data:
        s_user, _ = User.objects.get_or_create(
            username=uname,
            defaults={
                'email': f'{uname}@student.com',
                'role': 'STUDENT',
                'first_name': fname,
                'last_name': lname,
            }
        )
        s_user.set_password('student123')
        s_user.save()
        StudentProfile.objects.get_or_create(
            user=s_user,
            defaults={
                'grade_level': grade,
                'parent_name': parent,
                'parent_phone': pphone,
                'address': '124 Academic Way, Tech City'
            }
        )
        student_objs.append(s_user)
        print(f"  -> Student created: {uname} / student123")

    # 4. Subjects
    sub_math, _ = Subject.objects.get_or_create(
        code='MATH-10',
        defaults={'name': 'Advanced Mathematics', 'description': 'Algebra, Geometry, Trigonometry, and Coordinate Systems'}
    )
    sub_phy, _ = Subject.objects.get_or_create(
        code='PHY-10',
        defaults={'name': 'General Physics', 'description': 'Kinematics, Dynamics, Energy, and Waves'}
    )
    sub_chem, _ = Subject.objects.get_or_create(
        code='CHEM-10',
        defaults={'name': 'Fundamentals of Chemistry', 'description': 'Atomic structure, Bonding, and Periodic table'}
    )
    print("  -> Subjects registered: MATH-10, PHY-10, CHEM-10")

    # 5. Batches
    batch_math, _ = Batch.objects.get_or_create(
        name='Grade 10 - Mathematics Morning Cohort',
        defaults={
            'subject': sub_math,
            'teacher': teacher_user,
            'schedule_info': 'Mon, Wed, Fri - 8:30 AM - 10:00 AM',
            'is_active': True,
        }
    )
    batch_phy, _ = Batch.objects.get_or_create(
        name='Grade 10 - Physics Evening Intensive',
        defaults={
            'subject': sub_phy,
            'teacher': teacher_user,
            'schedule_info': 'Tue & Thu - 5:00 PM - 6:30 PM',
            'is_active': True,
        }
    )
    print("  -> Batches created.")

    # 6. Enrollments
    for st in student_objs:
        Enrollment.objects.get_or_create(student=st, batch=batch_math, defaults={'is_active': True})
    Enrollment.objects.get_or_create(student=student_objs[0], batch=batch_phy, defaults={'is_active': True})
    print("  -> Students enrolled into batches.")

    # 7. Live Classes
    now = timezone.now()

    # Active Live Class
    live_cls, _ = LiveClass.objects.get_or_create(
        title='Chapter 4: Quadratic Equations & Applications',
        batch=batch_math,
        defaults={
            'teacher': teacher_user,
            'meet_link': 'https://meet.google.com/edu-live-demo',
            'scheduled_start': now - timedelta(minutes=15),
            'actual_start_time': now - timedelta(minutes=12),
            'status': 'LIVE',
            'description': 'Discussion on quadratic formula and solving complex word problems.'
        }
    )
    # Mark Alex as already joined
    ClassAttendance.objects.get_or_create(
        live_class=live_cls,
        student=student_objs[0],
        defaults={'joined_at': now - timedelta(minutes=10)}
    )

    # Completed Class
    comp_cls, _ = LiveClass.objects.get_or_create(
        title='Chapter 3: Polynomials and Factoring',
        batch=batch_math,
        defaults={
            'teacher': teacher_user,
            'meet_link': 'https://meet.google.com/edu-past-demo',
            'scheduled_start': now - timedelta(days=2, hours=2),
            'actual_start_time': now - timedelta(days=2, hours=2),
            'actual_end_time': now - timedelta(days=2, hours=0, minutes=45),
            'status': 'COMPLETED',
            'description': 'Mastering grouping and synthetic division.'
        }
    )
    for st in student_objs:
        ClassAttendance.objects.get_or_create(live_class=comp_cls, student=st, defaults={'joined_at': now - timedelta(days=2, hours=1, minutes=58)})

    # Scheduled upcoming class
    LiveClass.objects.get_or_create(
        title='Chapter 5: Arithmetic Progressions & Series',
        batch=batch_math,
        defaults={
            'teacher': teacher_user,
            'meet_link': 'https://meet.google.com/edu-upcoming-demo',
            'scheduled_start': now + timedelta(days=2, hours=10),
            'status': 'SCHEDULED',
            'description': 'Sum of N terms and real-world progressions.'
        }
    )
    print("  -> Live Classes created with Google Meet links.")

    # 8. Exams & Mark Records
    exam_1, _ = Exam.objects.get_or_create(
        title='Quarterly Assessment: Algebra & Polynomials',
        batch=batch_math,
        defaults={
            'subject': sub_math,
            'exam_date': (now - timedelta(days=5)).date(),
            'total_marks': Decimal('100.00'),
            'passing_marks': Decimal('40.00'),
            'description': 'Comprehensive unit exam covering sections 1 through 3.',
            'created_by': teacher_user
        }
    )

    # Exam results
    ExamResult.objects.get_or_create(
        exam=exam_1,
        student=student_objs[0],
        defaults={'marks_obtained': Decimal('92.50'), 'remarks': 'Exceptional problem solving and neat presentation!'}
    )
    ExamResult.objects.get_or_create(
        exam=exam_1,
        student=student_objs[1],
        defaults={'marks_obtained': Decimal('85.00'), 'remarks': 'Great conceptual clarity.'}
    )
    ExamResult.objects.get_or_create(
        exam=exam_1,
        student=student_objs[2],
        defaults={'marks_obtained': Decimal('74.00'), 'remarks': 'Good effort. Review factoring quadratics.'}
    )

    # Exam 2 (with pending entry for demoing teacher marks entry)
    exam_2, _ = Exam.objects.get_or_create(
        title='Mid-term Assessment: Coordinate Geometry',
        batch=batch_math,
        defaults={
            'subject': sub_math,
            'exam_date': now.date(),
            'total_marks': Decimal('50.00'),
            'passing_marks': Decimal('20.00'),
            'description': 'Distance formula, section formula, and area of triangles.',
            'created_by': teacher_user
        }
    )
    for st in student_objs:
        ExamResult.objects.get_or_create(exam=exam_2, student=st)

    print("  -> Exams & Marks generated successfully.")
    print("\nDatabase successfully seeded with demo accounts & records!")


if __name__ == '__main__':
    seed()
