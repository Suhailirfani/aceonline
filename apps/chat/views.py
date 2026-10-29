from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib import messages
from django.db.models import Q, Max
from django.utils import timezone
from .models import Conversation, ChatMessage
from apps.accounts.models import CustomUser
from apps.academics.models import Subject


@login_required
def chat_inbox(request, conversation_id=None):
    user = request.user

    # Fetch conversations for the current user
    user_conversations = Conversation.objects.filter(participants=user).annotate(
        last_msg_time=Max('messages__created_at')
    ).order_by('-last_msg_time', '-updated_at')

    # Prepare conversation list with sanitized display info
    conversations_data = []
    for conv in user_conversations:
        partner_info = conv.get_partner_display_info(user)
        unread = conv.unread_count_for(user)
        latest_msg = conv.latest_message
        conversations_data.append({
            'conversation': conv,
            'partner': partner_info,
            'unread_count': unread,
            'latest_message': latest_msg,
        })

    active_conversation = None
    active_partner = None
    messages_list = []

    if conversation_id:
        active_conversation = get_object_or_404(Conversation, id=conversation_id)
        # Check access permission: participant or Admin
        if not (user in active_conversation.participants.all() or user.is_admin_user):
            return HttpResponseForbidden("You do not have permission to view this chat.")
    elif conversations_data:
        active_conversation = conversations_data[0]['conversation']

    if active_conversation:
        active_partner = active_conversation.get_partner_display_info(user)
        # Mark unread messages as read
        active_conversation.messages.filter(is_read=False).exclude(sender=user).update(is_read=True)
        messages_list = active_conversation.messages.select_related('sender').all()

    # Get available contacts to start new chat with
    contacts = []
    admins = CustomUser.objects.filter(Q(role='ADMIN') | Q(is_superuser=True)).distinct().exclude(id=user.id)
    
    if user.is_student:
        # Students can chat with:
        # 1. Teachers teaching their enrolled subjects or assigned to their standard
        teachers = CustomUser.objects.filter(role='TEACHER', is_active=True)
        if hasattr(user, 'student_profile'):
            profile = user.student_profile
            # Prioritize teachers of student's subjects
            sub_teachers = teachers.filter(
                Q(taught_subjects__in=profile.enrolled_subjects.all()) |
                Q(taught_subjects__standard=profile.standard)
            ).distinct()
            if sub_teachers.exists():
                teachers = sub_teachers

        # Add Admins
        for adm in admins:
            contacts.append({
                'id': adm.id,
                'name': 'School Administration',
                'role': 'Admin',
                'badge': 'Admin',
                'subtext': 'Official Support & Queries'
            })

        # Add Teachers - PRIVACY: name only!
        for t in teachers:
            full_name = t.get_full_name() or t.username
            contacts.append({
                'id': t.id,
                'name': full_name,
                'role': 'Teacher',
                'badge': 'Teacher',
                'subtext': 'Teacher'
            })

    elif user.is_teacher:
        # Teachers can chat with:
        # 1. Students in their taught subjects
        taught_subjects = user.taught_subjects.all()
        students = CustomUser.objects.filter(
            role='STUDENT',
            is_active=True,
            student_profile__enrolled_subjects__in=taught_subjects
        ).distinct()
        
        # If no specific subject enrollment found, allow active students
        if not students.exists():
            students = CustomUser.objects.filter(role='STUDENT', is_active=True)

        # Add Admins
        for adm in admins:
            contacts.append({
                'id': adm.id,
                'name': 'School Administration',
                'role': 'Admin',
                'badge': 'Admin',
                'subtext': 'Management'
            })

        # Add Students
        for s in students:
            full_name = s.get_full_name() or s.username
            std_name = s.student_profile.standard.name if hasattr(s, 'student_profile') and s.student_profile.standard else "Student"
            contacts.append({
                'id': s.id,
                'name': full_name,
                'role': 'Student',
                'badge': 'Student',
                'subtext': std_name
            })

    elif user.is_admin_user:
        # Admin can chat with any teacher or student
        teachers = CustomUser.objects.filter(role='TEACHER', is_active=True)
        students = CustomUser.objects.filter(role='STUDENT', is_active=True)

        for t in teachers:
            full_name = t.get_full_name() or t.username
            contacts.append({
                'id': t.id,
                'name': full_name,
                'role': 'Teacher',
                'badge': 'Teacher',
                'subtext': 'Faculty Member'
            })
        for s in students:
            full_name = s.get_full_name() or s.username
            std_name = s.student_profile.standard.name if hasattr(s, 'student_profile') and s.student_profile.standard else "Student"
            contacts.append({
                'id': s.id,
                'name': full_name,
                'role': 'Student',
                'badge': 'Student',
                'subtext': std_name
            })

    context = {
        'conversations_data': conversations_data,
        'active_conversation': active_conversation,
        'active_partner': active_partner,
        'messages_list': messages_list,
        'contacts': contacts,
    }
    return render(request, 'chat/chat_inbox.html', context)


