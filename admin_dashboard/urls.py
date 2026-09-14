from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    path('', views.dashboard, name='admin_dash'),
    path('Admin-Approval-Center/', views.admin_approval_center, name='approval_center'),
    path('Admin-Approval-Center/<str:item_type>/<int:pk>/', views.admin_approval_details, name='approval_details'),
    
    path('Admin-Announcments/', views.admin_announcement, name='ad_announcement'),
    path('Admin-News-Update/', views.admin_news_update, name='ad_news_update'),
    path('Admin-Events/', views.admin_events, name='ad_events'),
    path('Admin-Downloadable-Forms/', views.admin_download_forms, name='ad_forms'),
    path('Admin-Gallery/', views.admin_gallery, name='ad_gallery'),
    path('Admin-Offices/', views.admin_offices, name='ad_offices'),
    path('Admin-Office-Representative/', views.admin_office_rep, name='ad_office_rep'),
    path('Admin-Services/', views.admin_services, name='ad_services'),
    path('Admin-Users/', views.admin_users, name='ad_users'),
    path('Admin-Roles-Permision/', views.admin_roles, name='ad_roles'),
    path('Admin-Homepage/', views.admin_homepage, name='ad_homepage'),
    path('Admin-Contact-information/', views.admin_contact_info, name='ad_contact_info'),
    path('Admin-Interactive-Map/', views.admin_interactive_map, name='ad_map'),
    path('Admin-Emergency-Contact/', views.admin_emergency_contact, name='ad_emergency_contact'),
    path('Admin-Website-setting/', views.admin_web_setting, name='ad_web_setting'),
    path('Admin-Analytics-Reports/', views.admin_analytics, name='ad_analytics'),
    path('Admin-Activity-Logs/', views.admin_activity_log, name='ad_activity_log'),
    path('Admin-System-Settings/', views.admin_system_setting, name='ad_system_settings'),

]