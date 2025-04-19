import datetime
import json
import random
from datetime import timedelta

import jwt
import requests
from dal import autocomplete
from django.contrib.auth import login, get_user_model, logout
from django.core.mail import send_mail
from django.db import connections
from django.db.models import Count, Q
from django.http import JsonResponse, Http404
from django.utils import timezone
from django.utils.timezone import now

from job_portal import settings
from .forms import JobPostingForm
from .forms import OrganizationProfileForm, RecruiterProfileForm, RecruiterSettingsForm
from .models import OrganizationProfile, RecruiterProfile, Department, Industry, Role, Skills, \
    RecruiterSettings, Plan, SalaryMarket, Education


def index(request):
    return render(request, "job_portal/index.html")


# Function to generate tokens
def generate_ar_tokens(user_id, email, role='User', sign_up_method='web'):
    user_id_str = str(user_id)
    issued_at = datetime.datetime.now(datetime.timezone.utc)
    # Create the payload for the access token
    access_payload = {
        'sub': user_id_str,  # subject (user's unique identifier)
        'userId': user_id,
        'email': email,
        'role': role,
        'signUpMethod': sign_up_method,
        'iat': issued_at,  # issued at time
        'exp': issued_at + datetime.timedelta(minutes=15)  # expire in 15 minutes
    }

    # Create the access token (short-lived)
    access_token = jwt.encode(access_payload, settings.ACCESS_TOKEN_SECRET, algorithm="HS256")

    # Create the payload for the refresh token
    refresh_payload = {
        'sub': user_id_str,
        'userId': user_id,
        'email': email,
        'role': role,
        'signUpMethod': sign_up_method,
        'iat': issued_at,  # issued at time
        'exp': issued_at + datetime.timedelta(days=90)  # expire in 90 days
    }

    # Create the refresh token (long-lived)
    refresh_token = jwt.encode(refresh_payload, settings.REFRESH_TOKEN_SECRET, algorithm="HS256")

    return access_token, refresh_token


def google_auth_callback(request):
    # Handle the OAuth callback
    if 'code' in request.GET:
        # Exchange authorization code for tokens
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            'code': request.GET['code'],
            'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
            'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
            'redirect_uri': settings.GOOGLE_REDIRECT_URI,
            'grant_type': 'authorization_code',
        }

        response = requests.post(token_url, data=data)
        token_data = response.json()
        # Render a page that sends tokens to parent
        return render(request, 'job_portal/auth/oauth_callback.html', {
            'token_data': token_data
        })

    return JsonResponse({'error': 'No code provided'}, status=400)


