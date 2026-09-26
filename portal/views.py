from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from .models import CitizenProfile
from office_dashboard.models import OfficeRepresentative, Announcement, NewsUpdate, Event, Photo
from admin_dashboard.models import SuperAdmin, EmergencyContact
from django.utils import timezone
from django.http import JsonResponse
from .models import CitizenProfile, EmailOTP
from .otp_utils import send_signup_otp
from django.http import JsonResponse
from .otp_utils import send_signup_otp, send_password_reset_otp
from offices.models import Office

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

OFFICE_CARD_STYLE = {
    "office-of-the-mayor": ("fa-solid fa-user-tie", "navy", "icons/mayors_office.jpg"),
    "sangguniang-bayan-sb": ("fa-solid fa-gavel", "purple", "icons/sangguniangbayan.png"),
    "municipal-treasurer's-office": ("fa-solid fa-coins", "red", "icons/mun._treasurers_office.jpg"),
    "municipal-assessor's-office": ("fa-regular fa-clipboard", "purple", "icons/mun._assessors_office.jpg"),
    "municipal-accounting-office": ("fa-solid fa-calculator", "navy", "icons/oma.png"),
    "municipal-budget-office": ("fa-solid fa-chart-pie", "green2", "icons/budgetoffice.png"),
    "municipal-planning-and-development-coordinator": ("fa-solid fa-map", "green", "icons/MPDC.jpg"),
    "municipal-civil-registrar's-office": ("fa-solid fa-file-signature", "navy", "icons/omcr.jpg"),
    "municipal-health-office": ("fa-solid fa-house-medical", "green", "icons/mun._health_office.jpg"),
    "municipal-social-welfare-and-development-office-mswdo": ("fa-solid fa-hand-holding-heart", "red", "icons/mun._social_welfare_dev._office.jpg"),
    "municipal-engineering-office": ("fa-solid fa-hard-hat", "navy", "icons/mun._engineering_office.jpg"),
    "municipal-agriculture-office": ("fa-solid fa-seedling", "orange", "icons/mun._agri._office.jpg"),
    "business-permits-and-licensing-office-bplo": ("fa-solid fa-briefcase", "gold", "icons/bplo.png"),
    "human-resource-management-office-hrmo": ("fa-solid fa-users", "purple", "icons/humanresource.png"),
    "municipal-disaster-risk-reduction-management": ("fa-solid fa-triangle-exclamation", "navy", "icons/MDRRMO.jpg"),
    "municipal-environment-and-natural-resources-office": ("fa-regular fa-building", "green2", "icons/mun._environment_office.jpg"),
    "local-youth-development-office": ("fa-solid fa-people-group", "gold", "icons/lydo.png"),
    "municipal-tourism-office": ("fa-solid fa-compass", "gold", "icons/mto.png"),
    "office-of-the-bac-and-the-bac-secretariat": ("fa-solid fa-file-contract", "purple", "icons/oBAC.png"),
    "office-of-the-general-services": ("fa-solid fa-briefcase", "navy", "icons/officeofthegeneralservices.png"),
}
OFFICE_CARD_DEFAULT = ("fa-solid fa-landmark", "navy", None)


def offices(request):
    office_list = (
        Office.objects
        .exclude(slug="lgu-super-admin")
        .filter(is_visible=True)
        .order_by("name")
    )
    for office in office_list:
        icon, color, icon_image = OFFICE_CARD_STYLE.get(office.slug, OFFICE_CARD_DEFAULT)
        office.card_icon = icon
        office.card_color = color
        office.card_image = icon_image

    return render(request, "offices/offices.html", {
        "office_list": office_list,
    })

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

    prefill = request.session.pop("google_prefill", None) or {}
    return render(request, "account/signup.html", {"prefill": prefill})

def send_signup_otp_ajax(request):
    if request.method != "POST" or request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({"success": False, "error": "Invalid request."}, status=400)

    email = request.POST.get("email", "").strip().lower()
    if not email:
        return JsonResponse({"success": False, "error": "Please enter an email address first."}, status=400)

    if User.objects.filter(email=email).exists():
        return JsonResponse({"success": False, "error": "An account with this email already exists."}, status=400)

    success, error = send_signup_otp(email)
    if success:
        return JsonResponse({"success": True})
    return JsonResponse({"success": False, "error": error or "Could not send the code. Please try again."}, status=500)

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

def google_login_start(request):
    request.session['google_intent'] = 'login'
    return redirect('google_login')


def google_signup_start(request):
    request.session['google_intent'] = 'signup'
    return redirect('google_login')

def forgot_password(request):
    if request.method == "POST":
        identifier = request.POST.get("identifier", "").strip()
        otp_code = request.POST.get("otp_code", "").strip()
        new_password = request.POST.get("new_password", "")
        confirm_password = request.POST.get("confirm_password", "")

        user = (User.objects.filter(email__iexact=identifier).first()
                or User.objects.filter(username__iexact=identifier).first())

        if not user:
            messages.error(request, "No account found with that email or username.")
            return render(request, "account/forgot_password.html", {"identifier": identifier})

        if not otp_code:
            messages.error(request, "Please enter the verification code sent to your email.")
            return render(request, "account/forgot_password.html", {"identifier": identifier})

        if not EmailOTP.verify(user.email, otp_code):
            messages.error(request, "That verification code is incorrect or has expired. Please request a new one.")
            return render(request, "account/forgot_password.html", {"identifier": identifier})

        if not new_password or not confirm_password:
            messages.error(request, "Please enter and confirm your new password.")
            return render(request, "account/forgot_password.html", {"identifier": identifier})

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, "account/forgot_password.html", {"identifier": identifier})

        user.set_password(new_password)
        user.save()

        messages.success(request, "Your password has been reset. Please log in with your new password.")
        return redirect("login")

    return render(request, "account/forgot_password.html")


def send_reset_otp_ajax(request):
    if request.method != "POST" or request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({"success": False, "error": "Invalid request."}, status=400)

    identifier = request.POST.get("identifier", "").strip()
    if not identifier:
        return JsonResponse({"success": False, "error": "Please enter your email or username first."}, status=400)

    user = (User.objects.filter(email__iexact=identifier).first()
            or User.objects.filter(username__iexact=identifier).first())
    if not user:
        return JsonResponse({"success": False, "error": "No account found with that email or username."}, status=400)

    success, error = send_password_reset_otp(user.email)
    if success:
        return JsonResponse({"success": True})
    return JsonResponse({"success": False, "error": error or "Could not send the code. Please try again."}, status=500)
