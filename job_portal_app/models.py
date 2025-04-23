import os
import random
from datetime import timedelta, date
from enum import Enum

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
from slugify import slugify

from job_portal import settings


class ExternalLinkUser(AbstractUser):
    external_user_id = models.CharField(max_length=255)
    is_terminated = models.BooleanField(default=False)  # 👈 Add this field

    class Meta:
        db_table = 'lts360_jobs_auth_user'  # Custom table name

    def __str__(self):
        return self.external_user_id


# Function to generate logo upload path based on the organization_id
def get_logo_upload_path(instance, filename):
    """
    Generate the upload path for the organization logo based on the organization ID.
    """
    return os.path.join('jobs', 'organization', str(instance.organization_id), 'logos', filename)


COUNTRY_CHOICES = [
    ('IN', 'India'),
]

STATE_CHOICES = {
    'IN': [
        ('AP', 'Andhra Pradesh'),
        ('AR', 'Arunachal Pradesh'),
        ('AS', 'Assam'),
        ('BR', 'Bihar'),
        ('CT', 'Chhattisgarh'),
        ('GA', 'Goa'),
        ('GJ', 'Gujarat'),
        ('HR', 'Haryana'),
        ('HP', 'Himachal Pradesh'),
        ('JH', 'Jharkhand'),
        ('KA', 'Karnataka'),
        ('KL', 'Kerala'),
        ('MP', 'Madhya Pradesh'),
        ('MH', 'Maharashtra'),
        ('MN', 'Manipur'),
        ('ML', 'Meghalaya'),
        ('MZ', 'Mizoram'),
        ('NL', 'Nagaland'),
        ('OD', 'Odisha'),
        ('PB', 'Punjab'),
        ('RJ', 'Rajasthan'),
        ('SK', 'Sikkim'),
        ('TN', 'Tamil Nadu'),
        ('TG', 'Telangana'),
        ('TR', 'Tripura'),
        ('UP', 'Uttar Pradesh'),
        ('UK', 'Uttarakhand'),
        ('WB', 'West Bengal'),
    ],  # States of India
}


def generate_8digit_id():
    return random.randint(10_000_000, 99_999_999)


def get_recruiter_profile_upload_path(instance, filename):
    """
    Generate the upload path for the organization logo based on the organization ID.
    """
    return os.path.join('recruiters', str(instance.user_id), 'profile', filename)


class RecruiterRoleEnum(Enum):
    RECRUITER = 'RECRUITER'
    HIRING_MANAGER = 'HIRING_MANAGER'
    TALENT_ACQUISITION = 'TALENT_ACQUISITION'
    HR = 'HR'

    @classmethod
    def choices(cls):
        return [(tag.value, tag.value.replace('_', ' ').title()) for tag in cls]


def get_default_trial_end_date():
    return timezone.now() + timedelta(days=90)

# RecruiterProfile model
class RecruiterProfile(models.Model):
    user = models.OneToOneField('ExternalLinkUser', on_delete=models.CASCADE, related_name='profile')
    external_user_id = models.CharField(max_length=255)

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, null=True, blank=True, default=None)
    email = models.EmailField()

    role = models.CharField(max_length=50, choices=RecruiterRoleEnum.choices, default=RecruiterRoleEnum.RECRUITER.value)

    company = models.CharField(max_length=50)
    phone = PhoneNumberField()
    profile_picture = models.ImageField(upload_to=get_recruiter_profile_upload_path, blank=True, null=True)
    bio = models.TextField()
    years_of_experience = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_verified = models.BooleanField(default=False)

    plan = models.ForeignKey('Plan', on_delete=models.PROTECT, default=1)
    subscription_date = models.DateTimeField(auto_now_add=True)
    trial_end_date = models.DateTimeField(default=get_default_trial_end_date)
    is_trial_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_role_display()}"

    class Meta:
        db_table = 'recruiter_user_profile'  # Custom table name

    def is_profile_complete(self):
        # Check if all required fields are filled in
        required_fields = [
            self.first_name,
            self.last_name,
            self.email,
            self.role,
            self.company,
            self.phone,
            self.profile_picture,
            self.bio,
            self.years_of_experience,
            self.is_verified
        ]
        # Check if any of the fields are empty or None
        return all(required_fields)


def generate_unique_11_digit_id():
    while True:
        uid = random.randint(10_000_000_000, 99_999_999_999)  # 11-digit number
        if not UserProfile.objects.filter(unique_id=uid).exists():
            return uid

class UserProfile(models.Model):
    id = models.BigIntegerField(primary_key=True, default=generate_unique_11_digit_id, unique=True)

    # Inherit from UserProfile if needed, or just copy relevant fields to make StudentProfile standalone
    external_user_id = models.BigIntegerField(unique=True)

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    profile_picture = models.TextField(blank=True, null=True)
    email = models.EmailField()

    intro = models.CharField(max_length=500)

    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('others', 'Others'),
    ]
    gender = models.CharField( max_length=7, choices=GENDER_CHOICES,   blank=True, null=True )

    # Phone number, maybe verified?
    phone = PhoneNumberField(blank=True, null=True)

    # The student applying for a job
    applied_jobs = models.ManyToManyField('JobPosting', through='Application', related_name='students')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Profile Verification for Students
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        db_table = 'user_profile'

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = "%s %s" % (self.first_name, self.last_name)
        return full_name.strip()

    def is_profile_complete(self):
        """Check if the student's profile is complete."""
        required_fields = [
            self.first_name,
            self.last_name,
            self.email,
            self.phone
        ]
        return all(required_fields)


# Education Model
class UserProfileEducation(models.Model):
    user_profile = models.OneToOneField('UserProfile', related_name='education', on_delete=models.CASCADE)

    # The name of the organization (institution)
    organization_name = models.CharField(max_length=255)

    # The field of study (major/subject)
    field_of_study = models.CharField(max_length=255)

    # The start date of the education program
    start_date = models.DateField()

    # The end date or expected graduation date
    end_date = models.DateField(null=True, blank=True)

    # The grade achieved in the education program (e.g., GPA, Percentage)
    grade = models.DecimalField(max_digits=5, decimal_places=1, null=True)

    # Whether the user is currently studying or has completed the education
    currently_studying = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.organization_name} - {self.field_of_study}"

    class Meta:
        db_table = 'user_profile_education_info'

class UserProfileExperience(models.Model):
    user_profile = models.ForeignKey('UserProfile', related_name='experience', on_delete=models.CASCADE)

    JOB_TYPE_CHOICES = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('intern', 'Internship'),
        ('freelance', 'Freelance'),
    ]

    job_title = models.CharField(max_length=255, null=True)
    employment_type = models.CharField(max_length=50, choices=JOB_TYPE_CHOICES,  null=True)
    organization = models.CharField(max_length=255,  null=True)
    current_working_here = models.BooleanField(default=False,  null=True)
    experienced = models.BooleanField(default=True)
    start_date = models.DateField( null=True)
    end_date = models.DateField(null=True, blank=True)  # Nullable if currently working
    location = models.CharField(max_length=255,  null=True)

    class Meta:
        db_table = 'user_profile_experience'

    def __str__(self):
        return f"{self.job_title} at {self.organization}"

class UserProfileSkill(models.Model):
    user_profile = models.ForeignKey('UserProfile', related_name='skill', on_delete=models.CASCADE)
    skill = models.CharField(max_length=100)  # e.g., "Python"
    skill_code = models.CharField(max_length=50)  # e.g., "PY001"

    class Meta:
        db_table = 'user_profile_skill'

    def __str__(self):
        return f"{self.skill} ({self.skill_code}), Language: {self.language_code}, Proficiency: {self.proficiency}"

class UserProfileLanguage(models.Model):
    user_profile = models.ForeignKey('UserProfile', related_name='langauge', on_delete=models.CASCADE)
    language = models.CharField(max_length=100)  # e.g., "Python"
    language_code = models.CharField(max_length=50, null=True, blank=True)  # e.g., "EN" for English
    proficiency = models.CharField(max_length=50, null=True, blank=True)  # e.g., "Intermediate", "Fluent"
    proficiency_code = models.CharField(max_length=50, null=True, blank=True)  # e.g., "EN" for English

    class Meta:
        db_table = 'user_profile_language'

    def __str__(self):
        return f"Language: {self.langauge}, Proficiency: {self.proficiency}"

class UserProfileResume(models.Model):
    user_profile = models.OneToOneField(
        'UserProfile',
        related_name='resume',
        on_delete=models.CASCADE,
        unique=True
    )
    resume_download_url = models.CharField(max_length=255)
    resume_file_name = models.CharField(max_length=255)
    resume_size = models.CharField(max_length=50)
    resume_type = models.CharField(max_length=50)
    last_used = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'user_profile_resume'

    def __str__(self):
        return f"Resume ({self.resume_type}, {self.resume_size}) - {self.resume_download_url}"

class UserProfileCertificate(models.Model):
    user_profile = models.ForeignKey(
        'UserProfile',
        related_name='certificate',
        on_delete=models.CASCADE
    )
    issued_by =  models.CharField(max_length=50)
    certificate_download_url = models.CharField(max_length=255)
    certificate_file_name = models.CharField(max_length=255)
    certificate_size = models.CharField(max_length=50)
    certificate_type = models.CharField(max_length=50)

    class Meta:
        db_table = 'user_profile_certificate'

    def __str__(self):
        return f"Resume ({self.certificate_type}, {self.certificate_size}) - {self.certificate_download_url}"