def login_view(request):
    errors = []  # Initialize an empty list to hold error messages
    # Check if the user is already logged in before processing GET or POST

    if request.user.is_authenticated:
        return redirect('/career-listings/dashboard/')  # Redirect to home if the user is already logged in

    if request.method == 'POST':

        method = request.POST.get('method')

        if method == "google":

            id_token = request.POST.get('id_token')
            sign_in_method = method

            if not id_token:
                errors.append("Something went wrong")
                return render(request, "job_portal/login.html", {'errors': errors})

            api_url = 'https://api.lts360.com/api/auth/partner/google-sign-in/'  # External API for login
            try:
                response = requests.post(api_url, data={'id_token': id_token, 'sign_in_method': sign_in_method})

                if response.status_code == 200 or response.status_code == 201:
                    api_response = response.json()

                    # Assuming the API response structure contains 'isSuccessful' and 'data' fields
                    if api_response.get('isSuccessful'):
                        # Assuming 'data' contains user info
                        data = json.loads(api_response['data'])
                        # Extract required details from the response
                        user_details = data.get('user_details')
                        user_id = user_details.get('user_id')
                        email = user_details.get('email')
                        first_name= user_details.get('first_name')
                        last_name= user_details.get('last_name')


                        access_token, refresh_token = generate_ar_tokens(user_id, email)

                        # Check if the user exists in the Django database using the email
                        user = get_user_model().objects.filter(external_user_id=user_id).first()

                        if not user:
                            # If the user does not exist, create a new user
                            user = get_user_model().objects.create_user(
                                external_user_id=user_id,
                                email='',
                                username=user_id,  # Assuming email as the username
                                first_name='',
                                last_name= '',
                                password=''
                            )

                        # Create or update the UserProfile with external data (user_id)
                        user_profile, created = RecruiterProfile.objects.get_or_create(user=user)
                        user_profile.external_user_id = user_id
                        user_profile.first_name = first_name
                        user_profile.last_name = last_name
                        user_profile.email = email
                        user_profile.is_verified = True
                        user_profile.save()

                        # Log the user in
                        login(request, user)

                        # Set the access_token and refresh_token as HttpOnly cookies
                        response = redirect('/career-listings/dashboard/')  # Redirect to the dashboard

                        # Set cookies with the tokens
                        response.set_cookie(
                            'access_token',
                            access_token,
                            httponly=True,
                            secure=settings.SESSION_COOKIE_SECURE,
                            samesite='Strict',
                            max_age=15 * 60  # 15 minutes in seconds
                        )
                        response.set_cookie(
                            'refresh_token',
                            refresh_token,
                            httponly=True,
                            secure=settings.SESSION_COOKIE_SECURE,
                            samesite='Strict',
                            max_age=90 * 24 * 60 * 60  # 90 days in seconds
                        )

                        # Redirect after setting cookies
                        return response

                    else:
                        errors.append("Authentication failed: " + api_response.get('message', 'Unknown error'))
                else:
                    response_error = response.json()
                    error_message = response_error.get('message')
                    errors.append(error_message if error_message else "Something went wrong")

            except requests.exceptions.RequestException:
                errors.append(f"Something went wrong")

        else:
            email = request.POST.get('email')
            password = request.POST.get('password')

            if not email or not password:
                errors.append("Email and password are required.")
                return render(request, "login.html", {'errors': errors})

            api_url = 'https://api.lts360.com/api/auth/partner/legacy-email-login/'  # External API for login
            try:
                response = requests.post(api_url, data={'email': email, 'password': password})

                if response.status_code == 200 or response.status_code == 201:
                    api_response = response.json()

                    # Assuming the API response structure contains 'isSuccessful' and 'data' fields
                    if api_response.get('isSuccessful'):
                        # Assuming 'data' contains user info
                        data = json.loads(api_response['data'])
                        user_details = data.get('user_details')
                        user_id = user_details.get('user_id')
                        email = user_details.get('email')
                        first_name = user_details.get('first_name')
                        last_name = user_details.get('last_name')
                        access_token, refresh_token = generate_ar_tokens(user_id, email)

                        # Check if the user exists in the Django database using the email
                        user = get_user_model().objects.filter(external_user_id=user_id).first()

                        if not user:
                            # If the user does not exist, create a new user
                            user = get_user_model().objects.create_user(
                                external_user_id=user_id,
                                email='',
                                username=user_id,  # Assuming email as the username
                                first_name='',
                                last_name='',
                                password=''
                            )

                        # Create or update the UserProfile with external data (user_id)
                        user_profile, created = RecruiterProfile.objects.get_or_create(user=user)
                        user_profile.external_user_id = user_id
                        user_profile.first_name = first_name
                        user_profile.last_name = last_name
                        user_profile.email = email
                        user_profile.is_verified = True
                        user_profile.save()

                        RecruiterSettings.objects.get_or_create(user=user_profile)

                        # Log the user in
                        login(request, user)




                        # Set the access_token and refresh_token as HttpOnly cookies
                        response = redirect('/career-listings/dashboard/')  # Redirect to the dashboard

                        # Set cookies with the tokens
                        response.set_cookie(
                            'access_token',
                            access_token,
                            httponly=True,
                            secure=settings.SESSION_COOKIE_SECURE,
                            samesite='Strict',
                            max_age=15 * 60  # 15 minutes in seconds
                        )
                        response.set_cookie(
                            'refresh_token',
                            refresh_token,
                            httponly=True,
                            secure=settings.SESSION_COOKIE_SECURE,
                            samesite='Strict',
                            max_age=90 * 24 * 60 * 60  # 90 days in seconds
                        )

                        # Redirect after setting cookies
                        return response

                    else:
                        errors.append("Authentication failed: " + api_response.get('message', 'Unknown error'))
                else:
                    response_error = response.json()
                    error_message = response_error.get('message')
                    errors.append(error_message if error_message else "Something went wrong")

            except requests.exceptions.RequestException:
                errors.append(f"Something went wrong")

    return render(request, "job_portal/login.html", {'errors': errors})


