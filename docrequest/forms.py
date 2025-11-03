from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import DocumentRequest, ContactMessage, UserProfile
import re

YEAR_LEVEL_CHOICES = [
    ('1st Year', '1st Year'),
    ('2nd Year', '2nd Year'),
    ('3rd Year', '3rd Year'),
    ('4th Year', '4th Year'),
    ('Graduate', 'Graduate')
]
# ✅ Updated RegisterForm for School ID Registration
class RegisterForm(UserCreationForm):
    school_id = forms.CharField(
        max_length=8,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '20230574',
            'pattern': '[0-9]{8}',
            'title': 'Enter 8-digit School ID (e.g., 20230574)'
        }),
        help_text='Enter your 8-digit School ID (e.g., 20230574)'
    )
    
    role = forms.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Select your role'
    )
    
    first_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Juan'
        })
    )
    
    last_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Dela Cruz'
        })
    )
    
    department = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., College of Engineering (optional)'
        }),
        help_text='Your department or college'
    )
    
    course = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., BS Computer Science (optional)'
        }),
        help_text='Your course or program'
    )
    
    year_level = forms.ChoiceField(
        choices=YEAR_LEVEL_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        help_text='Current year level (for students only)'
    )
    
    class Meta:
        model = User
        fields = ['school_id', 'first_name', 'last_name', 'role', 'department', 'course', 'year_level', 'password1', 'password2']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Style password fields
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Create a strong password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        })
        
        # Update labels
        self.fields['school_id'].label = '🎓 School ID'
        self.fields['role'].label = '👤 I am a...'
        self.fields['first_name'].label = '👤 First Name'
        self.fields['last_name'].label = '👤 Last Name'
        self.fields['department'].label = '🏛️ Department/College'
        self.fields['course'].label = '📚 Course/Program'
        self.fields['year_level'].label = '📊 Year Level'
        self.fields['password1'].label = '🔒 Password'
        self.fields['password2'].label = '🔒 Confirm Password'
    
    def clean_school_id(self):
        """Validate School ID format and uniqueness"""
        school_id = self.cleaned_data.get('school_id')
        
        # Validate format: 8 digits
        if not re.match(r'^\d{8}$', school_id):
            raise ValidationError('School ID must be exactly 8 digits (e.g., 20230574)')
        
        # Validate year prefix (2000-2030)
        year_prefix = int(school_id[:4])
        if not (2000 <= year_prefix <= 2030):
            raise ValidationError('School ID must start with a valid year (2000-2030)')
        
        # Check if School ID already exists
        if UserProfile.objects.filter(school_id=school_id).exists():
            raise ValidationError('This School ID is already registered')
        
        # Check if username (school_id) already exists
        if User.objects.filter(username=school_id).exists():
            raise ValidationError('This School ID is already registered')
        
        return school_id
    
    def clean_year_level(self):
        """Validate year level is only for students"""
        role = self.cleaned_data.get('role')
        year_level = self.cleaned_data.get('year_level')
        
        if role == 'student' and not year_level:
            raise ValidationError('Year level is required for students')
        
        return year_level
    
    def save(self, commit=True):
        """Create user with School ID as username and auto-generated email"""
        school_id = self.cleaned_data.get('school_id')
        
        # Create User with school_id as username
        user = super().save(commit=False)
        user.username = school_id
        user.email = f"{school_id}@cityofmalabonuniversity.edu.ph"
        
        if commit:
            user.save()
            
            # Create or update UserProfile
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.school_id = school_id
            profile.role = self.cleaned_data.get('role')
            profile.department = self.cleaned_data.get('department', '')
            profile.course = self.cleaned_data.get('course', '')
            profile.year_level = self.cleaned_data.get('year_level', '')
            profile.save()
        
        return user


