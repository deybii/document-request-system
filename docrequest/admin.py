from django.contrib import admin
from .models import DocumentRequest, ContactMessage, UserProfile
from django.utils.html import format_html
from django.utils import timezone
import uuid

# ========================================
# Admin Actions for Document Requests
# ========================================

@admin.action(description="✅ Mark selected requests as Picked Up")
def mark_as_picked_up(modeladmin, request, queryset):
    queryset.update(picked_up=True, picked_up_date=timezone.now(), status='completed')
    modeladmin.message_user(request, f"{queryset.count()} request(s) marked as picked up successfully.")

@admin.action(description="📦 Mark as Ready for Pickup")
def mark_ready_for_pickup(modeladmin, request, queryset):
    queryset.update(ready_for_pickup=True, status='ready')
    modeladmin.message_user(request, f"{queryset.count()} request(s) marked as ready for pickup.")

@admin.action(description="💳 Simulate Payment Success")
def simulate_payment_success(modeladmin, request, queryset):
    for obj in queryset:
        obj.payment_status = 'paid'
        obj.payment_date = timezone.now()
        obj.payment_reference = f"SIM-{uuid.uuid4().hex[:8].upper()}"
        obj.save()
    modeladmin.message_user(request, f"{queryset.count()} payment(s) simulated successfully.")

@admin.action(description="❌ Simulate Payment Failure")
def simulate_payment_failure(modeladmin, request, queryset):
    queryset.update(payment_status='failed')
    modeladmin.message_user(request, f"{queryset.count()} payment(s) marked as failed.")


# ========================================
# Admin Actions for User Profiles
# ========================================

@admin.action(description="✅ Verify Selected Users")
def verify_users(modeladmin, request, queryset):
    queryset.update(is_verified=True)
    modeladmin.message_user(request, f"{queryset.count()} user(s) verified successfully.")

@admin.action(description="❌ Unverify Selected Users")
def unverify_users(modeladmin, request, queryset):
    queryset.update(is_verified=False)
    modeladmin.message_user(request, f"{queryset.count()} user(s) unverified.")