def dashboard(request):
    # Get duration filter (default to 1 days)
    duration = request.GET.get('duration', '7')

    # Calculate date range
    end_date = timezone.now().date()

    if duration == 'custom':
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date') or end_date
        try:
            start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            start_date = end_date - timedelta(days=7)
    elif duration == '1':  # Today
        start_date = end_date  # Today only, so start_date = end_date
    elif duration == '7':  # Last 7 days
        start_date = end_date - timedelta(days=7)
    elif duration == '30':  # Last 30 days
        start_date = end_date - timedelta(days=30)
    elif duration == '90':  # Last 90 days
        start_date = end_date - timedelta(days=int(duration) - 1)  # -1 to include today

    # Filter JobPostings by recruiter (user profile) and date range
    jobs = JobPosting.objects.filter(
        posted_by=request.user.profile,
        posted_at__date__range=[start_date, end_date]
    )

    # Filter JobApplications for those jobs and date range
    applicants = Application.objects.filter(
        job_listing__in=jobs,
        applied_at__date__range=[start_date, end_date]
    )

    # Calculate metrics
    total_jobs = jobs.count()
    total_applicants = applicants.count()
    hired_applicants = applicants.filter(status='hired').count()
    rejected_applicants = applicants.filter(is_rejected=True).count()

    hired_percentage = round((hired_applicants / total_applicants * 100) if total_applicants > 0 else 0, 1)

    # Get top job by number of applicants
    top_job = jobs.annotate(num_applicants=Count('applications')).order_by('-num_applicants').first()

    # Prepare chart data
    applications_timeline = {
        'labels': [],  # Dates
        'data': []  # Application counts per day
    }

    status_distribution = {
        'labels': ['Applied', 'Viewed', 'Interview', 'Hired', 'Rejected'],
        'data': [
            applicants.filter(status='applied').count(),
            applicants.filter(status='viewed').count(),
            applicants.filter(status='interview').count(),
            applicants.filter(status='hired').count(),
            rejected_applicants
        ]
    }

    # Generate timeline data based on selected duration
    delta = end_date - start_date
    num_days = delta.days + 1  # Include both start and end dates

    # For single day (Today)
    if num_days == 1:
        applications_timeline['labels'].append(start_date.strftime('%b %d'))
        applications_timeline['data'].append(total_applicants)
    # For longer durations (>30 days), group by week
    elif num_days > 30:
        current_date = start_date
        while current_date <= end_date:
            week_start = current_date
            week_end = min(current_date + timedelta(days=6), end_date)

            week_count = applicants.filter(
                applied_at__date__range=[week_start, week_end]
            ).count()

            applications_timeline['labels'].append(
                f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}"
            )
            applications_timeline['data'].append(week_count)
            current_date = week_end + timedelta(days=1)
    else:
        # Group by day
        for i in range(num_days):
            date = start_date + timedelta(days=i)
            applications_timeline['labels'].append(date.strftime('%b %d'))
            applications_timeline['data'].append(
                applicants.filter(applied_at__date=date).count()
            )

    # Get activities filtered by the selected date range
    recent_activities = []

    # Get jobs posted in date range
    jobs_for_activity = JobPosting.objects.filter(
        posted_by=request.user.profile,
        posted_at__date__range=[start_date, end_date]
    )

    # Get applications in date range
    applications_for_activity = Application.objects.filter(
        job_listing__posted_by=request.user.profile,
        applied_at__date__range=[start_date, end_date]
    )

    # Combine activities
    for job in jobs_for_activity:
        recent_activities.append({
            'activity': 'New Job Posted',
            'date': job.posted_at,
            'details': f"Job titled '{job.title}' posted.",
            'type': 'job'
        })

    for application in applications_for_activity:
        recent_activities.append({
            'activity': 'New Application',
            'date': application.applied_at,
            'details': f"Applicant {application.user.get_full_name()} applied for '{application.job_listing.title}'.",
            'type': 'application'
        })

    # Sort by most recent first
    recent_activities.sort(key=lambda x: x['date'], reverse=True)

    context = {
        'duration': duration,
        'start_date': start_date,
        'end_date': end_date,
        'total_jobs': total_jobs,
        'total_applicants': total_applicants,
        'hired_applicants': hired_applicants,
        'hired_percentage': hired_percentage,
        'top_job': {
            'title': top_job.title if top_job else 'No jobs',
            'applicants': top_job.num_applicants if top_job else 0
        },
        'applications_timeline': applications_timeline,
        'status_distribution': status_distribution,
        'recent_activities': recent_activities[:10]  # Limit to 10 most recent
    }

    return render(request, 'job_portal/dashboard.html', context)


def add_new_job_listing(request):
    # For testing purposes, manually set the user_id (e.g., user_id=1 or another valid test ID)
    SalaryMarket.create_default_salary_markets()
    # Check if the user has a company profile
    try:
        company_profile = OrganizationProfile.objects.get(user=request.user.profile)  # Use test_user_id here
    except OrganizationProfile.DoesNotExist:
        company_profile = None
    # Validate if the company profile is complete
    company_profile_complete = True

    if company_profile:
        if not company_profile.is_complete():
            # If company profile is incomplete, set the flag to show the alert
            company_profile_complete = False
    else:
        # If company profile does not exist, set the flag to show the alert
        company_profile_complete = False

    recruiter_settings_db = RecruiterSettings.objects.get(user=request.user.profile)
    recruiter_profile_complete = request.user.profile.is_profile_complete()
    currency_type = recruiter_settings_db.currency_type
    salary_market = SalaryMarket.objects.get(currency_type=currency_type)

    salary_markers = {
        'start':  salary_market.format_currency_salary_start(),
        'middle': salary_market.format_currency_salary_middle(),  # 500K
        'end': salary_market.format_currency_salary_end(),  # 1M
        'currency_symbol': salary_market.currency_symbol()
    }

    # Proceed with the job posting form
    if request.method == 'POST':
        form = JobPostingForm(request.POST, currency_type=currency_type, user=request.user.profile)
        if form.is_valid():

            form = form.save(commit=False)
            form.posted_by = request.user.profile
            form.organization_id = company_profile.organization_id
            form.save()
            return redirect('/career-listings/all-job-listings/')  # Redirect to a success page
        else:
            # In case of form errors, the form will be re-rendered with error messages
            return render(request, 'job_portal/add_new_listing.html',
                          {'form': form, 'company_profile_complete': company_profile_complete,
                           'recruiter_profile_complete': recruiter_profile_complete,
                           'salary_markers': salary_markers,
                           'can_post_job': company_profile_complete and recruiter_profile_complete})
    else:
        form = JobPostingForm(currency_type=currency_type, user=request.user.profile)  # Empty form for GET request

    return render(request, 'job_portal/add_new_listing.html',
                  {'form': form, 'company_profile_complete': company_profile_complete,
                   'recruiter_profile_complete': recruiter_profile_complete,
                   'salary_markers': salary_markers,
                   'can_post_job': company_profile_complete and recruiter_profile_complete})


