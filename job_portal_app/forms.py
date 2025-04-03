# job_postings/forms.py
import datetime
import json

from dal import autocomplete
from django import forms
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.core.validators import MaxLengthValidator, EmailValidator, \
    RegexValidator, FileExtensionValidator, MinLengthValidator
from django.forms import SelectDateWidget

from .models import JobPosting, OrganizationProfile, RecruiterRoleEnum, COUNTRY_CHOICES, STATE_CHOICES, \
    JobApplication, Department, JobIndustry, Skills, RecruiterSettings, Role, SalaryMarket
from job_portal_app.image_utils import compress_image

HIGHLIGHTS_CHOICES = [
    ('free_food', 'Free Food'),
    ('free_room', 'Free Accommodation'),
    ('transport', 'Transport Allowance'),
    ('bonus', 'Performance Bonus'),
    ('health', 'Health Insurance'),
    ('training', 'Training Program'),
    ('flexible', 'Flexible Hours'),
]


class JobPostingForm(forms.ModelForm):
    title = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200',
            'placeholder': 'e.g. Senior Software Engineer',
            'maxlength': '50',
            'id': 'id_title',

        }),
        validators=[
            RegexValidator(
                regex='^[a-zA-Z0-9\s\-\&\.\,]+$',  # You can adjust the allowed characters as per your needs
                message='Only letters, numbers, spaces, hyphens, ampersands, periods, and commas are allowed.',
                code='invalid_title'
            )
        ],
        help_text="Maximum 100 characters. Only letters, numbers, spaces, hyphens, ampersands, periods, and commas are allowed.",
        required=True
    )

    location = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200',
            'placeholder': 'e.g. Chennai',
            'maxlength': '30',
            'id': 'id_location',
        }),
        validators=[
            RegexValidator(
                regex='^[a-zA-Z0-9\s\-\&\,\.]+$',  # Allow letters, numbers, spaces, hyphens, commas, and periods
                message='Only letters, numbers, spaces, hyphens, commas, and periods are allowed.',
                code='invalid_location'
            )
        ],
        help_text="Maximum 100 characters. Only letters, numbers, spaces, hyphens, commas, and periods are allowed.",
        required=True
    )

    company = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200',
            'placeholder': 'Your company name',
            'maxlength': '100',
            'id': 'id_company'
        }),
        validators=[
            RegexValidator(
                regex='^[a-zA-Z0-9\s\-\&\,\.]+$',  # Allow letters, numbers, spaces, hyphens, commas, and periods
                message='Only letters, numbers, spaces, hyphens, commas, and periods are allowed.',
                code='invalid_company'
            )
        ],
        help_text="Maximum 100 characters. Only letters, numbers, spaces, hyphens, commas, and periods are allowed.",
        required=True
    )

    description = forms.CharField(
        max_length=2000,
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200',
            'placeholder': 'Describe the job responsibilities and requirements...',
            'maxlength': '1000',
            'id': 'id_description',
            'oninput': 'autoResize(this)',
            'style': 'min-height: 8rem; overflow-y: hidden; resize: none;'
        }),
        validators=[
            MinLengthValidator(50),  # Ensure the description is at least 50 characters
            MaxLengthValidator(1000)  # Ensure the description does not exceed 2000 characters
        ],
        help_text="Please provide a detailed description (between 50 and 2000 characters).",
        required=True
    )

    experience_type = forms.ChoiceField(
        choices=[
            ('fresher', 'Fresher'),
            ('min_max', 'Min-Max'),
            ('fixed', 'Fixed')
        ],
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200',
            'id': 'id_experience_type'
        }),
    )

    experience_range_min = forms.IntegerField(
        widget=forms.NumberInput(attrs={
            'type': 'range',
            'min': 0,
            'max': 50,
            'step': 1,
            'class': 'w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer focus:outline-none focus:ring-0',
            'id': 'id_experience_range_min'
        }),
        required=False  # Default to not required
    )

    experience_range_max = forms.IntegerField(
        widget=forms.NumberInput(attrs={
            'type': 'range',
            'min': 0,
            'max': 50,
            'step': 1,
            'class': 'w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer focus:outline-none focus:ring-0',
            'id': 'id_experience_range_max'
        }),
        required=False  # Default to not required
    )

    experience_fixed = forms.IntegerField(
        widget=forms.NumberInput(attrs={
            'type': 'range',
            'min': 0,
            'max': 50,
            'step': 1,
            'class': 'w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer focus:outline-none focus:ring-0',
            'id': 'id_experience_fixed'
        }),
        required=False  # Default to not required
    )

    salary_min = forms.IntegerField(
        widget=forms.NumberInput(attrs={
            'type': 'range',
            'step': 500,
            'class': 'w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer focus:outline-none focus:ring-0',
            'id': 'id_salary_min'
        }),
        required=False  # Default to not required
    )

    salary_max = forms.IntegerField(
        widget=forms.NumberInput(attrs={
            'type': 'range',
            'step': 500,
            'class': 'w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer focus:outline-none focus:ring-0',
            'id': 'id_salary_max'
        }),
        required=False  # Default to not required
    )
    salary_not_disclosed = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={
            'class': 'h-5 w-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500 transition duration-200',
            'id': 'id_salary_not_disclosed'
        }),
        required=False  # It's not required by default
    )

    industry_type = forms.ChoiceField(

        widget=autocomplete.Select2(
            url='/career-listings/industry-autocomplete/',
            attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200',
                'data-placeholder': 'Industry',
                'data-minimum-input-length': 1,
                'data-theme': 'tailwindcss-3',
                'data-tags': 'true',  # This enables free text entry
                'id': 'id_industry_type'
            },
            forward=['name'],
        ),
        required=True,
    )

    department = forms.ChoiceField(

        widget=autocomplete.ListSelect2(
            url='/career-listings/department-autocomplete/',
            attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200',
                'data-placeholder': 'Department',
                'data-minimum-input-length': 1,
                'data-theme': 'tailwindcss-3',
                'data-tags': 'true',  # This enables free text entry
                'id': 'id_department'
            },
            forward=['name'],
        ),
        required=True,
    )

    role = forms.ChoiceField(

        widget=autocomplete.ListSelect2(
            url='/career-listings/role-autocomplete/',
            attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200',
                'data-placeholder': 'Role',
                'data-minimum-input-length': 1,
                'data-theme': 'tailwindcss-3',
                'data-tags': 'true',  # This enables free text entry
                'id': 'id_role'
            },
            forward=['name'],
        ),
        required=True,
    )

    must_have_skills = forms.MultipleChoiceField(
        initial=['a'],
        choices=[('a', 'A'), ('b', 'B')],
        widget=autocomplete.Select2Multiple(
            url='/career-listings/skills-autocomplete/',
            attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200',
                'data-placeholder': 'Select 3-5 must-have skills',
                'data-minimum-input-length': 1,
                'data-tags': 'true',
                'data-minimum-selection-length': 3,
                'data-maximum-selection-length': 5,
                'data-width': '100%',
            }),
        required=True,
    )

    good_to_have_skills = forms.MultipleChoiceField(
        widget=autocomplete.Select2Multiple(
            url='/career-listings/skills-autocomplete/',
            attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200',
                'data-placeholder': 'Select 3-5 good-to-have skills',
                'data-minimum-input-length': 1,
                'data-tags': 'true',  # This enables free text entry
                'id': 'id_good_to_have_skills',
                'data-min-items': '1',  # Minimum items
                'data-max-items': '3',  # Maximum items
            }),
        required=False
    )

    highlights = forms.MultipleChoiceField(
        choices=HIGHLIGHTS_CHOICES,
        widget=forms.CheckboxSelectMultiple(
            attrs={
                'id': 'id_highlight'
            }
        ),
        required=False,
        initial=['free_food'],
        label="Select Job Perks"
    )

    # Calculate dates
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    max_date = datetime.date.today() + datetime.timedelta(days=30)

    expiry_date = forms.DateField(
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'min': tomorrow.strftime('%Y-%m-%d'),  # Tomorrow's date
                'max': max_date.strftime('%Y-%m-%d'),  # 30 days from today
                'value': max_date.strftime('%Y-%m-%d'),  # Default to max date
                'id': 'id_expiry_date',
            }
        ),
        required=True,
        label="Expiry Date (Tomorrow to 30 Days)",
        input_formats=['%Y-%m-%d'],
        initial=max_date,  # Backend initial value
    )

    def __init__(self, *args, **kwargs):
        currency_type = kwargs.pop('currency_type', None)
        super().__init__(*args, **kwargs)

        if self.instance:
            self.fields['expiry_date'].required = False

        if currency_type:

            # Fetch the salary market corresponding to the provided currency_type
            try:
                salary_market = SalaryMarket.objects.get(currency_type=currency_type)
                salary_markers = {
                    'start': salary_market.salary_start,
                    'middle': salary_market.salary_middle,  # 500K
                    'end': salary_market.salary_end  # 1M
                }
                self.fields['salary_min'].widget.attrs.update({
                    'min': salary_markers['start'],  # Set the min value from salary market
                    'max': salary_markers['end'],  # Set the max value from salary market
                })

                self.fields['salary_max'].widget.attrs.update({
                    'min': salary_markers['start'],  # Set the min value from salary market
                    'max': salary_markers['end'],  # Set the max value from salary market
                })

            except SalaryMarket.DoesNotExist:
                # Handle the case where the SalaryMarket doesn't exist for the given currency_type
                pass

        if self.instance:
            try:
                # Check if all required fields exist in the instance
                required_fields = ['must_have_skills', 'good_to_have_skills', 'role', 'department', 'industry_type']

                for field in required_fields:
                    if not hasattr(self.instance, field):
                        raise AttributeError(f"Field '{field}' not found in the instance.")

                # Parse skills fields
                if self.data:
                    must_have_skills = self.data.getlist('must_have_skills')  # Use data if available
                else:
                    must_have_skills = self.instance.must_have_skills if self.instance.must_have_skills else []  # Fallback to instance

                if self.data:
                    good_to_have_skills = self.data.getlist('good_to_have_skills')  # Use data if available
                else:
                    good_to_have_skills = self.instance.good_to_have_skills if self.instance.good_to_have_skills else []  # Fallback to instance

                # Generate choices for skills fields
                all_skills = list(Skills.objects.values_list('name', flat=True))

                must_have_skills_choices = [(skill, skill) for skill in
                                            list(set(must_have_skills + all_skills))]
                good_to_have_skills_choices = [(skill, skill) for skill in
                                               list(set(good_to_have_skills + all_skills))]

                # Assign choices and initial values to skills fields
                self.fields['must_have_skills'].choices = must_have_skills_choices
                self.initial['must_have_skills'] = must_have_skills
                self.fields['good_to_have_skills'].choices = good_to_have_skills_choices
                self.initial['good_to_have_skills'] = good_to_have_skills

                if hasattr(self.instance, 'industry_type'):
                    if self.data:
                        all_choices = [self.data['industry_type']] if self.data['industry_type'] else [] + list(
                            JobIndustry.objects.values_list('name', flat=True))
                        industry_type_choices = [(industry_type, industry_type) for industry_type in all_choices]
                        self.fields['industry_type'].choices = industry_type_choices

                    else:
                        all_choices = [self.instance.industry_type] if self.instance.industry_type else [] + list(
                            JobIndustry.objects.values_list('name', flat=True))
                        industry_type_choices = [(industry_type, industry_type) for industry_type in all_choices]
                        self.fields['industry_type'].choices = industry_type_choices

                if hasattr(self.instance, 'role'):
                    if self.data:
                        all_choices = [self.data['role']] if self.data[
                            'role'] else [] + list(Role.objects.values_list('name', flat=True))
                        role_choices = [(role, role) for role in all_choices]
                        self.fields['role'].choices = role_choices

                    else:
                        all_choices = [
                            self.instance.role] if self.instance.role else [] + list(Role.objects.values_list(
                            'name', flat=True))
                        role_choices = [(role_type, role_type) for role_type in all_choices]
                        self.fields['role'].choices = role_choices

                if hasattr(self.instance, 'department'):
                    if self.data:
                        all_choices = [self.data['department']] if self.data[
                            'department'] else [] + list(Department.objects.values_list('name', flat=True))
                        department_choices = [(department, department) for department in all_choices]
                        self.fields['department'].choices = department_choices

                    else:
                        all_choices = [
                            self.instance.department] if self.instance.department else [] + list(
                            Department.objects.values_list(
                                'name', flat=True))
                        department_choices = [(department, department) for department in all_choices]
                        self.fields['department'].choices = department_choices

                # Set initial values for other fields
                self.initial['highlights'] = self.instance.highlights

            except (TypeError, json.JSONDecodeError, AttributeError) as e:
                # Handle invalid or missing data gracefully
                self.initial['must_have_skills'] = []
                self.initial['good_to_have_skills'] = []
                self.initial['role'] = None
                self.initial['department'] = None
                self.initial['industry_type'] = None
                self.initial['highlights'] = None
                raise ValidationError("Something went wrong.")



    class Meta:
        model = JobPosting

        fields = [
            'title', 'experience_type', 'experience_range_min', 'experience_range_max',
            'experience_fixed',
            'salary_min', 'salary_max', 'salary_not_disclosed', 'work_mode', 'location',
            'must_have_skills', 'good_to_have_skills', 'description', 'highlights',
            'industry_type', 'department', 'role', 'employment_type', 'education',
            'company', 'vacancies', 'expiry_date'
        ]

        widgets = {
            'work_mode': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200',
                'id': 'id_work_mode'
            }),

            'employment_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200',
                'id': 'id_employment_type'
            }),

            'education': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200',
                'placeholder': 'e.g. Bachelor\'s degree in Computer Science',
                'id': 'id_education'
            }),

            'vacancies': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200',
                'placeholder': 'Number of open positions',
                'id': 'id_vacancies'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()

        if self.instance.status!='published':
            raise ValidationError('Job listing is not published to update')
        salary_not_disclosed = cleaned_data.get('salary_not_disclosed')
        salary_min = cleaned_data.get('salary_min')
        salary_max = cleaned_data.get('salary_max')

        # If 'salary_not_disclosed' is not checked, salary_min and salary_max should be required
        if not salary_not_disclosed:
            if salary_min is None or salary_max is None:
                raise ValidationError("Please provide both minimum and maximum salary values.")

            # Ensure salary_min is less than salary_max
            if salary_min > salary_max:
                raise ValidationError("Minimum salary must be less than maximum salary.")

        experience_type = cleaned_data.get('experience_type')
        experience_range_min = cleaned_data.get('experience_range_min')
        experience_range_max = cleaned_data.get('experience_range_max')
        experience_fixed = cleaned_data.get('experience_fixed')

        # Fresher case: No need for any additional fields
        if experience_type == 'fresher':
            if experience_range_min or experience_range_max or experience_fixed:
                raise ValidationError("No experience fields should be filled for fresher.")

        # Min-Max case: Ensure both range fields are provided and valid
        elif experience_type == 'min_max':
            if experience_range_min is None or experience_range_max is None:
                raise ValidationError("Please provide both minimum and maximum experience.")
            if experience_range_min > experience_range_max:
                raise ValidationError("Minimum experience must be less than maximum experience.")

        # Fixed case: Ensure the fixed experience field is provided
        elif experience_type == 'fixed':
            if experience_fixed is None:
                raise ValidationError("Please provide fixed experience.")

        expiry_date = cleaned_data.get('expiry_date')

        if expiry_date:
            if expiry_date < self.tomorrow:
                self.add_error('expiry_date', "Expiry date must be at least tomorrow.")
            if expiry_date > self.max_date:
                self.add_error('expiry_date', "Expiry date cannot be more than 30 days from today.")
        if self.instance:
            cleaned_data['expiry_date'] = self.instance.expiry_date

        return cleaned_data


