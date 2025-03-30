import os
import random
from datetime import timedelta
from enum import Enum

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db import transaction, IntegrityError
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
from django.db import models
from django.utils import timezone


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
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
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


def get_user_profile_upload_path(instance, filename):
    """
    Generate the upload path for the organization logo based on the organization ID.
    """
    return os.path.join('users', str(instance.user_id), 'profile', filename)


class UserProfile(models.Model):
    # Inherit from UserProfile if needed, or just copy relevant fields to make StudentProfile standalone
    external_user_id = models.CharField(max_length=255)  # External ID, like social media or university ID

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    profile_picture = models.ImageField(upload_to=get_user_profile_upload_path, blank=True, null=True)
    email = models.EmailField()

    # Phone number, maybe verified?
    phone = PhoneNumberField()

    # Educational Background
    education_level = models.CharField(max_length=100, choices=[('undergraduate', 'Undergraduate'),
                                                                ('graduate', 'Graduate'),
                                                                ('postgraduate', 'Postgraduate')],
                                       default='undergraduate')
    institution = models.CharField(max_length=255)
    graduation_year = models.IntegerField()
    current_position = models.CharField(max_length=255)
    years_of_experience = models.FloatField(max_length=255)

    resume_download_url = models.URLField(blank=True, null=True)  # URL for the resume file
    resume_type = models.CharField(max_length=255, blank=True, null=True)  # Type of resume (e.g., pdf, doc)
    portfolio_url = models.URLField(blank=True, null=True)  # Optional: A link to an online portfolio, if applicable
    skills = models.CharField(max_length=500, blank=True, null=True)  # Skills relevant to the job

    # The student applying for a job
    applied_jobs = models.ManyToManyField('JobPosting', through='JobApplication', related_name='students')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Profile Verification for Students
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.education_level}"

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
            self.phone,
            self.education_level,
            self.institution,
            self.graduation_year,
            self.skills
        ]
        return all(required_fields)


class CompanyProfile(models.Model):
    user = models.ForeignKey('RecruiterProfile', on_delete=models.CASCADE)  # Link to StudentProfile (ForeignKey)
    organization_id = models.PositiveBigIntegerField(unique=True)
    organization_name = models.CharField(max_length=255)
    logo = models.ImageField(upload_to=get_logo_upload_path, blank=True, null=True)
    email = models.EmailField()
    organization_address = models.CharField(max_length=255)
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
                    if CompanyProfile.objects.filter(
                            organization_id=self.organization_id
                    ).exists():  # Confirm real duplicate
                        continue
                    raise  # Re-raise if other error
        else:
            super().save(*args, **kwargs)


class JobPosting(models.Model):
    title = models.CharField(max_length=100)

    work_type = models.CharField(max_length=50,
                                 choices=[('remote', 'Remote'), ('office', 'Office'), ('hybrid', 'Hybrid')],
                                 default='office', blank=False)
    location = models.CharField(max_length=100)
    company = models.CharField(max_length=100)

    description = models.TextField()

    education = models.CharField(max_length=200)

    experience_type = models.CharField(max_length=50,
                                       choices=[('fresher', 'Fresher'), ('min_max', 'Min-Max Experience'),
                                                ('fixed', 'Fixed Experience')],
                                       default='fresher', blank=False)
    experience_range_min = models.IntegerField(default=0)
    experience_range_max = models.IntegerField(default=5)
    experience_fixed = models.IntegerField(default=2)

    salary_min = models.DecimalField(max_digits=10, decimal_places=2)
    salary_max = models.DecimalField(max_digits=10, decimal_places=2)
    salary_not_disclosed = models.BooleanField(default=False)

    must_have_skills = models.JSONField(default=list)  # Stores as list
    good_to_have_skills = models.JSONField(default=list)

    industry_type = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    role = models.CharField(max_length=100)
    employment_type = models.CharField(max_length=50, choices=[('full_time', 'Full Time'), ('part_time', 'Part Time'),
                                                               ('contract', 'Contract')], default='full_time',
                                       blank=False)
    vacancies = models.IntegerField(default=1)

    highlights = models.JSONField(default=list,
                                  help_text="List of selected job perks")

    posted_at = models.DateTimeField(auto_now_add=True)
    posted_by = models.ForeignKey('RecruiterProfile', on_delete=models.CASCADE, related_name='recruiter_user_profile')
    organization_id = models.BigIntegerField(null=True, blank=True)

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
            # For fresher, min-max and fixed experience should not be used
            if self.experience_range_min != 0 or self.experience_range_max != 5:
                raise ValidationError(
                    {"experience_range_min": "For fresher, experience range should not be set.",
                     "experience_range_max": "For fresher, experience range should not be set."}
                )
            if self.experience_fixed != 2:
                raise ValidationError({"experience_fixed": "For fresher, fixed experience should not be set."})

        elif self.experience_type == 'min-max':
            # If min-max type is selected, make sure the min is less than max
            if self.experience_range_min >= self.experience_range_max:
                raise ValidationError(
                    {"experience_range_min": "Minimum experience should be less than maximum experience.",
                     "experience_range_max": "Maximum experience should be greater than minimum experience."}
                )
            # Ensure fixed experience is not set when using min-max
            if self.experience_fixed != 2:
                raise ValidationError(
                    {"experience_fixed": "Fixed experience should not be set when using min-max experience type."})

        elif self.experience_type == 'fixed':
            # For fixed experience type, make sure min-max experience range is not set
            if self.experience_range_min != 0 or self.experience_range_max != 5:
                raise ValidationError(
                    {"experience_range_min": "Experience range should not be set when using fixed experience type.",
                     "experience_range_max": "Experience range should not be set when using fixed experience type."}
                )
            # Ensure fixed experience is set correctly
            if self.experience_fixed == 2:
                raise ValidationError(
                    {"experience_fixed": "Fixed experience should have a value other than the default of 2."})

        # Salary validation: ensure salary_min is not greater than salary_max
        if self.salary_min > self.salary_max != 0:
            raise ValidationError(
                {"salary_min": "Salary minimum cannot be greater than salary maximum.",
                 "salary_max": "Salary maximum must be greater than salary minimum if specified."}
            )

        # If salary_not_disclosed is True, set salary_min and salary_max to 0
        if self.salary_not_disclosed:
            self.salary_min = 0.00
            self.salary_max = 0.00


class JobApplication(models.Model):
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