def all_job_listings(request):
    # Start with base queryset
    queryset = JobPosting.objects.filter(posted_by=request.user.profile)

    # Apply experience filter if provided
    experience_filter = request.GET.get('experience')
    if experience_filter:
        if experience_filter == "Entry Level":
            queryset = queryset.filter(
                Q(experience_range_min__gte=0, experience_range_max__lte=2) |
                Q(experience_fixed__lte=2)  # Jobs where fixed experience ≤ 2 years
            )
        elif experience_filter == "Mid Level":
            queryset = queryset.filter(
                Q(experience_range_min__gte=2, experience_range_max__lte=5) |
                Q(experience_fixed__range=(2, 5))  # Jobs where fixed experience is 2-5 years
            )
        elif experience_filter == "Senior Level":
            queryset = queryset.filter(
                Q(experience_range_min__gte=5) |
                Q(experience_fixed__gte=5)  # Jobs where fixed experience ≥ 5 years
            )
        elif experience_filter == "Executive":
            queryset = queryset.filter(
                Q(experience_range_min__gte=10) |
                Q(experience_fixed__gte=10)  # Jobs where fixed experience ≥ 10 years
            )


    if 'work_mode' in request.GET:
        queryset = queryset.filter(work_mode=request.GET['work_mode'])

    if all(k in request.GET for k in ['date_from', 'date_to']):
        try:
            date_from = timezone.datetime.strptime(request.GET['date_from'], '%Y-%m-%d').date()
            date_to = timezone.datetime.strptime(request.GET['date_to'], '%Y-%m-%d').date()
            queryset = queryset.filter(
                posted_at__date__range=[date_from, date_to]
            )
        except ValueError:
            pass  # Handle invalid date format

    # Order and paginate
    queryset = queryset.order_by('-posted_at')
    paginator = Paginator(queryset, settings.ALL_JOBS_PAGINATION_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get('page'))
    active_filters = {
        'experience': request.GET.get('experience'),
        'work_mode': request.GET.get('work_mode'),
        'date_from': request.GET.get('date_from'),
        'date_to': request.GET.get('date_to'),
    }



    all_none = all(not value for value in active_filters.values())  # True if all are None or ""
    return render(request, 'job_portal/all_listings.html', {
        'page_obj': page_obj,
        'active_filters': active_filters,
        'is_filters_applied': not all_none
    })


def edit_job_listing(request, job_id):
    # Fetch the job posting by its ID
    recruiter_settings_db = RecruiterSettings.objects.get(user=request.user.profile)
    recruiter_profile_complete = request.user.profile.is_profile_complete()
    currency_type = recruiter_settings_db.currency_type
    salary_market = SalaryMarket.objects.get(currency_type = currency_type)

    salary_markers = {
        'start': salary_market.format_currency_salary_start(),
        'middle': salary_market.format_currency_salary_middle(),  # 500K
        'end': salary_market.format_currency_salary_end(),  # 1M
        'currency_symbol': salary_market.currency_symbol()
    }


    job_posting = get_object_or_404(JobPosting, pk=job_id)

    if request.method == 'POST':
        form = JobPostingForm(request.POST, instance=job_posting, currency_type=currency_type,user=request.user.profile)
        if form.is_valid():
            form.save()
            return redirect('edit_job_listing', job_id=job_id)  # Redirect after successful edit
        else:
            # In case of form errors, the form will be re-rendered with error messages
            return render(request, 'job_portal/edit_career_listing.html',
                          {'form': form,
                           'job_posting': job_posting,
                           'recruiter_profile_complete': recruiter_profile_complete,
                           'salary_markers': salary_markers})

    else:
        form = JobPostingForm(instance=job_posting, currency_type=currency_type, user=request.user.profile)  # Pre-populate the form with the existing job data


    return render(request, 'job_portal/edit_career_listing.html', {'form': form, 'job_posting': job_posting,
                                                                'recruiter_profile_complete': recruiter_profile_complete,
                                                                'salary_markers': salary_markers
                                                                })