class OrganizationProfile(models.Model):
    user = models.ForeignKey('RecruiterProfile', on_delete=models.CASCADE)  # Link to StudentProfile (ForeignKey)
    organization_id = models.PositiveBigIntegerField(unique=True)
    organization_name = models.CharField(max_length=255)
    logo = models.ImageField(upload_to=get_logo_upload_path, blank=True, null=True)
    email = models.EmailField()
    organization_address = models.CharField(max_length=255)
    website = models.URLField(
        max_length=200,
    )
    country = models.CharField(
        max_length=2,
        choices=COUNTRY_CHOICES,
        default='IN',
    )
    state = models.CharField(
        max_length=100)

    city = models.CharField(max_length=100)
    postal_code = models.CharField(
        max_length=10,  # Maximum length of the postal code
        validators=[
            RegexValidator(r'^\d{5,10}$', _('Invalid postal code. It should be between 5 and 10 digits.'))
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)  # Automatically set when the profile is created

    class Meta:
        db_table = 'lts360_jobs_organizations_profile'

    def is_complete(self):
        return bool(self.organization_name and self.organization_address and self.logo and self.organization_id)

    def save(self, *args, **kwargs):
        if not self.organization_id:
            while True:
                try:
                    with transaction.atomic():
                        self.organization_id = generate_8digit_id()
                        super().save(*args, **kwargs)
                        break
                except IntegrityError:
                    if OrganizationProfile.objects.filter(
                            organization_id=self.organization_id
                    ).exists():  # Confirm real duplicate
                        continue
                    raise  # Re-raise if other error
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return self.organization_name


def generate_unique_10_digit_id():
    while True:
        uid = random.randint(1000000000, 9999999999)  # 10-digit number
        if not JobPosting.objects.filter(id=uid).exists():
            return uid

class JobPosting(models.Model):
    id = models.BigIntegerField(primary_key=True, default=generate_unique_10_digit_id, unique=True)

    title = models.CharField(max_length=100)

    work_mode = models.CharField(max_length=50,
                                 choices=[('remote', 'Remote'), ('office', 'Office'), ('hybrid', 'Hybrid'), ['flexible', 'Flexible']],
                                 default='office', blank=False)
    location = models.CharField(max_length=100)

    company = models.ForeignKey('OrganizationProfile', on_delete=models.CASCADE, related_name='job_posts')

    description = models.TextField()

    education = models.CharField(max_length=200)

    experience_type = models.CharField(max_length=50,
                                       choices=[('fresher', 'Fresher'), ('min_max', 'Min-Max Experience'),
                                                ('fixed', 'Fixed Experience')],
                                       default='fresher', blank=False)

    experience_range_min = models.IntegerField(default=0)
    experience_range_max = models.IntegerField(default=0)
    experience_fixed = models.IntegerField(default=0)

    salary_min = models.DecimalField(max_digits=10, decimal_places=2)
    salary_max = models.DecimalField(max_digits=10, decimal_places=2)
    salary_not_disclosed = models.BooleanField(default=False)

    must_have_skills = models.JSONField(default=list)  # Stores as list
    good_to_have_skills = models.JSONField(default=list)

    industry_type = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    role = models.CharField(max_length=100)
    employment_type = models.CharField(max_length=50, choices=[('full_time', 'Full Time'), ('part_time', 'Part Time'),
                                                               ('contract', 'Contract'), ('internship', 'Internship')], default='full_time',
                                       blank=False)
    vacancies = models.IntegerField(default=1)

    highlights = models.JSONField(default=list,
                                  help_text="List of selected job perks")

    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    posted_at = models.DateTimeField(auto_now_add=True)
    posted_by = models.ForeignKey('RecruiterProfile', on_delete=models.CASCADE, related_name='recruiter_user_profile')
    organization_id = models.BigIntegerField(null=True, blank=True)

    expiry_date = models.DateField()

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
    ]

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='published'
    )

    APPROVAL_STATUS_CHOICES = [
        ('active', 'Active'),
        ('rejected', 'Rejected'),
    ]

    approval_status = models.CharField(max_length=10, choices=APPROVAL_STATUS_CHOICES, default='active')

    slug = models.SlugField(max_length=300, unique=True, blank=False)

    class Meta:
        db_table = 'lts360_jobs'  # Custom table name

    def __str__(self):
        return self.title

    def clean(self):
        """
        Custom validation to ensure that only one of the experience fields is filled
        based on the selected experience type.
        """

        if self.experience_type == 'fresher':
            self.experience_range_min = 0
            self.experience_range_max = 0
            self.experience_fixed = 0


        elif self.experience_type == 'min_max':
            # If min-max type is selected, make sure the min is less than max
            if self.experience_range_min >= self.experience_range_max:
                raise ValidationError(
                    {"experience_range_min": "Minimum experience should be less than maximum experience.",
                     "experience_range_max": "Maximum experience should be greater than minimum experience."}
                )

            # Ensure fixed experience is not set when using min-max
            if self.experience_fixed > 0:
                self.experience_fixed = 0


        elif self.experience_type == 'fixed':
            if self.experience_fixed <= 0:
                raise ValidationError(
                    {"experience_fixed": "Fixed experience should be greater than zero experience."}
                )

            # For fixed experience type, reset min-max experience range to 0
            self.experience_range_min = 0
            self.experience_range_max = 0



        if not self.salary_not_disclosed:
            # When salary IS disclosed (salary_not_disclosed is False)
            if self.salary_min is None or self.salary_max is None:
                raise ValidationError({
                    'salary_min': ValidationError("Minimum salary is required.", code='missing_salary_min'),
                    'salary_max': ValidationError("Maximum salary is required.", code='missing_salary_max'),
                })
            if self.salary_min > self.salary_max:
                raise ValidationError({
                        'salary_min': ValidationError("Minimum salary cannot be greater than maximum salary.",
                                                      code='invalid_range'),
                        'salary_max': ValidationError("Maximum salary must be greater than minimum salary.",
                                                      code='invalid_range'),
                    })

            if self.salary_min <= 0:
                raise ValidationError({
                    'salary_min': ValidationError("Minimum salary cannot be zero or less than zero.", code='negative_min_salary'),
                })

            if self.salary_max <= 0:
                raise ValidationError({
                    'salary_max': ValidationError("Maximum salary cannot be zero or less than zero.", code='negative_max_salary'),
                })
        else:
            # When salary is NOT disclosed (salary_not_disclosed is True)
            self.salary_min = 0.00
            self.salary_max = 0.00




        if self.expiry_date:
            tomorrow = date.today() + timedelta(days=1)
            max_date = date.today() + timedelta(days=30)

            if self.expiry_date < tomorrow:
                raise ValidationError(
                    {'expiry_date': "Expiry date must be at least tomorrow."}
                )
            if self.expiry_date > max_date:
                raise ValidationError(
                    {'expiry_date': "Expiry date cannot be more than 30 days from today."}
                )

    @property
    def days_remaining(self):
        if not self.expiry_date:
            return None
        return (self.expiry_date - date.today()).days

    @property
    def days_remaining_abs(self):
        return abs(self.days_remaining) if self.days_remaining is not None else None

    @property
    def is_draft(self):
        """Returns True if the job posting is in draft status"""
        return self.status == 'draft'

    @property
    def is_published(self):
        """Returns True if the job posting is published"""
        return self.status == 'published'

    def _format_salary_with_settings(self, salary):
        recruiter_settings = get_object_or_404(RecruiterSettings, user=self.posted_by)

        currency_symbol = recruiter_settings.get_currency_symbol()
        currency_type = recruiter_settings.get_currency_type().upper()

        if currency_type == 'INR':
            if salary >= 1_00_00_000:
                formatted = f"{salary / 1_00_00_000:.2f} Cr"
            elif salary >= 1_00_000:
                formatted = f"{salary / 1_00_000:.2f} Lakh"
            else:
                formatted = f"{salary}"
        else:
            if salary >= 1_000_000:
                formatted = f"{salary / 1_000_000:.2f}M"
            elif salary >= 1_000:
                formatted = f"{salary / 1_000:.2f}K"
            else:
                formatted = f"{salary}"

        return f"{currency_symbol}{formatted}"

    @property
    def formatted_salary_min(self):
        try:
            return self._format_salary_with_settings(self.salary_min)
        except RecruiterSettings.DoesNotExist:
            return str(self.salary_min)

    @property
    def formatted_salary_max(self):
        try:
            return self._format_salary_with_settings(self.salary_max)
        except RecruiterSettings.DoesNotExist:
            return str(self.salary_max)

    @property
    def build_slug_url(self):
        base_url = getattr(settings, 'ROOT_BASE_URL', 'https://www.lts360.com')
        return f"{base_url.rstrip('/')}/jobs/{self.slug}/"


    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            super().save(*args, **kwargs)  # Save once to get an ID
            self.slug = f"{base_slug}-{self.id}"
        super().save(*args, **kwargs)

def generate_unique_8_digit_id():
    while True:
        uid = random.randint(10_000_000, 99_999_999)  # 8-digit number
        if not Application.objects.filter(id=uid).exists():
            return uid

class Application(models.Model):
    id = models.BigIntegerField(primary_key=True, default=generate_unique_8_digit_id, unique=True)
    user = models.ForeignKey('UserProfile', on_delete=models.CASCADE)  # Link to StudentProfile (ForeignKey)
    job_listing = models.ForeignKey('JobPosting', on_delete=models.CASCADE,
                                    related_name='applications')  # Foreign key to JobPosting model
    applied_at = models.DateTimeField(auto_now_add=True)  # Timestamp when the application was made
    status = models.CharField(
        max_length=50,
        choices=[('applied', 'Applied'), ("viewed", 'Viewed'), ('reviewed', 'Reviewed'), ('interview', 'Interview'),
                 ('offer', 'Offer'),
                 ('hired', 'Hired'), ('rejected', 'Rejected')],
        default='pending'
    )
    is_rejected = models.BooleanField(default=False)
    is_top_applicant = models.BooleanField(default=False)
    reviewed_at = models.DateTimeField(null=True, blank=True)  # Optional: Date when the application was reviewed
    updated_at = models.DateTimeField(auto_now=True)  # Automatically updates whenever the application is saved

    def __str__(self):
        return f"Application from User ID {self.user_id} for Job ID {self.job_listing.id}"

    class Meta:
        db_table = 'lts360_job_applications'  # Custom table name for the database
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'job_listing'],
                name='unique_application_per_user_job'
            )
        ]

    def clean(self):
        # Custom validation to prevent duplicate applications
        if Application.objects.filter(
                user=self.user,
                job_listing=self.job_listing
        ).exclude(pk=self.pk).exists():
            raise ValidationError("This user has already applied to this job posting.")

    def save(self, *args, **kwargs):
        self.full_clean()  # Enforce validation before saving
        super().save(*args, **kwargs)

    @property
    def profile_url(self):
        # Check if the profile_picture field is not null
        if self.user.profile_picture:
            # Return the full URL by concatenating the base URL (from settings) with the profile picture path
            return self.user.profile_picture.url
        return None

    def update_status(self, status):
        self.status = status
        self.reviewed_at = timezone.now()
        self.save()

    def reject(self):
        self.is_rejected = True
        self.reviewed_at = timezone.now()
        self.save()

    def update_top_applicant(self, is_top_applicant):
        self.is_top_applicant = is_top_applicant
        self.save()

