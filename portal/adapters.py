from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse

from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import redirect

from admin_dashboard.models import SuperAdmin
from office_dashboard.models import OfficeRepresentative
from portal.models import CitizenProfile


class AccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        user = request.user
        if SuperAdmin.objects.filter(user=user).exists():
            return "/super-admin/"
        if OfficeRepresentative.objects.filter(user=user).exists():
            return "/office-dashboard/"
        return "/"


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        intent = request.session.get('google_intent')

        if sociallogin.is_existing:
            return

        email = sociallogin.user.email
        existing_user = User.objects.filter(email=email).first() if email else None

        if intent == 'login':
            if existing_user:
                return
            messages.error(request, "No account found for this Google account. Please sign up first.")
            raise ImmediateHttpResponse(redirect('login'))

        if intent == 'signup':
            if existing_user:
                messages.info(request, "You already have an account with this email — logging you in.")
                return

            request.session['google_prefill'] = {
                'first_name': sociallogin.user.first_name,
                'last_name': sociallogin.user.last_name,
                'email': email,
            }
            raise ImmediateHttpResponse(redirect('signup'))

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)

        if user.email and user.username != user.email:
            user.username = user.email
            user.save(update_fields=["username"])

        CitizenProfile.objects.get_or_create(user=user)
        return user

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)

        if user.email and user.username != user.email:
            user.username = user.email

        mobile_number = ""
        if form is not None:
            mobile_number = form.cleaned_data.get("mobile_number", "")
            first_name = form.cleaned_data.get("first_name")
            last_name = form.cleaned_data.get("last_name")
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name

        user.save()

        CitizenProfile.objects.get_or_create(user=user, defaults={"mobile_number": mobile_number})
        return user