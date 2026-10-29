from django.urls import path
from . import views

app_name = 'exams'

urlpatterns = [
    path('', views.exam_list, name='exam_list'),
    path('<int:pk>/marks/', views.marks_entry, name='marks_entry'),
    path('<int:pk>/ajax/save-mark/', views.ajax_save_mark, name='ajax_save_mark'),
    path('my-results/', views.student_my_results, name='student_results'),
]