def draft_listing_status(request, job_id):
    """Manually update job status to 'draft' and redirect to the same page."""
    listing = get_object_or_404(JobPosting, id=job_id)

    # Update status to draft
    listing.status = "draft"
    listing.save()  # Save the changes

    # Redirect back to the edit page
    return redirect('edit_job_listing', job_id=job_id)  # Redirect after successful edit


def  publish_listing_status(request, job_id):
    """Manually update job status to 'draft' and redirect to the same page."""
    listing = get_object_or_404(JobPosting, id=job_id)

    # Update status to draft
    listing.status = "published"
    listing.save()  # Save the changes

    # Redirect back to the edit page
    return redirect('edit_job_listing', job_id=job_id)  # Redirect after successful edit


def publish_listing_extend_expiry_date(request, job_id):
    """Update job expiry date with AJAX handling."""
    listing = get_object_or_404(JobPosting, id=job_id)

    if request.method == 'POST':
        new_expiry_date_str = request.POST.get('new_expiry_date')

        try:
            # Parse the date
            new_expiry_date = now().date() if not new_expiry_date_str else \
                now().strptime(new_expiry_date_str, '%Y-%m-%d').date()

            today = now().date()
            max_date = today + timedelta(days=30)

            # Validate
            if new_expiry_date == today:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Expiry date cannot be today'
                }, status=400)
            if new_expiry_date < today:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Expiry date cannot be in the past'
                }, status=400)

            elif new_expiry_date > max_date:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Expiry date cannot be more than 30 days from now'
                }, status=400)

            # Update listing
            listing.status = "published"
            listing.expiry_date = new_expiry_date
            listing.save()

            return JsonResponse({
                'status': 'success',
                'message': 'Deadline extended successfully',
                'new_date': new_expiry_date.strftime('%Y-%m-%d')
            })

        except ValueError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid date format'
            }, status=400)

    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=405)



def delete_listing(request, post_id):
    if request.method == 'DELETE':  # Ensure that the method is DELETE
        # Retrieve the job posting or return a 404 error if not found
        listing = get_object_or_404(JobPosting, id=post_id)

        # Perform the deletion
        listing.delete()

        # Return a JSON response confirming successful deletion
        return JsonResponse({'message': 'Posting deleted successfully'}, status=200)
    else:
        # If it's not a DELETE request, return method not allowed
        return JsonResponse({'message': 'Invalid method'}, status=405)


from django.core.paginator import Paginator
from django.conf import settings

