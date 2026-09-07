from django.urls import path
from . import views

app_name = 'office_dashboard'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('office-announcement', views.rep_announcement, name='rep_announce'),
    path('office-announcement/<int:pk>/edit', views.edit_announcement, name='edit_announcement'),
    path('office-announcement/<int:pk>/delete', views.delete_announcement, name='delete_announcement'),

    path('office-news&update', views.news_update, name='news_update'),
    path('office-news&update/<int:pk>/edit', views.edit_news, name='edit_news'),
    path('office-news&update/<int:pk>/delete', views.delete_news, name='delete_news'),
    
    path('office-events', views.events, name='event'),
    path('office-events/<int:pk>/edit', views.edit_event, name='edit_event'),
    path('office-events/<int:pk>/delete', views.delete_event, name='delete_event'),

    path('office-services', views.services, name='services'),
    path('office-downloadable-forms', views.downloadable_forms, name='downloadable_form'),
    
    path('office-gallery', views.gallery, name='gallery'),
    path('office-gallery/<int:pk>/delete', views.delete_photo, name='delete_photo'),

    path('office-profile', views.office_profile, name='profile'),
    path('office-directory', views.office_directory, name='directory'),
    path('office-location', views.office_location, name='location'),
    path('office-account', views.my_account, name='account'),
    path('office-change-password', views.change_pass, name='change_pass'),
    path('office-notifications', views.notification, name='notification'),
    path('office-log', views.activity_log, name='log'),

]
