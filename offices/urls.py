from django.urls import path
from . import views

app_name = 'offices'

urlpatterns = [
    path('forms/<int:pk>/fill/', views.fill_form, name='fill_form'),
    path('forms/<int:pk>/submit/', views.submit_form, name='submit_form'),
    path('forms/<int:pk>/view-pdf/', views.serve_form_pdf, name='view_pdf'),
    path('forms/<int:pk>/view/', views.view_form, name='view_form'),
    path('forms/submissions/<int:pk>/download/', views.download_filled, name='download_filled'),
    path('<str:slug>/', views.office_detail, name='office_detail'),
]