def all_listings_with_received_applicants(request):
    # Query to get job postings created by the user, sorted by the latest 'posted_at'
    job_postings = JobPosting.objects.filter(posted_by=request.user.profile) \
        .order_by('-posted_at')

    # Add pagination for job postings
    paginator = Paginator(job_postings, settings.ALL_JOBS_PAGINATION_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Create a list to hold job postings along with their applicants
    job_postings_with_applicants = []

    # For each job posting, get the related applicants (using job_id)
    for job in page_obj:
        applicants = job.applications.all().order_by('-applied_at')
        num_applicants = applicants.count()
        extra_applicants = num_applicants - 3 if num_applicants > 3 else 0

        job_postings_with_applicants.append({
            'job': job,
            'applicants': applicants[:3],  # Only get first 3 for display
            'num_applicants': num_applicants,
            'extra_applicants': extra_applicants
        })

    return render(request, 'job_portal/all_listings_with_applicants.html', {
        'job_postings_with_applicants': job_postings_with_applicants,
        'page_obj': page_obj,  # Pass pagination object to template
    })


def job_listing_applicants(request, job_id):
    # Get the job posting by ID
    job_posting = get_object_or_404(JobPosting, pk=job_id)

    # Query the JobApplication model to get all applications for this job
    applicants = job_posting.applications.all().order_by('-applied_at')

    # Add pagination for applicants
    paginator = Paginator(applicants, settings.ALL_JOBS_PAGINATION_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'job_portal/listing_applicants.html', {
        'job': job_posting,
        'applicants': page_obj,  # Pass paginated applicants
        'page_obj': page_obj  # Pass pagination object to template
    })


def manage_applicant(request, job_id, applicant_id):
    # Get the job posting by ID
    job_posting = get_object_or_404(JobPosting, pk=job_id)

    # Query the JobApplication model to get the application for this job by this user
    applicant = get_object_or_404(Application, user_id=applicant_id, job_listing=job_posting)

    # Check if applicant is rejected
    is_rejected = applicant.is_rejected

    # Define your status workflow
    status_workflow = [
        {'id': 'applied', 'name': 'Applied', 'order': 1},
        {'id': 'viewed', 'name': 'Viewed', 'order': 2},
        {'id': 'interview', 'name': 'Interview', 'order': 3},
        {'id': 'offer', 'name': 'Offer', 'order': 4},
        {'id': 'hired', 'name': 'Hired', 'order': 5}
    ]

    # Get the current status of the applicant
    last_status = next(s for s in status_workflow if s['id'] == applicant.status)

    # Calculate progress
    last_step = last_status['order']
    total_steps = len([s for s in status_workflow])  # Exclude Rejected

    # Ensure total_steps is not zero (for safety, to avoid division by zero)
    if total_steps == 0:
        total_steps = 1  # You can adjust the fallback value as needed

    progress_percentage = (last_step / total_steps) * 100 if not is_rejected else 100

    # Available statuses for dropdown (exclude previous steps if not rejected)
    if is_rejected:
        available_statuses = []  # No available statuses if the applicant is rejected
    else:
        available_statuses = [s for s in status_workflow if s['order'] > last_status['order']]

    return render(request, 'job_portal/manage_applicant.html', {
        'job': job_posting,
        'applicant': applicant,
        'statuses': [s for s in status_workflow if s['order'] < 50],  # Exclude Rejected
        'current_status': last_status,
        'current_step': last_step,
        'total_steps': total_steps,
        'progress_percentage': progress_percentage,
        'available_statuses': available_statuses,
        'is_rejected': is_rejected
    })


from django.shortcuts import get_object_or_404, redirect, render
from .forms import UpdateStatusForm
from .models import JobPosting, Application

def manage_applicant_update_status(request, job_id, applicant_id):
    # Define your status workflow with order
    status_workflow = [
        {'id': 'applied', 'name': 'Applied', 'order': 1},
        {'id': 'viewed', 'name': 'Viewed', 'order': 2},
        {'id': 'interview', 'name': 'Interview', 'order': 3},
        {'id': 'offer', 'name': 'Offer', 'order': 4},
        {'id': 'hired', 'name': 'Hired', 'order': 5}
    ]

    # Get the job posting by ID
    job_posting = get_object_or_404(JobPosting, pk=job_id)

    # Get the applicant's job application
    applicant = get_object_or_404(Application, user_id=applicant_id, job_listing=job_posting)

    # Get the current status order of the applicant
    current_status = applicant.status
    current_status_order = next((status['order'] for status in status_workflow if status['id'] == current_status), None)

    # Only process the form for POST request
    if request.method == 'POST':
        form = UpdateStatusForm(request.POST, instance=applicant)

        if form.is_valid():
            new_status = form.cleaned_data['status']
            new_status_order = next((status['order'] for status in status_workflow if status['id'] == new_status), None)

            # Ensure the new status is moving forward (not backward)
            if new_status_order is not None and new_status_order <= current_status_order:
                return redirect('manage_applicant', job_id=job_posting.id, applicant_id=applicant.id)

            # If the status change is valid, update the status
            applicant.update_status(new_status)
            # Redirect back to the applicant's details or to the applicant list
            return redirect('manage_applicant', job_id=job_posting.id, applicant_id=applicant.id)
        else:
            # If form is not valid, return the form with errors to the template
            return render(request, 'job_portal/manage_applicant.html', {
                'job': job_posting,
                'applicant': applicant,
                'form': form,
            })

    else:
        # If GET request, return a 405 Method Not Allowed error (or handle with a redirect)
        return redirect('manage_applicant', job_id=job_posting.id, applicant_id=applicant.id)



def manage_applicant_reject_applicant(request, job_id, applicant_id):
    if request.method == 'POST':
        # Get the job posting and the applicant's job application
        job_posting = get_object_or_404(JobPosting, pk=job_id)
        applicant = get_object_or_404(Application, user_id=applicant_id, job_listing=job_posting)

        # Update the status to 'rejected'
        applicant.reject()

        return redirect('manage_applicant', job_id=job_posting.id, applicant_id=applicant.id)
    else:
        return JsonResponse({'message': 'Invalid method'}, status=405)


def manage_applicant_mark_top_applicant(request, job_id, applicant_id):
    if request.method == 'POST':
        # Get the job posting and the applicant's job application
        job_posting = get_object_or_404(JobPosting, pk=job_id)
        applicant = get_object_or_404(Application, user_id=applicant_id, job_listing=job_posting)
        applicant.update_top_applicant(False if applicant.is_top_applicant else True)

        return redirect('manage_applicant', job_id=job_posting.id, applicant_id=applicant.id)
    else:
        return JsonResponse({'message': 'Invalid method'}, status=405)


def company_profile_view(request):
    user = request.user  # Get the logged-in user
    recruiter_profile = user.profile  # This gets the related RecruiterProfile instance
    # Retrieve the company profile for the logged-in user if it exists
    try:
        company_profile = OrganizationProfile.objects.get(user=request.user.profile)
    except OrganizationProfile.DoesNotExist:
        company_profile = None

    if request.method == 'POST':
        form = OrganizationProfileForm(request.POST, request.FILES, instance=company_profile)
        if form.is_valid():
            logo = form.cleaned_data.get('logo')
            if not logo:
                form.add_error('logo', 'Logo is required.')
                return render(request, 'job_portal/recruiter_organization_profile.html', {'form': form, 'is_recruiter_profile_complete': recruiter_profile.is_profile_complete})
            # Save the form data (this will create or update the company profile)
            company_profile = form.save(commit=False)
            company_profile.user = recruiter_profile  # Ensure the user is assigned
            company_profile.save()

            # Redirect to a success page or show a success message
            return redirect("company_profile")
    else:
        # If it's a GET request, use the existing company profile if available, or an empty form
        form = OrganizationProfileForm(instance=company_profile)
    return render(request, 'job_portal/recruiter_organization_profile.html',
                  {'form': form, 'is_recruiter_profile_complete': recruiter_profile.is_profile_complete})


def recruiter_profile_view(request):
    user = request.user  # Get the logged-in user
    recruiter_profile = user.profile  # This gets the related RecruiterProfile instance

    if request.method == 'POST':
        form = RecruiterProfileForm(request.POST, request.FILES, instance=recruiter_profile)
        if form.is_valid():
            form.save()
            return redirect("recruiter_profile")
    else:
        form = RecruiterProfileForm(instance=recruiter_profile)

    profile_complete = request.user.profile.is_profile_complete()

    return render(request, 'job_portal/recruiter_profile.html', {'form': form, 'profile_complete': profile_complete})


def account(request):

    # Get the user_id from the request
    user_id = request.user.profile.external_user_id
    try:
        # Query the secondary database and handle the response inline
        with connections['secondary'].cursor() as cursor:
            cursor.execute("""
                SELECT u.first_name, u.last_name, u.email, u.profile_pic_url, u.profile_pic_url_96x96, u.created_at, 
                       u.updated_at as profile_updated_at, u.about, u.is_email_verified,  u.account_type, 
                       ul.latitude, ul.longitude, ul.geo, ul.location_type, ul.updated_at
                FROM users u
                LEFT JOIN user_locations ul ON u.user_id = ul.user_id
                WHERE u.user_id = %s
            """, [user_id])

            result = cursor.fetchone()  # Fetch the first row


        if not result:
            logout(request)
            return redirect("login_view")

        # Extract year from created_at and create the response inline
        created_at_year = result[5].year if result[5] else None
        profile_pic_url = f"{settings.PROFILE_BASE_URL}/{result[3]}" if result[3] else None
        profile_pic_url_96x96 = f"{settings.PROFILE_BASE_URL}/{result[4]}" if result[4] else None
        response_data = {
            "user_id": user_id,
            "first_name": result[0],
            "last_name": result[1],
            "email": result[2],
            "profile_pic_url": profile_pic_url,
            "profile_pic_url_96x96": profile_pic_url_96x96,
            "updated_at": result[6],
            "about": result[7],
            "is_email_verified": bool(result[8]),
            "account_type": result[9],
            "location": {
                "latitude": result[10],
                "longitude": result[11],
                "geo": result[12],
                "location_type": result[13],
                "updated_at": result[14]
            } if result[10] and result[11] else None,
            "created_at": created_at_year,
        }

        # Return the template response
        return render(request, 'job_portal/account.html', response_data)
    except Exception:
        # Catch any database or other exceptions
        return render(request, 'job_portal/account.html')


def profile_verification_send_otp_to_email(request):
    if request.method == 'POST':
        # Ensure the request is coming from the same origin by checking the Referer header
        referer = request.META.get('HTTP_REFERER', '')
        if not referer.startswith(request.scheme + '://' + request.get_host()):
            return JsonResponse({'error': 'Invalid origin.'}, status=400)

        # Parse the incoming JSON data
        data = json.loads(request.body)  # Convert the JSON string to a Python dictionary
        new_email = data.get('new_email')  # Extract the 'new_email' value from the parsed data

        if not new_email:
            return JsonResponse({'error': 'Email is required.'}, status=400)
            # Check if the new email is the same as the current email
        profile = request.user.profile  # Assuming the user is logged in

        if profile.email == new_email:
            return JsonResponse({'error': 'New email is the same as the current email.'}, status=400)

        # Generate a 6-digit OTP
        otp = str(random.randint(100000, 999999))

        # Store OTP and email in the session for validation later
        request.session['otp'] = otp
        request.session['new_email'] = new_email

        # Send OTP to the new email
        subject = "Your Email Change OTP"
        message = f"Your OTP for email change is: {otp}"
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [new_email])

        # Respond back with success
        return JsonResponse({'success': True, 'message': 'OTP sent successfully.'})

    return JsonResponse({'error': 'Invalid request method.'}, status=400)


