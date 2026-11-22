from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

urlpatterns = [
    path('favicon.ico', lambda r: HttpResponse(b'', content_type='image/x-icon')),
    path('admin/', admin.site.urls),
    path('', include('assistant.urls')),
]
