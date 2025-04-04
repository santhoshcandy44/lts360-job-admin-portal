# project/urls.py

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('career-listings/', include('job_portal_app.urls',  namespace='job_portal_app')),  # Include your app's URLs
]
