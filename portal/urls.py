from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('announcement/', views.announcement, name='announcement'),
    path('search/', views.site_search, name='site_search'),
    path('announcement/events-calendar/', views.events_calendar_partial, name='events_calendar_partial'),
    path('gallery/', views.gallery, name='gallery'),
    path('offices/', views.offices, name='offices'),
    path('about/', views.about, name='about'),
    path('history/', views.history, name='history'),
    path('contact/', views.contact, name='contact'),

    path('login/', views.login, name='login'),
    path('signup/', views.signup, name='signup'),
    path('send-signup-otp/', views.send_signup_otp_ajax, name='send_signup_otp'),

    path('logout/', views.logout, name='logout'),

    path('google-login-start/', views.google_login_start, name='google_login_start'),
    path('google-signup-start/', views.google_signup_start, name='google_signup_start'),

    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('send-reset-otp/', views.send_reset_otp_ajax, name='send_reset_otp'),
]