class Industry(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=15, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'job_industries'  # Custom table name
        ordering = ['name']

    def __str__(self):
        return self.name

    @classmethod
    def create_default_job_industries(cls):

        default_job_industries = [
            {'name': 'Software & IT', 'code': 'IT-1A2B3'},
            {'name': 'Medical & Healthcare', 'code': 'HS-7F8G9'},
            {'name': 'Teaching & Education', 'code': 'EDU-0H1I2'},
            {'name': 'Medicines', 'code': 'PHAR-6L7M8'},
            {'name': 'Banking & Finance', 'code': 'FIN-9N0P1'},
            {'name': 'Real Estate', 'code': 'RE-5S6T7'},
            {'name': 'Colleges & Universities', 'code': 'HE-8U9V0'},
            {'name': 'Sales & Marketing', 'code': 'SALES-1W2X3'},
            {'name': 'Shops & Retail', 'code': 'RETAIL-0C1D2'},
            {'name': 'Hiring & HR', 'code': 'HR-9I0J1'},
            {'name': 'Transport & Logistics', 'code': 'TRANSP-5M6N7'},
            {'name': 'Hotels & Tourism', 'code': 'HOSP-8O9P0'},
            {'name': 'Agriculture & Farming', 'code': 'AGRI-3B4C5'},
            {'name': 'Entertainment & Media', 'code': 'MEDIA-6D7E8'},
            {'name': 'Construction', 'code': 'CONST-2H3I4'},
            {'name': 'Fashion & Beauty', 'code': 'FASHION-8L9M0'},
            {'name': 'Food & Restaurants', 'code': 'FOOD-4P5Q6'},
            {'name': 'Arts & Design', 'code': 'ART-7R8S9'},
            {'name': 'Arts & Science', 'code': 'ARTSCIENCE-7R5M9'},
            {'name': 'Sports & Fitness', 'code': 'SPORTS-0T1U2'},
            {'name': 'Telecommunications', 'code': 'TELECOM-6X7Y8'}
        ]

        for industry in default_job_industries:
            cls.objects.get_or_create(
                name=industry['name'],
                code=industry['code'],
                defaults={'description': f"{industry['code']} - {industry['name']} industry"}
            )

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'job_departments'  # Custom table name
        ordering = ['name']

    def __str__(self):
        return self.name

    @classmethod
    def create_default_departments(cls):
        default_departments = [
            # Engineering Departments
            {'name': 'Computer Science and Engineering', 'code': 'CSE-1A2B3'},
            {'name': 'Electrical and Electronics Engineering', 'code': 'EEE-4C5D6'},
            {'name': 'Electronics and Communication Engineering', 'code': 'ECE-7E8F9'},
            {'name': 'Mechanical Engineering', 'code': 'ME-0G1H2'},
            {'name': 'Civil Engineering', 'code': 'CE-3I4J5'},
            {'name': 'Artificial Intelligence', 'code': 'AI-6K7L8'},
            {'name': 'Data Science', 'code': 'DS-9M0N1'},

            # Science Departments
            {'name': 'Mathematics', 'code': 'MATH-2O3P4'},
            {'name': 'Physics', 'code': 'PHY-5Q6R7'},
            {'name': 'Chemistry', 'code': 'CHEM-8S9T0'},

            # Interdisciplinary
            {'name': 'Biotechnology', 'code': 'BT-1U2V3'},
            {'name': 'Robotics', 'code': 'ROBO-4W5X6'},

            # Management
            {'name': 'Business Administration', 'code': 'MBA-7Y8Z9'},
            {'name': 'Finance', 'code': 'FIN-0A1B2'}
        ]

        for dept in default_departments:
            cls.objects.get_or_create(
                name=dept['name'],
                code=dept['code'],
                defaults={'description': f"{dept['code']} Department"}
            )

class Role(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)  # Code is now unique and can be industry + role code
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'job_roles'  # Custom table name
        ordering = ['name']

    def __str__(self):
        return self.name

    @classmethod
    def create_default_roles(cls):
        # Default roles by industry code with role name and manually added codes
        default_roles = {
            'IT': [
                {'name': 'Software Engineer', 'code': 'IT-SE-01ABC'},
                {'name': 'Network Engineer', 'code': 'IT-NE-02XYZ'},
                {'name': 'System Administrator', 'code': 'IT-SA-03DEF'},
                {'name': 'Database Administrator', 'code': 'IT-DBA-04GHI'},
                {'name': 'Tech Support Specialist', 'code': 'IT-TSS-05JKL'}
            ],
            'TECH': [
                {'name': 'Product Manager', 'code': 'TECH-PM-06MNO'},
                {'name': 'UI/UX Designer', 'code': 'TECH-UXD-07PQR'},
                {'name': 'Web Developer', 'code': 'TECH-WD-08STU'},
                {'name': 'Data Analyst', 'code': 'TECH-DA-09VWX'},
            ],
            'HS': [
                {'name': 'Doctor', 'code': 'HS-DOC-10YZA'},
                {'name': 'Nurse', 'code': 'HS-NUR-11BCD'},
                {'name': 'Medical Researcher', 'code': 'HS-MR-12EFG'},
                {'name': 'Pharmacist', 'code': 'HS-PHARM-13HIJ'},
            ],
            'EDU': [
                {'name': 'Teacher', 'code': 'EDU-TCH-14KLM'},
                {'name': 'Professor', 'code': 'EDU-PROF-15NOP'},
                {'name': 'Lecturer', 'code': 'EDU-LCT-16QRS'},
                {'name': 'Education Coordinator', 'code': 'EDU-EDC-17TUV'},
            ],
            'ACC': [
                {'name': 'Accountant', 'code': 'ACC-ACC-18WXY'},
                {'name': 'Financial Analyst', 'code': 'ACC-FA-19ZAB'},
                {'name': 'Tax Consultant', 'code': 'ACC-TC-20CDE'},
                {'name': 'Auditor', 'code': 'ACC-AUD-21FGH'},
            ],
            'PHAR': [
                {'name': 'Pharmacist', 'code': 'PHAR-PHARM-22IJK'},
                {'name': 'Clinical Researcher', 'code': 'PHAR-CR-23LMN'},
                {'name': 'Regulatory Affairs Specialist', 'code': 'PHAR-RAS-24OPQ'},
            ],
            'FIN': [
                {'name': 'Financial Advisor', 'code': 'FIN-FA-25RST'},
                {'name': 'Investment Banker', 'code': 'FIN-IB-26UVW'},
                {'name': 'Risk Manager', 'code': 'FIN-RM-27XYZ'},
                {'name': 'Financial Controller', 'code': 'FIN-FC-28ABC'},
            ],
            'ENG': [
                {'name': 'Civil Engineer', 'code': 'ENG-CE-29DEF'},
                {'name': 'Mechanical Engineer', 'code': 'ENG-ME-30GHI'},
                {'name': 'Electrical Engineer', 'code': 'ENG-EE-31JKL'},
                {'name': 'Software Engineer', 'code': 'ENG-SE-32MNO'},
            ],
            'RE': [
                {'name': 'Real Estate Agent', 'code': 'RE-REA-33PQR'},
                {'name': 'Real Estate Developer', 'code': 'RE-RED-34STU'},
                {'name': 'Property Manager', 'code': 'RE-PM-35VWX'},
                {'name': 'Real Estate Consultant', 'code': 'RE-REC-36YZA'},
            ],
            'HE': [
                {'name': 'Higher Education Administrator', 'code': 'HE-HEA-37BCD'},
                {'name': 'University Professor', 'code': 'HE-UP-38CDE'},
                {'name': 'Higher Education Counselor', 'code': 'HE-HEC-39FGH'},
            ],
            'SALES': [
                {'name': 'Sales Manager', 'code': 'SALES-SM-40HIJ'},
                {'name': 'Sales Executive', 'code': 'SALES-SE-41JKL'},
                {'name': 'Sales Consultant', 'code': 'SALES-SC-42MNO'},
                {'name': 'Account Executive', 'code': 'SALES-AE-43PQR'},
            ],
            'GOV': [
                {'name': 'Government Official', 'code': 'GOV-GO-44STU'},
                {'name': 'Policy Analyst', 'code': 'GOV-PA-45VWX'},
                {'name': 'Public Relations Officer', 'code': 'GOV-PRO-46YZA'},
            ],
            'ENERGY': [
                {'name': 'Energy Analyst', 'code': 'ENERGY-EA-47BCD'},
                {'name': 'Energy Manager', 'code': 'ENERGY-EM-48CDE'},
                {'name': 'Renewable Energy Specialist', 'code': 'ENERGY-RES-49FGH'},
            ],
            'RETAIL': [
                {'name': 'Retail Manager', 'code': 'RETAIL-RM-50GHI'},
                {'name': 'Sales Associate', 'code': 'RETAIL-SA-51JKL'},
                {'name': 'Store Manager', 'code': 'RETAIL-SM-52MNO'},
                {'name': 'Cashier', 'code': 'RETAIL-C-53PQR'},
            ],
            'MANUFACTURING': [
                {'name': 'Manufacturing Engineer', 'code': 'MANUFACTURING-ME-54STU'},
                {'name': 'Production Manager', 'code': 'MANUFACTURING-PM-55VWX'},
                {'name': 'Quality Control Specialist', 'code': 'MANUFACTURING-QCS-56YZA'},
            ],
            'ARCH': [
                {'name': 'Architect', 'code': 'ARCH-ARCH-57ABC'},
                {'name': 'Interior Designer', 'code': 'ARCH-ID-58DEF'},
                {'name': 'Urban Planner', 'code': 'ARCH-UP-59GHI'},
            ],
            'HR': [
                {'name': 'HR Manager', 'code': 'HR-HRM-60JKL'},
                {'name': 'Recruitment Specialist', 'code': 'HR-RS-61MNO'},
                {'name': 'HR Consultant', 'code': 'HR-HRC-62PQR'},
            ],
            'NONPROFIT': [
                {'name': 'Nonprofit Manager', 'code': 'NONPROFIT-NM-63RST'},
                {'name': 'Fundraiser', 'code': 'NONPROFIT-FR-64UVW'},
                {'name': 'Social Worker', 'code': 'NONPROFIT-SW-65XYZ'},
            ],
            'TRANSPORT': [
                {'name': 'Logistics Manager', 'code': 'TRANSPORT-LM-66ABC'},
                {'name': 'Transportation Planner', 'code': 'TRANSPORT-TP-67DEF'},
                {'name': 'Fleet Manager', 'code': 'TRANSPORT-FM-68GHI'},
            ],
            'HOSPITALITY': [
                {'name': 'Hotel Manager', 'code': 'HOSPITALITY-HM-69JKL'},
                {'name': 'Chef', 'code': 'HOSPITALITY-C-70MNO'},
                {'name': 'Event Coordinator', 'code': 'HOSPITALITY-EC-71PQR'},
            ]
        }

        # Loop over the default roles and create them
        for industry_code, roles in default_roles.items():
            for role in roles:
                role_code = role['code']  # Manually assigned role code
                # Ensure the role does not already exist
                if not cls.objects.filter(code=role_code).exists():
                    cls.objects.create(
                        name=role['name'],
                        code=role_code,
                    )

class Education(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(
        max_length=8,  # Code is fixed to 8 characters
        unique=True,
        blank=True,  # Let this field be optional initially
    )
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'job_educations'  # Custom table name
        ordering = ['name']

    def __str__(self):
        return self.name

    @classmethod
    def create_default_education(cls):
        default_education = [
            {'name': 'Associate Degree', 'code': 'ASS-MNO901'},
            {'name': 'Bachelor of Arts', 'code': 'BAF-ABC987'},
            {'name': 'Bachelor of Commerce', 'code': 'BCM-XYZ234'},
            {'name': 'Bachelor of Law', 'code': 'BLL-DEF345'},
            {'name': 'Bachelor of Science', 'code': 'BSC-ABC123'},
            {'name': 'Bachelor of Technology', 'code': 'BSC-XYZ456'},
            {'name': 'Certified Public Accountant', 'code': 'CPA-JKL567'},
            {'name': 'Doctor of Education', 'code': 'EDU-PQR678'},
            {'name': 'Doctor of Philosophy', 'code': 'PHD-GHI345'},
            {'name': 'Diploma', 'code': 'DIP-JKL678'},
            {'name': 'Diploma in Engineering', 'code': 'DIE-VWX234'},
            {'name': 'Diploma in Information Technology', 'code': 'DIT-ZYX987'},
            {'name': 'Diploma in Pharmacy', 'code': 'DIP-PAR234'},
            {'name': 'Doctor of Medicine', 'code': 'MD-KLM567'},
            {'name': 'Doctor of Pharmacy', 'code': 'DPh-KLM789'},
            {'name': 'Engineering Degree', 'code': 'ENG-XYZ456'},
            {'name': 'Master of Arts', 'code': 'MA-ABC123'},
            {'name': 'Master of Business Administration', 'code': 'MBA-QRS234'},
            {'name': 'Master of Computer Applications', 'code': 'MCA-DEF789'},
            {'name': 'Master of Engineering', 'code': 'MEng-XYZ987'},
            {'name': 'Master of Law', 'code': 'LLM-KLM123'},
            {'name': 'Master of Science', 'code': 'MSC-PQR789'},
            {'name': 'Master of Technology', 'code': 'MST-DEF012'},
            {'name': 'Master of Business Administration', 'code': 'MBA-RTY567'},
            {'name': 'Masters in Business Administration', 'code': 'MBA-ABD123'},
            {'name': 'Master in Public Administration', 'code': 'MPA-XCV678'},
            {'name': 'Master in Social Work', 'code': 'MSW-FGH789'},
            {'name': 'Nursing Degree', 'code': 'NUR-ABC456'},
            {'name': 'Post Graduate Diploma', 'code': 'PGD-KLM890'},
            {'name': 'Post Graduate Degree', 'code': 'PGD-PQR123'},
            {'name': 'Postgraduate Certificate', 'code': 'PGC-LMN456'},
            {'name': 'Postgraduate Diploma in Education', 'code': 'PGDE-ABC789'},
            {'name': 'Professional Degree in Engineering', 'code': 'PDE-XYZ123'},
            {'name': 'PhD in Science', 'code': 'PHD-DEF234'},
            {'name': 'PhD in Technology', 'code': 'PHD-TKL567'},
            {'name': 'Specialist Degree in Dentistry', 'code': 'DDS-XYZ789'},
            {'name': 'Technical Degree', 'code': 'TD-ABC456'},
            {'name': 'Vocational Certificate', 'code': 'VOC-XYZ321'},
            {'name': 'Vocational Diploma', 'code': 'VOD-KLM234'},
            {'name': 'Bachelor of Fine Arts', 'code': 'BFA-GHJ345'},
            {'name': 'Bachelor of Interior Design', 'code': 'BID-ABC567'},
            {'name': 'Bachelor of Nursing', 'code': 'BNR-XYZ678'},
            {'name': 'Bachelor of Performing Arts', 'code': 'BPA-QRS890'},
            {'name': 'Bachelor of Public Administration', 'code': 'BPA-DEF234'},
            {'name': 'Bachelor of Technology in Information Technology', 'code': 'BTech-IT-456'},
            {'name': 'Bachelor of Veterinary Science', 'code': 'BVS-VET123'},
            {'name': 'Master of Hotel Management', 'code': 'MHM-DEF345'},
            {'name': 'Master of Interior Design', 'code': 'MID-XYZ987'},
            {'name': 'Master of Public Health', 'code': 'MPH-QRS234'},
            {'name': 'Master of Social Work', 'code': 'MSW-XYZ789'},
            {'name': 'Master of Science in Agriculture', 'code': 'MSA-DEF567'},
        ]

        for edu in default_education:
            # Create each education entry manually with a specified code
            cls.objects.get_or_create(
                name=edu['name'],
                code=edu['code'],
                defaults={'description': f"{edu['name']} Education"}
            )

class Skills(models.Model):
    name = models.CharField(max_length=100)  # Name of the skill
    code = models.CharField(max_length=50, unique=True)  # Code is unique (industry + skill number)
    description = models.TextField(blank=True)  # Description of the skill

    class Meta:
        db_table = 'job_skills'  # Custom table name
        ordering = ['name']

    def __str__(self):
        return self.name

    @classmethod
    def create_default_skills(cls):
        # Default skills by industry code with skill name and skill code
        default_skills = {
            'IT': [
                {'name': 'Software Development', 'code': 'IT-3F9A2'},
                {'name': 'Network Security', 'code': 'IT-7D1B3'},
                {'name': 'System Administration', 'code': 'IT-1E8F5'},
                {'name': 'Database Management', 'code': 'IT-9C2D4'},
                {'name': 'Technical Support', 'code': 'IT-5B3A8'},
                {'name': 'Python Programming', 'code': 'IT-6A1B9'},
                {'name': 'Java Programming', 'code': 'IT-4C8F7'},
                {'name': 'Kotlin Programming', 'code': 'IT-3D6E2'},
                {'name': 'Web Development', 'code': 'IT-9B7C1'},
                {'name': 'Cloud Computing', 'code': 'IT-5F2A4'},
                {'name': 'Ruby Programming', 'code': 'IT-8C9B6'},
                {'name': 'JavaScript Programming', 'code': 'IT-3D2A7'},
                {'name': 'PHP Development', 'code': 'IT-1E5F8'},
                {'name': 'C++ Programming', 'code': 'IT-4B7A1'},
                {'name': 'C# Programming', 'code': 'IT-9C1B6'},
                {'name': 'Swift Programming', 'code': 'IT-8F3D2'},
                {'name': 'SQL Databases', 'code': 'IT-7A9E1'},
                {'name': 'NoSQL Databases', 'code': 'IT-6B4F5'},
                {'name': 'Mobile App Development', 'code': 'IT-5C3E7'},
                {'name': 'Blockchain Development', 'code': 'IT-2D9A8'},
                {'name': 'DevOps', 'code': 'IT-3F6B9'},
                {'name': 'Cybersecurity', 'code': 'IT-1A5D3'},
                {'name': 'Big Data', 'code': 'IT-9F7A4'},
                {'name': 'AI Development', 'code': 'IT-6B1F7'},
                {'name': 'Machine Learning', 'code': 'IT-5C8A2'},
                {'name': 'Data Science', 'code': 'IT-7D3B9'},
                {'name': 'Git Version Control', 'code': 'IT-4A1F8'},
                {'name': 'Agile Methodology', 'code': 'IT-8C2D7'},
                {'name': 'Software Testing', 'code': 'IT-5E9B4'},
                {'name': 'Network Administration', 'code': 'IT-6F7A1'},
                {'name': 'Cloud Architecture', 'code': 'IT-2B3C9'},
                {'name': 'Linux Administration', 'code': 'IT-7A8F6'},
                {'name': 'Windows Server Administration', 'code': 'IT-1C5D9'},
                {'name': 'AWS', 'code': 'IT-4E8B2'},
                {'name': 'Google Cloud', 'code': 'IT-3D6F1'},
                {'name': 'Azure Cloud', 'code': 'IT-9C5A3'},
                {'name': 'Data Analytics', 'code': 'IT-2A7B8'},
                {'name': 'IoT (Internet of Things)', 'code': 'IT-6E9F3'},
                {'name': 'Virtualization', 'code': 'IT-5D4C1'},
                {'name': 'AR/VR Development', 'code': 'IT-7F1B9'},
                {'name': 'Web Security', 'code': 'IT-8A6E3'},
                {'name': 'SQL Query Optimization', 'code': 'IT-2F4D9'},
                {'name': 'Docker', 'code': 'IT-3C7A5'},
                {'name': 'Containers', 'code': 'IT-5E8F2'},
                {'name': 'Serverless Architecture', 'code': 'IT-9F4B7'},
                {'name': 'Infrastructure as Code', 'code': 'IT-1A3C8'},
                {'name': 'Jenkins', 'code': 'IT-4E2D9'},
                {'name': 'Ansible', 'code': 'IT-5B7F1'},
                {'name': 'Terraform', 'code': 'IT-3C9A2'},
                {'name': 'Kubernetes', 'code': 'IT-8B1F6'}
            ],

            'TECH': [
                {'name': 'Project Management', 'code': 'TECH-5C9B4'},
                {'name': 'UI/UX Design', 'code': 'TECH-1A8F3'},
                {'name': 'Web Development', 'code': 'TECH-7B6F1'},
                {'name': 'Data Analysis', 'code': 'TECH-3E5C8'},
                {'name': 'Machine Learning', 'code': 'TECH-2B4A7'},
                {'name': 'Artificial Intelligence', 'code': 'TECH-6C1F5'},
                {'name': 'Big Data', 'code': 'TECH-9F3A4'},
                {'name': 'Blockchain Development', 'code': 'TECH-4B7C9'},
                {'name': 'Digital Marketing', 'code': 'TECH-5D3A8'},
                {'name': 'Product Management', 'code': 'TECH-6F9B2'},
                {'name': 'Cloud Computing', 'code': 'TECH-7C2D1'},
                {'name': 'SEO', 'code': 'TECH-3B9F4'},
                {'name': 'Content Strategy', 'code': 'TECH-4E5A1'},
                {'name': 'Web Analytics', 'code': 'TECH-9F7B6'},
                {'name': 'App Development', 'code': 'TECH-6C4F2'},
                {'name': 'Growth Hacking', 'code': 'TECH-1D7A5'},
                {'name': 'E-commerce Development', 'code': 'TECH-3C9B8'},
                {'name': 'Database Design', 'code': 'TECH-7F4A2'},
                {'name': 'Product Design', 'code': 'TECH-5B6F9'},
                {'name': 'Graphic Design', 'code': 'TECH-2A4D7'},
                {'name': 'Salesforce', 'code': 'TECH-8C5B1'},
                {'name': 'Customer Success', 'code': 'TECH-4E9D7'},
                {'name': 'CRM Systems', 'code': 'TECH-9B2F6'},
                {'name': 'Web Security', 'code': 'TECH-6C1D5'},
                {'name': 'Server Administration', 'code': 'TECH-2A7B9'},
                {'name': 'API Development', 'code': 'TECH-8D6F1'},
                {'name': 'Business Intelligence', 'code': 'TECH-4F7B2'},
                {'name': 'Cloud Security', 'code': 'TECH-9C1E5'},
                {'name': 'DevOps', 'code': 'TECH-3A7B6'},
                {'name': 'Automation Testing', 'code': 'TECH-5C9D2'},
                {'name': 'Mobile App Testing', 'code': 'TECH-6E3A4'},
                {'name': 'Software Architecture', 'code': 'TECH-7F8B1'},
                {'name': 'Agile Development', 'code': 'TECH-2D4E9'},
                {'name': 'Data Visualization', 'code': 'TECH-4F6A2'},
                {'name': 'Cloud Architecture', 'code': 'TECH-9C2B7'},
                {'name': 'Python Development', 'code': 'TECH-3E1F5'},
                {'name': 'JavaScript Development', 'code': 'TECH-8B2A7'},
                {'name': 'Ruby Development', 'code': 'TECH-7F9B4'},
                {'name': 'React Development', 'code': 'TECH-2A1B5'},
                {'name': 'Vue.js Development', 'code': 'TECH-6C4D9'},
                {'name': 'Angular Development', 'code': 'TECH-8F7C1'},
                {'name': 'JQuery Development', 'code': 'TECH-9E2A3'},
                {'name': 'Spring Framework', 'code': 'TECH-4C5F1'},
                {'name': 'Node.js Development', 'code': 'TECH-2A9B4'},
                {'name': 'PHP Development', 'code': 'TECH-3E7F2'},
                {'name': 'C++ Development', 'code': 'TECH-5B8F1'},
                {'name': 'C# Development', 'code': 'TECH-4D3E2'},
                {'name': 'Go Programming', 'code': 'TECH-9F7A5'},
                {'name': 'Swift Programming', 'code': 'TECH-8E3B1'},
                {'name': 'Kotlin Development', 'code': 'TECH-6C5F9'}
            ],

            'HS': [
                {'name': 'Medical Research', 'code': 'HS-7A1B9'},
                {'name': 'Clinical Trials', 'code': 'HS-5C9E3'},
                {'name': 'Healthcare Administration', 'code': 'HS-4B3F6'},
                {'name': 'Nursing', 'code': 'HS-9E2D4'},
                {'name': 'Pharmacy Management', 'code': 'HS-3A1F8'},
                {'name': 'Patient Care', 'code': 'HS-2B7F5'},
                {'name': 'Medical Billing', 'code': 'HS-6A4E1'},
                {'name': 'Emergency Response', 'code': 'HS-5C8A7'},
                {'name': 'Medical Coding', 'code': 'HS-7D1F9'},
                {'name': 'Surgical Assistance', 'code': 'HS-8C4A2'},
                {'name': 'Public Health', 'code': 'HS-2D9F4'},
                {'name': 'Healthcare IT', 'code': 'HS-1A3E7'},
                {'name': 'Pharmaceutical Sales', 'code': 'HS-5F2C8'},
                {'name': 'Medical Laboratory Technology', 'code': 'HS-9B1F3'},
                {'name': 'Radiology', 'code': 'HS-4C7E2'},
                {'name': 'Physical Therapy', 'code': 'HS-6A9F1'},
                {'name': 'Occupational Therapy', 'code': 'HS-8B5D2'},
                {'name': 'Dentistry', 'code': 'HS-7C9F4'},
                {'name': 'Healthcare Marketing', 'code': 'HS-5A2E7'},
                {'name': 'Health Education', 'code': 'HS-1F4B6'},
                {'name': 'Public Health Policy', 'code': 'HS-9C3A1'},
                {'name': 'Epidemiology', 'code': 'HS-2D8F5'},
                {'name': 'Toxicology', 'code': 'HS-6A9B4'},
                {'name': 'Mental Health', 'code': 'HS-4F3A7'},
                {'name': 'Health Informatics', 'code': 'HS-3B2F8'},
                {'name': 'Medical Device Technology', 'code': 'HS-7E6C9'},
                {'name': 'Pediatrics', 'code': 'HS-5A8B1'},
                {'name': 'Geriatrics', 'code': 'HS-9F3B2'},
                {'name': 'Nutrition', 'code': 'HS-6E2F1'},
                {'name': 'Hospice Care', 'code': 'HS-4D1A5'},
                {'name': 'Clinical Psychology', 'code': 'HS-8F9B4'},
                {'name': 'Veterinary Care', 'code': 'HS-1E7C9'},
                {'name': 'Medical Supply Chain', 'code': 'HS-3C9F1'},
                {'name': 'Clinical Pharmacology', 'code': 'HS-6B2A8'},
                {'name': 'Healthcare Consulting', 'code': 'HS-9A3F7'},
                {'name': 'Health Insurance', 'code': 'HS-2B6A4'},
                {'name': 'Regulatory Affairs', 'code': 'HS-5C1D7'},
                {'name': 'Telemedicine', 'code': 'HS-3A7F6'},
                {'name': 'Healthcare Analytics', 'code': 'HS-7F4C9'},
                {'name': 'Surgical Technology', 'code': 'HS-8D1B5'},
                {'name': 'Medical Devices Regulatory', 'code': 'HS-9E7A3'},
                {'name': 'Healthcare Software', 'code': 'HS-7C2A8'},
                {'name': 'Ambulance Services', 'code': 'HS-8B1F2'},
                {'name': 'Forensic Medicine', 'code': 'HS-9D6A1'},
                {'name': 'Medical Records', 'code': 'HS-4C9E7'},
                {'name': 'Medical Tourism', 'code': 'HS-6A1D9'},
                {'name': 'Healthcare Operations', 'code': 'HS-2F9C8'},
                {'name': 'Telehealth', 'code': 'HS-7B1E3'},
                {'name': 'Palliative Care', 'code': 'HS-8D5F2'},
                {'name': 'Health Coaching', 'code': 'HS-5E9C3'}
            ],

            'EDU': [
                {'name': 'Teaching', 'code': 'EDU-A3F2D'},
                {'name': 'Curriculum Design', 'code': 'EDU-9B1ZJ'},
                {'name': 'Classroom Management', 'code': 'EDU-P8V4X'},
                {'name': 'Educational Technology', 'code': 'EDU-M0W9G'},
                {'name': 'Instructional Design', 'code': 'EDU-L3T6Y'},
                {'name': 'Learning Assessment', 'code': 'EDU-R7U5K'},
                {'name': 'Teacher Training', 'code': 'EDU-T2Z8V'},
                {'name': 'Special Education', 'code': 'EDU-B9X6L'},
                {'name': 'Language Teaching', 'code': 'EDU-W1J3K'},
                {'name': 'Pedagogy', 'code': 'EDU-Y5A2Z'},
                {'name': 'Educational Research', 'code': 'EDU-Q8V1P'},
                {'name': 'Educational Leadership', 'code': 'EDU-J4C7D'},
                {'name': 'Higher Education Administration', 'code': 'EDU-E6T2Z'},
                {'name': 'Student Support Services', 'code': 'EDU-U3F0J'},
                {'name': 'Online Education', 'code': 'EDU-P9S4F'},
                {'name': 'Learning Management Systems', 'code': 'EDU-X5T7P'},
                {'name': 'Educational Administration', 'code': 'EDU-O2J9W'},
                {'name': 'Teacher Evaluation', 'code': 'EDU-Q0V7R'},
                {'name': 'K-12 Education', 'code': 'EDU-Y1X2T'},
                {'name': 'Adult Education', 'code': 'EDU-B7P4V'},
                {'name': 'Tutoring', 'code': 'EDU-C8Q5H'},
                {'name': 'Instructional Technology', 'code': 'EDU-R4V2S'},
                {'name': 'E-learning Development', 'code': 'EDU-J3W7D'},
                {'name': 'Classroom Technology', 'code': 'EDU-F2V6R'},
                {'name': 'Student Engagement', 'code': 'EDU-P8C2S'},
                {'name': 'School Management', 'code': 'EDU-M9K4L'},
                {'name': 'Curriculum Assessment', 'code': 'EDU-G1W5F'},
                {'name': 'Language Assessment', 'code': 'EDU-J6P7T'},
                {'name': 'Education Policy', 'code': 'EDU-N4Z0F'},
                {'name': 'Academic Advising', 'code': 'EDU-V3X9L'},
                {'name': 'School Counseling', 'code': 'EDU-S1A4D'},
                {'name': 'University Administration', 'code': 'EDU-W8P3R'},
                {'name': 'Education Law', 'code': 'EDU-B5L7S'},
                {'name': 'Global Education', 'code': 'EDU-D2M8V'},
                {'name': 'Inclusive Education', 'code': 'EDU-A6Z9L'},
                {'name': 'School Safety', 'code': 'EDU-K3X7Y'},
                {'name': 'College Admissions', 'code': 'EDU-F4B2Q'},
                {'name': 'Distance Learning', 'code': 'EDU-J1Z8F'},
                {'name': 'Vocational Education', 'code': 'EDU-P9N4Y'},
                {'name': 'Peer Tutoring', 'code': 'EDU-O7V2L'},
                {'name': 'Nonprofit Education', 'code': 'EDU-C3B1K'},
                {'name': 'School Psychology', 'code': 'EDU-Q4D0R'},
                {'name': 'Educational Software', 'code': 'EDU-M5L3V'},
                {'name': 'Study Abroad Programs', 'code': 'EDU-S8K2W'},
                {'name': 'Higher Ed Marketing', 'code': 'EDU-H9Z1N'},
                {'name': 'Grant Writing', 'code': 'EDU-T2P5R'},
                {'name': 'Educational Consulting', 'code': 'EDU-K7F8N'},
                {'name': 'School Finance', 'code': 'EDU-W6J0C'},
                {'name': 'STEM Education', 'code': 'EDU-V3Z5P'},
                {'name': 'STEAM Education', 'code': 'EDU-A8Y2M'},
            ],

            'ACC': [
                {'name': 'Financial Reporting', 'code': 'ACC-F9B5Y'},
                {'name': 'Tax Preparation', 'code': 'ACC-M4Z3V'},
                {'name': 'Auditing', 'code': 'ACC-H1D9G'},
                {'name': 'Cost Accounting', 'code': 'ACC-E8L2X'},
                {'name': 'Forensic Accounting', 'code': 'ACC-C3Y7T'},
                {'name': 'Financial Analysis', 'code': 'ACC-V5K1D'},
                {'name': 'Management Accounting', 'code': 'ACC-T9F3P'},
                {'name': 'Internal Controls', 'code': 'ACC-S2D6M'},
                {'name': 'Budgeting', 'code': 'ACC-W0R7K'},
                {'name': 'Investment Management', 'code': 'ACC-N4C1V'},
                {'name': 'Corporate Finance', 'code': 'ACC-P3X5T'},
                {'name': 'Bank Reconciliation', 'code': 'ACC-Q7M8B'},
                {'name': 'Accounts Payable', 'code': 'ACC-R9A4D'},
                {'name': 'Accounts Receivable', 'code': 'ACC-J5S0C'},
                {'name': 'Payroll Processing', 'code': 'ACC-G1D2M'},
                {'name': 'Financial Forecasting', 'code': 'ACC-T7V9Q'},
                {'name': 'Risk Management', 'code': 'ACC-B5P3Y'},
                {'name': 'Investment Analysis', 'code': 'ACC-F0S9K'},
                {'name': 'Credit Analysis', 'code': 'ACC-M8L2H'},
                {'name': 'Financial Modeling', 'code': 'ACC-X4V7S'},
                {'name': 'Tax Compliance', 'code': 'ACC-W1A3J'},
                {'name': 'Financial Audit', 'code': 'ACC-L9K6Q'},
                {'name': 'ERP Systems', 'code': 'ACC-D2F8V'},
                {'name': 'General Ledger', 'code': 'ACC-H5X0N'},
                {'name': 'QuickBooks', 'code': 'ACC-V3G9M'},
                {'name': 'Xero', 'code': 'ACC-Y1D4P'},
                {'name': 'Financial Regulations', 'code': 'ACC-Z5Q1J'},
                {'name': 'Financial Planning', 'code': 'ACC-P9V3X'},
                {'name': 'Nonprofit Accounting', 'code': 'ACC-R8L4G'},
                {'name': 'Financial Reporting Standards', 'code': 'ACC-S7M1D'},
                {'name': 'Mergers and Acquisitions', 'code': 'ACC-J0P2T'},
                {'name': 'Corporate Taxation', 'code': 'ACC-F3A7K'},
                {'name': 'Real Estate Accounting', 'code': 'ACC-R6V4Y'},
                {'name': 'Public Accounting', 'code': 'ACC-Z9M1B'},
                {'name': 'International Accounting', 'code': 'ACC-U8W5L'},
                {'name': 'Financial Statement Preparation', 'code': 'ACC-X2J9S'},
                {'name': 'Fixed Assets Accounting', 'code': 'ACC-N6C4B'},
                {'name': 'Business Valuation', 'code': 'ACC-V0P2D'},
                {'name': 'Treasury Management', 'code': 'ACC-S8M4P'},
                {'name': 'Payroll Taxation', 'code': 'ACC-J4A5W'},
                {'name': 'Financial Software Implementation', 'code': 'ACC-Q9B1F'},
                {'name': 'Debt Management', 'code': 'ACC-T3P0S'},
                {'name': 'Accounting Research', 'code': 'ACC-M7X1B'},
                {'name': 'Fraud Prevention', 'code': 'ACC-P2S9L'},
                {'name': 'Accounting Systems', 'code': 'ACC-H6T7P'},
                {'name': 'Investment Banking', 'code': 'ACC-W0R1D'},
                {'name': 'Accounting Standards', 'code': 'ACC-B7X4Y'},
                {'name': 'Audit Planning', 'code': 'ACC-Z3P8T'},
                {'name': 'Financial Due Diligence', 'code': 'ACC-R4Q1M'},
                {'name': 'Corporate Accounting', 'code': 'ACC-K9F2W'},
            ],

            'PHAR': [
                {'name': 'Pharmaceutical Sales', 'code': 'PHAR-A1B2C'},
                {'name': 'Clinical Research', 'code': 'PHAR-E3D4F'},
                {'name': 'Regulatory Affairs', 'code': 'PHAR-G5H6I'},
                {'name': 'Pharmacovigilance', 'code': 'PHAR-J7K8L'},
                {'name': 'Formulation Development', 'code': 'PHAR-M9N0O'},
                {'name': 'Pharmaceutical Marketing', 'code': 'PHAR-P1Q2R'},
                {'name': 'Drug Safety', 'code': 'PHAR-S3T4U'},
                {'name': 'Quality Control', 'code': 'PHAR-V5W6X'},
                {'name': 'Drug Development', 'code': 'PHAR-Y7Z8A'},
                {'name': 'Pharmaceutical Manufacturing', 'code': 'PHAR-B9C0D'},
                {'name': 'Good Manufacturing Practices', 'code': 'PHAR-E1F2G'},
                {'name': 'Clinical Trials', 'code': 'PHAR-H3I4J'},
                {'name': 'Medical Affairs', 'code': 'PHAR-K5L6M'},
                {'name': 'Pharmaceutical Research', 'code': 'PHAR-N7O8P'},
                {'name': 'Clinical Data Management', 'code': 'PHAR-Q9R0S'},
                {'name': 'Pharmacy Practice', 'code': 'PHAR-T1U2V'},
                {'name': 'Pharmacology', 'code': 'PHAR-W3X4Y'},
                {'name': 'Pharmacy Technology', 'code': 'PHAR-Z5A6B'},
                {'name': 'Regulatory Compliance', 'code': 'PHAR-C7D8E'},
                {'name': 'Pharmaceutical Operations', 'code': 'PHAR-F9G0H'},
                {'name': 'Health Economics', 'code': 'PHAR-I1J2K'},
                {'name': 'Pharmacogenomics', 'code': 'PHAR-L3M4N'},
                {'name': 'Medical Writing', 'code': 'PHAR-O5P6Q'},
                {'name': 'Drug Packaging', 'code': 'PHAR-R7S8T'},
                {'name': 'Clinical Pharmacology', 'code': 'PHAR-U9V0W'},
                {'name': 'Biopharmaceuticals', 'code': 'PHAR-X1Y2Z'},
                {'name': 'Pharmacy Law', 'code': 'PHAR-A3B4C'},
                {'name': 'Pharmaceutical Project Management', 'code': 'PHAR-D5E6F'},
                {'name': 'Supply Chain Management', 'code': 'PHAR-G7H8I'},
                {'name': 'Pharmacy Informatics', 'code': 'PHAR-J9K0L'},
                {'name': 'Regulatory Submissions', 'code': 'PHAR-M1N2O'},
                {'name': 'Clinical Pharmacist', 'code': 'PHAR-P3Q4R'},
                {'name': 'Clinical Trial Monitoring', 'code': 'PHAR-S5T6U'},
                {'name': 'Pharmaceutical Chemistry', 'code': 'PHAR-V7W8X'},
                {'name': 'Pharmacokinetics', 'code': 'PHAR-Y9Z0A'},
                {'name': 'Drug Stability Testing', 'code': 'PHAR-B1C2D'},
                {'name': 'Pharmaceutical Quality Assurance', 'code': 'PHAR-E3F4G'},
                {'name': 'Medical Device Regulation', 'code': 'PHAR-H5I6J'},
                {'name': 'Pharmacy Education', 'code': 'PHAR-K7L8M'},
                {'name': 'Preclinical Development', 'code': 'PHAR-N9O0P'},
                {'name': 'Biotechnology', 'code': 'PHAR-Q1R2S'},
                {'name': 'Pharmacy Administration', 'code': 'PHAR-T3U4V'},
                {'name': 'Medication Therapy Management', 'code': 'PHAR-W5X6Y'},
                {'name': 'Pharmacy Operations Management', 'code': 'PHAR-Z7A8B'},
                {'name': 'Drug Discovery', 'code': 'PHAR-C9D0E'},
                {'name': 'Pharmaceutical Patents', 'code': 'PHAR-F1G2H'},
                {'name': 'Compounding', 'code': 'PHAR-I3J4K'},
                {'name': 'Pharmacovigilance Reporting', 'code': 'PHAR-L5M6N'},
                {'name': 'Pharmacy Technology Systems', 'code': 'PHAR-O7P8Q'},
                {'name': 'Clinical Pharmacy Research', 'code': 'PHAR-R9S0T'}
            ],

            'FIN': [
                {'name': 'Financial Analysis', 'code': 'FIN-A1B2C'},
                {'name': 'Investment Management', 'code': 'FIN-D3E4F'},
                {'name': 'Risk Management', 'code': 'FIN-G5H6I'},
                {'name': 'Corporate Finance', 'code': 'FIN-J7K8L'},
                {'name': 'Financial Forecasting', 'code': 'FIN-M9N0O'},
                {'name': 'Financial Modeling', 'code': 'FIN-P1Q2R'},
                {'name': 'Mergers and Acquisitions', 'code': 'FIN-S3T4U'},
                {'name': 'Debt Management', 'code': 'FIN-V5W6X'},
                {'name': 'Credit Analysis', 'code': 'FIN-Y7Z8A'},
                {'name': 'Financial Reporting', 'code': 'FIN-B9C0D'},
                {'name': 'Capital Budgeting', 'code': 'FIN-E1F2G'},
                {'name': 'Private Equity', 'code': 'FIN-H3I4J'},
                {'name': 'Tax Planning', 'code': 'FIN-K5L6M'},
                {'name': 'Investment Banking', 'code': 'FIN-N7O8P'},
                {'name': 'Financial Strategy', 'code': 'FIN-Q9R0S'},
                {'name': 'Portfolio Management', 'code': 'FIN-T1U2V'},
                {'name': 'Financial Risk Analysis', 'code': 'FIN-W3X4Y'},
                {'name': 'Treasury Management', 'code': 'FIN-Z5A6B'},
                {'name': 'Financial Compliance', 'code': 'FIN-C7D8E'},
                {'name': 'Business Valuation', 'code': 'FIN-F9G0H'},
                {'name': 'Asset Management', 'code': 'FIN-I1J2K'},
                {'name': 'Investment Advisory', 'code': 'FIN-L3M4N'},
                {'name': 'Financial Planning', 'code': 'FIN-O5P6Q'},
                {'name': 'Banking Operations', 'code': 'FIN-R7S8T'},
                {'name': 'Corporate Accounting', 'code': 'FIN-U9V0W'},
                {'name': 'Financial Regulation', 'code': 'FIN-X1Y2Z'},
                {'name': 'Quantitative Finance', 'code': 'FIN-A3B4C'},
                {'name': 'Business Finance', 'code': 'FIN-D5E6F'},
                {'name': 'Financial Statement Analysis', 'code': 'FIN-G7H8I'},
                {'name': 'Market Analysis', 'code': 'FIN-J9K0L'},
                {'name': 'Wealth Management', 'code': 'FIN-M1N2O'},
                {'name': 'Insurance Planning', 'code': 'FIN-P3Q4R'},
                {'name': 'Corporate Taxation', 'code': 'FIN-S5T6U'},
                {'name': 'Financial Software', 'code': 'FIN-V7W8X'},
                {'name': 'Investment Strategy', 'code': 'FIN-Y9Z0A'},
                {'name': 'Global Finance', 'code': 'FIN-B1C2D'},
                {'name': 'Financial Research', 'code': 'FIN-E3F4G'},
                {'name': 'Banking Laws', 'code': 'FIN-H5I6J'},
                {'name': 'Asset Allocation', 'code': 'FIN-K7L8M'},
                {'name': 'Financial Due Diligence', 'code': 'FIN-N9O0P'},
                {'name': 'Retail Banking', 'code': 'FIN-Q1R2S'},
                {'name': 'Financial Technology', 'code': 'FIN-T3U4V'},
                {'name': 'Hedge Funds', 'code': 'FIN-W5X6Y'},
                {'name': 'Financial Data Analysis', 'code': 'FIN-Z7A8B'},
                {'name': 'Financial Reporting Standards', 'code': 'FIN-C9D0E'},
                {'name': 'Real Estate Investment', 'code': 'FIN-F1G2H'},
                {'name': 'Credit Risk', 'code': 'FIN-I3J4K'},
                {'name': 'Behavioral Finance', 'code': 'FIN-L5M6N'},
                {'name': 'Compliance Monitoring', 'code': 'FIN-O7P8Q'},
                {'name': 'Financial Performance Measurement', 'code': 'FIN-R9S0T'}
            ],

            'ENG': [
                {'name': 'Mechanical Engineering', 'code': 'ENG-A1B2C'},
                {'name': 'Civil Engineering', 'code': 'ENG-D3E4F'},
                {'name': 'Electrical Engineering', 'code': 'ENG-G5H6I'},
                {'name': 'Software Engineering', 'code': 'ENG-J7K8L'},
                {'name': 'Structural Engineering', 'code': 'ENG-M9N0O'},
                {'name': 'Project Management', 'code': 'ENG-P1Q2R'},
                {'name': 'Engineering Design', 'code': 'ENG-S3T4U'},
                {'name': 'Geotechnical Engineering', 'code': 'ENG-V5W6X'},
                {'name': 'Automation Engineering', 'code': 'ENG-Y7Z8A'},
                {'name': 'Renewable Energy', 'code': 'ENG-B9C0D'},
                {'name': 'Robotics Engineering', 'code': 'ENG-E1F2G'},
                {'name': 'Industrial Engineering', 'code': 'ENG-H3I4J'},
                {'name': 'Civil Construction', 'code': 'ENG-K5L6M'},
                {'name': 'Electrical Systems', 'code': 'ENG-N7O8P'},
                {'name': 'Mechatronics Engineering', 'code': 'ENG-Q9R0S'},
                {'name': 'Marine Engineering', 'code': 'ENG-T1U2V'},
                {'name': 'Environmental Engineering', 'code': 'ENG-W3X4Y'},
                {'name': 'Manufacturing Engineering', 'code': 'ENG-Z5A6B'},
                {'name': 'Aerospace Engineering', 'code': 'ENG-C7D8E'},
                {'name': 'Nuclear Engineering', 'code': 'ENG-F9G0H'},
                {'name': 'Telecommunications Engineering', 'code': 'ENG-I1J2K'},
                {'name': 'Energy Engineering', 'code': 'ENG-L3M4N'},
                {'name': 'Engineering Software', 'code': 'ENG-O5P6Q'},
                {'name': 'Construction Management', 'code': 'ENG-R7S8T'},
                {'name': 'HVAC Engineering', 'code': 'ENG-U9V0W'},
                {'name': 'Biomedical Engineering', 'code': 'ENG-X1Y2Z'},
                {'name': 'Geological Engineering', 'code': 'ENG-A3B4C'},
                {'name': 'Design Engineering', 'code': 'ENG-D5E6F'},
                {'name': 'Control Systems', 'code': 'ENG-G7H8I'},
                {'name': 'Materials Engineering', 'code': 'ENG-J9K0L'},
                {'name': 'Engineering Analysis', 'code': 'ENG-M1N2O'},
                {'name': 'Surveying Engineering', 'code': 'ENG-P3Q4R'},
                {'name': 'Engineering Consulting', 'code': 'ENG-S5T6U'},
                {'name': 'Traffic Engineering', 'code': 'ENG-V7W8X'},
                {'name': 'Water Resources Engineering', 'code': 'ENG-Y9Z0A'},
                {'name': 'Engineering Research', 'code': 'ENG-B1C2D'},
                {'name': 'Sustainable Engineering', 'code': 'ENG-E3F4G'},
                {'name': 'Engineering Education', 'code': 'ENG-H5I6J'},
                {'name': 'Construction Engineering', 'code': 'ENG-K7L8M'},
                {'name': 'Engineering Technology', 'code': 'ENG-N9O0P'},
                {'name': 'Industrial Automation', 'code': 'ENG-Q1R2S'}
            ],

            'RE': [
                {'name': 'Residential Real Estate', 'code': 'RE-A1B2C'},
                {'name': 'Commercial Real Estate', 'code': 'RE-D3E4F'},
                {'name': 'Real Estate Investment', 'code': 'RE-G5H6I'},
                {'name': 'Property Management', 'code': 'RE-J7K8L'},
                {'name': 'Real Estate Development', 'code': 'RE-M9N0O'},
                {'name': 'Real Estate Finance', 'code': 'RE-P1Q2R'},
                {'name': 'Real Estate Marketing', 'code': 'RE-S3T4U'},
                {'name': 'Urban Planning', 'code': 'RE-V5W6X'},
                {'name': 'Real Estate Appraisal', 'code': 'RE-Y7Z8A'},
                {'name': 'Commercial Leasing', 'code': 'RE-B9C0D'},
                {'name': 'Residential Leasing', 'code': 'RE-E1F2G'},
                {'name': 'Real Estate Brokerage', 'code': 'RE-H3I4J'},
                {'name': 'Real Estate Law', 'code': 'RE-K5L6M'},
                {'name': 'Construction Management', 'code': 'RE-N7O8P'},
                {'name': 'Real Estate Valuation', 'code': 'RE-Q9R0S'},
                {'name': 'Real Estate Investment Trusts', 'code': 'RE-T1U2V'},
                {'name': 'Property Development', 'code': 'RE-W3X4Y'},
                {'name': 'Real Estate Sales', 'code': 'RE-Z5A6B'},
                {'name': 'Real Estate Financing', 'code': 'RE-C7D8E'},
                {'name': 'Mortgage Brokerage', 'code': 'RE-F9G0H'},
                {'name': 'Real Estate Advisory', 'code': 'RE-I1J2K'},
                {'name': 'Property Taxation', 'code': 'RE-L3M4N'},
                {'name': 'Land Development', 'code': 'RE-O5P6Q'},
                {'name': 'Real Estate Economics', 'code': 'RE-R7S8T'},
                {'name': 'Real Estate Consulting', 'code': 'RE-U9V0W'},
                {'name': 'Real Estate Asset Management', 'code': 'RE-X1Y2Z'},
                {'name': 'Luxury Real Estate', 'code': 'RE-A3B4C'},
                {'name': 'Real Estate Syndication', 'code': 'RE-D5E6F'},
                {'name': 'Investment Property', 'code': 'RE-G7H8I'},
                {'name': 'Real Estate Taxes', 'code': 'RE-J9K0L'},
                {'name': 'Real Estate Management Software', 'code': 'RE-M1N2O'},
                {'name': 'Commercial Property Management', 'code': 'RE-P3Q4R'},
                {'name': 'Real Estate Transaction', 'code': 'RE-S5T6U'},
                {'name': 'Real Estate Compliance', 'code': 'RE-V7W8X'}
            ],

            'SALES': [
                {'name': 'Sales Strategy', 'code': 'SALES-1A2B3'},
                {'name': 'Customer Relationship Management (CRM)', 'code': 'SALES-4C5D6'},
                {'name': 'Sales Negotiation', 'code': 'SALES-7E8F9'},
                {'name': 'Lead Generation', 'code': 'SALES-A1B2C'},
                {'name': 'Sales Analytics', 'code': 'SALES-D3E4F'},
                {'name': 'B2B Sales', 'code': 'SALES-G5H6I'},
                {'name': 'B2C Sales', 'code': 'SALES-J7K8L'},
                {'name': 'Product Knowledge', 'code': 'SALES-M9N0O'},
                {'name': 'Sales Presentations', 'code': 'SALES-P1Q2R'},
                {'name': 'Account Management', 'code': 'SALES-S3T4U'},
                {'name': 'Sales Forecasting', 'code': 'SALES-V5W6X'},
                {'name': 'Sales Performance Tracking', 'code': 'SALES-Y7Z8A'},
                {'name': 'Negotiation Skills', 'code': 'SALES-B9C0D'},
                {'name': 'Sales Leadership', 'code': 'SALES-E1F2G'},
                {'name': 'Market Research', 'code': 'SALES-H3I4J'},
                {'name': 'Customer Retention', 'code': 'SALES-K5L6M'},
                {'name': 'Sales Reporting', 'code': 'SALES-N7O8P'},
                {'name': 'Competitive Intelligence', 'code': 'SALES-Q9R0S'},
                {'name': 'Sales Training', 'code': 'SALES-T1U2V'},
                {'name': 'Field Sales', 'code': 'SALES-W3X4Y'},
                {'name': 'Sales Process Optimization', 'code': 'SALES-Z5A6B'},
                {'name': 'Pricing Strategy', 'code': 'SALES-C7D8E'},
                {'name': 'Channel Sales', 'code': 'SALES-F9G0H'},
                {'name': 'Sales Enablement', 'code': 'SALES-I1J2K'},
                {'name': 'Negotiation Tactics', 'code': 'SALES-L3M4N'},
                {'name': 'Client Onboarding', 'code': 'SALES-O5P6Q'},
                {'name': 'Sales Operations', 'code': 'SALES-R7S8T'},
                {'name': 'Cross-Selling', 'code': 'SALES-U9V0W'},
                {'name': 'Upselling', 'code': 'SALES-X1Y2Z'},
                {'name': 'Team Collaboration', 'code': 'SALES-A3B4C'}
            ],

            'GOV': [
                {'name': 'Policy Analysis', 'code': 'GOV-1A2B3'},
                {'name': 'Public Administration', 'code': 'GOV-4C5D6'},
                {'name': 'Government Relations', 'code': 'GOV-7E8F9'},
                {'name': 'Regulatory Affairs', 'code': 'GOV-A1B2C'},
                {'name': 'Public Policy', 'code': 'GOV-D3E4F'},
                {'name': 'Legislation Process', 'code': 'GOV-G5H6I'},
                {'name': 'Government Budgeting', 'code': 'GOV-J7K8L'},
                {'name': 'Governmental Affairs', 'code': 'GOV-M9N0O'},
                {'name': 'Crisis Management', 'code': 'GOV-P1Q2R'},
                {'name': 'Public Sector Governance', 'code': 'GOV-S3T4U'},
                {'name': 'Election Campaign Strategy', 'code': 'GOV-V5W6X'},
                {'name': 'Public Engagement', 'code': 'GOV-Y7Z8A'},
                {'name': 'Community Outreach', 'code': 'GOV-B9C0D'},
                {'name': 'Government Policy Writing', 'code': 'GOV-E1F2G'},
                {'name': 'Public Sector Finance', 'code': 'GOV-H3I4J'},
                {'name': 'International Relations', 'code': 'GOV-K5L6M'},
                {'name': 'Diplomatic Relations', 'code': 'GOV-N7O8P'},
                {'name': 'Government Compliance', 'code': 'GOV-Q9R0S'},
                {'name': 'Urban Planning', 'code': 'GOV-T1U2V'},
                {'name': 'Emergency Management', 'code': 'GOV-W3X4Y'},
                {'name': 'Government Contracting', 'code': 'GOV-Z5A6B'},
                {'name': 'Public Sector Marketing', 'code': 'GOV-C7D8E'},
                {'name': 'Public Relations', 'code': 'GOV-F9G0H'},
                {'name': 'Public Funding', 'code': 'GOV-I1J2K'},
                {'name': 'Government Research', 'code': 'GOV-L3M4N'},
                {'name': 'Public Safety', 'code': 'GOV-O5P6Q'},
                {'name': 'Civic Engagement', 'code': 'GOV-R7S8T'},
                {'name': 'Transparency & Accountability', 'code': 'GOV-U9V0W'}
            ],

            'ENERGY': [
                {'name': 'Energy Management', 'code': 'ENERGY-1A2B3'},
                {'name': 'Renewable Energy', 'code': 'ENERGY-4C5D6'},
                {'name': 'Energy Efficiency', 'code': 'ENERGY-7E8F9'},
                {'name': 'Energy Policy', 'code': 'ENERGY-A1B2C'},
                {'name': 'Oil and Gas Industry', 'code': 'ENERGY-D3E4F'},
                {'name': 'Energy Systems', 'code': 'ENERGY-G5H6I'},
                {'name': 'Power Generation', 'code': 'ENERGY-J7K8L'},
                {'name': 'Solar Energy', 'code': 'ENERGY-M9N0O'},
                {'name': 'Wind Energy', 'code': 'ENERGY-P1Q2R'},
                {'name': 'Energy Storage', 'code': 'ENERGY-S3T4U'},
                {'name': 'Nuclear Energy', 'code': 'ENERGY-V5W6X'},
                {'name': 'Energy Transition', 'code': 'ENERGY-Y7Z8A'},
                {'name': 'Geothermal Energy', 'code': 'ENERGY-B9C0D'},
                {'name': 'Carbon Emission Reduction', 'code': 'ENERGY-E1F2G'},
                {'name': 'Electric Vehicles', 'code': 'ENERGY-H3I4J'},
                {'name': 'Energy Trading', 'code': 'ENERGY-K5L6M'},
                {'name': 'Hydropower', 'code': 'ENERGY-N7O8P'},
                {'name': 'Sustainable Energy Solutions', 'code': 'ENERGY-Q9R0S'},
                {'name': 'Energy Finance', 'code': 'ENERGY-T1U2V'},
                {'name': 'Energy Research', 'code': 'ENERGY-W3X4Y'},
                {'name': 'Clean Energy', 'code': 'ENERGY-Z5A6B'},
                {'name': 'Smart Grids', 'code': 'ENERGY-C7D8E'},
                {'name': 'Carbon Footprint Reduction', 'code': 'ENERGY-F9G0H'},
                {'name': 'Energy Auditing', 'code': 'ENERGY-I1J2K'},
                {'name': 'Energy Market Analysis', 'code': 'ENERGY-L3M4N'},
                {'name': 'Energy Consumption', 'code': 'ENERGY-O5P6Q'},
                {'name': 'Power Systems Engineering', 'code': 'ENERGY-R7S8T'}
            ],

            'RETAIL': [
                {'name': 'Retail Management', 'code': 'RETAIL-1A2B3'},
                {'name': 'Customer Service', 'code': 'RETAIL-4C5D6'},
                {'name': 'Sales Floor Management', 'code': 'RETAIL-7E8F9'},
                {'name': 'Inventory Management', 'code': 'RETAIL-A1B2C'},
                {'name': 'Visual Merchandising', 'code': 'RETAIL-D3E4F'},
                {'name': 'Retail Marketing', 'code': 'RETAIL-G5H6I'},
                {'name': 'Customer Relationship Management', 'code': 'RETAIL-J7K8L'},
                {'name': 'Retail Operations', 'code': 'RETAIL-M9N0O'},
                {'name': 'Point of Sale Systems', 'code': 'RETAIL-P1Q2R'},
                {'name': 'Product Assortment', 'code': 'RETAIL-S3T4U'},
                {'name': 'Retail Analytics', 'code': 'RETAIL-V5W6X'},
                {'name': 'Retail Sales Strategy', 'code': 'RETAIL-Y7Z8A'},
                {'name': 'Store Design', 'code': 'RETAIL-B9C0D'},
                {'name': 'Cash Management', 'code': 'RETAIL-E1F2G'},
                {'name': 'Supply Chain Management', 'code': 'RETAIL-H3I4J'},
                {'name': 'Product Knowledge', 'code': 'RETAIL-K5L6M'},
                {'name': 'E-commerce', 'code': 'RETAIL-N7O8P'},
                {'name': 'Retail Budgeting', 'code': 'RETAIL-Q9R0S'},
                {'name': 'Pricing Strategy', 'code': 'RETAIL-T1U2V'},
                {'name': 'Store Leadership', 'code': 'RETAIL-W3X4Y'},
                {'name': 'Retail Training', 'code': 'RETAIL-Z5A6B'},
                {'name': 'Branding', 'code': 'RETAIL-C7D8E'},
                {'name': 'Consumer Behavior', 'code': 'RETAIL-F9G0H'},
                {'name': 'Product Launch', 'code': 'RETAIL-I1J2K'},
                {'name': 'Retail Sales Training', 'code': 'RETAIL-L3M4N'},
                {'name': 'Merchandising', 'code': 'RETAIL-O5P6Q'},
                {'name': 'Retail Compliance', 'code': 'RETAIL-R7S8T'},
                {'name': 'Retail Technology', 'code': 'RETAIL-U9V0W'},
                {'name': 'Customer Experience', 'code': 'RETAIL-X1Y2Z'},
                {'name': 'Retail Finance', 'code': 'RETAIL-A3B4C'}
            ],

            'MANUFACTURING': [
                {'name': 'Production Planning', 'code': 'MANUFACTURING-1A2B3'},
                {'name': 'Lean Manufacturing', 'code': 'MANUFACTURING-4C5D6'},
                {'name': 'Six Sigma', 'code': 'MANUFACTURING-7E8F9'},
                {'name': 'Manufacturing Engineering', 'code': 'MANUFACTURING-A1B2C'},
                {'name': 'Quality Control', 'code': 'MANUFACTURING-D3E4F'},
                {'name': 'Supply Chain Optimization', 'code': 'MANUFACTURING-G5H6I'},
                {'name': 'Operations Management', 'code': 'MANUFACTURING-J7K8L'},
                {'name': 'Industrial Engineering', 'code': 'MANUFACTURING-M9N0O'},
                {'name': 'Materials Handling', 'code': 'MANUFACTURING-P1Q2R'},
                {'name': 'Process Improvement', 'code': 'MANUFACTURING-S3T4U'},
                {'name': 'Product Development', 'code': 'MANUFACTURING-V5W6X'},
                {'name': 'Manufacturing Software', 'code': 'MANUFACTURING-Y7Z8A'},
                {'name': 'Inventory Management', 'code': 'MANUFACTURING-B9C0D'},
                {'name': 'Production Scheduling', 'code': 'MANUFACTURING-E1F2G'},
                {'name': 'Facility Layout', 'code': 'MANUFACTURING-H3I4J'},
                {'name': 'Robotics', 'code': 'MANUFACTURING-K5L6M'},
                {'name': 'CNC Programming', 'code': 'MANUFACTURING-N7O8P'},
                {'name': 'Automation', 'code': 'MANUFACTURING-Q9R0S'},
                {'name': 'Maintenance Management', 'code': 'MANUFACTURING-T1U2V'},
                {'name': 'Machinery Operation', 'code': 'MANUFACTURING-W3X4Y'},
                {'name': 'Plant Operations', 'code': 'MANUFACTURING-Z5A6B'},
                {'name': 'Production Efficiency', 'code': 'MANUFACTURING-C7D8E'},
                {'name': 'Manufacturing Cost Reduction', 'code': 'MANUFACTURING-F9G0H'},
                {'name': 'Product Design', 'code': 'MANUFACTURING-I1J2K'},
                {'name': 'Inventory Optimization', 'code': 'MANUFACTURING-L3M4N'},
                {'name': 'Product Quality Assurance', 'code': 'MANUFACTURING-O5P6Q'},
                {'name': 'Process Control', 'code': 'MANUFACTURING-R7S8T'},
                {'name': 'Workforce Management', 'code': 'MANUFACTURING-U9V0W'}
            ],

            'ARCH': [
                {'name': 'Architectural Design', 'code': 'ARCH-A1B2C'},
                {'name': 'Urban Planning', 'code': 'ARCH-D3E4F'},
                {'name': 'Construction Management', 'code': 'ARCH-G5H6I'},
                {'name': 'Building Information Modeling (BIM)', 'code': 'ARCH-J7K8L'},
                {'name': 'Sustainable Design', 'code': 'ARCH-M9N0O'},
                {'name': 'Project Management', 'code': 'ARCH-P1Q2R'},
                {'name': 'Space Planning', 'code': 'ARCH-S3T4U'},
                {'name': 'Building Codes', 'code': 'ARCH-V5W6X'},
                {'name': 'Structural Engineering', 'code': 'ARCH-Y7Z8A'},
                {'name': 'Interior Architecture', 'code': 'ARCH-B9C0D'},
                {'name': 'Landscape Architecture', 'code': 'ARCH-E1F2G'},
                {'name': '3D Modeling', 'code': 'ARCH-H3I4J'},
                {'name': 'Construction Documentation', 'code': 'ARCH-K5L6M'},
                {'name': 'Sustainable Architecture', 'code': 'ARCH-N7O8P'},
                {'name': 'Architectural Drafting', 'code': 'ARCH-Q9R0S'},
                {'name': 'Design Software', 'code': 'ARCH-T1U2V'},
                {'name': 'Client Consultation', 'code': 'ARCH-W3X4Y'},
                {'name': 'Renovation Design', 'code': 'ARCH-Z5A6B'},
                {'name': 'Feasibility Studies', 'code': 'ARCH-C7D8E'},
                {'name': 'Contract Administration', 'code': 'ARCH-F9G0H'},
                {'name': 'Urban Design', 'code': 'ARCH-I1J2K'},
                {'name': 'Building Systems', 'code': 'ARCH-L3M4N'},
                {'name': 'Facade Design', 'code': 'ARCH-O5P6Q'},
                {'name': 'Lighting Design', 'code': 'ARCH-R7S8T'},
                {'name': 'Acoustic Design', 'code': 'ARCH-U9V0W'},
                {'name': 'Building Materials', 'code': 'ARCH-X1Y2Z'},
                {'name': 'Renovation Planning', 'code': 'ARCH-A3B4C'},
                {'name': 'Site Planning', 'code': 'ARCH-D5E6F'}
            ],

            'HR': [
                {'name': 'Talent Acquisition', 'code': 'HR-P1Q2R'},
                {'name': 'Employee Relations', 'code': 'HR-S3T4U'},
                {'name': 'Human Resource Management', 'code': 'HR-V5W6X'},
                {'name': 'Compensation and Benefits', 'code': 'HR-Y7Z8A'},
                {'name': 'Training and Development', 'code': 'HR-B9C0D'},
                {'name': 'Performance Management', 'code': 'HR-E1F2G'},
                {'name': 'HR Policies', 'code': 'HR-H3I4J'},
                {'name': 'Recruitment Strategy', 'code': 'HR-K5L6M'},
                {'name': 'Employee Engagement', 'code': 'HR-N7O8P'},
                {'name': 'Labor Law Compliance', 'code': 'HR-Q9R0S'},
                {'name': 'Workforce Planning', 'code': 'HR-T1U2V'},
                {'name': 'HR Technology', 'code': 'HR-W3X4Y'},
                {'name': 'HR Analytics', 'code': 'HR-Z5A6B'},
                {'name': 'Diversity and Inclusion', 'code': 'HR-C7D8E'},
                {'name': 'Payroll Management', 'code': 'HR-F9G0H'},
                {'name': 'Onboarding', 'code': 'HR-I1J2K'},
                {'name': 'HR Communication', 'code': 'HR-L3M4N'},
                {'name': 'Employee Retention', 'code': 'HR-O5P6Q'},
                {'name': 'Leadership Development', 'code': 'HR-R7S8T'},
                {'name': 'Workplace Culture', 'code': 'HR-U9V0W'},
                {'name': 'Organizational Development', 'code': 'HR-X1Y2Z'},
                {'name': 'Talent Management', 'code': 'HR-A3B4C'},
                {'name': 'Employee Wellness', 'code': 'HR-D5E6F'},
                {'name': 'Succession Planning', 'code': 'HR-G7H8I'},
                {'name': 'HR Compliance', 'code': 'HR-J9K0L'},
                {'name': 'Conflict Resolution', 'code': 'HR-M1N2O'},
                {'name': 'HR Consulting', 'code': 'HR-P3Q4R'},
                {'name': 'Global HR', 'code': 'HR-S5T6U'}
            ],

            'NONPROFIT': [
                {'name': 'Fundraising', 'code': 'NONPROFIT-A1B2C'},
                {'name': 'Grant Writing', 'code': 'NONPROFIT-D3E4F'},
                {'name': 'Program Management', 'code': 'NONPROFIT-G5H6I'},
                {'name': 'Nonprofit Leadership', 'code': 'NONPROFIT-J7K8L'},
                {'name': 'Nonprofit Marketing', 'code': 'NONPROFIT-M9N0O'},
                {'name': 'Volunteer Management', 'code': 'NONPROFIT-P1Q2R'},
                {'name': 'Public Relations', 'code': 'NONPROFIT-S3T4U'},
                {'name': 'Advocacy', 'code': 'NONPROFIT-V5W6X'},
                {'name': 'Nonprofit Fundraising Strategy', 'code': 'NONPROFIT-Y7Z8A'},
                {'name': 'Nonprofit Financial Management', 'code': 'NONPROFIT-B9C0D'},
                {'name': 'Program Evaluation', 'code': 'NONPROFIT-E1F2G'},
                {'name': 'Board Governance', 'code': 'NONPROFIT-H3I4J'},
                {'name': 'Philanthropy', 'code': 'NONPROFIT-K5L6M'},
                {'name': 'Community Outreach', 'code': 'NONPROFIT-N7O8P'},
                {'name': 'Nonprofit Compliance', 'code': 'NONPROFIT-Q9R0S'},
                {'name': 'Nonprofit Strategy', 'code': 'NONPROFIT-T1U2V'},
                {'name': 'Capacity Building', 'code': 'NONPROFIT-W3X4Y'},
                {'name': 'Nonprofit Advocacy', 'code': 'NONPROFIT-Z5A6B'},
                {'name': 'Social Impact', 'code': 'NONPROFIT-C7D8E'},
                {'name': 'Nonprofit Networking', 'code': 'NONPROFIT-F9G0H'},
                {'name': 'Nonprofit Marketing Strategy', 'code': 'NONPROFIT-I1J2K'},
                {'name': 'Nonprofit Fundraising Events', 'code': 'NONPROFIT-L3M4N'},
                {'name': 'Donor Relations', 'code': 'NONPROFIT-O5P6Q'},
                {'name': 'Nonprofit Event Planning', 'code': 'NONPROFIT-R7S8T'},
                {'name': 'Social Media for Nonprofits', 'code': 'NONPROFIT-U9V0W'},
                {'name': 'Nonprofit Data Analysis', 'code': 'NONPROFIT-X1Y2Z'},
                {'name': 'Nonprofit Financial Reporting', 'code': 'NONPROFIT-A3B4C'},
                {'name': 'Volunteer Coordination', 'code': 'NONPROFIT-D5E6F'},
                {'name': 'Nonprofit Advocacy Campaigns', 'code': 'NONPROFIT-G7H8I'},
                {'name': 'Community Engagement', 'code': 'NONPROFIT-J9K0L'}
            ],

            'TRANSPORT': [
                {'name': 'Logistics Management', 'code': 'TRANSPORT-B1C2D'},
                {'name': 'Supply Chain Management', 'code': 'TRANSPORT-E3F4G'},
                {'name': 'Fleet Management', 'code': 'TRANSPORT-H5I6J'},
                {'name': 'Transport Planning', 'code': 'TRANSPORT-K7L8M'},
                {'name': 'Transportation Systems', 'code': 'TRANSPORT-N9O0P'},
                {'name': 'Route Optimization', 'code': 'TRANSPORT-Q1R2S'},
                {'name': 'Freight Management', 'code': 'TRANSPORT-T3U4V'},
                {'name': 'Transport Safety', 'code': 'TRANSPORT-W5X6Y'},
                {'name': 'Transportation Logistics', 'code': 'TRANSPORT-Z7A8B'},
                {'name': 'Transport Operations', 'code': 'TRANSPORT-C9D0E'},
                {'name': 'Vehicle Maintenance', 'code': 'TRANSPORT-F1G2H'},
                {'name': 'Shipping and Delivery', 'code': 'TRANSPORT-I3J4K'},
                {'name': 'Cargo Management', 'code': 'TRANSPORT-L5M6N'},
                {'name': 'Transportation Compliance', 'code': 'TRANSPORT-O7P8Q'},
                {'name': 'Transport Network Design', 'code': 'TRANSPORT-R9S0T'},
                {'name': 'Transportation Analysis', 'code': 'TRANSPORT-U1V2W'},
                {'name': 'Transport Management Systems', 'code': 'TRANSPORT-X3Y4Z'},
                {'name': 'Intermodal Transportation', 'code': 'TRANSPORT-A5B6C'},
                {'name': 'Transport Operations Optimization', 'code': 'TRANSPORT-D7E8F'},
                {'name': 'Vehicle Operations', 'code': 'TRANSPORT-G9H0I'},
                {'name': 'Transport Scheduling', 'code': 'TRANSPORT-J1K2L'},
                {'name': 'Fleet Maintenance', 'code': 'TRANSPORT-M3N4O'},
                {'name': 'Supply Chain Optimization', 'code': 'TRANSPORT-P5Q6R'},
                {'name': 'Transport Risk Management', 'code': 'TRANSPORT-S7T8U'},
                {'name': 'Logistics Technology', 'code': 'TRANSPORT-V9W0X'},
                {'name': 'Driver Management', 'code': 'TRANSPORT-Y1Z2A'},
                {'name': 'Transportation Innovation', 'code': 'TRANSPORT-B3C4D'},
                {'name': 'Supply Chain Logistics', 'code': 'TRANSPORT-E5F6G'},
                {'name': 'Traffic Management', 'code': 'TRANSPORT-H7I8J'},
                {'name': 'Transportation Safety', 'code': 'TRANSPORT-K9L0M'}
            ],

            'HOSPITALITY': [
                {'name': 'Hotel Management', 'code': 'HOSPITALITY-E1F2G'},
                {'name': 'Event Planning', 'code': 'HOSPITALITY-H3I4J'},
                {'name': 'Restaurant Management', 'code': 'HOSPITALITY-K5L6M'},
                {'name': 'Guest Services', 'code': 'HOSPITALITY-N7O8P'},
                {'name': 'Housekeeping Management', 'code': 'HOSPITALITY-Q9R0S'},
                {'name': 'Food and Beverage Management', 'code': 'HOSPITALITY-T1U2V'},
                {'name': 'Catering Services', 'code': 'HOSPITALITY-W3X4Y'},
                {'name': 'Tourism Management', 'code': 'HOSPITALITY-Z5A6B'},
                {'name': 'Customer Service Excellence', 'code': 'HOSPITALITY-C7D8E'},
                {'name': 'Restaurant Operations', 'code': 'HOSPITALITY-F9G0H'},
                {'name': 'Revenue Management', 'code': 'HOSPITALITY-I1J2K'},
                {'name': 'Event Coordination', 'code': 'HOSPITALITY-L3M4N'},
                {'name': 'Food Service Management', 'code': 'HOSPITALITY-O5P6Q'},
                {'name': 'Hospitality Marketing', 'code': 'HOSPITALITY-R7S8T'},
                {'name': 'Tour Guide Services', 'code': 'HOSPITALITY-U9V0W'},
                {'name': 'Catering Operations', 'code': 'HOSPITALITY-X1Y2Z'},
                {'name': 'Hospitality Industry Knowledge', 'code': 'HOSPITALITY-A3B4C'},
                {'name': 'Travel Management', 'code': 'HOSPITALITY-D5E6F'},
                {'name': 'Hospitality Event Planning', 'code': 'HOSPITALITY-G7H8I'},
                {'name': 'Guest Experience', 'code': 'HOSPITALITY-J9K0L'},
                {'name': 'Hotel Operations', 'code': 'HOSPITALITY-M1N2O'},
                {'name': 'Front Desk Operations', 'code': 'HOSPITALITY-P3Q4R'},
                {'name': 'Tourist Destination Management', 'code': 'HOSPITALITY-S5T6U'},
                {'name': 'Hotel and Resort Development', 'code': 'HOSPITALITY-V7W8X'},
                {'name': 'Food Safety Regulations', 'code': 'HOSPITALITY-Y9Z0A'},
                {'name': 'Catering Coordination', 'code': 'HOSPITALITY-B1C2D'},
                {'name': 'Team Management', 'code': 'HOSPITALITY-E3F4G'},
                {'name': 'Luxury Hospitality', 'code': 'HOSPITALITY-H5I6J'},
                {'name': 'Customer Loyalty Programs', 'code': 'HOSPITALITY-K7L8M'},
                {'name': 'Sustainable Hospitality', 'code': 'HOSPITALITY-N9O0P'}
            ]

        }

        # Loop over the default skills and create them
        for industry_code, skills in default_skills.items():
            for skill in skills:
                skill_code = f"{industry_code}-{skill['code']}"  # Combine industry and skill code
                # Ensure the skill does not already exist
                if not cls.objects.filter(code=skill_code).exists():
                    cls.objects.create(
                        name=skill['name'],
                        code=skill_code,
                        description=skill.get('description', '')
                    )

class SalaryMarket(models.Model):
    CURRENCY_CHOICES = [
        ('INR', 'Indian Rupee'),
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('GBP', 'British Pound'),
        # Add more currencies as needed
    ]

    CURRENCY_SYMBOLS = {
        'INR': '₹',
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        # Add more currency symbols here if needed
    }

    currency_type = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='INR'  # Default to INR
    )

    salary_start = models.IntegerField(default=0)  # Salary start value (e.g., 0)
    salary_middle = models.IntegerField(default=500000)  # Salary middle value (e.g., 500,000)
    salary_end = models.IntegerField(default=1000000)  # Salary end value (e.g., 1,000,000)

    class Meta:
        db_table = 'job_salary_market'

    @classmethod
    def create_default_salary_markets(cls):
        """
        Create default salary markets for each currency type if they don't already exist.
        This is a class method that can be called to ensure data is populated.
        """
        # Loop through each currency and create a SalaryMarket if it doesn't exist
        for currency, symbol in cls.CURRENCY_SYMBOLS.items():
            # Check if a SalaryMarket for this currency already exists
            if not cls.objects.filter(currency_type=currency).exists():
                cls.objects.create(
                    currency_type=currency,
                    salary_start=0,  # Default start salary
                    salary_middle=500000,  # Default middle salary
                    salary_end=1000000  # Default end salary
                )
                print(f"Created default SalaryMarket for {currency} ({symbol})")
            else:
                print(f"SalaryMarket for {currency} already exists.")

    def __str__(self):
        return f"Salary Market for {self.currency_type}"

    def get_currency_symbol(self):
        """
        Return the currency symbol based on the currency type.
        """
        return self.CURRENCY_SYMBOLS.get(self.currency_type)  # Default to '₹' if no symbol is found

    def get_salary_range(self):
        """
        Returns a tuple containing the salary range: start, middle, and end.
        """
        return (self.salary_start, self.salary_middle, self.salary_end)

    def _format_salary(self, salary):
        if self.currency_type == 'INR':
            if salary >= 1_00_00_000:
                formatted = f"{salary / 1_00_00_000:.2f} Cr"
            elif salary >= 1_00_000:
                formatted = f"{salary / 1_00_000:.2f} Lakh"
            else:
                formatted = f"{salary}"
        else:
            if salary >= 1_000_000:
                formatted = f"{salary / 1_000_000:.2f}M"
            elif salary >= 1_000:
                formatted = f"{salary / 1_000:.2f}K"
            else:
                formatted = f"{salary}"

        return f"{self.CURRENCY_SYMBOLS.get(self.currency_type)}{formatted}"

    def currency_symbol(self):
        return self.CURRENCY_SYMBOLS.get(self.currency_type)

    def format_currency_salary_start(self):
        return self._format_salary(self.salary_start)


    def format_currency_salary_middle(self):
        return self._format_salary(self.salary_middle)

    def format_currency_salary_end(self):
        return self._format_salary(self.salary_end)

class RecruiterSettings(models.Model):

    CURRENCY_CHOICES = [
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('GBP', 'British Pound'),
        ('INR', 'Indian Rupee'),
        # You can add more currencies as needed
    ]

    CURRENCY_SYMBOLS = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'INR': '₹',
        # Add more currency symbols here if needed
    }

    user = models.OneToOneField(RecruiterProfile, on_delete=models.CASCADE)

    # Currency type field
    currency_type = models.CharField(
        default="INR",
        unique=True,
        blank=False,
        max_length=3,  # Max length of 3 for currency code (e.g., 'USD', 'EUR')
        choices=CURRENCY_CHOICES,  # Use choices to limit to valid currencies
    )

    class Meta:
        db_table = 'lts360_jobs_settings'

    def get_currency_symbol(self):
        """
        Return the currency symbol based on the currency type.
        """
        return self.CURRENCY_SYMBOLS.get(self.currency_type, '₹')  # Default to '₹' if no symbol is found

    def get_currency_type(self):
        return self.currency_type

    def __str__(self):
        return f"Settings for {self.user.first_name} {self.user.last_name}"

class Plan(models.Model):
    name = models.CharField(max_length=100)
    is_free = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    features = models.JSONField()

    class Meta:
        db_table = 'lts360_jobs_plans'

    def __str__(self):
        return self.name

    @classmethod
    def initialize_default_plans(cls):
        """Create initial plans if they don't exist"""
        free_plan, _ = cls.objects.get_or_create(
            name="Free",
            defaults={
                'is_free': True,
                'price': 0,
                'features': {
                    'job_postings': 1,
                    'applications': 50,
                    'analytics': 'basic'
                }
            }
        )

        premium_plan, _ = cls.objects.get_or_create(
            name="Premium",
            defaults={
                'is_free': False,
                'price': 29.99,
                'features': {
                    'job_postings': 'unlimited',
                    'applications': 'unlimited',
                    'analytics': 'advanced'
                }
            }
        )
        return free_plan, premium_plan