# ========================================
# UserProfile Admin
# ========================================

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        'school_id',
        'get_user_name',
        'get_email_display',
        'role',
        'department',
        'course',
        'year_level',
        'is_verified',
        'created_at'
    ]
    list_filter = ['role', 'is_verified', 'department', 'year_level', 'created_at']
    search_fields = [
        'school_id',
        'user__first_name',
        'user__last_name',
        'user__email',
        'department',
        'course'
    ]
    list_editable = ['is_verified']
    list_display_links = ['school_id', 'get_user_name']
    readonly_fields = ['user', 'created_at', 'updated_at', 'get_email_display']
    actions = [verify_users, unverify_users]
    
    fieldsets = (
        ('✅ Verification Status', {
            'fields': ('is_verified',),
            'description': 'Verify user identity before allowing document requests'
        }),
        ('👤 User Information', {
            'fields': ('user', 'school_id', 'role', 'get_email_display')
        }),
        ('🎓 Academic Information', {
            'fields': ('department', 'course', 'year_level', 'graduation_year'),
            'classes': ('collapse',)
        }),
        ('🕒 Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['-created_at']
    
    # Custom display methods
    
    def get_user_name(self, obj):
        """Display user's full name with link"""
        full_name = obj.user.get_full_name()
        if full_name:
            return format_html(
                '<strong>{}</strong>',
                full_name
            )
        return obj.user.username
    get_user_name.short_description = 'Name'
    get_user_name.admin_order_field = 'user__first_name'
    
    def get_email_display(self, obj):
        """Display user's email as clickable link"""
        return format_html(
            '<a href="mailto:{}" style="color: #0073aa;">{}</a>',
            obj.user.email,
            obj.user.email
        )
    get_email_display.short_description = 'Email'
    get_email_display.admin_order_field = 'user__email'


# ========================================
# DocumentRequest Admin
# ========================================

@admin.register(DocumentRequest)
class DocumentRequestAdmin(admin.ModelAdmin):
    list_display = [
        'order_id_display',
        'get_user_info',
        'document_type',
        'payment_method_display',
        'payment_status_display',
        'status',
        'ready_for_pickup',
        'picked_up',
        'created_at'
    ]
    list_editable = ['status', 'ready_for_pickup', 'picked_up']
    list_display_links = ['order_id_display', 'get_user_info']
    
    actions = [
        mark_as_picked_up,
        mark_ready_for_pickup,
        simulate_payment_success,
        simulate_payment_failure
    ]
    
    list_filter = [
        'status',
        'payment_status',
        'payment_method',
        'document_type',
        'ready_for_pickup',
        'picked_up',
        'created_at'
    ]
    
    search_fields = [
        'order_id',
        'user__username',
        'user__email',
        'user__first_name',
        'user__last_name',
        'school_id',
        'section',
        'course'
    ]
    
    readonly_fields = [
        'order_id',
        'created_at',
        'updated_at',
        'user',
        'payment_reference',
        'payment_date',
        'get_user_profile_link'
    ]
    
    fieldsets = (
        ('📋 Order Information', {
            'fields': ('order_id', 'user', 'get_user_profile_link', 'document_type', 'purpose', 'notes'),
            'classes': ('wide',)
        }),
        ('📊 Status', {
            'fields': ('status',)
        }),
        ('🎓 School Information', {
            'fields': ('school_id', 'section', 'course', 'school_year', 'graduation_year'),
            'classes': ('collapse',)
        }),
        ('💳 Payment Info (Simulated)', {
            'fields': (
                'payment_method',
                'payment_status',
                'payment_amount',
                'payment_reference',
                'payment_date'
            ),
            'description': '⚠️ This is a simulated payment system - no real money is charged'
        }),
        ('📦 Physical Document Delivery', {
            'fields': ('ready_for_pickup', 'picked_up', 'picked_up_date'),
            'description': 'Mark when the physical document is ready for pickup'
        }),
        ('🕒 Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['-created_at']

    # Custom display methods
    
    def order_id_display(self, obj):
        """Display Order ID with prominent styling"""
        return format_html(
            '<strong style="color: #0073aa; font-family: monospace; font-size: 13px;">{}</strong>',
            obj.order_id
        )
    order_id_display.short_description = 'Order ID'
    order_id_display.admin_order_field = 'order_id'
    
    def get_user_info(self, obj):
        """Display user with School ID and role"""
        if hasattr(obj.user, 'profile'):
            role_badge = {
                'student': '🎓',
                'alumni': '👨‍🎓',
                'faculty': '👨‍🏫'
            }
            icon = role_badge.get(obj.user.profile.role, '👤')
            verified = '✅' if obj.user.profile.is_verified else '⚠️'
            
            return format_html(
                '{} <strong>{}</strong><br>'
                '<small style="color: #666;">School ID: {}</small> {}',
                icon,
                obj.user.get_full_name() or obj.user.username,
                obj.user.profile.school_id,
                verified
            )
        return obj.user.username
    get_user_info.short_description = 'User'
    get_user_info.admin_order_field = 'user__username'
    
    def get_user_profile_link(self, obj):
        """Link to user's profile in admin"""
        if hasattr(obj.user, 'profile'):
            from django.urls import reverse
            url = reverse('admin:docrequest_userprofile_change', args=[obj.user.profile.id])
            return format_html(
                '<a href="{}" style="color: #0073aa;">👤 View User Profile</a>',
                url
            )
        return 'No profile'
    get_user_profile_link.short_description = 'User Profile'

    def payment_method_display(self, obj):
        """Display payment method with icon"""
        icons = {
            'online': '💳',
            'cash': '💵'
        }
        colors = {
            'online': '#0073aa',
            'cash': '#46b450'
        }
        return format_html(
            '<span style="color: {};">{} {}</span>',
            colors.get(obj.payment_method, '#000'),
            icons.get(obj.payment_method, ''),
            obj.get_payment_method_display()
        )
    payment_method_display.short_description = 'Payment Method'
    
    def payment_status_display(self, obj):
        """Display payment status with color coding"""
        status_labels = {
            'unpaid': '<span style="color: orange; font-weight: bold;">⏳ Unpaid</span>',
            'paid': '<span style="color: green; font-weight: bold;">✅ Paid</span>',
            'failed': '<span style="color: red; font-weight: bold;">❌ Failed</span>',
        }
        display = status_labels.get(obj.payment_status, obj.payment_status)
        
        # Add reference if paid
        if obj.payment_status == 'paid' and obj.payment_reference:
            display += f'<br><small style="color: #666;">Ref: {obj.payment_reference}</small>'
        
        return format_html(display)
    payment_status_display.short_description = 'Payment Status'

    def ready_for_pickup_display(self, obj):
        """Display ready for pickup status"""
        if obj.ready_for_pickup:
            return format_html('<span style="color: green; font-weight: bold;">✅ Ready</span>')
        return format_html('<span style="color: red;">❌ Not Ready</span>')
    ready_for_pickup_display.short_description = 'Ready for Pickup'
    
    def picked_up_display(self, obj):
        """Display pickup status"""
        if obj.picked_up:
            date_text = ''
            if obj.picked_up_date:
                date_text = f'<br><small style="color: #666;">{obj.picked_up_date.strftime("%b %d, %Y")}</small>'
            return format_html(
                '<span style="color: green; font-weight: bold;">✅ Picked Up</span>{}',
                date_text
            )
        return format_html('<span style="color: orange;">⏳ Waiting</span>')
    picked_up_display.short_description = 'Pickup Status'


# ========================================
# ContactMessage Admin
# ========================================

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'email', 'subject', 'has_attachment', 'created_at']
    readonly_fields = ['created_at', 'id', 'attachment_preview']

    fieldsets = (
        ('Message Info', {
            'fields': ('id', 'name', 'email', 'subject', 'message')
        }),
        ('Attachment', {
            'fields': ('attachment', 'attachment_preview')
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )

    ordering = ['-created_at']

    def has_attachment(self, obj):
        return bool(obj.attachment)
    has_attachment.boolean = True
    has_attachment.short_description = 'Has Attachment'

    def attachment_preview(self, obj):
        if obj.attachment:
            file_url = obj.attachment.url
            file_name = obj.attachment.name.split('/')[-1]
            
            if any(ext in file_name.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                return format_html(
                    '<a href="{}" target="_blank">'
                    '<img src="{}" width="150" style="border-radius:5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">'
                    '</a>',
                    file_url,
                    file_url
                )
            else:
                return format_html(
                    '<a href="{}" target="_blank" style="color:#0073aa; text-decoration:none;">'
                    '📥 Download: {}</a>',
                    file_url,
                    file_name
                )
        return format_html('<span style="color: #999;">(No attachment)</span>')
    attachment_preview.short_description = "Preview"