# core/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum

import requests
import uuid
import json
import hmac
import hashlib
from datetime import date

from .models import (
    UserProfile, AkawoGroup, GroupMember,
    Contribution, Payment, Withdrawal,
    Transaction
)
from .utils import generate_referral_code


# =========================
# AUTH
# =========================

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
            return redirect("dashboard_redirect")

        messages.error(request, "Invalid login")

    return render(request, "login.html")


@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


# =========================
# ROLE
# =========================

@login_required
def select_role_view(request):
    if request.method == "POST":
        role = request.POST.get("selected_role")
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.role = role
        profile.save()

        return redirect("dashboard_redirect")

    return render(request, "role.html")


@login_required
def dashboard_redirect(request):
    profile = request.user.profile

    if profile.role == "organizer":
        return redirect("organizer_dashboard")

    if GroupMember.objects.filter(user=request.user).exists():
        return redirect("contributor_dashboard")

    return redirect("join_group")


# =========================
# GROUPS
# =========================

@login_required
def create_group(request):
    if request.method == "POST":
        group = AkawoGroup.objects.create(
            group_name=request.POST.get("name"),
            organizer=request.user,
            contribution_cycle=request.POST.get("contribution_type"),
            contribution_amount=request.POST.get("amount"),
            referral_code=generate_referral_code(),
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

            return redirect("contributor_dashboard")

        except AkawoGroup.DoesNotExist:
            messages.error(request, "Invalid code")

    return render(request, "join_group.html")


# =========================
# DASHBOARDS
# =========================

@login_required
def organizer_dashboard(request):
    groups = AkawoGroup.objects.filter(organizer=request.user)
    return render(request, "organizer_dashboard.html", {"groups": groups})


@login_required
def contributor_dashboard(request):
    memberships = GroupMember.objects.filter(user=request.user).select_related("group")
    groups = [m.group for m in memberships]

    return render(request, "contributor_dashboard.html", {"groups": groups})


# =========================
# PAYMENTS (CORE LOGIC)
# =========================

@login_required
def start_contribution_payment(request, member_id):
    member = get_object_or_404(GroupMember, id=member_id)

    amount = int(member.group.contribution_amount) * 100
    reference = str(uuid.uuid4())

    Payment.objects.create(
        member=member,
        amount=amount / 100,
        reference=reference,
        payment_method="paystack"
    )

    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "email": member.user.email,
        "amount": amount,
        "reference": reference,
        "callback_url": request.build_absolute_uri("/payment/callback/"),
    }

    res = requests.post("https://api.paystack.co/transaction/initialize", json=data, headers=headers)
    response = res.json()

    if response.get("status"):
        return redirect(response["data"]["authorization_url"])

    return HttpResponse("Payment error")


# =========================
# ORGANIZER CASH PAYMENT
# =========================

@login_required
def pay_for_contributor(request, group_id):
    if request.method == "POST":
        member = get_object_or_404(GroupMember, id=request.POST.get("member_id"))

        amount = float(request.POST.get("amount"))

        Contribution.objects.create(
            member=member,
            amount=amount,
            paid_by="organizer",
            status="completed"
        )

        Transaction.objects.create(
            user=member.user,
            amount=amount,
            transaction_type="contribution",
            status="success"
        )

        messages.success(request, "Payment recorded")

    return redirect("organizer_dashboard")


# =========================
# WEBHOOK (ONLY ONE)
# =========================

@csrf_exempt
def paystack_webhook(request):
    payload = request.body
    signature = request.META.get("HTTP_X_PAYSTACK_SIGNATURE")

    computed = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode(),
        payload,
        hashlib.sha512
    ).hexdigest()

    if signature != computed:
        return HttpResponse(status=400)

    data = json.loads(payload)

    if data["event"] == "charge.success":
        ref = data["data"]["reference"]

        try:
            payment = Payment.objects.get(reference=ref)

            if payment.status != "success":
                payment.status = "success"
                payment.save()

                Contribution.objects.create(
                    member=payment.member,
                    amount=payment.amount,
                    paid_by="self",
                    status="completed"
                )

        except Payment.DoesNotExist:
            pass

    return HttpResponse(status=200)


# =========================
# CONTRIBUTIONS VIEW
# =========================

@login_required
def group_contributions(request, group_id):
    group = get_object_or_404(AkawoGroup, id=group_id)
    member = get_object_or_404(GroupMember, user=request.user, group=group)

    contributions = Contribution.objects.filter(member=member).order_by("-created_at")

    return render(request, "contributions.html", {
        "group": group,
        "contributions": contributions
    })


# =========================
# WITHDRAWALS
# =========================

@login_required
def contributor_withdrawals(request, group_id):
    group = get_object_or_404(AkawoGroup, id=group_id)
    member = get_object_or_404(GroupMember, user=request.user, group=group)

    withdrawals = Withdrawal.objects.filter(member=member)

    return render(request, "withdrawals.html", {
        "withdrawals": withdrawals
    })


# =========================
# TRANSACTIONS
# =========================

@login_required
def transaction_history(request):
    txs = Transaction.objects.filter(user=request.user).order_by("-created_at")

    return render(request, "transactions.html", {"transactions": txs})
