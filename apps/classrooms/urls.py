from django.urls import path
from . import views

app_name = 'classrooms'

urlpatterns = [
    path('', views.class_list, name='class_list'),
    path('<int:pk>/', views.class_detail, name='class_detail'),
    # AJAX endpoints
    path('<int:pk>/ajax/start/', views.ajax_start_class, name='ajax_start_class'),
    path('<int:pk>/ajax/end/', views.ajax_end_class, name='ajax_end_class'),
    path('<int:pk>/ajax/join/', views.ajax_join_class, name='ajax_join_class'),
    path('<int:pk>/ajax/attendees/', views.ajax_get_attendees, name='ajax_get_attendees'),
]
