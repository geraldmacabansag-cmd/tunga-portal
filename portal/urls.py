from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('announcement/', views.announcement, name='announcement'),
    path('offices/', views.offices, name='offices'),
    path('about/', views.about, name='about'),
    path('history/', views.history, name='history'),
    path('contact/', views.contact, name='contact'),

    path('login/', views.login, name='login'),
    path('signup/', views.signup, name='signup'),

    path('logout/', views.logout, name='logout'),
]