"""
URL configuration for job_portal project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from tkinter.font import names

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views
from .views import DepartmentAutocomplete, IndustryAutocomplete, RoleAutocomplete, SkillsAutocomplete

app_name = 'job_portal_app'  # This defines the namespace

handler404 = 'job_portal_app.views.handler404'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('tinymce/', include('tinymce.urls')),  # TinyMCE URL setup
    path("__reload__/", include("django_browser_reload.urls")),
    path('', views.index, name='index'),
    path('career-listings/login/', views.login_view, name='login_view'),
    path('career-listings/dashboard/', views.dashboard, name='dashboard'),

    path('career-listings/all-job-listings/', views.all_job_listings, name='all_job_listings'),
    path('career-listings/delete/<int:post_id>/', views.delete_listing, name='delete_listing'),
    path('career-listings/add-new-job-listing/', views.add_new_job_listing, name='add_new_job_listing'),

    path('career-listings/listing/edit-job-listing/<int:job_id>/', views.edit_job_listing, name='edit_job_listing'),
    path('career-listings/listing/edit-job-listing/draft-status/<int:job_id>/', views.draft_listing_status,
         name='edit_job_posting_draft_status'),

    path('career-listings/listing/edit-job-listing/publish-status/<int:job_id>/', views.publish_listing_status,
         name='edit_job_posting_publish_status'),

    path('career-listings/listing/edit-job-listing/extend-expiry-date/<int:job_id>/',
         views.publish_listing_extend_expiry_date,
         name='publish_listing_extend_expiry_date'),

    path('career-listings/received-applications/', views.all_listings_with_received_applicants,
         name='all_listings_with_received_applicants'),

    path('career-listings/received-applications/<int:job_id>/applications/', views.job_listing_applicants,
         name='job_listing_applicants'),
    path('career-listings/received-applications/<int:job_id>/applications/applicant/<int:applicant_id>',
         views.manage_applicant, name='manage_applicant'),
    path('career-listings/received-applications/<int:job_id>/applications/applicant/<int:applicant_id>/update-status',
         views.manage_applicant_update_status, name='manage_applicant_update_status'),

    path(
        'career-listings/received-applications/<int:job_id>/applications/applicant/<int:applicant_id>/reject-applicant',
        views.manage_applicant_reject_applicant, name='manage_applicant_reject_applicant'),

    path(
        'career-listings/received-applications/<int:job_id>/applications/applicant/<int:applicant_id>/change-status-top-applicant',
        views.manage_applicant_mark_top_applicant, name='manage_applicant_mark_top_applicant'),

    path('career-listings/company-profile/', views.company_profile, name='company_profile'),
    path('career-listings/recruiter-profile/', views.recruiter_profile, name='recruiter_profile'),
    path('career-listings/recruiter-settings/', views.recruiter_settings, name='recruiter_settings'),

    path('career-listings/account/', views.account, name='account'),
    path('career-listings/profile/email-verification/send-otp/', views.profile_verification_send_otp_to_email,
         name='profile_verification_send_otp_to_email'),
    path('career-listings/profile/email-verification/verify-otp/', views.profile_verification_verify_otp,
         name='profile_verification_verify_otp'),
    path('career-listings/logout/', views.logout_view, name='logout_view'),

    # path('career-listings/plans/', views.plans, name='plans'),

    path('career-listings/department-autocomplete/',
         DepartmentAutocomplete.as_view(),
         name='department-autocomplete'),

    path('career-listings/industry-autocomplete/',
         IndustryAutocomplete.as_view(),
         name='industry-autocomplete'),

    path('career-listings/role-autocomplete/',
         RoleAutocomplete.as_view(),
         name='role-autocomplete'),

    path('career-listings/skills-autocomplete/',
         SkillsAutocomplete.as_view(),
         name='skills-autocomplete'),
    path('google-auth-callback/', views.google_auth_callback, name="google_auth_callback"),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
