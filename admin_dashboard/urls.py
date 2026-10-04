from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    path('', views.dashboard, name='admin_dash'),
    path('Admin-Approval-Center/', views.admin_approval_center, name='approval_center'),
    path('Admin-Approval-Center/<str:item_type>/<int:pk>/', views.admin_approval_details, name='approval_details'),
    
    path('Admin-Announcments/', views.admin_announcement, name='ad_announcement'),
    path('Admin-Announcement/create/', views.admin_create_announcement, name='admin_create_announcement'),
    path('Admin-Announcement/<int:pk>/edit/', views.admin_edit_announcement, name='admin_edit_announcement'),
    path('Admin-Announcement/<int:pk>/delete/', views.admin_delete_announcement, name='admin_delete_announcement'),
    path('Admin-Announcement/<int:pk>/toggle-pin/', views.admin_announcement_toggle_pin, name='admin_announcement_toggle_pin'),

    path('Admin-News-Update/', views.admin_news_update, name='ad_news_update'),
    path('Admin-News-Update/<int:pk>/save/', views.admin_news_save, name='admin_news_save'),
    path('Admin-News-Update/<int:pk>/delete/', views.admin_news_delete, name='admin_news_delete'),
    
    path('Admin-Events/', views.admin_events, name='ad_events'),
    path('Admin-Events/<int:pk>/save/', views.admin_event_save, name='admin_event_save'),
    path('Admin-Events/<int:pk>/delete/', views.admin_event_delete, name='admin_event_delete'),

    path('Admin-Downloadable-Forms/', views.admin_download_forms, name='ad_forms'),
    path('Admin-Downloadable-Forms/<int:pk>/save/', views.admin_form_save, name='admin_form_save'),
    path('Admin-Downloadable-Forms/<int:pk>/delete/', views.admin_form_delete, name='admin_form_delete'),
    path('Admin-Downloadable-Forms/<int:pk>/download/', views.admin_download_form_file, name='admin_download_form_file'),
    path('Admin-Downloadable-Forms/<int:pk>/view/', views.admin_view_form_file, name='admin_view_form_file'),
    path('Admin-Downloadable-Forms/<int:pk>/fields/', views.admin_form_fields_builder, name='admin_form_fields_builder'),
    path('Admin-Downloadable-Forms/<int:pk>/fields/save/', views.admin_save_form_fields, name='admin_save_form_fields'),

    path('Admin-Gallery/', views.admin_gallery, name='ad_gallery'),
    path('Admin-Gallery/<int:pk>/', views.admin_album_detail, name='ad_album_detail'),
    path('Admin-Gallery/photo/<int:pk>/archive/', views.admin_photo_archive_toggle, name='admin_photo_archive'),
    path('Admin-Gallery/photo/<int:pk>/delete/', views.admin_photo_delete, name='admin_photo_delete'),
    path('Admin-Gallery/photo/<int:pk>/save/', views.admin_photo_save, name='admin_photo_save'),
    path('Admin-Gallery/album/<int:pk>/toggle-featured/', views.admin_album_toggle_featured, name='admin_album_toggle_featured'),

    path('Admin-Offices/', views.admin_offices, name='ad_offices'),
    path('Admin-Offices/<int:pk>/edit/', views.admin_office_edit, name='admin_office_edit'),
    path('Admin-Offices/<int:pk>/toggle-visibility/', views.admin_office_toggle_visibility, name='admin_office_toggle_visibility'),
    
    path('Admin-Office-Representative/', views.admin_office_rep, name='ad_office_rep'),
    path('Admin-Office-Representative/<int:pk>/toggle-active/', views.admin_rep_toggle_active, name='admin_rep_toggle_active'),
    path('Admin-Office-Representative/assign/', views.admin_assign_representative, name='admin_assign_representative'),
    path('Admin-Office-Representative/<int:pk>/replace-user/', views.admin_rep_replace_user, name='admin_rep_replace_user'),

    path('Admin-Services/', views.admin_services, name='ad_services'),
    path('Admin-Services/<int:pk>/', views.admin_service_detail, name='ad_service_detail'),
    path('Admin-Services/<int:pk>/delete/', views.admin_service_delete, name='ad_service_delete'),
    path('Admin-Services/toggle-editing/', views.admin_toggle_service_editing, name='admin_toggle_service_editing'),

    path('Admin-Users/', views.admin_users, name='ad_users'),
    path('Admin-Users/<int:pk>/toggle-active/', views.admin_user_toggle_active, name='admin_user_toggle_active'),

    path('Admin-Roles-Permision/', views.admin_roles, name='ad_roles'),

    path('Admin-My-Account/', views.admin_my_account, name='admin_account'),
    path('Admin-Change-Password/', views.admin_change_password, name='admin_change_pass'),

    path('Admin-Homepage/', views.admin_homepage, name='ad_homepage'),
    path('Admin-Homepage/quick-link/<int:pk>/save/', views.admin_quicklink_save, name='admin_quicklink_save'),
    path('Admin-Homepage/quick-link/create/save/', lambda request: views.admin_quicklink_save(request, pk=0), name='admin_quicklink_create'),
    path('Admin-Homepage/quick-link/<int:pk>/delete/', views.admin_quicklink_delete, name='admin_quicklink_delete'),
    path('Admin-Homepage/quick-link/<int:pk>/move-up/', lambda request, pk: views.admin_quicklink_move(request, pk, 'up'), name='admin_quicklink_move_up'),
    path('Admin-Homepage/quick-link/<int:pk>/move-down/', lambda request, pk: views.admin_quicklink_move(request, pk, 'down'), name='admin_quicklink_move_down'),

    path('Admin-About-Page/', views.admin_about_page, name='ad_about_page'),
    path('Admin-About-Page/milestone/<int:pk>/save/', views.admin_about_milestone_save, name='admin_about_milestone_save'),
    path('Admin-About-Page/milestone/create/save/', lambda request: views.admin_about_milestone_save(request, pk=0), name='admin_about_milestone_create'),
    path('Admin-About-Page/milestone/<int:pk>/delete/', views.admin_about_milestone_delete, name='admin_about_milestone_delete'),
    path('Admin-About-Page/official/<int:pk>/save/', views.admin_about_official_save, name='admin_about_official_save'),
    path('Admin-About-Page/official/create/save/', lambda request: views.admin_about_official_save(request, pk=0), name='admin_about_official_create'),
    path('Admin-About-Page/official/<int:pk>/delete/', views.admin_about_official_delete, name='admin_about_official_delete'),
    path('Admin-About-Page/barangay/<int:pk>/save/', views.admin_about_barangay_save, name='admin_about_barangay_save'),
    path('Admin-About-Page/barangay/create/save/', lambda request: views.admin_about_barangay_save(request, pk=0), name='admin_about_barangay_create'),
    path('Admin-About-Page/barangay/<int:pk>/delete/', views.admin_about_barangay_delete, name='admin_about_barangay_delete'),
    path('Admin-About-Page/reset-defaults/', views.admin_about_reset_defaults, name='admin_about_reset_defaults'),


    path('Admin-Interactive-Map/', views.admin_interactive_map, name='ad_map'),

    path('Admin-Emergency-Contact/', views.admin_emergency_contact, name='ad_emergency_contact'),
    path('Admin-Emergency-Contact/<int:pk>/save/', views.admin_contact_save, name='admin_contact_save'),
    path('Admin-Emergency-Contact/create/save/', lambda request: views.admin_contact_save(request, pk=0), name='admin_contact_create'),
    path('Admin-Emergency-Contact/<int:pk>/delete/', views.admin_contact_delete, name='admin_contact_delete'),

    path('Admin-Website-setting/', views.admin_web_setting, name='ad_web_setting'),
    path('Admin-Analytics-Reports/', views.admin_analytics, name='ad_analytics'),
    path('Admin-Analytics-Reports/export/office-activity/', views.admin_export_office_activity, name='admin_export_office_activity'),
    path('Admin-Analytics-Reports/export/approval-history/', views.admin_export_approval_history, name='admin_export_approval_history'),
    path('Admin-Activity-Logs/', views.admin_activity_log, name='ad_activity_log'),
    path('Admin-System-Settings/', views.admin_system_setting, name='ad_system_settings'),

    path('Admin-Archive/', views.admin_archive, name='ad_archive'),
    path('Admin-Archive/<str:item_type>/<int:pk>/restore/', views.admin_archive_restore, name='admin_archive_restore'),
    path('Admin-Archive/<str:item_type>/<int:pk>/delete-permanent/', views.admin_archive_delete_permanent, name='admin_archive_delete_permanent'),

]