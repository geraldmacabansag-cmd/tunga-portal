"""
URL configuration for tunga_portal project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from tungamap import views as tungamap_views

# Tunga Map data API (used by the map on the Super Admin "Interactive Map" page).
tungamap_api = ([
    path('api/places/', tungamap_views.places, name='places'),
    path('api/places/<int:pk>/', tungamap_views.place_detail, name='place_detail'),
], 'tungamap')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('portal.urls')),
    path('offices/', include('offices.urls')),
    path('office-dashboard/', include('office_dashboard.urls')),
    path('super-admin/', include('admin_dashboard.urls')),
    path('accounts/', include('allauth.urls')),
    path('map/', include(tungamap_api)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)