from django.contrib import admin
from .models import Conversation, ChatMessage


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation_type', 'subject', 'created_at', 'updated_at')
    list_filter = ('conversation_type', 'created_at')
    search_fields = ('participants__username', 'participants__first_name', 'participants__last_name')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender', 'content_preview', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('content', 'sender__username')

    def content_preview(self, obj):
        return obj.content[:50]

