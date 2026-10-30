import os
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from apps.accounts.views import login_view, logout_view, dashboard_redirect, landing_page


def service_worker(request):
    sw_path = os.path.join(settings.BASE_DIR, 'static', 'sw.js')
    if os.path.exists(sw_path):
        with open(sw_path, 'rb') as f:
            content = f.read()
        response = HttpResponse(content, content_type='application/javascript')
        response['Service-Worker-Allowed'] = '/'
        return response
    return HttpResponse('// sw not found', status=404)


def manifest_json(request):
    manifest_path = os.path.join(settings.BASE_DIR, 'static', 'manifest.json')
    if os.path.exists(manifest_path):
        with open(manifest_path, 'rb') as f:
            content = f.read()
        return HttpResponse(content, content_type='application/manifest+json')
    return HttpResponse('{}', status=404)


urlpatterns = [
    path('sw.js', service_worker, name='service_worker'),
    path('manifest.json', manifest_json, name='manifest_json'),
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
