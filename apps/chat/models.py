from django.db import models
from django.conf import settings


class Conversation(models.Model):
    TYPE_CHOICES = (
        ('TEACHER_STUDENT', 'Teacher & Student'),
        ('ADMIN_STUDENT', 'Admin & Student'),
        ('ADMIN_TEACHER', 'Admin & Teacher'),
    )

    conversation_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='chat_conversations'
    )
    subject = models.ForeignKey(
        'academics.Subject',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_conversations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        p_names = ", ".join([u.get_full_name() or u.username for u in self.participants.all()[:2]])
        return f"Chat ({self.get_conversation_type_display()}): {p_names}"

    def get_other_participant(self, current_user):
        """Returns the other participant in a 1-on-1 conversation."""
        return self.participants.exclude(id=current_user.id).first()

    def get_partner_display_info(self, current_user):
        """
        Returns sanitized display info for the chat partner.
        Teacher Privacy: ONLY teacher full_name/username is exposed. NO phone or email.
        """
        other = self.get_other_participant(current_user)
        if not other:
            return {
                'name': 'Tuition Support',
                'role': 'Support',
                'badge': 'Support',
                'initial': 'S'
            }

        full_name = other.get_full_name() or other.username
        initial = full_name[0].upper() if full_name else '?'

        if other.is_teacher:
            # Teacher Privacy Rule: strictly show name only!
            return {
                'id': other.id,
                'name': full_name,
                'role': 'Teacher',
                'badge': 'Teacher',
                'initial': initial,
                'subtext': f"Subject: {self.subject.name}" if self.subject else "Teacher"
            }
        elif other.is_admin_user:
            return {
                'id': other.id,
                'name': 'School Administration' if not current_user.is_admin_user else full_name,
                'role': 'Admin',
                'badge': 'Admin',
                'initial': 'A',
                'subtext': 'Official Admin'
            }
        else:
            # Student
            subtext = "Student"
            if hasattr(other, 'student_profile') and other.student_profile.standard:
                subtext = f"Class: {other.student_profile.standard.name}"
            return {
                'id': other.id,
                'name': full_name,
                'role': 'Student',
                'badge': 'Student',
                'initial': initial,
                'subtext': subtext
            }

    @property
    def latest_message(self):
        return self.messages.order_by('-created_at').first()

    def unread_count_for(self, user):
        return self.messages.filter(is_read=False).exclude(sender=user).count()


class ChatMessage(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username}: {self.content[:30]}"

    def sender_display_name(self):
        """
        Enforce privacy: Teacher's name only.
        """
        if self.sender.is_teacher:
            return self.sender.get_full_name() or self.sender.username
        elif self.sender.is_admin_user:
            return "Admin"
        else:
            return self.sender.get_full_name() or self.sender.username

