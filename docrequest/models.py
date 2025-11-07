from django.db import models
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid
from datetime import datetime


def contact_attachment_upload_path(instance, filename):
    """Upload path for contact message attachments"""
    return f'contact_attachments/{filename}'


# ✅ NEW: UserProfile Model for School ID and Role Management
class UserProfile(models.Model):
    """Extended user profile with school-specific information"""
    
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('alumni', 'Alumni'),
        ('faculty', 'Faculty'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    school_id = models.CharField(
        max_length=8,
        unique=True,
        help_text="8-digit School ID (e.g., 20230574)"
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='student',
        help_text="User role: Student, Alumni, or Faculty"
    )
    department = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Department or College (e.g., College of Engineering)"
    )
    course = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Course/Program (e.g., BS Computer Science)"
    )
    year_level = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Year level (for students: 1st, 2nd, 3rd, 4th)"
    )
    graduation_year = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Year of graduation (for alumni)"
    )
    is_verified = models.BooleanField(
        default=False,
        help_text="Whether the user's identity has been verified by admin"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        ordering = ['school_id']
    
    def __str__(self):
        return f"{self.school_id} - {self.user.get_full_name()} ({self.get_role_display()})"
    
    def get_email(self):
        """Generate email based on school ID"""
        return f"{self.school_id}@cityofmalabonuniversity.edu.ph"
    
    def is_student(self):
        return self.role == 'student'
    
    def is_alumni(self):
        return self.role == 'alumni'
    
    def is_faculty(self):
        return self.role == 'faculty'


# ✅ Signal to auto-create UserProfile when User is created
# Update the existing signal in models.py
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create UserProfile automatically when a User is created"""
    if created:
        # Generate school_id from username or user ID
        if instance.username.isdigit() and len(instance.username) == 8:
            school_id = instance.username
        else:
            school_id = f"{2023}{instance.id:04d}"
        
        UserProfile.objects.get_or_create(
            user=instance,
            defaults={
                'school_id': school_id,
                'role': 'student',
                'is_verified': instance.is_staff or instance.is_superuser
            }
        )


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save UserProfile whenever User is saved"""
    if hasattr(instance, 'profile'):
        profile = instance.profile
        # Fix empty school_id
        if not profile.school_id or profile.school_id.strip() == '':
            if instance.username.isdigit() and len(instance.username) == 8:
                profile.school_id = instance.username
            else:
                profile.school_id = f"{2023}{instance.id:04d}"
            profile.save()

class DocumentRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('ready', 'Ready for Pickup'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ]

    DOCUMENT_TYPES = [
        ('transcript', 'Academic Transcript'),
        ('diploma', 'Diploma/Certificate'),
        ('grade_report', 'Grade Report'),
        ('enrollment_cert', 'Certificate of Enrollment'),
        ('good_moral', 'Certificate of Good Moral Character'),
        ('transfer_cert', 'Transfer Certificate'),
        ('other', 'Other'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('online', 'Online (GCash/Maya)'),
        ('cash', 'Cash on Pickup'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),  
        ('partially_refunded', 'Partially Refunded'),
    ]
    
    # Unique Order ID
    order_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        blank=True,
        default='',  
        help_text="Unique order identifier (e.g., DOC-20250109-A3F2)"
    )
    
    # User & Document Info
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='document_requests')
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    purpose = models.TextField(help_text="Reason for requesting this document")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, null=True, help_text="Additional notes or special instructions")
    
    # Payment Info
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='online',
        help_text="Choose: Online (Simulated GCash/Maya) or Cash on Pickup"
    )
    payment_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Payment amount in PHP"
    )
    payment_status = models.CharField(
        max_length=20,
        default='unpaid',
        choices=PAYMENT_STATUS_CHOICES,
        help_text="Payment status (simulated)"
    )
    payment_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Simulated payment reference number"
    )
    payment_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date when payment was completed"
    )
    
    # User Academic Info (kept for backward compatibility)
    school_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Your school ID number"
    )
    section = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Your class section (e.g., A, B, or 1-A)"
    )
    course = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Your course or program (e.g., BS Computer Science)"
    )
    school_year = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Academic year (e.g., 2023-2024)"
    )
    graduation_year = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Expected or actual graduation year"
    )
    
    # Pickup Info
    ready_for_pickup = models.BooleanField(
        default=False,
        help_text="Check when document is ready for physical pickup"
    )
    picked_up = models.BooleanField(
        default=False,
        help_text="Check when user has picked up the document"
    )
    picked_up_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date when document was picked up"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Document Request'
        verbose_name_plural = 'Document Requests'
    
    def __str__(self):
        if self.order_id:
            return f"Order #{self.order_id} - {self.user.username} - {self.get_document_type_display()}"
        return f"{self.user.username} - {self.get_document_type_display()}"
    
    def save(self, *args, **kwargs):
        if not self.order_id:
            self.order_id = self.generate_order_id()
        
        # Auto-set payment amount based on document type
        if not self.payment_amount:
            self.payment_amount = self.calculate_payment_amount()
        
        # ✅ Auto-fill school_id from user profile if not set
        if not self.school_id and hasattr(self.user, 'profile'):
            self.school_id = self.user.profile.school_id
        
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_order_id():
        """Generate unique Order ID format: DOC-YYYYMMDD-XXXX"""
        date_part = datetime.now().strftime('%Y%m%d')
        unique_part = str(uuid.uuid4().hex[:4]).upper()
        return f"DOC-{date_part}-{unique_part}"
    
    def calculate_payment_amount(self):
        """Calculate payment amount based on document type"""
        pricing = {
            'transcript': 150.00,
            'diploma': 200.00,
            'grade_report': 50.00,
            'enrollment_cert': 50.00,
            'good_moral': 50.00,
            'transfer_cert': 100.00,
            'other': 50.00,
        }
        return pricing.get(self.document_type, 50.00)
    
    def requires_payment(self):
        """Check if document type requires payment"""
        return True
    
    def is_paid(self):
        """Check if payment is completed"""
        return self.payment_status == 'paid'
    
    def can_pickup(self):
        """Check if document is ready for pickup"""
        return self.ready_for_pickup and self.is_paid() and not self.picked_up
    
    def get_payment_status_badge(self):
        """Get colored badge for payment status"""
        badges = {
            'unpaid': 'warning',
            'paid': 'success',
            'failed': 'danger',
        }
        return badges.get(self.payment_status, 'secondary')
    
    @staticmethod
    def user_has_active_request(user):
        """Check if user has any active (non-completed/non-rejected) requests"""
        active_statuses = ['pending', 'processing', 'ready']
        return DocumentRequest.objects.filter(
            user=user,
            status__in=active_statuses
        ).exists()
    
    @staticmethod
    def get_user_active_request(user):
        """Get user's current active request if any"""
        active_statuses = ['pending', 'processing', 'ready']
        return DocumentRequest.objects.filter(
            user=user,
            status__in=active_statuses
        ).first()
    
    def can_be_cancelled(self):
        """Check if request can be cancelled by user"""
        return self.status in ['pending', 'processing']
    
    def is_cancelled(self):
        """Check if request was cancelled"""
        return self.status == 'rejected' and '[CANCELLED BY USER' in (self.notes or '')