def profile_verification_verify_otp(request):
    if request.method == 'POST':
        # Ensure the request is coming from the same origin by checking the Referer header
        referer = request.META.get('HTTP_REFERER', '')
        if not referer.startswith(request.scheme + '://' + request.get_host()):
            return JsonResponse({'error': 'Invalid origin.'}, status=400)

        # Parse the incoming JSON data
        data = json.loads(request.body)
        otp_entered = data.get('otp')  # Get OTP entered by the user
        new_email = data.get('new_email')  # Get the new email entered by the user

        if not otp_entered or not new_email:
            return JsonResponse({'error': 'OTP and new_email are required.'}, status=400)

        # Check if the OTP in session matches the entered OTP
        session_otp = request.session.get('otp')
        session_email = request.session.get('new_email')

        if not session_otp or not session_email:
            return JsonResponse({'error': 'OTP or email data missing from session.'}, status=400)

        if otp_entered != session_otp:
            return JsonResponse({'error': 'Invalid OTP.'}, status=400)

        # Check if the new email is the same as the current email
        profile = request.user.profile  # Assuming the user is logged in
        if profile.email == new_email:
            return JsonResponse({'error': 'New email is the same as the current email.'}, status=400)

        # Update the user's email in the database
        profile.email = new_email
        profile.save()

        # Clear OTP and email from the session as the process is complete
        del request.session['otp']
        del request.session['new_email']

        # Respond back with success
        return JsonResponse({'success': True, 'message': 'Email updated successfully.'})

    return JsonResponse({'error': 'Invalid request method.'}, status=400)


