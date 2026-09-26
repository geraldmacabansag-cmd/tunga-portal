from django.urls import path
from . import views

urlpatterns = [
    path('mayor/', views.mayor, name='mayor'),
    path('<str:slug>/', views.office_detail, name='office_detail'),
]