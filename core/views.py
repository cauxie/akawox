from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from .models import (
    UserProfile, AkawoGroup, GroupMember,
    Contribution, Payment, Withdrawal,
    Report, Transaction, Notification
)

import requests
import uuid
import json
import hashlib
import hmac


# ======================
# AUTH
# ======================

def index(request):
    return render(request, "index.html")


def signup_view(request):
    if request.method == "POST":
        username = request.POST["signup-username"]
        password = request.POST["signup-password1"]
        email = request.POST["signup-email"]

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username taken")
            return redirect("signup")

        user = User.objects.create_user(username=username, email=email, password=password)
        messages.success(request, "Account created")
        return redirect("login")

    return render(request, "signup.html")


def login_view(request):
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST["login-username"],
            password=request.POST["login-password"]
        )
        if user:
            auth_login(request, user)
            return redirect("dashboard")

        messages.error(request, "Invalid credentials")

    return render(request, "login.html")


@login_required
def dashboard_redirect(request):
    if AkawoGroup.objects.filter(organizer=request.user).exists():
        return redirect("organizer_dashboard")

    if GroupMember.objects.filter(user=request.user).exists():
        return redirect("contributor_dashboard")

    return redirect("select_role")


# ======================
# GROUPS
# ======================

@login_required
def create_group(request):
    if request.method == "POST":
        group = AkawoGroup.objects.create(
            group_name=request.POST.get("name"),
            organizer=request.user,
            contribution_cycle=request.POST.get("contribution_type"),
            contribution_amount=request.POST.get("contribution_amount"),
        )
        GroupMember.objects.create(user=request.user, group=group)
        messages.success(request, "Group created")
    return redirect("organizer_dashboard")


@login_required
def join_group(request):
    if request.method == "POST":
        code = request.POST.get("referral_code")

        try:
            group = AkawoGroup.objects.get(referral_code=code)

            if GroupMember.objects.filter(user=request.user, group=group).exists():
                messages.info(request, "Already joined")
            else:
                GroupMember.objects.create(user=request.user, group=group)
                messages.success(request, "Joined successfully")

        except AkawoGroup.DoesNotExist:
            messages.error(request, "Invalid code")

    return redirect("contributor_dashboard")


# ======================
# DASHBOARDS
# ======================

@login_required
def organizer_dashboard(request):
    groups = AkawoGroup.objects.filter(organizer=request.user)
    return render(request, "organizer_dashboard.html", {"groups": groups})


@login_required
def contributor_dashboard(request):
    groups = GroupMember.objects.filter(user=request.user)
    return render(request, "contributor_dashboard.html", {"groups": groups})


# ======================
# PAYSTACK HELPERS
# ======================

def initialize_payment(email, amount, reference, callback_url):
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "email": email,
        "amount": int(amount * 100),  # convert to kobo
        "reference": reference,
        "callback_url": callback_url,
    }

    res = requests.post(
        "https://api.paystack.co/transaction/initialize",
        headers=headers,
        json=data
    )

    return res.json()


# ======================
# CONTRIBUTOR PAYMENT
# ======================

@login_required
def start_contribution_payment(request, member_id):
    member = get_object_or_404(GroupMember, id=member_id)

    reference = str(uuid.uuid4())

    Payment.objects.create(
        contributor=member,
        amount=member.group.contribution_amount,
        reference=reference,
        status="initiated"
    )

    response = initialize_payment(
        email=member.user.email,
        amount=member.group.contribution_amount,
        reference=reference,
        callback_url=request.build_absolute_uri("/payment/callback/")
    )

    if response.get("status"):
        return redirect(response["data"]["authorization_url"])

    return HttpResponse("Payment init failed")


# ======================
# ORGANIZER PAYS FOR CONTRIBUTOR
# ======================

@login_required
def pay_for_contributor(request, group_id):
    if request.method == "POST":
        contributor_id = request.POST.get("contributor_id")

        member = get_object_or_404(GroupMember, id=contributor_id, group_id=group_id)

        reference = f"org_{uuid.uuid4().hex[:10]}"

        Payment.objects.create(
            contributor=member,
            amount=member.group.contribution_amount,
            reference=reference,
            status="initiated"
        )

        response = initialize_payment(
            email=request.user.email,  # organizer pays
            amount=member.group.contribution_amount,
            reference=reference,
            callback_url=request.build_absolute_uri("/payment/callback/")
        )

        if response.get("status"):
            return redirect(response["data"]["authorization_url"])

    return redirect("organizer_dashboard")


# ======================
# PAYMENT CALLBACK
# ======================

def payment_callback(request):
    reference = request.GET.get("reference")

    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"
    }

    res = requests.get(
        f"https://api.paystack.co/transaction/verify/{reference}",
        headers=headers
    )

    data = res.json()

    if data.get("status") and data["data"]["status"] == "success":
        payment = get_object_or_404(Payment, reference=reference)

        if payment.status != "success":
            payment.status = "success"
            payment.save()

            Contribution.objects.create(
                member=payment.contributor,
                amount=payment.amount,
                paid_by="organizer" if reference.startswith("org_") else "self",
                payment_reference=reference,
                status="completed"
            )

    return render(request, "success.html")


# ======================
# WEBHOOK (backup)
# ======================

@csrf_exempt
def paystack_webhook(request):
    payload = request.body

    signature = request.META.get("HTTP_X_PAYSTACK_SIGNATURE")
    secret = settings.PAYSTACK_SECRET_KEY.encode()

    expected = hmac.new(secret, payload, hashlib.sha512).hexdigest()

    if signature != expected:
        return HttpResponse(status=400)

    data = json.loads(payload)

    if data.get("event") == "charge.success":
        reference = data["data"]["reference"]

        try:
            payment = Payment.objects.get(reference=reference)

            if payment.status != "success":
                payment.status = "success"
                payment.save()

        except Payment.DoesNotExist:
            pass

    return HttpResponse(status=200)


# ======================
# SIMPLE VIEWS
# ======================

@login_required
def contributor_withdrawals(request, group_id):
    member = get_object_or_404(GroupMember, user=request.user, group_id=group_id)
    withdrawals = Withdrawal.objects.filter(member=member)
    return render(request, "contributor_withdrawals.html", {"withdrawals": withdrawals})


def terms_and_conditions(request):
    return render(request, "terms.html")


def privacy_policy(request):
    return render(request, "policy.html")