def logout_view(request):
    # Log the user out
    if request.user.is_authenticated:
        logout(request)

    # Redirect to the login page or homepage after logging out
    return redirect('login_view')  # Change 'login' to your URL name for the login page


def recruiter_settings(request):
    # Get the recruiter's profile (assuming the user has a related profile)
    recruiter_profile = request.user.profile

    # Use get_or_create to fetch existing settings or create new ones if not found
    recruiter_settings, created = RecruiterSettings.objects.get_or_create(user=recruiter_profile)

    # Handle POST request (form submission)
    if request.method == 'POST':
        form = RecruiterSettingsForm(request.POST, instance=recruiter_settings)
        if form.is_valid():
            form.save()
            return redirect('recruiter_settings')  # Redirect to the same page after form submission
    else:
        # Handle GET request (render form)
        form = RecruiterSettingsForm(instance=recruiter_settings)

    return render(request, 'job_portal/recruiter_settings.html', {
        'form': form,
        'recruiter_profile': recruiter_profile,
        'is_recruiter_profile_complete': recruiter_profile.is_profile_complete

    })


def plans(request):
    profile = request.user.profile
    available_plans = Plan.objects.filter(is_free=False)
    context = {
        'current_plan': profile.plan,
        'is_trial_active': profile.is_trial_active,
        'trial_end_date': profile.trial_end_date,
        'trial_ended': not profile.is_trial_active and profile.trial_end_date < timezone.now(),
        'available_plans': available_plans,
    }
    return render(request, 'job_portal/plans.html', context)


class DepartmentAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Department.objects.all()

        if self.q:
            qs = qs.filter(
                Q(name__icontains=self.q) |  # Search name
                Q(code__icontains=self.q)  # Search code
            )
        return qs


class IndustryAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Industry.objects.all()

        if self.q:
            qs = qs.filter(
                Q(name__icontains=self.q) |  # Search name
                Q(code__icontains=self.q)  # Search code
            )
        return qs



class EducationAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Education.objects.all()

        if self.q:
            qs = qs.filter(
                Q(name__icontains=self.q) |  # Search name
                Q(code__icontains=self.q)  # Search code
            )
        return qs


class RoleAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Role.objects.all()
        if self.q:
            qs = qs.filter(
                Q(name__icontains=self.q) |  # Search name
                Q(code__icontains=self.q)  # Search code
            )
        return qs


class SkillsAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Skills.objects.all()
        if self.q:
            qs = qs.filter(
                Q(name__icontains=self.q) |  # Search name
                Q(code__icontains=self.q)  # Search code
            )
        return qs

class CompanyAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return OrganizationProfile.objects.none()

        profile = self.request.user.profile

        qs = OrganizationProfile.objects.filter(user=profile)

        if self.q:
            qs = qs.filter(organization_name__icontains=self.q)

        return qs


def account_terminated(request):
    if request.user.is_terminated:
        return render(request, 'job_portal/auth/account_terminated.html')
    else:
        raise Http404()

def handler404(request, exception):
    context = {
        'error_title': "Page Not Found",
        'error_message': "The page you're looking for doesn't exist or has been moved.",
    }
    return render(request, 'core/404.html', context, status=404)



