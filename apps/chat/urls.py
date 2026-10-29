from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.chat_inbox, name='inbox'),
    path('thread/<int:conversation_id>/', views.chat_inbox, name='chat_thread'),
    path('start/<int:user_id>/', views.start_or_get_conversation, name='start_chat'),
    path('api/send/<int:conversation_id>/', views.send_message_api, name='api_send'),
    path('api/messages/<int:conversation_id>/', views.get_messages_api, name='api_messages'),
    path('admin-management/', views.admin_chat_management, name='admin_management'),
    path('admin/delete-message/<int:message_id>/', views.admin_delete_message, name='admin_delete_message'),
]

