from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/student/', views.register_student, name='register_student'),
    path('register/teacher/', views.register_teacher, name='register_teacher'),
    path('redirect/', views.dashboard_redirect, name='dashboard_redirect'),
    
    # Teacher Management (CRUD)
    path('teachers/', views.teacher_list, name='teacher_list'),
    path('teachers/create/', views.teacher_create, name='teacher_create'),
    path('teachers/<int:pk>/edit/', views.teacher_edit, name='teacher_edit'),
    path('teachers/<int:pk>/delete/', views.teacher_delete, name='teacher_delete'),
    path('teachers/<int:pk>/toggle-status/', views.teacher_toggle_status, name='teacher_toggle_status'),

    # Student Management (CRUD)
    path('students/', views.student_list, name='student_list'),
    path('students/create/', views.student_create, name='student_create'),
    path('students/<int:pk>/approve/', views.student_approve, name='student_approve'),
    path('students/<int:pk>/reject/', views.student_reject, name='student_reject'),
]