@login_required
def start_or_get_conversation(request, user_id):
    """
    Finds or creates a 1-on-1 conversation between request.user and target user.
    """
    current_user = request.user
    target_user = get_object_or_404(CustomUser, id=user_id)

    if current_user.id == target_user.id:
        messages.error(request, "You cannot chat with yourself.")
        return redirect('chat:inbox')

    # Determine conversation type
    conv_type = 'TEACHER_STUDENT'
    if current_user.is_admin_user or target_user.is_admin_user:
        if current_user.is_student or target_user.is_student:
            conv_type = 'ADMIN_STUDENT'
        else:
            conv_type = 'ADMIN_TEACHER'
    elif (current_user.is_teacher and target_user.is_student) or (current_user.is_student and target_user.is_teacher):
        conv_type = 'TEACHER_STUDENT'
    else:
        # Same role direct chat default
        conv_type = 'TEACHER_STUDENT'

    # Check if a 1-on-1 conversation already exists between these two users
    existing = Conversation.objects.filter(participants=current_user).filter(participants=target_user).first()

    if existing:
        return redirect('chat:chat_thread', conversation_id=existing.id)

    # Create new conversation
    conversation = Conversation.objects.create(conversation_type=conv_type)
    conversation.participants.add(current_user, target_user)

    # Attempt to associate subject if teacher and student
    teacher = current_user if current_user.is_teacher else (target_user if target_user.is_teacher else None)
    if teacher and teacher.taught_subjects.exists():
        conversation.subject = teacher.taught_subjects.first()
        conversation.save()

    return redirect('chat:chat_thread', conversation_id=conversation.id)


@login_required
def send_message_api(request, conversation_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    conversation = get_object_or_404(Conversation, id=conversation_id)
    user = request.user

    # Permission check: must be participant or admin
    if not (user in conversation.participants.all() or user.is_admin_user):
        return JsonResponse({'success': False, 'error': 'Forbidden'}, status=403)

    content = request.POST.get('content', '').strip()
    if not content:
        return JsonResponse({'success': False, 'error': 'Empty message'}, status=400)

    # If Admin is posting into a conversation they aren't directly in, add them or record message
    msg = ChatMessage.objects.create(
        conversation=conversation,
        sender=user,
        content=content
    )
    conversation.updated_at = timezone.now()
    conversation.save(update_fields=['updated_at'])

    # Format sender display name respecting privacy
    sender_name = msg.sender_display_name()

    return JsonResponse({
        'success': True,
        'message': {
            'id': msg.id,
            'content': msg.content,
            'sender_id': user.id,
            'sender_name': sender_name,
            'is_self': True,
            'created_at': timezone.localtime(msg.created_at).strftime('%I:%M %p'),
        }
    })


@login_required
def get_messages_api(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id)
    user = request.user

    if not (user in conversation.participants.all() or user.is_admin_user):
        return JsonResponse({'success': False, 'error': 'Forbidden'}, status=403)

    after_id = request.GET.get('after_id', 0)
    try:
        after_id = int(after_id)
    except ValueError:
        after_id = 0

    messages_qs = conversation.messages.select_related('sender').filter(id__gt=after_id).order_by('created_at')

    # Mark incoming unread messages as read
    conversation.messages.filter(id__gt=after_id, is_read=False).exclude(sender=user).update(is_read=True)

    data = []
    for m in messages_qs:
        data.append({
            'id': m.id,
            'content': m.content,
            'sender_id': m.sender_id,
            'sender_name': m.sender_display_name(),
            'is_self': (m.sender_id == user.id),
            'created_at': timezone.localtime(m.created_at).strftime('%I:%M %p'),
        })

    return JsonResponse({'success': True, 'messages': data})


@login_required
def admin_chat_management(request):
    """
    Dedicated Page for Admin to manage, monitor and audit all chats across the platform.
    """
    if not request.user.is_admin_user:
        messages.error(request, "Access restricted to Administrators.")
        return redirect('dashboard_redirect')

    chat_type = request.GET.get('type', 'ALL')
    search_query = request.GET.get('q', '').strip()
    selected_conv_id = request.GET.get('conv_id', None)

    conversations_qs = Conversation.objects.all().prefetch_related('participants', 'messages')

    if chat_type and chat_type != 'ALL':
        conversations_qs = conversations_qs.filter(conversation_type=chat_type)

    if search_query:
        conversations_qs = conversations_qs.filter(
            Q(participants__first_name__icontains=search_query) |
            Q(participants__last_name__icontains=search_query) |
            Q(participants__username__icontains=search_query) |
            Q(messages__content__icontains=search_query)
        ).distinct()

    # Metrics
    total_conversations = Conversation.objects.count()
    total_messages = ChatMessage.objects.count()
    teacher_student_count = Conversation.objects.filter(conversation_type='TEACHER_STUDENT').count()
    admin_chat_count = Conversation.objects.filter(
        Q(conversation_type='ADMIN_STUDENT') | Q(conversation_type='ADMIN_TEACHER')
    ).count()

    selected_conversation = None
    selected_messages = []
    if selected_conv_id:
        selected_conversation = get_object_or_404(Conversation, id=selected_conv_id)
        selected_messages = selected_conversation.messages.select_related('sender').all()

    context = {
        'conversations': conversations_qs[:50],
        'total_conversations': total_conversations,
        'total_messages': total_messages,
        'teacher_student_count': teacher_student_count,
        'admin_chat_count': admin_chat_count,
        'current_type': chat_type,
        'search_query': search_query,
        'selected_conversation': selected_conversation,
        'selected_messages': selected_messages,
    }
    return render(request, 'chat/admin_manage_chat.html', context)


@login_required
def admin_delete_message(request, message_id):
    """
    Admin moderation: delete an inappropriate message.
    """
    if not request.user.is_admin_user:
        return HttpResponseForbidden("Admin access required.")

    msg = get_object_or_404(ChatMessage, id=message_id)
    conv_id = msg.conversation_id
    msg.delete()
    messages.success(request, "Message deleted successfully by Admin.")
    return redirect(f"/chat/admin-management/?conv_id={conv_id}")
