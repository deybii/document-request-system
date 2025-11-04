from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.http import HttpResponse
from .forms import RegisterForm, LoginForm, DocumentRequestForm, ContactForm
from .models import DocumentRequest, UserProfile
from datetime import date, datetime
import uuid
import csv


def index(request):
    """Landing page with login/register"""
    if request.user.is_authenticated:
        # ✅ Redirect staff/admin users properly
        if request.user.is_staff or request.user.is_superuser:
            return redirect('admin_dashboard')
        return redirect('home')
    
    login_form = LoginForm()
    register_form = RegisterForm()
    
    if request.method == 'POST':
        if 'login_submit' in request.POST:
            login_form = LoginForm(request, data=request.POST)
            if login_form.is_valid():
                school_id = login_form.cleaned_data.get('username')
                password = login_form.cleaned_data.get('password')
                user = authenticate(username=school_id, password=password)
                
                if user is not None:
                    login(request, user)
                    display_name = user.get_full_name() or school_id
                    messages.success(request, f'✅ Welcome back, {display_name}!')
                    
                    # ✅ Redirect based on role
                    if user.is_staff or user.is_superuser:
                        return redirect('admin_dashboard')
                    else:
                        return redirect('home')
                else:
                    messages.error(request, '❌ Invalid School ID or password.')
            else:
                messages.error(request, '❌ Invalid School ID or password. Please check your credentials.')
        
        elif 'register_submit' in request.POST:
            register_form = RegisterForm(request.POST)
            if register_form.is_valid():
                user = register_form.save()
                login(request, user)
                messages.success(
                    request,
                    f'✅ Registration successful! Welcome, {user.get_full_name()}! '
                    f'Your account email is: {user.email}'
                )
                return redirect('home')
            else:
                for field, errors in register_form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field}: {error}')
    
    context = {
        'login_form': login_form,
        'register_form': register_form,
    }
    return render(request, 'index.html', context)


@login_required
def home(request):
    """User dashboard/home page"""
    recent_requests = DocumentRequest.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    total_requests = DocumentRequest.objects.filter(user=request.user).count()
    pending_requests = DocumentRequest.objects.filter(user=request.user, status='pending').count()
    ready_requests = DocumentRequest.objects.filter(user=request.user, ready_for_pickup=True, picked_up=False).count()
    completed_requests = DocumentRequest.objects.filter(user=request.user, status='completed').count()
    
    user_profile = None
    if hasattr(request.user, 'profile'):
        user_profile = request.user.profile
    
    # ✅ Get active request
    active_request = DocumentRequest.get_user_active_request(request.user)
    
    context = {
        'recent_requests': recent_requests,
        'total_requests': total_requests,
        'pending_requests': pending_requests,
        'ready_requests': ready_requests,
        'completed_requests': completed_requests,
        'user_profile': user_profile,
        'active_request': active_request,  # ✅ Pass to template
    }
    return render(request, 'home.html', context)

@login_required
def request_document(request):
    """Create a new document request with active request limit"""
    
    # ✅ Get active request first
    active_request = DocumentRequest.get_user_active_request(request.user)
    
    # ✅ Check if user already has an active request
    if active_request and request.method == 'POST':
        messages.warning(
            request,
            f'⚠️ You already have an active request (Order ID: <strong>{active_request.order_id}</strong>). '
            f'Status: <strong>{active_request.get_status_display()}</strong>. '
            f'Please wait until it is completed or rejected before submitting a new request.',
            extra_tags='safe'
        )
        # Don't redirect - just show the form with the error
    
    if request.method == 'POST' and not active_request:
        form = DocumentRequestForm(request.POST, user=request.user)
        if form.is_valid():
            doc_request = form.save(commit=False)
            doc_request.user = request.user
            
            if not doc_request.school_id and hasattr(request.user, 'profile'):
                doc_request.school_id = request.user.profile.school_id
            
            doc_request.save()
            
            if doc_request.payment_method == 'cash':
                messages.success(
                    request,
                    f'✅ Request submitted! Your Order ID is <strong>{doc_request.order_id}</strong>. '
                    f'Please pay ₱{doc_request.payment_amount} cash when picking up your document.',
                    extra_tags='safe'
                )
                return redirect('request_success', order_id=doc_request.order_id)
            else:
                messages.info(request, 'Please complete your payment to process your request.')
                return redirect('simulated_payment', order_id=doc_request.order_id)
        else:
            # Show form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = DocumentRequestForm(user=request.user)
    
    # ✅ Always get user's request history
    my_requests = DocumentRequest.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'form': form,
        'my_requests': my_requests,
        'active_request': active_request,  # ✅ Pass active request to template
    }
    return render(request, 'request.html', context)