# ✅ Updated LoginForm for School ID Login
class LoginForm(AuthenticationForm):
    username = forms.CharField(
        max_length=8,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '20230574',
            'pattern': '[0-9]{8}',
            'title': 'Enter your 8-digit School ID',
            'autocomplete': 'username'
        }),
        label='🎓 School ID'
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password'
        }),
        label='🔒 Password'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'autofocus': True
        })
    
    def clean_username(self):
        """Validate School ID format"""
        username = self.cleaned_data.get('username')
        
        # Validate format: 8 digits
        if not re.match(r'^\d{8}$', username):
            raise ValidationError('Please enter your 8-digit School ID (e.g., 20230574)')
        
        return username


class DocumentRequestForm(forms.ModelForm):
    class Meta:
        model = DocumentRequest
        fields = [
            'document_type', 
            'purpose', 
            'notes',
            'school_id', 
            'section', 
            'course', 
            'school_year', 
            'graduation_year',
            'payment_method',
        ]
        widgets = {
            'document_type': forms.Select(attrs={
                'class': 'form-control form-select',
                'required': True
            }),
            'purpose': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'e.g., Job Application, Scholarship Application, Transfer to another school',
                'required': True
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Any special instructions or additional information (optional)'
            }),
            'school_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 20230574',
                'readonly': 'readonly'  # ✅ Auto-filled from profile
            }),
            'section': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 1-A, Section B (optional)'
            }),
            'course': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., BS Computer Science, Grade 12 STEM (optional)'
            }),
            'school_year': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 2023-2024 (optional)'
            }),
            'graduation_year': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 2025 (optional)'
            }),
            'payment_method': forms.RadioSelect(attrs={
                'class': 'payment-method-radio'
            }),
        }
        labels = {
            'document_type': '📄 Document Type',
            'purpose': '📝 Purpose of Request',
            'notes': '💬 Additional Notes',
            'school_id': '🎓 School ID Number',
            'section': '📚 Section',
            'course': '🎯 Course/Program',
            'school_year': '📅 School Year',
            'graduation_year': '🎓 Graduation Year',
            'payment_method': '💳 Payment Method',
        }
        help_texts = {
            'document_type': 'Select the type of document you need',
            'purpose': 'Please specify why you need this document',
            'school_id': 'Your official school ID number (auto-filled)',
            'payment_method': 'Choose how you want to pay for this document',
        }
    
    def __init__(self, *args, **kwargs):
        # ✅ Get user to auto-fill school_id
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Auto-fill school_id from user profile
        if self.user and hasattr(self.user, 'profile'):
            self.fields['school_id'].initial = self.user.profile.school_id
        
        self.fields['payment_method'].widget.attrs.update({
            'class': 'form-check-input payment-radio'
        })
        
        self.fields['school_id'].required = False
        self.fields['purpose'].required = True

    def clean_school_id(self):
        """Always return the user's school_id if available"""
        school_id = self.cleaned_data.get('school_id')
        if not school_id and self.user and hasattr(self.user, 'profile'):
            return self.user.profile.school_id  # Auto-fill backend
        return school_id

    def clean(self):
        """Validate that user doesn't have an active request"""
        cleaned_data = super().clean()
        
        # Check if user already has an active request
        if self.user and DocumentRequest.user_has_active_request(self.user):
            active_request = DocumentRequest.get_user_active_request(self.user)
            raise ValidationError(
                f'You already have an active request (Order ID: {active_request.order_id}). '
                f'Please wait until your current request is completed or rejected before submitting a new one.'
            )
        
        return cleaned_data

class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'message', 'attachment']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your full name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'your.email@example.com'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'What is this about?'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Please describe your inquiry in detail...'
            }),
            'attachment': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }
        labels = {
            'name': '👤 Your Name',
            'email': '📧 Email Address',
            'subject': '📋 Subject',
            'message': '💬 Message',
            'attachment': '📎 Attachment (Optional)',
        }
        help_texts = {
            'attachment': 'You can attach an image to help us understand your issue better',
        }