class ContactMessage(models.Model):
    """Model for contact form messages"""
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    attachment = models.ImageField(
        upload_to=contact_attachment_upload_path,
        blank=True,
        null=True,
        help_text="Upload an image to help us understand your issue"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Contact Message'
        verbose_name_plural = 'Contact Messages'
    
    def __str__(self):
        return f"{self.name} - {self.subject}"

    def attachment_preview(self):
        """Display attachment preview in admin"""
        if self.attachment:
            return mark_safe(
                f'<img src="{self.attachment.url}" width="200" height="200" '
                f'style="object-fit:contain; border-radius:5px;" />'
            )
        return "(No attachment)"

    attachment_preview.short_description = "Attachment Preview"

class PaymentTransaction(models.Model):
    """Track all payment-related transactions including refunds"""
    
    TRANSACTION_TYPES = [
        ('payment', 'Payment'),
        ('refund', 'Refund'),
        ('adjustment', 'Adjustment'),
    ]
    
    TRANSACTION_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    request = models.ForeignKey(
        DocumentRequest, 
        on_delete=models.CASCADE, 
        related_name='payment_transactions'
    )
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS, default='pending')
    reference_number = models.CharField(max_length=100, unique=True, blank=True)
    payment_method = models.CharField(max_length=20, blank=True)
    
    # Refund specific fields
    refund_reason = models.TextField(blank=True, null=True)
    refund_approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_refunds'
    )
    
    # Processing info
    processed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='processed_transactions'
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Payment Transaction'
        verbose_name_plural = 'Payment Transactions'
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.request.order_id} - ₱{self.amount}"
    
    def save(self, *args, **kwargs):
        if not self.reference_number:
            self.reference_number = self.generate_reference_number()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_reference_number():
        """Generate unique transaction reference"""
        prefix = datetime.now().strftime('%Y%m%d')
        unique = uuid.uuid4().hex[:6].upper()
        return f"TXN-{prefix}-{unique}"