@login_required
def simulated_payment(request, order_id):
    """Simulated payment page"""
    doc_request = get_object_or_404(DocumentRequest, order_id=order_id, user=request.user)
    
    if doc_request.payment_status == 'paid':
        messages.info(request, 'This order has already been paid.')
        return redirect('request_success', order_id=doc_request.order_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'simulate_success':
            doc_request.payment_status = 'paid'
            doc_request.payment_date = timezone.now()
            doc_request.payment_reference = f"SIM-{uuid.uuid4().hex[:8].upper()}"
            doc_request.save()
            
            messages.success(request, f'✅ Payment successful! Reference: {doc_request.payment_reference}')
            return redirect('request_success', order_id=doc_request.order_id)
        
        elif action == 'simulate_failure':
            doc_request.payment_status = 'failed'
            doc_request.save()
            
            messages.error(request, '❌ Payment failed! Please try again.')
            return redirect('simulated_payment', order_id=doc_request.order_id)
    
    context = {'doc_request': doc_request}
    return render(request, 'simulated_payment.html', context)


@login_required
def request_success(request, order_id):
    """Success page"""
    doc_request = get_object_or_404(DocumentRequest, order_id=order_id, user=request.user)
    context = {'doc_request': doc_request}
    return render(request, 'request_success.html', context)


@login_required
def my_requests(request):
    """View all user requests with enhanced filtering"""
    requests = DocumentRequest.objects.filter(user=request.user).order_by('-created_at')
    
    # Status filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        requests = requests.filter(status=status_filter)
    
    # Payment status filter
    payment_filter = request.GET.get('payment_status', '')
    if payment_filter:
        requests = requests.filter(payment_status=payment_filter)
    
    # Document type filter
    document_filter = request.GET.get('document_type', '')
    if document_filter:
        requests = requests.filter(document_type=document_filter)
    
    # Search query
    search_query = request.GET.get('search', '')
    if search_query:
        requests = requests.filter(
            Q(order_id__icontains=search_query) |
            Q(document_type__icontains=search_query)
        )
    
    # Date range filter
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            requests = requests.filter(created_at__date__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            requests = requests.filter(created_at__date__lte=date_to_obj)
        except ValueError:
            pass
    
    # Calculate statistics
    total_count = DocumentRequest.objects.filter(user=request.user).count()
    pending_count = DocumentRequest.objects.filter(user=request.user, status='pending').count()
    processing_count = DocumentRequest.objects.filter(user=request.user, status='processing').count()
    ready_count = DocumentRequest.objects.filter(user=request.user, status='ready').count()
    completed_count = DocumentRequest.objects.filter(user=request.user, status='completed').count()
    
    active_request = DocumentRequest.get_user_active_request(request.user)
    
    context = {
        'requests': requests,
        'status_filter': status_filter,
        'payment_filter': payment_filter,
        'document_filter': document_filter,
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'total_count': total_count,
        'pending_count': pending_count,
        'processing_count': processing_count,
        'ready_count': ready_count,
        'completed_count': completed_count,
        'active_request': active_request,  # ✅ Pass to template
    }
    return render(request, 'my_requests.html', context)


@login_required
def request_detail(request, order_id):
    """View request details"""
    doc_request = get_object_or_404(DocumentRequest, order_id=order_id, user=request.user)
    context = {'doc_request': doc_request}
    return render(request, 'request_detail.html', context)


def contact(request):
    """Contact form"""
    if request.method == 'POST':
        form = ContactForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Your message has been sent successfully!')
            return redirect('contact')
        else:
            messages.error(request, '❌ Please correct the errors in the form.')
    else:
        form = ContactForm()
    
    context = {'form': form}
    return render(request, 'contact.html', context)


def about(request):
    """About page"""
    return render(request, 'about.html')


@login_required
def logout_view(request):
    """Logout"""
    user_name = request.user.get_full_name() or request.user.username
    logout(request)
    messages.info(request, f'👋 Goodbye, {user_name}! You have been logged out.')
    return redirect('index')


# ========================================
# REGISTRAR/ADMIN VIEWS
# ========================================

@staff_member_required
def admin_dashboard(request):
    """Enhanced admin dashboard"""
    # Request Statistics
    total_requests = DocumentRequest.objects.count()
    pending_requests = DocumentRequest.objects.filter(status='pending').count()
    processing_requests = DocumentRequest.objects.filter(status='processing').count()
    ready_requests = DocumentRequest.objects.filter(status='ready').count()
    completed_requests = DocumentRequest.objects.filter(status='completed').count()
    rejected_requests = DocumentRequest.objects.filter(status='rejected').count()
    
    # Payment Statistics
    paid_requests = DocumentRequest.objects.filter(payment_status='paid').count()
    unpaid_requests = DocumentRequest.objects.filter(payment_status='unpaid').count()
    failed_payments = DocumentRequest.objects.filter(payment_status='failed').count()
    online_payments = DocumentRequest.objects.filter(payment_method='online').count()
    cash_payments = DocumentRequest.objects.filter(payment_method='cash').count()
    
    # Pickup Statistics
    ready_for_pickup = DocumentRequest.objects.filter(ready_for_pickup=True, picked_up=False).count()
    picked_up = DocumentRequest.objects.filter(picked_up=True).count()
    
    # User Statistics
    total_users = UserProfile.objects.count()
    student_users = UserProfile.objects.filter(role='student').count()
    alumni_users = UserProfile.objects.filter(role='alumni').count()
    faculty_users = UserProfile.objects.filter(role='faculty').count()
    verified_users = UserProfile.objects.filter(is_verified=True).count()
    unverified_users = UserProfile.objects.filter(is_verified=False).count()
    
    # Recent Activity
    recent_requests = DocumentRequest.objects.select_related('user').order_by('-created_at')[:10]
    recent_users = UserProfile.objects.select_related('user').order_by('-created_at')[:5]
    
    # Document Type Breakdown
    document_breakdown = DocumentRequest.objects.values('document_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Today's Statistics
    today = date.today()
    today_requests = DocumentRequest.objects.filter(created_at__date=today).count()
    today_payments = DocumentRequest.objects.filter(
        payment_status='paid',
        payment_date__date=today
    ).count()
    
    context = {
        'total_requests': total_requests,
        'pending_requests': pending_requests,
        'processing_requests': processing_requests,
        'ready_requests': ready_requests,
        'completed_requests': completed_requests,
        'rejected_requests': rejected_requests,
        'paid_requests': paid_requests,
        'unpaid_requests': unpaid_requests,
        'failed_payments': failed_payments,
        'online_payments': online_payments,
        'cash_payments': cash_payments,
        'ready_for_pickup': ready_for_pickup,
        'picked_up': picked_up,
        'recent_requests': recent_requests,
        'recent_users': recent_users,
        'document_breakdown': document_breakdown,
        'today_requests': today_requests,
        'today_payments': today_payments,
        'total_users': total_users,
        'student_users': student_users,
        'alumni_users': alumni_users,
        'faculty_users': faculty_users,
        'verified_users': verified_users,
        'unverified_users': unverified_users,
    }
    return render(request, 'admin_dashboard.html', context)


@staff_member_required
def admin_requests(request):
    """Admin view to manage document requests with advanced filtering and bulk actions"""
    
    # ====== HANDLE BULK ACTIONS (POST) ======
    if request.method == 'POST':
        bulk_action = request.POST.get('bulk_action')
        selected_ids = request.POST.get('selected_ids', '')
        
        if not selected_ids:
            messages.error(request, '❌ No requests selected.')
            return redirect('admin_requests')
        
        # Convert comma-separated IDs to list
        try:
            selected_ids_list = [int(id.strip()) for id in selected_ids.split(',') if id.strip()]
        except ValueError:
            messages.error(request, '❌ Invalid selection.')
            return redirect('admin_requests')
        
        if not selected_ids_list:
            messages.error(request, '❌ Invalid selection.')
            return redirect('admin_requests')
        
        # Get selected requests
        selected_requests = DocumentRequest.objects.filter(id__in=selected_ids_list)
        count = selected_requests.count()
        
        if count == 0:
            messages.error(request, '❌ No valid requests found.')
            return redirect('admin_requests')
        
        # ====== PROCESS BULK ACTION ======
        try:
            if bulk_action == 'mark_processing':
                selected_requests.update(status='processing')
                messages.success(request, f'✅ Successfully marked {count} request(s) as Processing.')
            
            elif bulk_action == 'mark_ready':
                selected_requests.update(status='ready', ready_for_pickup=True)
                messages.success(request, f'✅ Successfully marked {count} request(s) as Ready for Pickup.')
            
            elif bulk_action == 'mark_completed':
                selected_requests.update(
                    status='completed', 
                    picked_up=True,
                    picked_up_date=timezone.now()
                )
                messages.success(request, f'✅ Successfully marked {count} request(s) as Completed.')
            
            elif bulk_action == 'confirm_payment':
                updated = 0
                for req in selected_requests.filter(payment_status='unpaid'):
                    req.payment_status = 'paid'
                    req.payment_date = timezone.now()
                    req.payment_reference = f"BULK-{uuid.uuid4().hex[:8].upper()}"
                    req.save()
                    updated += 1
                messages.success(request, f'✅ Successfully confirmed payment for {updated} request(s).')
            
            elif bulk_action == 'reject':
                selected_requests.update(status='rejected')
                messages.warning(request, f'⚠️ Successfully rejected {count} request(s).')
            
            elif bulk_action == 'export_selected':
                # Export selected requests to CSV
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="requests_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
                
                writer = csv.writer(response)
                writer.writerow([
                    'Order ID', 'Student Name', 'Student ID', 'Email', 
                    'Document Type', 'Status', 'Payment Status', 
                    'Payment Method', 'Payment Amount', 'Created Date', 
                    'Ready for Pickup', 'Picked Up'
                ])
                
                for req in selected_requests:
                    writer.writerow([
                        req.order_id,
                        req.user.get_full_name(),
                        req.user.username,
                        req.user.email,
                        req.get_document_type_display(),
                        req.get_status_display(),
                        req.get_payment_status_display(),
                        req.get_payment_method_display(),
                        f"₱{req.payment_amount}",
                        req.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        'Yes' if req.ready_for_pickup else 'No',
                        'Yes' if req.picked_up else 'No'
                    ])
                
                return response
            
            else:
                messages.error(request, '❌ Invalid bulk action.')
        
        except Exception as e:
            messages.error(request, f'❌ Error processing bulk action: {str(e)}')
        
        # Preserve filters after bulk action
        query_params = request.GET.copy()
        if query_params:
            return redirect(f"{request.path}?{query_params.urlencode()}")
        return redirect('admin_requests')
    
    # ====== HANDLE FILTERS (GET) ======
    requests = DocumentRequest.objects.all().select_related('user', 'user__profile').order_by('-created_at')

    # Status filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        requests = requests.filter(status=status_filter)
    
    # Payment status filter
    payment_filter = request.GET.get('payment_status', '')
    if payment_filter:
        requests = requests.filter(payment_status=payment_filter)
    
    # Document type filter
    document_filter = request.GET.get('document_type', '')
    if document_filter:
        requests = requests.filter(document_type=document_filter)
    
    # Payment method filter
    payment_method_filter = request.GET.get('payment_method', '')
    if payment_method_filter:
        requests = requests.filter(payment_method=payment_method_filter)
    
    # Pickup status filter
    pickup_filter = request.GET.get('pickup_status', '')
    if pickup_filter == 'ready':
        requests = requests.filter(ready_for_pickup=True, picked_up=False)
    elif pickup_filter == 'picked_up':
        requests = requests.filter(picked_up=True)
    elif pickup_filter == 'not_ready':
        requests = requests.filter(ready_for_pickup=False, picked_up=False)
    
    # Search query
    search_query = request.GET.get('search', '')
    if search_query:
        requests = requests.filter(
            Q(order_id__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(document_type__icontains=search_query)
        )
    
    # Date range filter
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            requests = requests.filter(created_at__date__gte=date_from_obj)
        except ValueError:
            messages.warning(request, '⚠️ Invalid "from" date format. Use YYYY-MM-DD.')
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            requests = requests.filter(created_at__date__lte=date_to_obj)
        except ValueError:
            messages.warning(request, '⚠️ Invalid "to" date format. Use YYYY-MM-DD.')

    # Pagination
    paginator = Paginator(requests, 20)  # 20 requests per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ✅ Calculate counts for all statuses (for stats cards)
    all_requests = DocumentRequest.objects.all()
    pending_count = all_requests.filter(status='pending').count()
    processing_count = all_requests.filter(status='processing').count()
    ready_count = all_requests.filter(status='ready').count()
    completed_count = all_requests.filter(status='completed').count()
    rejected_count = all_requests.filter(status='rejected').count()
    
    # Payment counts
    paid_count = all_requests.filter(payment_status='paid').count()
    unpaid_count = all_requests.filter(payment_status='unpaid').count()
    
    # Total counts
    total_count = all_requests.count()
    filtered_count = requests.count()

    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'payment_filter': payment_filter,
        'document_filter': document_filter,
        'payment_method_filter': payment_method_filter,
        'pickup_filter': pickup_filter,
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'pending_count': pending_count,
        'processing_count': processing_count,
        'ready_count': ready_count,
        'completed_count': completed_count,
        'rejected_count': rejected_count,
        'paid_count': paid_count,
        'unpaid_count': unpaid_count,
        'total_count': total_count,
        'filtered_count': filtered_count,
    }

    return render(request, 'admin_requests.html', context)


@staff_member_required
def admin_users(request):
    """Manage user profiles with enhanced filtering"""
    profiles = UserProfile.objects.all().select_related('user').order_by('-created_at')
    
    # Role filter
    role_filter = request.GET.get('role', '')
    if role_filter:
        profiles = profiles.filter(role=role_filter)
    
    # Verification status filter
    verified_filter = request.GET.get('verified', '')
    if verified_filter == 'yes':
        profiles = profiles.filter(is_verified=True)
    elif verified_filter == 'no':
        profiles = profiles.filter(is_verified=False)
    
    # Search query
    search_query = request.GET.get('search', '')
    if search_query:
        profiles = profiles.filter(
            Q(school_id__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__username__icontains=search_query)
        )
    
    # Date range filter
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            profiles = profiles.filter(created_at__date__gte=date_from_obj)
        except ValueError:
            messages.warning(request, '⚠️ Invalid "from" date format. Use YYYY-MM-DD.')
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            profiles = profiles.filter(created_at__date__lte=date_to_obj)
        except ValueError:
            messages.warning(request, '⚠️ Invalid "to" date format. Use YYYY-MM-DD.')
    
    # Pagination
    paginator = Paginator(profiles, 20)  # 20 users per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # ✅ Calculate user statistics
    all_profiles = UserProfile.objects.all()
    verified_count = all_profiles.filter(is_verified=True).count()
    pending_count = all_profiles.filter(is_verified=False).count()
    student_count = all_profiles.filter(role='student').count()
    alumni_count = all_profiles.filter(role='alumni').count()
    faculty_count = all_profiles.filter(role='faculty').count()
    total_count = all_profiles.count()
    filtered_count = profiles.count()
    
    context = {
        'page_obj': page_obj,
        'role_filter': role_filter,
        'verified_filter': verified_filter,
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'verified_count': verified_count,
        'pending_count': pending_count,
        'student_count': student_count,
        'alumni_count': alumni_count,
        'faculty_count': faculty_count,
        'total_count': total_count,
        'filtered_count': filtered_count,
    }
    return render(request, 'admin_users.html', context)


@staff_member_required
def admin_request_detail(request, order_id):
    """View and manage single request"""
    doc_request = get_object_or_404(DocumentRequest, order_id=order_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'mark_processing':
            doc_request.status = 'processing'
            doc_request.save()
            messages.success(request, f'✅ Request {order_id} marked as Processing')
        
        elif action == 'mark_ready':
            doc_request.status = 'ready'
            doc_request.ready_for_pickup = True
            doc_request.save()
            messages.success(request, f'✅ Request {order_id} marked as Ready for Pickup')
        
        elif action == 'mark_picked_up':
            doc_request.picked_up = True
            doc_request.picked_up_date = timezone.now()
            doc_request.status = 'completed'
            doc_request.save()
            messages.success(request, f'✅ Request {order_id} marked as Picked Up')
        
        elif action == 'mark_paid':
            doc_request.payment_status = 'paid'
            doc_request.payment_date = timezone.now()
            doc_request.payment_reference = f"CASH-{uuid.uuid4().hex[:8].upper()}"
            doc_request.save()
            messages.success(request, f'✅ Cash payment confirmed for {order_id}')
        
        elif action == 'reject':
            doc_request.status = 'rejected'
            doc_request.save()
            messages.warning(request, f'⚠️ Request {order_id} rejected')
        
        return redirect('admin_request_detail', order_id=order_id)
    
    context = {'doc_request': doc_request}
    return render(request, 'admin_request_detail.html', context)


@staff_member_required
def admin_verify_user(request, profile_id):
    """Verify a user's profile"""
    profile = get_object_or_404(UserProfile, id=profile_id)
    profile.is_verified = not profile.is_verified
    profile.save()
    
    status = 'verified' if profile.is_verified else 'unverified'
    messages.success(request, f'✅ User {profile.school_id} has been {status}')
    
    # Preserve filters when returning to admin_users
    query_params = request.GET.copy()
    if query_params:
        return redirect(f"{reverse('admin_users')}?{query_params.urlencode()}")
    return redirect('admin_users')

@staff_member_required
def admin_edit_user(request, profile_id):
    """Edit user profile and account details"""
    profile = get_object_or_404(UserProfile, id=profile_id)
    user = profile.user
    
    if request.method == 'POST':
        # Update User model
        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name = request.POST.get('last_name', '').strip()
        user.email = request.POST.get('email', '').strip()
        
        # Update UserProfile model
        profile.role = request.POST.get('role', profile.role)
        profile.department = request.POST.get('department', '').strip()
        profile.course = request.POST.get('course', '').strip()
        profile.year_level = request.POST.get('year_level', '').strip()
        
        graduation_year = request.POST.get('graduation_year', '').strip()
        if graduation_year:
            try:
                profile.graduation_year = int(graduation_year)
            except ValueError:
                profile.graduation_year = None
        else:
            profile.graduation_year = None
        
        profile.is_verified = request.POST.get('is_verified') == 'on'
        
        try:
            user.save()
            profile.save()
            messages.success(
                request,
                f'✅ Successfully updated profile for {user.get_full_name()} ({profile.school_id})'
            )
            return redirect('admin_users')
        except Exception as e:
            messages.error(request, f'❌ Error updating user: {str(e)}')
    
    context = {'profile': profile}
    return render(request, 'admin_edit_user.html', context)


@staff_member_required
def admin_delete_user(request, profile_id):
    """Delete user and their profile"""
    profile = get_object_or_404(UserProfile, id=profile_id)
    user = profile.user
    
    if request.method == 'POST':
        user_name = user.get_full_name()
        school_id = profile.school_id
        
        # Check if user has any active requests
        active_requests = DocumentRequest.objects.filter(
            user=user,
            status__in=['pending', 'processing', 'ready']
        ).count()
        
        if active_requests > 0:
            messages.warning(
                request,
                f'⚠️ Cannot delete user {user_name} ({school_id}). '
                f'They have {active_requests} active request(s). '
                f'Please complete or reject their requests first.'
            )
            return redirect('admin_users')
        
        try:
            # Delete user (profile will be deleted via CASCADE)
            user.delete()
            messages.success(
                request,
                f'✅ Successfully deleted user: {user_name} ({school_id})'
            )
        except Exception as e:
            messages.error(request, f'❌ Error deleting user: {str(e)}')
    
    return redirect('admin_users')

@login_required
def user_profile(request):
    """View user's own profile"""
    if not hasattr(request.user, 'profile'):
        messages.error(request, '❌ Profile not found. Please contact administrator.')
        return redirect('home')
    
    profile = request.user.profile
    
    # Get user statistics
    total_requests = DocumentRequest.objects.filter(user=request.user).count()
    completed_requests = DocumentRequest.objects.filter(user=request.user, status='completed').count()
    active_request = DocumentRequest.get_user_active_request(request.user)
    
    context = {
        'profile': profile,
        'total_requests': total_requests,
        'completed_requests': completed_requests,
        'active_request': active_request,
    }
    return render(request, 'user_profile.html', context)


@login_required
def edit_profile(request):
    """Edit user's own profile"""
    if not hasattr(request.user, 'profile'):
        messages.error(request, '❌ Profile not found. Please contact administrator.')
        return redirect('home')
    
    profile = request.user.profile
    user = request.user
    
    if request.method == 'POST':
        # Update User model (limited fields)
        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name = request.POST.get('last_name', '').strip()
        
        # Email validation
        new_email = request.POST.get('email', '').strip()
        if new_email != user.email:
            if User.objects.filter(email=new_email).exclude(id=user.id).exists():
                messages.error(request, '❌ This email is already in use.')
                return redirect('edit_profile')
            user.email = new_email
        
        # Update UserProfile model (limited fields)
        profile.department = request.POST.get('department', '').strip()
        profile.course = request.POST.get('course', '').strip()
        profile.year_level = request.POST.get('year_level', '').strip()
        
        graduation_year = request.POST.get('graduation_year', '').strip()
        if graduation_year:
            try:
                profile.graduation_year = int(graduation_year)
            except ValueError:
                profile.graduation_year = None
        else:
            profile.graduation_year = None
        
        # Password change (optional)
        current_password = request.POST.get('current_password', '').strip()
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        
        if new_password:
            if not current_password:
                messages.error(request, '❌ Please enter your current password.')
                return redirect('edit_profile')
            
            if not user.check_password(current_password):
                messages.error(request, '❌ Current password is incorrect.')
                return redirect('edit_profile')
            
            if new_password != confirm_password:
                messages.error(request, '❌ New passwords do not match.')
                return redirect('edit_profile')
            
            if len(new_password) < 8:
                messages.error(request, '❌ Password must be at least 8 characters long.')
                return redirect('edit_profile')
            
            user.set_password(new_password)
            messages.success(request, '✅ Password updated successfully! Please log in again.')
        
        try:
            user.save()
            profile.save()
            
            if new_password:
                # Re-login after password change
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, user)
            
            messages.success(request, '✅ Profile updated successfully!')
            return redirect('user_profile')
        except Exception as e:
            messages.error(request, f'❌ Error updating profile: {str(e)}')
    
    context = {'profile': profile}
    return render(request, 'edit_profile.html', context)

@login_required
def cancel_request(request, order_id):
    """Allow users to cancel their own pending/processing requests"""
    doc_request = get_object_or_404(DocumentRequest, order_id=order_id, user=request.user)
    
    # Only allow cancellation if request is pending or processing
    if doc_request.status not in ['pending', 'processing']:
        messages.warning(
            request, 
            f'⚠️ Cannot cancel request {order_id}. '
            f'Status: {doc_request.get_status_display()}. '
            f'Only pending or processing requests can be cancelled.'
        )
        return redirect('request_detail', order_id=order_id)
    
    if request.method == 'POST':
        # Update request status to rejected/cancelled
        doc_request.status = 'rejected'
        doc_request.notes = f"{doc_request.notes}\n\n[CANCELLED BY USER on {timezone.now().strftime('%Y-%m-%d %H:%M')}]" if doc_request.notes else f"[CANCELLED BY USER on {timezone.now().strftime('%Y-%m-%d %H:%M')}]"
        doc_request.save()
        
        messages.success(
            request,
            f'✅ Request {order_id} has been cancelled successfully. '
            f'You can now submit a new request.',
            extra_tags='safe'
        )
        return redirect('my_requests')
    
    # If GET request, redirect to detail page
    return redirect('request_detail', order_id=order_id)