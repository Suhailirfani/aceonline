from django.urls import path
from . import views

app_name = 'academics'

urlpatterns = [
    # Standards (Classes e.g. 1st Standard to M.Com)
    path('standards/', views.standard_list, name='standard_list'),
    path('standards/<int:pk>/edit/', views.standard_edit, name='standard_edit'),
    path('standards/<int:pk>/delete/', views.standard_delete, name='standard_delete'),

    # Dynamic API for Standard -> Subjects lookup
    path('api/standards/<int:standard_id>/subjects/', views.api_standard_subjects, name='api_standard_subjects'),

    # Subjects (mapped per Standard)
    path('subjects/', views.subject_list, name='subject_list'),

    # On-Demand Subjects (Student Requests & Admin Review)
    path('on-demand-subjects/', views.on_demand_list, name='on_demand_list'),
    path('on-demand-subjects/<int:pk>/approve/', views.on_demand_approve, name='on_demand_approve'),
    path('on-demand-subjects/<int:pk>/reject/', views.on_demand_reject, name='on_demand_reject'),

    # Batches
    path('batches/', views.batch_list, name='batch_list'),
    path('batches/<int:pk>/', views.batch_detail, name='batch_detail'),
]
