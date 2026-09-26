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
    path('office-services/<int:service_pk>/steps/save', views.save_process_steps, name='save_process_steps'),
    path('office-services/<int:pk>/delete', views.delete_service, name='delete_service'),
    path('office-services/<int:service_pk>/requirements/save', views.save_requirements, name='save_requirements'),
    path('office-services/<int:service_pk>/legal-basis/save', views.save_legal_basis, name='save_legal_basis'),
    path('office-services/<int:service_pk>/schedule-of-service/save', views.save_schedule_of_service, name='save_schedule_of_service'),
    path('office-services/<int:service_pk>/reminders/save', views.save_reminders, name='save_reminders'),
    path('office-services/<int:service_pk>/forms/<int:pk>/delete', views.delete_service_form, name='delete_service_form'),
    path('office-services/<int:pk>/edit', views.edit_service, name='edit_service'),
    
    path('office-downloadable-forms', views.downloadable_forms, name='downloadable_form'),
    path('office-downloadable-forms/upload', views.upload_form, name='upload_form'),
    path('office-downloadable-forms/<int:pk>/edit', views.edit_form, name='edit_form'),
    path('office-downloadable-forms/<int:pk>/delete', views.delete_form, name='delete_form'),
    path('office-downloadable-forms/<int:pk>/download', views.download_form, name='download_form'),
    path('office-downloadable-forms/<int:pk>/fields', views.form_fields_builder, name='form_fields_builder'),
    path('office-downloadable-forms/<int:pk>/fields/save', views.save_form_fields, name='save_form_fields'),
    
    path('office-gallery', views.gallery, name='gallery'),
    path('office-gallery/<int:pk>/delete', views.delete_photo, name='delete_photo'),
    path('office-gallery/albums/create', views.create_album, name='create_album'),
    path('office-gallery/albums/<int:pk>/delete', views.delete_album, name='delete_album'),
    path('office-gallery/albums/<int:pk>/rename', views.rename_album, name='rename_album'),

    path('office-profile', views.office_profile, name='profile'),
    path('office-profile/services/add', views.add_service, name='add_service'),
    path('office-profile/charter/<str:field>/edit', views.edit_office_charter_field, name='edit_office_charter_field'),

    path('office-profile/toggle-visibility', views.office_toggle_visibility, name='toggle_visibility'),

    path('office-directory', views.office_directory, name='directory'),
    path('office-location', views.office_location, name='location'),
    path('office-page-settings', views.office_page_settings, name='page_settings'),
    path('office-page-settings/reorder-services', views.office_reorder_services, name='reorder_services'),

    path('office-account', views.my_account, name='account'),
    path('office-change-password', views.change_pass, name='change_pass'),
    path('office-notifications', views.notification, name='notification'),
    path('office-notifications/<int:pk>/read', views.mark_notification_read, name='mark_notification_read'),
    path('office-notifications/mark-all-read', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('office-notifications/<int:pk>/delete', views.delete_notification, name='delete_notification'),

    path('office-log', views.activity_log, name='log'),

]