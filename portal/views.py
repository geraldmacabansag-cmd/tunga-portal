from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from .models import CitizenProfile
from office_dashboard.models import OfficeRepresentative, Announcement, NewsUpdate, Event, Photo
from admin_dashboard.models import SuperAdmin, EmergencyContact
from django.utils import timezone

# Create your views here.
def home(request):
    home_announcements = list(
        Announcement.objects.filter(status='published')
        .order_by('-date_posted', '-created_at')[:3]
    )
    for a in home_announcements:
        a.display_date = a.date_posted or a.created_at.date()

    upcoming_event = (
        Event.objects.filter(status='published', event_date__gte=timezone.localdate())
        .order_by('event_date')
        .first()
    )

    latest_news = (
        NewsUpdate.objects.filter(status='published')
        .select_related('representative__office')
        .order_by('-date_published', '-created_at')
        .first()
    )

    gallery_photos = list(
        Photo.objects.filter(status='published')
        .order_by('-created_at')[:8]
    )

    return render(request, "portal/home.html", {
        "emergency_contacts": EmergencyContact.objects.all(),
        "home_announcements": home_announcements,
        "upcoming_event": upcoming_event,
        "latest_news": latest_news,
        "gallery_photos": gallery_photos,
    })

def announcement(request):
    announcements = list(
        Announcement.objects.filter(status='published')
        .select_related('representative__office')
        .order_by('-date_posted', '-created_at')[:5]
    )
    for a in announcements:
        a.display_date = a.date_posted or a.created_at.date()

    news_items = list(
        NewsUpdate.objects.filter(status='published')
        .select_related('representative__office')
        .order_by('-date_published', '-created_at')[:5]
    )
    for n in news_items:
        n.display_date = n.date_published or n.created_at.date()

    return render(request, "portal/announcements.html", {
        "announcements": announcements,
        "news_items": news_items,
    })

def offices(request):
    return render(request, "offices/offices.html")

def about(request):
    return render(request, "portal/about.html")

def history(request):
    return render(request, "portal/history.html")

def contact(request):
    return render(request, "portal/contactus.html")

def signup(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        mobile_number = request.POST.get("mobile_number", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not all([first_name, last_name, email, password, confirm_password]):
            messages.error(request, "Please fill in all required fields.")
            return render(request, "account/signup.html")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, "account/signup.html")

        if User.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
            return render(request, "account/signup.html")

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        CitizenProfile.objects.create(user=user, mobile_number=mobile_number)

        messages.success(request, "Account created successfully. Please log in.")
        return redirect("login")

    return render(request, "account/signup.html")


def login(request):
    next_url = request.POST.get("next") or request.GET.get("next") or "home"

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")

        user = authenticate(request, username=email, password=password)
        if user is not None:
            auth_login(request, user)
            if SuperAdmin.objects.filter(user=user).exists():
                return redirect("admin_dashboard:admin_dash")
            if OfficeRepresentative.objects.filter(user=user).exists():
                return redirect("office_dashboard:dashboard")
            return redirect(next_url or "home")

        messages.error(request, "Invalid email or password.")
        return render(request, "account/login.html", {"next": next_url})

    return render(request, "account/login.html", {"next": next_url})

def logout(request):
    auth_logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("home")


