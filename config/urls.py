from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.accounts.views import login_view, logout_view, dashboard_redirect, landing_page

urlpatterns = [
    path('', landing_page, name='home'),
    path('dashboard-redirect/', dashboard_redirect, name='dashboard_redirect'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('academics/', include('apps.academics.urls', namespace='academics')),
    path('classes/', include('apps.classrooms.urls', namespace='classrooms')),
    path('exams/', include('apps.exams.urls', namespace='exams')),
    path('chat/', include('apps.chat.urls', namespace='chat')),
    path('dashboard/', include('apps.dashboards.urls', namespace='dashboards')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
