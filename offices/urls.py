from django.urls import path
from . import views

urlpatterns = [
    path('mayor/', views.mayor, name='mayor'),
]