from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    path('', views.dashboard, name='admin_dash'),
    path('Admin-Approval-Center/', views.admin_approval_center, name='approval_center'),
    path('Admin-Approval-Center/<str:item_type>/<int:pk>/', views.admin_approval_details, name='approval_details'),
    
    path('Admin-Announcments/', views.admin_announcement, name='ad_announcement'),
    path('Admin-News-Update/', views.admin_news_update, name='ad_news_update'),
    path('Admin-News-Update/<int:pk>/save/', views.admin_news_save, name='admin_news_save'),
    path('Admin-News-Update/<int:pk>/delete/', views.admin_news_delete, name='admin_news_delete'),
    
    path('Admin-Events/', views.admin_events, name='ad_events'),
    path('Admin-Events/<int:pk>/save/', views.admin_event_save, name='admin_event_save'),
    path('Admin-Events/<int:pk>/delete/', views.admin_event_delete, name='admin_event_delete'),

    path('Admin-Downloadable-Forms/', views.admin_download_forms, name='ad_forms'),

    path('Admin-Gallery/', views.admin_gallery, name='ad_gallery'),
    path('Admin-Gallery/<int:pk>/', views.admin_album_detail, name='ad_album_detail'),
    path('Admin-Gallery/photo/<int:pk>/archive/', views.admin_photo_archive_toggle, name='admin_photo_archive'),
    path('Admin-Gallery/photo/<int:pk>/delete/', views.admin_photo_delete, name='admin_photo_delete'),

    path('Admin-Offices/', views.admin_offices, name='ad_offices'),
    path('Admin-Office-Representative/', views.admin_office_rep, name='ad_office_rep'),
    path('Admin-Office-Representative/<int:pk>/toggle-active/', views.admin_rep_toggle_active, name='admin_rep_toggle_active'),

    path('Admin-Services/', views.admin_services, name='ad_services'),
    path('Admin-Services/<int:pk>/', views.admin_service_detail, name='ad_service_detail'),
    path('Admin-Services/<int:pk>/delete/', views.admin_service_delete, name='ad_service_delete'),

    path('Admin-Users/', views.admin_users, name='ad_users'),
    path('Admin-Users/<int:pk>/toggle-active/', views.admin_user_toggle_active, name='admin_user_toggle_active'),

    path('Admin-Roles-Permision/', views.admin_roles, name='ad_roles'),
    path('Admin-Homepage/', views.admin_homepage, name='ad_homepage'),
    path('Admin-Contact-information/', views.admin_contact_info, name='ad_contact_info'),
    path('Admin-Interactive-Map/', views.admin_interactive_map, name='ad_map'),

    path('Admin-Emergency-Contact/', views.admin_emergency_contact, name='ad_emergency_contact'),
    path('Admin-Emergency-Contact/<int:pk>/save/', views.admin_contact_save, name='admin_contact_save'),
    path('Admin-Emergency-Contact/create/save/', lambda request: views.admin_contact_save(request, pk=0), name='admin_contact_create'),
    path('Admin-Emergency-Contact/<int:pk>/delete/', views.admin_contact_delete, name='admin_contact_delete'),

    path('Admin-Website-setting/', views.admin_web_setting, name='ad_web_setting'),
    path('Admin-Analytics-Reports/', views.admin_analytics, name='ad_analytics'),
    path('Admin-Activity-Logs/', views.admin_activity_log, name='ad_activity_log'),
    path('Admin-System-Settings/', views.admin_system_setting, name='ad_system_settings'),

]