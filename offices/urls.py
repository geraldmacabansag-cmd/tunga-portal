from django.urls import path
from . import views

app_name = 'offices'

urlpatterns = [
    path('mayor/', views.mayor, name='mayor'),
    path('forms/<int:pk>/fill/', views.fill_form, name='fill_form'),
    path('forms/<int:pk>/submit/', views.submit_form, name='submit_form'),
    path('forms/<int:pk>/view-pdf/', views.serve_form_pdf, name='view_pdf'),
    path('<str:slug>/', views.office_detail, name='office_detail'),
]