class JobIndustry(models.Model):
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
            {'name': 'Information Technology', 'code': 'IT'},
            {'name': 'Tech', 'code': 'TECH'},
            {'name': 'Healthcare', 'code': 'HS'},
            {'name': 'Education', 'code': 'EDU'},
            {'name': 'Accounting', 'code': 'ACC'},
            {'name': 'Pharmaceutical', 'code': 'PHAR'},
            {'name': 'Finance', 'code': 'FIN'},
            {'name': 'Engineering', 'code': 'ENG'},
            {'name': 'Real Estate', 'code': 'RE'},
            {'name': 'Higher Education', 'code': 'HE'},
            {'name': 'Sales', 'code': 'SALES'},
            {'name': 'Government', 'code': 'GOV'},
            {'name': 'Energy', 'code': 'ENERGY'},
            {'name': 'Retail', 'code': 'RETAIL'},
            {'name': 'Manufacturing', 'code': 'MANUFACTURING'},
            {'name': 'Architecture', 'code': 'ARCH'},
            {'name': 'Human Resources', 'code': 'HR'},
            {'name': 'Nonprofit', 'code': 'NONPROFIT'},
            {'name': 'Transportation', 'code': 'TRANSPORT'},
            {'name': 'Hospitality', 'code': 'HOSPITALITY'},
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
            {'name': 'Computer Science and Engineering', 'code': 'CSE'},
            {'name': 'Electrical and Electronics Engineering', 'code': 'EEE'},
            {'name': 'Electronics and Communication Engineering', 'code': 'ECE'},
            {'name': 'Mechanical Engineering', 'code': 'ME'},
            {'name': 'Civil Engineering', 'code': 'CE'},
            {'name': 'Artificial Intelligence', 'code': 'AI'},
            {'name': 'Data Science', 'code': 'DS'},

            # Science Departments
            {'name': 'Mathematics', 'code': 'MATH'},
            {'name': 'Physics', 'code': 'PHY'},
            {'name': 'Chemistry', 'code': 'CHEM'},

            # Interdisciplinary
            {'name': 'Biotechnology', 'code': 'BT'},
            {'name': 'Robotics', 'code': 'ROBO'},

            # Management
            {'name': 'Business Administration', 'code': 'MBA'},
            {'name': 'Finance', 'code': 'FIN'},
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
        # Default roles by industry code with role name and role code
        default_roles = {
            'IT': [
                {'name': 'Software Engineer', 'code': 'IT-SE'},
                {'name': 'Network Engineer', 'code': 'IT-NE'},
                {'name': 'System Administrator', 'code': 'IT-SA'},
                {'name': 'Database Administrator', 'code': 'IT-DBA'},
                {'name': 'Tech Support Specialist', 'code': 'IT-TSS'}
            ],
            'TECH': [
                {'name': 'Product Manager', 'code': 'TECH-PM'},
                {'name': 'UI/UX Designer', 'code': 'TECH-UXD'},
                {'name': 'Web Developer', 'code': 'TECH-WD'},
                {'name': 'Data Analyst', 'code': 'TECH-DA'},
            ],
            'HS': [
                {'name': 'Doctor', 'code': 'HS-DOC'},
                {'name': 'Nurse', 'code': 'HS-NUR'},
                {'name': 'Medical Researcher', 'code': 'HS-MR'},
                {'name': 'Pharmacist', 'code': 'HS-PHARM'},
            ],
            'EDU': [
                {'name': 'Teacher', 'code': 'EDU-TCH'},
                {'name': 'Professor', 'code': 'EDU-PROF'},
                {'name': 'Lecturer', 'code': 'EDU-LCT'},
                {'name': 'Education Coordinator', 'code': 'EDU-EDC'},
            ],
            'ACC': [
                {'name': 'Accountant', 'code': 'ACC-ACC'},
                {'name': 'Financial Analyst', 'code': 'ACC-FA'},
                {'name': 'Tax Consultant', 'code': 'ACC-TC'},
                {'name': 'Auditor', 'code': 'ACC-AUD'},
            ],
            'PHAR': [
                {'name': 'Pharmacist', 'code': 'PHAR-PHARM'},
                {'name': 'Clinical Researcher', 'code': 'PHAR-CR'},
                {'name': 'Regulatory Affairs Specialist', 'code': 'PHAR-RAS'},
            ],
            'FIN': [
                {'name': 'Financial Advisor', 'code': 'FIN-FA'},
                {'name': 'Investment Banker', 'code': 'FIN-IB'},
                {'name': 'Risk Manager', 'code': 'FIN-RM'},
                {'name': 'Financial Controller', 'code': 'FIN-FC'},
            ],
            'ENG': [
                {'name': 'Civil Engineer', 'code': 'ENG-CE'},
                {'name': 'Mechanical Engineer', 'code': 'ENG-ME'},
                {'name': 'Electrical Engineer', 'code': 'ENG-EE'},
                {'name': 'Software Engineer', 'code': 'ENG-SE'},
            ],
            'RE': [
                {'name': 'Real Estate Agent', 'code': 'RE-REA'},
                {'name': 'Real Estate Developer', 'code': 'RE-RED'},
                {'name': 'Property Manager', 'code': 'RE-PM'},
                {'name': 'Real Estate Consultant', 'code': 'RE-REC'},
            ],
            'HE': [
                {'name': 'Higher Education Administrator', 'code': 'HE-HEA'},
                {'name': 'University Professor', 'code': 'HE-UP'},
                {'name': 'Higher Education Counselor', 'code': 'HE-HEC'},
            ],
            'SALES': [
                {'name': 'Sales Manager', 'code': 'SALES-SM'},
                {'name': 'Sales Executive', 'code': 'SALES-SE'},
                {'name': 'Sales Consultant', 'code': 'SALES-SC'},
                {'name': 'Account Executive', 'code': 'SALES-AE'},
            ],
            'GOV': [
                {'name': 'Government Official', 'code': 'GOV-GO'},
                {'name': 'Policy Analyst', 'code': 'GOV-PA'},
                {'name': 'Public Relations Officer', 'code': 'GOV-PRO'},
            ],
            'ENERGY': [
                {'name': 'Energy Analyst', 'code': 'ENERGY-EA'},
                {'name': 'Energy Manager', 'code': 'ENERGY-EM'},
                {'name': 'Renewable Energy Specialist', 'code': 'ENERGY-RES'},
            ],
            'RETAIL': [
                {'name': 'Retail Manager', 'code': 'RETAIL-RM'},
                {'name': 'Sales Associate', 'code': 'RETAIL-SA'},
                {'name': 'Store Manager', 'code': 'RETAIL-SM'},
                {'name': 'Cashier', 'code': 'RETAIL-C'},
            ],
            'MANUFACTURING': [
                {'name': 'Manufacturing Engineer', 'code': 'MANUFACTURING-ME'},
                {'name': 'Production Manager', 'code': 'MANUFACTURING-PM'},
                {'name': 'Quality Control Specialist', 'code': 'MANUFACTURING-QCS'},
            ],
            'ARCH': [
                {'name': 'Architect', 'code': 'ARCH-ARCH'},
                {'name': 'Interior Designer', 'code': 'ARCH-ID'},
                {'name': 'Urban Planner', 'code': 'ARCH-UP'},
            ],
            'HR': [
                {'name': 'HR Manager', 'code': 'HR-HRM'},
                {'name': 'Recruitment Specialist', 'code': 'HR-RS'},
                {'name': 'HR Consultant', 'code': 'HR-HRC'},
            ],
            'NONPROFIT': [
                {'name': 'Nonprofit Manager', 'code': 'NONPROFIT-NM'},
                {'name': 'Fundraiser', 'code': 'NONPROFIT-FR'},
                {'name': 'Social Worker', 'code': 'NONPROFIT-SW'},
            ],
            'TRANSPORT': [
                {'name': 'Logistics Manager', 'code': 'TRANSPORT-LM'},
                {'name': 'Transportation Planner', 'code': 'TRANSPORT-TP'},
                {'name': 'Fleet Manager', 'code': 'TRANSPORT-FM'},
            ],
            'HOSPITALITY': [
                {'name': 'Hotel Manager', 'code': 'HOSPITALITY-HM'},
                {'name': 'Chef', 'code': 'HOSPITALITY-C'},
                {'name': 'Event Coordinator', 'code': 'HOSPITALITY-EC'},
            ]
        }

        # Loop over the default roles and create them
        for industry_code, roles in default_roles.items():

            for role in roles:
                role_code = f"{industry_code}-{role['code']}"  # Combine industry and role code
                # Ensure the role does not already exist
                if not cls.objects.filter(code=role_code).exists():
                    cls.objects.create(
                        name=role['name'],
                        code=role_code,
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
                {'name': 'Software Development', 'code': 'IT-001'},
                {'name': 'Network Security', 'code': 'IT-002'},
                {'name': 'System Administration', 'code': 'IT-003'},
                {'name': 'Database Management', 'code': 'IT-004'},
                {'name': 'Technical Support', 'code': 'IT-005'},
                {'name': 'Python Programming', 'code': 'IT-006'},
                {'name': 'Java Programming', 'code': 'IT-007'},
                {'name': 'Kotlin Programming', 'code': 'IT-008'},
                {'name': 'Web Development', 'code': 'IT-009'},
                {'name': 'Cloud Computing', 'code': 'IT-010'},
                {'name': 'Ruby Programming', 'code': 'IT-011'},
                {'name': 'JavaScript Programming', 'code': 'IT-012'},
                {'name': 'PHP Development', 'code': 'IT-013'},
                {'name': 'C++ Programming', 'code': 'IT-014'},
                {'name': 'C# Programming', 'code': 'IT-015'},
                {'name': 'Swift Programming', 'code': 'IT-016'},
                {'name': 'SQL Databases', 'code': 'IT-017'},
                {'name': 'NoSQL Databases', 'code': 'IT-018'},
                {'name': 'Mobile App Development', 'code': 'IT-019'},
                {'name': 'Blockchain Development', 'code': 'IT-020'},
                {'name': 'DevOps', 'code': 'IT-021'},
                {'name': 'Cybersecurity', 'code': 'IT-022'},
                {'name': 'Big Data', 'code': 'IT-023'},
                {'name': 'AI Development', 'code': 'IT-024'},
                {'name': 'Machine Learning', 'code': 'IT-025'},
                {'name': 'Data Science', 'code': 'IT-026'},
                {'name': 'Git Version Control', 'code': 'IT-027'},
                {'name': 'Agile Methodology', 'code': 'IT-028'},
                {'name': 'Software Testing', 'code': 'IT-029'},
                {'name': 'Network Administration', 'code': 'IT-030'},
                {'name': 'Cloud Architecture', 'code': 'IT-031'},
                {'name': 'Linux Administration', 'code': 'IT-032'},
                {'name': 'Windows Server Administration', 'code': 'IT-033'},
                {'name': 'AWS', 'code': 'IT-034'},
                {'name': 'Google Cloud', 'code': 'IT-035'},
                {'name': 'Azure Cloud', 'code': 'IT-036'},
                {'name': 'Data Analytics', 'code': 'IT-037'},
                {'name': 'IoT (Internet of Things)', 'code': 'IT-038'},
                {'name': 'Virtualization', 'code': 'IT-039'},
                {'name': 'AR/VR Development', 'code': 'IT-040'},
                {'name': 'Web Security', 'code': 'IT-041'},
                {'name': 'SQL Query Optimization', 'code': 'IT-042'},
                {'name': 'Docker', 'code': 'IT-043'},
                {'name': 'Containers', 'code': 'IT-044'},
                {'name': 'Serverless Architecture', 'code': 'IT-045'},
                {'name': 'Infrastructure as Code', 'code': 'IT-046'},
                {'name': 'Jenkins', 'code': 'IT-047'},
                {'name': 'Ansible', 'code': 'IT-048'},
                {'name': 'Terraform', 'code': 'IT-049'},
                {'name': 'Kubernetes', 'code': 'IT-050'},
            ],
            'TECH': [
                {'name': 'Project Management', 'code': 'TECH-001'},
                {'name': 'UI/UX Design', 'code': 'TECH-002'},
                {'name': 'Web Development', 'code': 'TECH-003'},
                {'name': 'Data Analysis', 'code': 'TECH-004'},
                {'name': 'Machine Learning', 'code': 'TECH-005'},
                {'name': 'Artificial Intelligence', 'code': 'TECH-006'},
                {'name': 'Big Data', 'code': 'TECH-007'},
                {'name': 'Blockchain Development', 'code': 'TECH-008'},
                {'name': 'Digital Marketing', 'code': 'TECH-009'},
                {'name': 'Product Management', 'code': 'TECH-010'},
                {'name': 'Cloud Computing', 'code': 'TECH-011'},
                {'name': 'SEO', 'code': 'TECH-012'},
                {'name': 'Content Strategy', 'code': 'TECH-013'},
                {'name': 'Web Analytics', 'code': 'TECH-014'},
                {'name': 'App Development', 'code': 'TECH-015'},
                {'name': 'Growth Hacking', 'code': 'TECH-016'},
                {'name': 'E-commerce Development', 'code': 'TECH-017'},
                {'name': 'Database Design', 'code': 'TECH-018'},
                {'name': 'Product Design', 'code': 'TECH-019'},
                {'name': 'Graphic Design', 'code': 'TECH-020'},
                {'name': 'Salesforce', 'code': 'TECH-021'},
                {'name': 'Customer Success', 'code': 'TECH-022'},
                {'name': 'CRM Systems', 'code': 'TECH-023'},
                {'name': 'Web Security', 'code': 'TECH-024'},
                {'name': 'Server Administration', 'code': 'TECH-025'},
                {'name': 'API Development', 'code': 'TECH-026'},
                {'name': 'Business Intelligence', 'code': 'TECH-027'},
                {'name': 'Cloud Security', 'code': 'TECH-028'},
                {'name': 'DevOps', 'code': 'TECH-029'},
                {'name': 'Automation Testing', 'code': 'TECH-030'},
                {'name': 'Mobile App Testing', 'code': 'TECH-031'},
                {'name': 'Software Architecture', 'code': 'TECH-032'},
                {'name': 'Agile Development', 'code': 'TECH-033'},
                {'name': 'Data Visualization', 'code': 'TECH-034'},
                {'name': 'Cloud Architecture', 'code': 'TECH-035'},
                {'name': 'Python Development', 'code': 'TECH-036'},
                {'name': 'JavaScript Development', 'code': 'TECH-037'},
                {'name': 'Ruby Development', 'code': 'TECH-038'},
                {'name': 'React Development', 'code': 'TECH-039'},
                {'name': 'Vue.js Development', 'code': 'TECH-040'},
                {'name': 'Angular Development', 'code': 'TECH-041'},
                {'name': 'JQuery Development', 'code': 'TECH-042'},
                {'name': 'Spring Framework', 'code': 'TECH-043'},
                {'name': 'Node.js Development', 'code': 'TECH-044'},
                {'name': 'PHP Development', 'code': 'TECH-045'},
                {'name': 'C++ Development', 'code': 'TECH-046'},
                {'name': 'C# Development', 'code': 'TECH-047'},
                {'name': 'Go Programming', 'code': 'TECH-048'},
                {'name': 'Swift Programming', 'code': 'TECH-049'},
                {'name': 'Kotlin Development', 'code': 'TECH-050'},
            ],
            'HS': [
                {'name': 'Medical Research', 'code': 'HS-001'},
                {'name': 'Clinical Trials', 'code': 'HS-002'},
                {'name': 'Healthcare Administration', 'code': 'HS-003'},
                {'name': 'Nursing', 'code': 'HS-004'},
                {'name': 'Pharmacy Management', 'code': 'HS-005'},
                {'name': 'Patient Care', 'code': 'HS-006'},
                {'name': 'Medical Billing', 'code': 'HS-007'},
                {'name': 'Emergency Response', 'code': 'HS-008'},
                {'name': 'Medical Coding', 'code': 'HS-009'},
                {'name': 'Surgical Assistance', 'code': 'HS-010'},
                {'name': 'Public Health', 'code': 'HS-011'},
                {'name': 'Healthcare IT', 'code': 'HS-012'},
                {'name': 'Pharmaceutical Sales', 'code': 'HS-013'},
                {'name': 'Medical Laboratory Technology', 'code': 'HS-014'},
                {'name': 'Radiology', 'code': 'HS-015'},
                {'name': 'Physical Therapy', 'code': 'HS-016'},
                {'name': 'Occupational Therapy', 'code': 'HS-017'},
                {'name': 'Dentistry', 'code': 'HS-018'},
                {'name': 'Healthcare Marketing', 'code': 'HS-019'},
                {'name': 'Health Education', 'code': 'HS-020'},
                {'name': 'Public Health Policy', 'code': 'HS-021'},
                {'name': 'Epidemiology', 'code': 'HS-022'},
                {'name': 'Toxicology', 'code': 'HS-023'},
                {'name': 'Mental Health', 'code': 'HS-024'},
                {'name': 'Health Informatics', 'code': 'HS-025'},
                {'name': 'Medical Device Technology', 'code': 'HS-026'},
                {'name': 'Pediatrics', 'code': 'HS-027'},
                {'name': 'Geriatrics', 'code': 'HS-028'},
                {'name': 'Nutrition', 'code': 'HS-029'},
                {'name': 'Hospice Care', 'code': 'HS-030'},
                {'name': 'Clinical Psychology', 'code': 'HS-031'},
                {'name': 'Veterinary Care', 'code': 'HS-032'},
                {'name': 'Medical Supply Chain', 'code': 'HS-033'},
                {'name': 'Clinical Pharmacology', 'code': 'HS-034'},
                {'name': 'Healthcare Consulting', 'code': 'HS-035'},
                {'name': 'Health Insurance', 'code': 'HS-036'},
                {'name': 'Regulatory Affairs', 'code': 'HS-037'},
                {'name': 'Telemedicine', 'code': 'HS-038'},
                {'name': 'Healthcare Analytics', 'code': 'HS-039'},
                {'name': 'Surgical Technology', 'code': 'HS-040'},
                {'name': 'Medical Devices Regulatory', 'code': 'HS-041'},
                {'name': 'Healthcare Software', 'code': 'HS-042'},
                {'name': 'Ambulance Services', 'code': 'HS-043'},
                {'name': 'Forensic Medicine', 'code': 'HS-044'},
                {'name': 'Medical Records', 'code': 'HS-045'},
                {'name': 'Medical Tourism', 'code': 'HS-046'},
                {'name': 'Healthcare Operations', 'code': 'HS-047'},
                {'name': 'Telehealth', 'code': 'HS-048'},
                {'name': 'Palliative Care', 'code': 'HS-049'},
                {'name': 'Health Coaching', 'code': 'HS-050'},
            ],

            # Previous industries (IT, TECH, HS) are already included
            'EDU': [
                {'name': 'Teaching', 'code': 'EDU-001'},
                {'name': 'Curriculum Design', 'code': 'EDU-002'},
                {'name': 'Classroom Management', 'code': 'EDU-003'},
                {'name': 'Educational Technology', 'code': 'EDU-004'},
                {'name': 'Instructional Design', 'code': 'EDU-005'},
                {'name': 'Learning Assessment', 'code': 'EDU-006'},
                {'name': 'Teacher Training', 'code': 'EDU-007'},
                {'name': 'Special Education', 'code': 'EDU-008'},
                {'name': 'Language Teaching', 'code': 'EDU-009'},
                {'name': 'Pedagogy', 'code': 'EDU-010'},
                {'name': 'Educational Research', 'code': 'EDU-011'},
                {'name': 'Educational Leadership', 'code': 'EDU-012'},
                {'name': 'Higher Education Administration', 'code': 'EDU-013'},
                {'name': 'Student Support Services', 'code': 'EDU-014'},
                {'name': 'Online Education', 'code': 'EDU-015'},
                {'name': 'Learning Management Systems', 'code': 'EDU-016'},
                {'name': 'Educational Administration', 'code': 'EDU-017'},
                {'name': 'Teacher Evaluation', 'code': 'EDU-018'},
                {'name': 'K-12 Education', 'code': 'EDU-019'},
                {'name': 'Adult Education', 'code': 'EDU-020'},
                {'name': 'Tutoring', 'code': 'EDU-021'},
                {'name': 'Instructional Technology', 'code': 'EDU-022'},
                {'name': 'E-learning Development', 'code': 'EDU-023'},
                {'name': 'Classroom Technology', 'code': 'EDU-024'},
                {'name': 'Student Engagement', 'code': 'EDU-025'},
                {'name': 'School Management', 'code': 'EDU-026'},
                {'name': 'Curriculum Assessment', 'code': 'EDU-027'},
                {'name': 'Language Assessment', 'code': 'EDU-028'},
                {'name': 'Education Policy', 'code': 'EDU-029'},
                {'name': 'Academic Advising', 'code': 'EDU-030'},
                {'name': 'School Counseling', 'code': 'EDU-031'},
                {'name': 'University Administration', 'code': 'EDU-032'},
                {'name': 'Education Law', 'code': 'EDU-033'},
                {'name': 'Global Education', 'code': 'EDU-034'},
                {'name': 'Inclusive Education', 'code': 'EDU-035'},
                {'name': 'School Safety', 'code': 'EDU-036'},
                {'name': 'College Admissions', 'code': 'EDU-037'},
                {'name': 'Distance Learning', 'code': 'EDU-038'},
                {'name': 'Vocational Education', 'code': 'EDU-039'},
                {'name': 'Peer Tutoring', 'code': 'EDU-040'},
                {'name': 'Nonprofit Education', 'code': 'EDU-041'},
                {'name': 'School Psychology', 'code': 'EDU-042'},
                {'name': 'Educational Software', 'code': 'EDU-043'},
                {'name': 'Study Abroad Programs', 'code': 'EDU-044'},
                {'name': 'Higher Ed Marketing', 'code': 'EDU-045'},
                {'name': 'Grant Writing', 'code': 'EDU-046'},
                {'name': 'Educational Consulting', 'code': 'EDU-047'},
                {'name': 'School Finance', 'code': 'EDU-048'},
                {'name': 'STEM Education', 'code': 'EDU-049'},
                {'name': 'STEAM Education', 'code': 'EDU-050'},
            ],
            'ACC': [
                {'name': 'Financial Reporting', 'code': 'ACC-001'},
                {'name': 'Tax Preparation', 'code': 'ACC-002'},
                {'name': 'Auditing', 'code': 'ACC-003'},
                {'name': 'Cost Accounting', 'code': 'ACC-004'},
                {'name': 'Forensic Accounting', 'code': 'ACC-005'},
                {'name': 'Financial Analysis', 'code': 'ACC-006'},
                {'name': 'Management Accounting', 'code': 'ACC-007'},
                {'name': 'Internal Controls', 'code': 'ACC-008'},
                {'name': 'Budgeting', 'code': 'ACC-009'},
                {'name': 'Investment Management', 'code': 'ACC-010'},
                {'name': 'Corporate Finance', 'code': 'ACC-011'},
                {'name': 'Bank Reconciliation', 'code': 'ACC-012'},
                {'name': 'Accounts Payable', 'code': 'ACC-013'},
                {'name': 'Accounts Receivable', 'code': 'ACC-014'},
                {'name': 'Payroll Processing', 'code': 'ACC-015'},
                {'name': 'Financial Forecasting', 'code': 'ACC-016'},
                {'name': 'Risk Management', 'code': 'ACC-017'},
                {'name': 'Investment Analysis', 'code': 'ACC-018'},
                {'name': 'Credit Analysis', 'code': 'ACC-019'},
                {'name': 'Financial Modeling', 'code': 'ACC-020'},
                {'name': 'Tax Compliance', 'code': 'ACC-021'},
                {'name': 'Financial Audit', 'code': 'ACC-022'},
                {'name': 'ERP Systems', 'code': 'ACC-023'},
                {'name': 'General Ledger', 'code': 'ACC-024'},
                {'name': 'QuickBooks', 'code': 'ACC-025'},
                {'name': 'Xero', 'code': 'ACC-026'},
                {'name': 'Financial Regulations', 'code': 'ACC-027'},
                {'name': 'Financial Planning', 'code': 'ACC-028'},
                {'name': 'Nonprofit Accounting', 'code': 'ACC-029'},
                {'name': 'Financial Reporting Standards', 'code': 'ACC-030'},
                {'name': 'Mergers and Acquisitions', 'code': 'ACC-031'},
                {'name': 'Corporate Taxation', 'code': 'ACC-032'},
                {'name': 'Real Estate Accounting', 'code': 'ACC-033'},
                {'name': 'Public Accounting', 'code': 'ACC-034'},
                {'name': 'International Accounting', 'code': 'ACC-035'},
                {'name': 'Financial Statement Preparation', 'code': 'ACC-036'},
                {'name': 'Fixed Assets Accounting', 'code': 'ACC-037'},
                {'name': 'Business Valuation', 'code': 'ACC-038'},
                {'name': 'Treasury Management', 'code': 'ACC-039'},
                {'name': 'Payroll Taxation', 'code': 'ACC-040'},
                {'name': 'Financial Software Implementation', 'code': 'ACC-041'},
                {'name': 'Debt Management', 'code': 'ACC-042'},
                {'name': 'Accounting Research', 'code': 'ACC-043'},
                {'name': 'Fraud Prevention', 'code': 'ACC-044'},
                {'name': 'Accounting Systems', 'code': 'ACC-045'},
                {'name': 'Investment Banking', 'code': 'ACC-046'},
                {'name': 'Accounting Standards', 'code': 'ACC-047'},
                {'name': 'Audit Planning', 'code': 'ACC-048'},
                {'name': 'Financial Due Diligence', 'code': 'ACC-049'},
                {'name': 'Corporate Accounting', 'code': 'ACC-050'},
            ],
            'PHAR': [
                {'name': 'Pharmaceutical Sales', 'code': 'PHAR-001'},
                {'name': 'Clinical Research', 'code': 'PHAR-002'},
                {'name': 'Regulatory Affairs', 'code': 'PHAR-003'},
                {'name': 'Pharmacovigilance', 'code': 'PHAR-004'},
                {'name': 'Formulation Development', 'code': 'PHAR-005'},
                {'name': 'Pharmaceutical Marketing', 'code': 'PHAR-006'},
                {'name': 'Drug Safety', 'code': 'PHAR-007'},
                {'name': 'Quality Control', 'code': 'PHAR-008'},
                {'name': 'Drug Development', 'code': 'PHAR-009'},
                {'name': 'Pharmaceutical Manufacturing', 'code': 'PHAR-010'},
                {'name': 'Good Manufacturing Practices', 'code': 'PHAR-011'},
                {'name': 'Clinical Trials', 'code': 'PHAR-012'},
                {'name': 'Medical Affairs', 'code': 'PHAR-013'},
                {'name': 'Pharmaceutical Research', 'code': 'PHAR-014'},
                {'name': 'Clinical Data Management', 'code': 'PHAR-015'},
                {'name': 'Pharmacy Practice', 'code': 'PHAR-016'},
                {'name': 'Pharmacology', 'code': 'PHAR-017'},
                {'name': 'Pharmacy Technology', 'code': 'PHAR-018'},
                {'name': 'Regulatory Compliance', 'code': 'PHAR-019'},
                {'name': 'Pharmaceutical Operations', 'code': 'PHAR-020'},
                {'name': 'Health Economics', 'code': 'PHAR-021'},
                {'name': 'Pharmacogenomics', 'code': 'PHAR-022'},
                {'name': 'Medical Writing', 'code': 'PHAR-023'},
                {'name': 'Drug Packaging', 'code': 'PHAR-024'},
                {'name': 'Clinical Pharmacology', 'code': 'PHAR-025'},
                {'name': 'Biopharmaceuticals', 'code': 'PHAR-026'},
                {'name': 'Pharmacy Law', 'code': 'PHAR-027'},
                {'name': 'Pharmaceutical Project Management', 'code': 'PHAR-028'},
                {'name': 'Supply Chain Management', 'code': 'PHAR-029'},
                {'name': 'Pharmacy Informatics', 'code': 'PHAR-030'},
                {'name': 'Regulatory Submissions', 'code': 'PHAR-031'},
                {'name': 'Clinical Pharmacist', 'code': 'PHAR-032'},
                {'name': 'Clinical Trial Monitoring', 'code': 'PHAR-033'},
                {'name': 'Pharmaceutical Chemistry', 'code': 'PHAR-034'},
                {'name': 'Pharmacokinetics', 'code': 'PHAR-035'},
                {'name': 'Drug Stability Testing', 'code': 'PHAR-036'},
                {'name': 'Pharmaceutical Quality Assurance', 'code': 'PHAR-037'},
                {'name': 'Medical Device Regulation', 'code': 'PHAR-038'},
                {'name': 'Pharmacy Education', 'code': 'PHAR-039'},
                {'name': 'Preclinical Development', 'code': 'PHAR-040'},
                {'name': 'Biotechnology', 'code': 'PHAR-041'},
                {'name': 'Pharmacy Administration', 'code': 'PHAR-042'},
                {'name': 'Medication Therapy Management', 'code': 'PHAR-043'},
                {'name': 'Pharmacy Operations Management', 'code': 'PHAR-044'},
                {'name': 'Drug Discovery', 'code': 'PHAR-045'},
                {'name': 'Pharmaceutical Patents', 'code': 'PHAR-046'},
                {'name': 'Compounding', 'code': 'PHAR-047'},
                {'name': 'Pharmacovigilance Reporting', 'code': 'PHAR-048'},
                {'name': 'Pharmacy Technology Systems', 'code': 'PHAR-049'},
                {'name': 'Clinical Pharmacy Research', 'code': 'PHAR-050'},
            ],
            'FIN': [
                {'name': 'Financial Analysis', 'code': 'FIN-001'},
                {'name': 'Investment Management', 'code': 'FIN-002'},
                {'name': 'Risk Management', 'code': 'FIN-003'},
                {'name': 'Corporate Finance', 'code': 'FIN-004'},
                {'name': 'Financial Forecasting', 'code': 'FIN-005'},
                {'name': 'Financial Modeling', 'code': 'FIN-006'},
                {'name': 'Mergers and Acquisitions', 'code': 'FIN-007'},
                {'name': 'Debt Management', 'code': 'FIN-008'},
                {'name': 'Credit Analysis', 'code': 'FIN-009'},
                {'name': 'Financial Reporting', 'code': 'FIN-010'},
                {'name': 'Capital Budgeting', 'code': 'FIN-011'},
                {'name': 'Private Equity', 'code': 'FIN-012'},
                {'name': 'Tax Planning', 'code': 'FIN-013'},
                {'name': 'Investment Banking', 'code': 'FIN-014'},
                {'name': 'Financial Strategy', 'code': 'FIN-015'},
                {'name': 'Portfolio Management', 'code': 'FIN-016'},
                {'name': 'Financial Risk Analysis', 'code': 'FIN-017'},
                {'name': 'Treasury Management', 'code': 'FIN-018'},
                {'name': 'Financial Compliance', 'code': 'FIN-019'},
                {'name': 'Business Valuation', 'code': 'FIN-020'},
                {'name': 'Asset Management', 'code': 'FIN-021'},
                {'name': 'Investment Advisory', 'code': 'FIN-022'},
                {'name': 'Financial Planning', 'code': 'FIN-023'},
                {'name': 'Banking Operations', 'code': 'FIN-024'},
                {'name': 'Corporate Accounting', 'code': 'FIN-025'},
                {'name': 'Financial Regulation', 'code': 'FIN-026'},
                {'name': 'Quantitative Finance', 'code': 'FIN-027'},
                {'name': 'Business Finance', 'code': 'FIN-028'},
                {'name': 'Financial Statement Analysis', 'code': 'FIN-029'},
                {'name': 'Market Analysis', 'code': 'FIN-030'},
                {'name': 'Wealth Management', 'code': 'FIN-031'},
                {'name': 'Insurance Planning', 'code': 'FIN-032'},
                {'name': 'Corporate Taxation', 'code': 'FIN-033'},
                {'name': 'Financial Software', 'code': 'FIN-034'},
                {'name': 'Investment Strategy', 'code': 'FIN-035'},
                {'name': 'Global Finance', 'code': 'FIN-036'},
                {'name': 'Financial Research', 'code': 'FIN-037'},
                {'name': 'Banking Laws', 'code': 'FIN-038'},
                {'name': 'Asset Allocation', 'code': 'FIN-039'},
                {'name': 'Financial Due Diligence', 'code': 'FIN-040'},
                {'name': 'Retail Banking', 'code': 'FIN-041'},
                {'name': 'Financial Technology', 'code': 'FIN-042'},
                {'name': 'Hedge Funds', 'code': 'FIN-043'},
                {'name': 'Financial Data Analysis', 'code': 'FIN-044'},
                {'name': 'Financial Reporting Standards', 'code': 'FIN-045'},
                {'name': 'Real Estate Investment', 'code': 'FIN-046'},
                {'name': 'Credit Risk', 'code': 'FIN-047'},
                {'name': 'Behavioral Finance', 'code': 'FIN-048'},
                {'name': 'Compliance Monitoring', 'code': 'FIN-049'},
                {'name': 'Financial Performance Measurement', 'code': 'FIN-050'},
            ],
            'ENG': [
                {'name': 'Mechanical Engineering', 'code': 'ENG-001'},
                {'name': 'Civil Engineering', 'code': 'ENG-002'},
                {'name': 'Electrical Engineering', 'code': 'ENG-003'},
                {'name': 'Software Engineering', 'code': 'ENG-004'},
                {'name': 'Structural Engineering', 'code': 'ENG-005'},
                {'name': 'Project Management', 'code': 'ENG-006'},
                {'name': 'Engineering Design', 'code': 'ENG-007'},
                {'name': 'Geotechnical Engineering', 'code': 'ENG-008'},
                {'name': 'Automation Engineering', 'code': 'ENG-009'},
                {'name': 'Thermodynamics', 'code': 'ENG-010'},
                {'name': 'Materials Engineering', 'code': 'ENG-011'},
                {'name': 'Environmental Engineering', 'code': 'ENG-012'},
                {'name': 'Engineering Research', 'code': 'ENG-013'},
                {'name': 'Energy Systems', 'code': 'ENG-014'},
                {'name': 'Control Systems', 'code': 'ENG-015'},
                {'name': 'Mechatronics', 'code': 'ENG-016'},
                {'name': 'CAD (Computer-Aided Design)', 'code': 'ENG-017'},
                {'name': 'Building Information Modeling (BIM)', 'code': 'ENG-018'},
                {'name': 'Robotics Engineering', 'code': 'ENG-019'},
                {'name': 'Sustainability Engineering', 'code': 'ENG-020'},
                {'name': 'Aerospace Engineering', 'code': 'ENG-021'},
                {'name': 'Electrical Power Systems', 'code': 'ENG-022'},
                {'name': 'Renewable Energy Engineering', 'code': 'ENG-023'},
                {'name': 'HVAC Systems', 'code': 'ENG-024'},
                {'name': 'Manufacturing Engineering', 'code': 'ENG-025'},
                {'name': 'Safety Engineering', 'code': 'ENG-026'},
                {'name': 'Quality Control', 'code': 'ENG-027'},
                {'name': 'Production Engineering', 'code': 'ENG-028'},
                {'name': 'Design for Manufacturability', 'code': 'ENG-029'},
                {'name': 'Environmental Impact Assessment', 'code': 'ENG-030'},
                {'name': 'Naval Architecture', 'code': 'ENG-031'},
                {'name': 'Traffic Engineering', 'code': 'ENG-032'},
                {'name': 'Construction Management', 'code': 'ENG-033'},
                {'name': 'Engineering Consulting', 'code': 'ENG-034'},
                {'name': 'Fluid Mechanics', 'code': 'ENG-035'},
                {'name': 'Engineering Ethics', 'code': 'ENG-036'},
                {'name': 'Infrastructure Engineering', 'code': 'ENG-037'},
                {'name': 'Geographic Information Systems (GIS)', 'code': 'ENG-038'},
                {'name': 'Acoustical Engineering', 'code': 'ENG-039'},
                {'name': 'Nanotechnology', 'code': 'ENG-040'},
                {'name': 'Mining Engineering', 'code': 'ENG-041'},
                {'name': 'Energy Efficiency', 'code': 'ENG-042'},
                {'name': 'Electrical Circuit Design', 'code': 'ENG-043'},
                {'name': 'Power Electronics', 'code': 'ENG-044'},
                {'name': 'Urban Engineering', 'code': 'ENG-045'},
                {'name': 'Transport Engineering', 'code': 'ENG-046'},
                {'name': 'Instrumentation Engineering', 'code': 'ENG-047'},
                {'name': 'Telecommunications Engineering', 'code': 'ENG-048'},
                {'name': 'Construction Technology', 'code': 'ENG-049'},
                {'name': 'Lean Manufacturing', 'code': 'ENG-050'},
            ],
            'RE': [
                {'name': 'Real Estate Investment', 'code': 'RE-001'},
                {'name': 'Property Management', 'code': 'RE-002'},
                {'name': 'Real Estate Marketing', 'code': 'RE-003'},
                {'name': 'Real Estate Development', 'code': 'RE-004'},
                {'name': 'Real Estate Law', 'code': 'RE-005'},
                {'name': 'Real Estate Financing', 'code': 'RE-006'},
                {'name': 'Real Estate Valuation', 'code': 'RE-007'},
                {'name': 'Real Estate Negotiation', 'code': 'RE-008'},
                {'name': 'Land Acquisition', 'code': 'RE-009'},
                {'name': 'Commercial Real Estate', 'code': 'RE-010'},
                {'name': 'Real Estate Brokerage', 'code': 'RE-011'},
                {'name': 'Property Taxation', 'code': 'RE-012'},
                {'name': 'Real Estate Investment Trusts (REITs)', 'code': 'RE-013'},
                {'name': 'Mortgage Brokerage', 'code': 'RE-014'},
                {'name': 'Lease Management', 'code': 'RE-015'},
                {'name': 'Real Estate Appraisal', 'code': 'RE-016'},
                {'name': 'Real Estate Finance', 'code': 'RE-017'},
                {'name': 'Real Estate Research', 'code': 'RE-018'},
                {'name': 'Property Inspection', 'code': 'RE-019'},
                {'name': 'Real Estate Economics', 'code': 'RE-020'},
                {'name': 'Urban Planning', 'code': 'RE-021'},
                {'name': 'Real Estate Investment Analysis', 'code': 'RE-022'},
                {'name': 'Real Estate Project Management', 'code': 'RE-023'},
                {'name': 'Real Estate Portfolio Management', 'code': 'RE-024'},
                {'name': 'Property Development', 'code': 'RE-025'},
                {'name': 'Real Estate Auctions', 'code': 'RE-026'},
                {'name': 'Title Insurance', 'code': 'RE-027'},
                {'name': 'Building Codes and Standards', 'code': 'RE-028'},
                {'name': 'Real Estate Operations', 'code': 'RE-029'},
                {'name': 'Real Estate Risk Management', 'code': 'RE-030'},
                {'name': 'Real Estate Asset Management', 'code': 'RE-031'},
                {'name': 'Leasehold Management', 'code': 'RE-032'},
                {'name': 'Real Estate Marketing Strategy', 'code': 'RE-033'},
                {'name': 'Environmental Sustainability in Real Estate', 'code': 'RE-034'},
                {'name': 'Commercial Leasing', 'code': 'RE-035'},
                {'name': 'Real Estate Investment Management', 'code': 'RE-036'},
                {'name': 'Residential Real Estate', 'code': 'RE-037'},
                {'name': 'Real Estate Sales', 'code': 'RE-038'},
                {'name': 'Real Estate Property Management', 'code': 'RE-039'},
                {'name': 'Real Estate Finance Management', 'code': 'RE-040'},
                {'name': 'Building Management Systems', 'code': 'RE-041'},
                {'name': 'Real Estate Development Finance', 'code': 'RE-042'},
                {'name': 'Construction Project Management', 'code': 'RE-043'},
                {'name': 'Real Estate Construction', 'code': 'RE-044'},
                {'name': 'Affordable Housing', 'code': 'RE-045'},
                {'name': 'Real Estate Market Analysis', 'code': 'RE-046'},
                {'name': 'Public Real Estate Policy', 'code': 'RE-047'},
                {'name': 'Real Estate Investment Fund', 'code': 'RE-048'},
                {'name': 'Real Estate Syndication', 'code': 'RE-049'},
                {'name': 'Urban Regeneration', 'code': 'RE-050'},
            ],

            'SALES': [
                {'name': 'Sales Strategy', 'code': 'SALES-001'},
                {'name': 'Customer Relationship Management (CRM)', 'code': 'SALES-002'},
                {'name': 'Sales Negotiation', 'code': 'SALES-003'},
                {'name': 'Lead Generation', 'code': 'SALES-004'},
                {'name': 'Sales Analytics', 'code': 'SALES-005'},
                {'name': 'B2B Sales', 'code': 'SALES-006'},
                {'name': 'B2C Sales', 'code': 'SALES-007'},
                {'name': 'Product Knowledge', 'code': 'SALES-008'},
                {'name': 'Sales Presentations', 'code': 'SALES-009'},
                {'name': 'Account Management', 'code': 'SALES-010'},
                {'name': 'Sales Forecasting', 'code': 'SALES-011'},
                {'name': 'Sales Performance Tracking', 'code': 'SALES-012'},
                {'name': 'Negotiation Skills', 'code': 'SALES-013'},
                {'name': 'Sales Leadership', 'code': 'SALES-014'},
                {'name': 'Market Research', 'code': 'SALES-015'},
                {'name': 'Customer Retention', 'code': 'SALES-016'},
                {'name': 'Sales Reporting', 'code': 'SALES-017'},
                {'name': 'Competitive Intelligence', 'code': 'SALES-018'},
                {'name': 'Sales Training', 'code': 'SALES-019'},
                {'name': 'Field Sales', 'code': 'SALES-020'},
                {'name': 'Sales Process Optimization', 'code': 'SALES-021'},
                {'name': 'Pricing Strategy', 'code': 'SALES-022'},
                {'name': 'Channel Sales', 'code': 'SALES-023'},
                {'name': 'Sales Enablement', 'code': 'SALES-024'},
                {'name': 'Negotiation Tactics', 'code': 'SALES-025'},
                {'name': 'Client Onboarding', 'code': 'SALES-026'},
                {'name': 'Sales Operations', 'code': 'SALES-027'},
                {'name': 'Cross-Selling', 'code': 'SALES-028'},
                {'name': 'Upselling', 'code': 'SALES-029'},
                {'name': 'Team Collaboration', 'code': 'SALES-030'},
            ],
            'GOV': [
                {'name': 'Policy Analysis', 'code': 'GOV-001'},
                {'name': 'Public Administration', 'code': 'GOV-002'},
                {'name': 'Government Relations', 'code': 'GOV-003'},
                {'name': 'Regulatory Affairs', 'code': 'GOV-004'},
                {'name': 'Public Policy', 'code': 'GOV-005'},
                {'name': 'Legislation Process', 'code': 'GOV-006'},
                {'name': 'Government Budgeting', 'code': 'GOV-007'},
                {'name': 'Governmental Affairs', 'code': 'GOV-008'},
                {'name': 'Crisis Management', 'code': 'GOV-009'},
                {'name': 'Public Sector Governance', 'code': 'GOV-010'},
                {'name': 'Election Campaign Strategy', 'code': 'GOV-011'},
                {'name': 'Public Engagement', 'code': 'GOV-012'},
                {'name': 'Community Outreach', 'code': 'GOV-013'},
                {'name': 'Government Policy Writing', 'code': 'GOV-014'},
                {'name': 'Public Sector Finance', 'code': 'GOV-015'},
                {'name': 'International Relations', 'code': 'GOV-016'},
                {'name': 'Diplomatic Relations', 'code': 'GOV-017'},
                {'name': 'Government Compliance', 'code': 'GOV-018'},
                {'name': 'Urban Planning', 'code': 'GOV-019'},
                {'name': 'Emergency Management', 'code': 'GOV-020'},
                {'name': 'Government Contracting', 'code': 'GOV-021'},
                {'name': 'Public Sector Marketing', 'code': 'GOV-022'},
                {'name': 'Public Relations', 'code': 'GOV-023'},
                {'name': 'Public Funding', 'code': 'GOV-024'},
                {'name': 'Government Research', 'code': 'GOV-025'},
                {'name': 'Public Safety', 'code': 'GOV-026'},
                {'name': 'Civic Engagement', 'code': 'GOV-027'},
                {'name': 'Transparency & Accountability', 'code': 'GOV-028'},
            ],
            'ENERGY': [
                {'name': 'Energy Management', 'code': 'ENERGY-001'},
                {'name': 'Renewable Energy', 'code': 'ENERGY-002'},
                {'name': 'Energy Efficiency', 'code': 'ENERGY-003'},
                {'name': 'Energy Policy', 'code': 'ENERGY-004'},
                {'name': 'Oil and Gas Industry', 'code': 'ENERGY-005'},
                {'name': 'Energy Systems', 'code': 'ENERGY-006'},
                {'name': 'Power Generation', 'code': 'ENERGY-007'},
                {'name': 'Solar Energy', 'code': 'ENERGY-008'},
                {'name': 'Wind Energy', 'code': 'ENERGY-009'},
                {'name': 'Energy Storage', 'code': 'ENERGY-010'},
                {'name': 'Nuclear Energy', 'code': 'ENERGY-011'},
                {'name': 'Energy Transition', 'code': 'ENERGY-012'},
                {'name': 'Geothermal Energy', 'code': 'ENERGY-013'},
                {'name': 'Carbon Emission Reduction', 'code': 'ENERGY-014'},
                {'name': 'Electric Vehicles', 'code': 'ENERGY-015'},
                {'name': 'Energy Trading', 'code': 'ENERGY-016'},
                {'name': 'Hydropower', 'code': 'ENERGY-017'},
                {'name': 'Sustainable Energy Solutions', 'code': 'ENERGY-018'},
                {'name': 'Energy Finance', 'code': 'ENERGY-019'},
                {'name': 'Energy Research', 'code': 'ENERGY-020'},
                {'name': 'Clean Energy', 'code': 'ENERGY-021'},
                {'name': 'Smart Grids', 'code': 'ENERGY-022'},
                {'name': 'Carbon Footprint Reduction', 'code': 'ENERGY-023'},
                {'name': 'Energy Auditing', 'code': 'ENERGY-024'},
                {'name': 'Energy Market Analysis', 'code': 'ENERGY-025'},
                {'name': 'Energy Consumption', 'code': 'ENERGY-026'},
                {'name': 'Power Systems Engineering', 'code': 'ENERGY-027'},
            ],
            'RETAIL': [
                {'name': 'Retail Management', 'code': 'RETAIL-001'},
                {'name': 'Customer Service', 'code': 'RETAIL-002'},
                {'name': 'Sales Floor Management', 'code': 'RETAIL-003'},
                {'name': 'Inventory Management', 'code': 'RETAIL-004'},
                {'name': 'Visual Merchandising', 'code': 'RETAIL-005'},
                {'name': 'Retail Marketing', 'code': 'RETAIL-006'},
                {'name': 'Customer Relationship Management', 'code': 'RETAIL-007'},
                {'name': 'Retail Operations', 'code': 'RETAIL-008'},
                {'name': 'Point of Sale Systems', 'code': 'RETAIL-009'},
                {'name': 'Product Assortment', 'code': 'RETAIL-010'},
                {'name': 'Retail Analytics', 'code': 'RETAIL-011'},
                {'name': 'Retail Sales Strategy', 'code': 'RETAIL-012'},
                {'name': 'Store Design', 'code': 'RETAIL-013'},
                {'name': 'Cash Management', 'code': 'RETAIL-014'},
                {'name': 'Supply Chain Management', 'code': 'RETAIL-015'},
                {'name': 'Product Knowledge', 'code': 'RETAIL-016'},
                {'name': 'E-commerce', 'code': 'RETAIL-017'},
                {'name': 'Retail Budgeting', 'code': 'RETAIL-018'},
                {'name': 'Pricing Strategy', 'code': 'RETAIL-019'},
                {'name': 'Store Leadership', 'code': 'RETAIL-020'},
                {'name': 'Retail Training', 'code': 'RETAIL-021'},
                {'name': 'Branding', 'code': 'RETAIL-022'},
                {'name': 'Consumer Behavior', 'code': 'RETAIL-023'},
                {'name': 'Product Launch', 'code': 'RETAIL-024'},
                {'name': 'Retail Sales Training', 'code': 'RETAIL-025'},
                {'name': 'Merchandising', 'code': 'RETAIL-026'},
                {'name': 'Retail Compliance', 'code': 'RETAIL-027'},
                {'name': 'Retail Technology', 'code': 'RETAIL-028'},
                {'name': 'Customer Experience', 'code': 'RETAIL-029'},
                {'name': 'Retail Finance', 'code': 'RETAIL-030'},
            ],
            'MANUFACTURING': [
                {'name': 'Production Planning', 'code': 'MANUFACTURING-001'},
                {'name': 'Lean Manufacturing', 'code': 'MANUFACTURING-002'},
                {'name': 'Six Sigma', 'code': 'MANUFACTURING-003'},
                {'name': 'Manufacturing Engineering', 'code': 'MANUFACTURING-004'},
                {'name': 'Quality Control', 'code': 'MANUFACTURING-005'},
                {'name': 'Supply Chain Optimization', 'code': 'MANUFACTURING-006'},
                {'name': 'Operations Management', 'code': 'MANUFACTURING-007'},
                {'name': 'Industrial Engineering', 'code': 'MANUFACTURING-008'},
                {'name': 'Materials Handling', 'code': 'MANUFACTURING-009'},
                {'name': 'Process Improvement', 'code': 'MANUFACTURING-010'},
                {'name': 'Product Development', 'code': 'MANUFACTURING-011'},
                {'name': 'Manufacturing Software', 'code': 'MANUFACTURING-012'},
                {'name': 'Inventory Management', 'code': 'MANUFACTURING-013'},
                {'name': 'Production Scheduling', 'code': 'MANUFACTURING-014'},
                {'name': 'Facility Layout', 'code': 'MANUFACTURING-015'},
                {'name': 'Robotics', 'code': 'MANUFACTURING-016'},
                {'name': 'CNC Programming', 'code': 'MANUFACTURING-017'},
                {'name': 'Automation', 'code': 'MANUFACTURING-018'},
                {'name': 'Maintenance Management', 'code': 'MANUFACTURING-019'},
                {'name': 'Machinery Operation', 'code': 'MANUFACTURING-020'},
                {'name': 'Plant Operations', 'code': 'MANUFACTURING-021'},
                {'name': 'Production Efficiency', 'code': 'MANUFACTURING-022'},
                {'name': 'Manufacturing Cost Reduction', 'code': 'MANUFACTURING-023'},
                {'name': 'Product Design', 'code': 'MANUFACTURING-024'},
                {'name': 'Inventory Optimization', 'code': 'MANUFACTURING-025'},
                {'name': 'Product Quality Assurance', 'code': 'MANUFACTURING-026'},
                {'name': 'Process Control', 'code': 'MANUFACTURING-027'},
                {'name': 'Workforce Management', 'code': 'MANUFACTURING-028'},
            ],
            'ARCH': [
                {'name': 'Architectural Design', 'code': 'ARCH-001'},
                {'name': 'Urban Planning', 'code': 'ARCH-002'},
                {'name': 'Construction Management', 'code': 'ARCH-003'},
                {'name': 'Building Information Modeling (BIM)', 'code': 'ARCH-004'},
                {'name': 'Sustainable Design', 'code': 'ARCH-005'},
                {'name': 'Project Management', 'code': 'ARCH-006'},
                {'name': 'Space Planning', 'code': 'ARCH-007'},
                {'name': 'Building Codes', 'code': 'ARCH-008'},
                {'name': 'Structural Engineering', 'code': 'ARCH-009'},
                {'name': 'Interior Architecture', 'code': 'ARCH-010'},
                {'name': 'Landscape Architecture', 'code': 'ARCH-011'},
                {'name': '3D Modeling', 'code': 'ARCH-012'},
                {'name': 'Construction Documentation', 'code': 'ARCH-013'},
                {'name': 'Sustainable Architecture', 'code': 'ARCH-014'},
                {'name': 'Architectural Drafting', 'code': 'ARCH-015'},
                {'name': 'Design Software', 'code': 'ARCH-016'},
                {'name': 'Client Consultation', 'code': 'ARCH-017'},
                {'name': 'Renovation Design', 'code': 'ARCH-018'},
                {'name': 'Feasibility Studies', 'code': 'ARCH-019'},
                {'name': 'Contract Administration', 'code': 'ARCH-020'},
                {'name': 'Urban Design', 'code': 'ARCH-021'},
                {'name': 'Building Systems', 'code': 'ARCH-022'},
                {'name': 'Facade Design', 'code': 'ARCH-023'},
                {'name': 'Lighting Design', 'code': 'ARCH-024'},
                {'name': 'Acoustic Design', 'code': 'ARCH-025'},
                {'name': 'Building Materials', 'code': 'ARCH-026'},
                {'name': 'Renovation Planning', 'code': 'ARCH-027'},
                {'name': 'Site Planning', 'code': 'ARCH-028'},
            ],
            'HR': [
                {'name': 'Talent Acquisition', 'code': 'HR-001'},
                {'name': 'Employee Relations', 'code': 'HR-002'},
                {'name': 'Human Resource Management', 'code': 'HR-003'},
                {'name': 'Compensation and Benefits', 'code': 'HR-004'},
                {'name': 'Training and Development', 'code': 'HR-005'},
                {'name': 'Performance Management', 'code': 'HR-006'},
                {'name': 'HR Policies', 'code': 'HR-007'},
                {'name': 'Recruitment Strategy', 'code': 'HR-008'},
                {'name': 'Employee Engagement', 'code': 'HR-009'},
                {'name': 'Labor Law Compliance', 'code': 'HR-010'},
                {'name': 'Workforce Planning', 'code': 'HR-011'},
                {'name': 'HR Technology', 'code': 'HR-012'},
                {'name': 'HR Analytics', 'code': 'HR-013'},
                {'name': 'Diversity and Inclusion', 'code': 'HR-014'},
                {'name': 'Payroll Management', 'code': 'HR-015'},
                {'name': 'Onboarding', 'code': 'HR-016'},
                {'name': 'HR Communication', 'code': 'HR-017'},
                {'name': 'Employee Retention', 'code': 'HR-018'},
                {'name': 'Leadership Development', 'code': 'HR-019'},
                {'name': 'Workplace Culture', 'code': 'HR-020'},
                {'name': 'Organizational Development', 'code': 'HR-021'},
                {'name': 'Talent Management', 'code': 'HR-022'},
                {'name': 'Employee Wellness', 'code': 'HR-023'},
                {'name': 'Succession Planning', 'code': 'HR-024'},
                {'name': 'HR Compliance', 'code': 'HR-025'},
                {'name': 'Conflict Resolution', 'code': 'HR-026'},
                {'name': 'HR Consulting', 'code': 'HR-027'},
                {'name': 'Global HR', 'code': 'HR-028'},
            ],
            'NONPROFIT': [
                {'name': 'Fundraising', 'code': 'NONPROFIT-001'},
                {'name': 'Grant Writing', 'code': 'NONPROFIT-002'},
                {'name': 'Program Management', 'code': 'NONPROFIT-003'},
                {'name': 'Nonprofit Leadership', 'code': 'NONPROFIT-004'},
                {'name': 'Nonprofit Marketing', 'code': 'NONPROFIT-005'},
                {'name': 'Volunteer Management', 'code': 'NONPROFIT-006'},
                {'name': 'Public Relations', 'code': 'NONPROFIT-007'},
                {'name': 'Advocacy', 'code': 'NONPROFIT-008'},
                {'name': 'Nonprofit Fundraising Strategy', 'code': 'NONPROFIT-009'},
                {'name': 'Nonprofit Financial Management', 'code': 'NONPROFIT-010'},
                {'name': 'Program Evaluation', 'code': 'NONPROFIT-011'},
                {'name': 'Board Governance', 'code': 'NONPROFIT-012'},
                {'name': 'Philanthropy', 'code': 'NONPROFIT-013'},
                {'name': 'Community Outreach', 'code': 'NONPROFIT-014'},
                {'name': 'Nonprofit Compliance', 'code': 'NONPROFIT-015'},
                {'name': 'Nonprofit Strategy', 'code': 'NONPROFIT-016'},
                {'name': 'Capacity Building', 'code': 'NONPROFIT-017'},
                {'name': 'Nonprofit Advocacy', 'code': 'NONPROFIT-018'},
                {'name': 'Social Impact', 'code': 'NONPROFIT-019'},
                {'name': 'Nonprofit Networking', 'code': 'NONPROFIT-020'},
                {'name': 'Nonprofit Marketing Strategy', 'code': 'NONPROFIT-021'},
                {'name': 'Nonprofit Fundraising Events', 'code': 'NONPROFIT-022'},
                {'name': 'Donor Relations', 'code': 'NONPROFIT-023'},
                {'name': 'Nonprofit Event Planning', 'code': 'NONPROFIT-024'},
                {'name': 'Social Media for Nonprofits', 'code': 'NONPROFIT-025'},
                {'name': 'Nonprofit Data Analysis', 'code': 'NONPROFIT-026'},
                {'name': 'Nonprofit Financial Reporting', 'code': 'NONPROFIT-027'},
                {'name': 'Volunteer Coordination', 'code': 'NONPROFIT-028'},
                {'name': 'Nonprofit Advocacy Campaigns', 'code': 'NONPROFIT-029'},
                {'name': 'Community Engagement', 'code': 'NONPROFIT-030'},
            ],
            'TRANSPORT': [
                {'name': 'Logistics Management', 'code': 'TRANSPORT-001'},
                {'name': 'Supply Chain Management', 'code': 'TRANSPORT-002'},
                {'name': 'Fleet Management', 'code': 'TRANSPORT-003'},
                {'name': 'Transport Planning', 'code': 'TRANSPORT-004'},
                {'name': 'Transportation Systems', 'code': 'TRANSPORT-005'},
                {'name': 'Route Optimization', 'code': 'TRANSPORT-006'},
                {'name': 'Freight Management', 'code': 'TRANSPORT-007'},
                {'name': 'Transport Safety', 'code': 'TRANSPORT-008'},
                {'name': 'Transportation Logistics', 'code': 'TRANSPORT-009'},
                {'name': 'Transport Operations', 'code': 'TRANSPORT-010'},
                {'name': 'Vehicle Maintenance', 'code': 'TRANSPORT-011'},
                {'name': 'Shipping and Delivery', 'code': 'TRANSPORT-012'},
                {'name': 'Cargo Management', 'code': 'TRANSPORT-013'},
                {'name': 'Transportation Compliance', 'code': 'TRANSPORT-014'},
                {'name': 'Transport Network Design', 'code': 'TRANSPORT-015'},
                {'name': 'Transportation Analysis', 'code': 'TRANSPORT-016'},
                {'name': 'Transport Management Systems', 'code': 'TRANSPORT-017'},
                {'name': 'Intermodal Transportation', 'code': 'TRANSPORT-018'},
                {'name': 'Transport Operations Optimization', 'code': 'TRANSPORT-019'},
                {'name': 'Vehicle Operations', 'code': 'TRANSPORT-020'},
                {'name': 'Transport Scheduling', 'code': 'TRANSPORT-021'},
                {'name': 'Fleet Maintenance', 'code': 'TRANSPORT-022'},
                {'name': 'Supply Chain Optimization', 'code': 'TRANSPORT-023'},
                {'name': 'Transport Risk Management', 'code': 'TRANSPORT-024'},
                {'name': 'Logistics Technology', 'code': 'TRANSPORT-025'},
                {'name': 'Driver Management', 'code': 'TRANSPORT-026'},
                {'name': 'Transportation Innovation', 'code': 'TRANSPORT-027'},
                {'name': 'Supply Chain Logistics', 'code': 'TRANSPORT-028'},
                {'name': 'Traffic Management', 'code': 'TRANSPORT-029'},
                {'name': 'Transportation Safety', 'code': 'TRANSPORT-030'},
            ],
            'HOSPITALITY': [
                {'name': 'Hotel Management', 'code': 'HOSPITALITY-001'},
                {'name': 'Event Planning', 'code': 'HOSPITALITY-002'},
                {'name': 'Restaurant Management', 'code': 'HOSPITALITY-003'},
                {'name': 'Guest Services', 'code': 'HOSPITALITY-004'},
                {'name': 'Housekeeping Management', 'code': 'HOSPITALITY-005'},
                {'name': 'Food and Beverage Management', 'code': 'HOSPITALITY-006'},
                {'name': 'Catering Services', 'code': 'HOSPITALITY-007'},
                {'name': 'Tourism Management', 'code': 'HOSPITALITY-008'},
                {'name': 'Customer Service Excellence', 'code': 'HOSPITALITY-009'},
                {'name': 'Restaurant Operations', 'code': 'HOSPITALITY-010'},
                {'name': 'Revenue Management', 'code': 'HOSPITALITY-011'},
                {'name': 'Event Coordination', 'code': 'HOSPITALITY-012'},
                {'name': 'Food Service Management', 'code': 'HOSPITALITY-013'},
                {'name': 'Hospitality Marketing', 'code': 'HOSPITALITY-014'},
                {'name': 'Tour Guide Services', 'code': 'HOSPITALITY-015'},
                {'name': 'Catering Operations', 'code': 'HOSPITALITY-016'},
                {'name': 'Hospitality Industry Knowledge', 'code': 'HOSPITALITY-017'},
                {'name': 'Travel Management', 'code': 'HOSPITALITY-018'},
                {'name': 'Hospitality Event Planning', 'code': 'HOSPITALITY-019'},
                {'name': 'Guest Experience', 'code': 'HOSPITALITY-020'},
                {'name': 'Hotel Operations', 'code': 'HOSPITALITY-021'},
                {'name': 'Front Desk Operations', 'code': 'HOSPITALITY-022'},
                {'name': 'Tourist Destination Management', 'code': 'HOSPITALITY-023'},
                {'name': 'Hotel and Resort Development', 'code': 'HOSPITALITY-024'},
                {'name': 'Food Safety Regulations', 'code': 'HOSPITALITY-025'},
                {'name': 'Catering Coordination', 'code': 'HOSPITALITY-026'},
                {'name': 'Team Management', 'code': 'HOSPITALITY-027'},
                {'name': 'Luxury Hospitality', 'code': 'HOSPITALITY-028'},
                {'name': 'Customer Loyalty Programs', 'code': 'HOSPITALITY-029'},
                {'name': 'Sustainable Hospitality', 'code': 'HOSPITALITY-030'},
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
        return self.CURRENCY_SYMBOLS.get(self.currency_type, '₹')  # Default to '₹' if no symbol is found

    def get_salary_range(self):
        """
        Returns a tuple containing the salary range: start, middle, and end.
        """
        return (self.salary_start, self.salary_middle, self.salary_end)


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

    def __str__(self):
        return f"Settings for {self.user.get_full_name()}"


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
