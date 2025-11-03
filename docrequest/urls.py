from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('home/', views.home, name='home'),
    path('logout/', views.logout_view, name='logout'),
    path('request/', views.request_document, name='request'),
    path('request/payment/<str:order_id>/', views.simulated_payment, name='simulated_payment'),
    path('request/success/<str:order_id>/', views.request_success, name='request_success'),
    path('my-requests/', views.my_requests, name='my_requests'),
    path('request/detail/<str:order_id>/', views.request_detail, name='request_detail'),
    path('contact/', views.contact, name='contact'),
    path('about/', views.about, name='about'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/requests/', views.admin_requests, name='admin_requests'),
    path('dashboard/users/', views.admin_users, name='admin_users'),
    path('dashboard/request/<str:order_id>/', views.admin_request_detail, name='admin_request_detail'),
    path('dashboard/user/verify/<int:profile_id>/', views.admin_verify_user, name='admin_verify_user'),
]