class UpdateStatusForm(forms.ModelForm):
    class Meta:
        model = JobApplication
        fields = ['status']

    STATUS_CHOICES = [
        ('applied', 'Applied'),
        ('viewed', 'Viewed'),
        ('reviewed', 'Reviewed'),
        ('interview', 'Interview'),
        ('offer', 'Offer'),
        ('hired', 'Hired'),
    ]

    status = forms.ChoiceField(choices=STATUS_CHOICES, required=True)


class OrganizationProfileForm(forms.ModelForm):
    organization_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200',
            'placeholder': 'Enter Organization Name',
            'id': 'id_organization_name',
            'maxlength': '100',
        }),
        validators=[
            RegexValidator(
                regex='^[a-zA-Z0-9\s\-\.,&]+$',
                message='Only letters, numbers, spaces, hyphens, commas, periods and ampersands are allowed',
                code='invalid_organization_name'
            )
        ],
        help_text="Maximum 100 characters (letters, numbers and basic punctuation only)",
        required=True
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200',
            'placeholder': 'your.company@example.com',
            'id': 'id_email',
            'autocomplete': 'email',
        }),
        validators=[
            EmailValidator(message="Please enter a valid email address")
        ],
        help_text="Official company email address",
        required=True
    )

    organization_address = forms.CharField(
        max_length=500,
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200',
            'placeholder': 'Enter Organization Address',
            'rows': 4,
            'id': 'id_organization_address',
            'maxlength': '500',
        }),
        validators=[
            MaxLengthValidator(500, message="Maximum 500 characters allowed")
        ],
        help_text="Maximum 500 characters allowed",
        required=True
    )

    country = forms.ChoiceField(
        choices=COUNTRY_CHOICES,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200',
            'id': 'id_country'
        }),
        help_text="Select your country",
        required=True
    )

    state = forms.ChoiceField(
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200',
            'id': 'id_state'
        }),
        help_text="Select your state/province",
        required=True
    )

    city = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200',
            'placeholder': 'Enter City',
            'id': 'id_city',
            'maxlength': '50',
        }),
        validators=[
            RegexValidator(
                regex='^[a-zA-Z\s\-]+$',
                message='Only letters, spaces and hyphens are allowed',
                code='invalid_city'
            )
        ],
        help_text="Maximum 50 characters (letters and spaces only)",
        required=True
    )

    postal_code = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200',
            'placeholder': 'Enter Postal Code',
            'id': 'id_postal_code',
            'maxlength': '10',
        }),
        validators=[
            RegexValidator(
                regex='^[a-zA-Z0-9\-]+$',
                message='Only letters, numbers and hyphens are allowed',
                code='invalid_postal_code'
            )
        ],
        help_text="Enter your postal/zip code (max 10 characters)",
        required=True
    )

    logo = forms.ImageField(
        required=True,
        widget=forms.FileInput(attrs={
            'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 transition duration-200',
            'accept': 'image/*',
            'id': 'id_logo',
        }),
        help_text="Required. Upload company logo (max 2MB)",
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png']),
        ]
    )

    class Meta:
        model = OrganizationProfile
        fields = [
            'organization_name', 'organization_address',
            'email', 'country', 'city', 'state', 'postal_code', 'logo'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default value for state based on country
        if not self.instance.pk:  # If the object is being created (not updated)
            country = 'IN'  # Default country
            state = 'MH'  # Default state for India
        else:
            country = self.instance.country
            state = self.instance.state

        self.fields['country'].initial = country
        self.fields['state'].choices = STATE_CHOICES.get(country, [])
        self.fields['state'].initial = state

        # Add onchange event to country field to update states
        self.fields['country'].widget.attrs['onchange'] = 'updateStates(this)'

    def clean_logo(self):
        logo = self.cleaned_data.get('logo')

        if logo:
            # Check if it's a new file upload
            if isinstance(logo, UploadedFile):
                # Validate file size
                if logo.size > 2 * 1024 * 1024:  # 2MB limit
                    raise ValidationError("Image file too large (max 2MB)")

                # Validate content type
                if not logo.content_type.startswith('image'):
                    raise ValidationError("File is not an image")

                # Validate file extension
                if not logo.name.lower().endswith(('.png', '.jpg', '.jpeg')):
                    raise ValidationError("Invalid image file type (only .png, .jpg, .jpeg allowed)")
                try:
                    # Use the reusable compression function
                    compressed_logo = compress_image(
                        logo,
                        max_size=(500, 500),
                        quality=85,
                        output_format='JPEG'  # or 'PNG' if you prefer
                    )
                    return compressed_logo
                except ValueError as e:
                    raise forms.ValidationError("Failed to upload image")

        return logo

    def clean(self):
        cleaned_data = super().clean()
        country = cleaned_data.get('country')
        state = cleaned_data.get('state')

        # Validate that the selected state belongs to the selected country
        if country and state:
            valid_states = dict(STATE_CHOICES.get(country, []))
            if state not in valid_states:
                raise ValidationError({
                    'state': "Selected state is not valid for the chosen country"
                })

        return cleaned_data


from django import forms
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
    MaxLengthValidator,
    EmailValidator,
    RegexValidator
)
from phonenumber_field.formfields import PhoneNumberField
from .models import RecruiterProfile


class RecruiterProfileForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200',
            'placeholder': 'Enter First Name',
            'id': 'id_first_name',
            'maxlength': '30',
        }),
        validators=[
            RegexValidator(
                regex='^[a-zA-Z\s\-\.\']+$',
                message='Only letters, spaces, hyphens, periods and apostrophes are allowed',
                code='invalid_first_name'
            )
        ],
        help_text="Maximum 30 characters (letters and spaces only)",
        required=True
    )

    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200',
            'placeholder': 'Enter Last Name',
            'id': 'id_last_name',
            'maxlength': '30',
        }),
        validators=[
            RegexValidator(
                regex='^[a-zA-Z\s\-\.\']+$',
                message='Only letters, spaces, hyphens, periods and apostrophes are allowed',
                code='invalid_last_name'
            )
        ],
        help_text="Maximum 30 characters (letters and spaces only)",
        required=True
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200',
            'placeholder': 'your.email@example.com',
            'id': 'id_email',
            'autocomplete': 'email',
        }),
        validators=[
            EmailValidator(message="Please enter a valid email address")
        ],
        help_text="We'll never share your email with anyone else.",
        required=True
    )

    phone = PhoneNumberField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200',
            'placeholder': '+91 (123) 456-7890',
            'id': 'id_phone',
            'type': 'tel',
            'maxlength': '20',
            'pattern': '^\+[0-9]{1,3}[0-9]{4,14}$',  # Basic international phone pattern
        }),
        validators=[
            RegexValidator(
                regex='^\+[0-9]{1,3}[0-9]{4,14}$',
                message='Phone number must be in international format (e.g. +919155552671)',
                code='invalid_phone'
            )
        ],
        help_text="Include country code (e.g. +1 for US). Example: +919155552671",
        required=True

    )

    company = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200',
            'placeholder': 'Enter Company Name',
            'id': 'id_company',
            'maxlength': '100',
        }),
        validators=[
            RegexValidator(
                regex='^[a-zA-Z0-9\s\-\.,&]+$',
                message='Only letters, numbers, spaces, hyphens, commas, periods and ampersands are allowed',
                code='invalid_company'
            )
        ],
        help_text="Maximum 100 characters",
        required=True
    )

    role = forms.ChoiceField(
        choices=RecruiterRoleEnum.choices(),
        initial=RecruiterRoleEnum.RECRUITER.value,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200',
            'id': 'id_role'
        }),
        help_text="Select your primary role",
        required=True
    )

    years_of_experience = forms.IntegerField(
        min_value=0,
        max_value=50,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200',
            'placeholder': '5',
            'id': 'id_years_of_experience',
            'min': '0',
            'max': '50',
            'step': '1',
            'oninput': 'clampValue(this)',  # JavaScript enforcement
        }),
        validators=[
            MinValueValidator(0, message="Experience cannot be negative"),
            MaxValueValidator(50, message="Maximum 50 years experience")
        ],
        help_text="Enter a value between 0-50 years",
        required=True
    )

    bio = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200',
            'placeholder': 'Tell us about your professional background...',
            'rows': 4,
            'id': 'id_bio',
            'maxlength': '500',
        }),
        validators=[
            MaxLengthValidator(500, message="Maximum 500 characters allowed")
        ],
        help_text="Maximum 500 characters allowed",
        required=True
    )

    profile_picture = forms.ImageField(
        required=True,
        widget=forms.FileInput(attrs={
            'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 transition duration-200',
            'accept': 'image/*',
            'id': 'id_profile_picture',
            'onchange': 'previewImage(this)',
        }),
        help_text="Required. Upload your profile picture (max 2MB)",
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png']),
        ]
    )

    class Meta:
        model = RecruiterProfile
        fields = [
            'first_name',
            'last_name',
            'email',
            'role',
            'company',
            'phone',
            'profile_picture',
            'bio',
            'years_of_experience',
        ]
        widgets = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['role'].initial = RecruiterRoleEnum.RECRUITER.value
            self.fields['years_of_experience'].initial = 0

    def clean_profile_picture(self):
        picture = self.cleaned_data.get('profile_picture')

        if picture:
            # Check if it's a new file upload
            if isinstance(picture, UploadedFile):
                # Validate file size
                if picture.size > 2 * 1024 * 1024:  # 2MB limit
                    raise ValidationError("Image file too large (max 2MB)")

                # Validate content type
                if not picture.content_type.startswith('image'):
                    raise ValidationError("File is not an image")
                # For existing files, validate the filename extension
                if not picture.name.lower().endswith(('.png', '.jpg', '.jpeg')):
                    raise ValidationError("Invalid image file type")

                try:
                    # Use the reusable compression function
                    compressed_logo = compress_image(
                        picture,
                        max_size=(500, 500),
                        quality=85,
                        output_format='JPEG'  # or 'PNG' if you prefer
                    )
                    return compressed_logo
                except ValueError as e:
                    raise forms.ValidationError("Failed to upload image")

        return picture


class RecruiterSettingsForm(forms.ModelForm):
    class Meta:
        model = RecruiterSettings
        fields = ['currency_type']
        widgets = {
            'currency_type': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500',
            }),
        }
        labels = {
            'currency_type': 'Preferred Currency',
        }
