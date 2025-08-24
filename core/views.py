# core/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import IntegrityError
from .models import UserProfile, AkawoGroup, Report, ContributionHistory, GroupMember, Contribution, Payment, Withdrawal
from .utils import generate_referral_code
from datetime import datetime, date
import requests
import uuid
import hashlib
import hmac
import json
from django.http import HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from io import BytesIO
import qrcode
from .models import Payout, CustomPayout
from django.shortcuts import get_object_or_404
from .models import Transaction



@login_required
def create_group(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        contribution_type = request.POST.get('contribution_type')
        photo = request.FILES.get('photo')
        contribution_amount = request.POST.get('contribution_amount')
        withdrawal_schedule = request.POST.get('withdrawal_schedule')

        group = AkawoGroup.objects.create(
            group_name=name,
            organizer=request.user,
            contribution_cycle=contribution_type,
            photo=photo,
            referral_code=generate_referral_code(),
            contribution_amount=contribution_amount,
            withdrawal_schedule=withdrawal_schedule
        )
        group.members.add(request.user)
        messages.success(request, 'Group created successfully.')
        return redirect('organizer_dashboard')
    return redirect('organizer_dashboard')

def update_group_cycle(group):
    today = date.today()
    first_of_month = date(today.year, today.month, 1)

    if group.current_cycle_month != first_of_month:
        for member in GroupMember.objects.filter(group=group):
            ContributionHistory.objects.create(
                group=group,
                member=member,
                amount=0,
                status="unpaid",
                period=group.current_cycle_month or today,
            )
        group.monthly_total = 0
        group.unpaid_count = GroupMember.objects.filter(group=group).count()
        group.current_cycle_month = first_of_month
        group.save()

def index(request):
    return render(request, 'index.html')

def signup_view(request):
    if request.method == "POST":
        username = request.POST["signup-username"]
        password1 = request.POST["signup-password1"]
        password2 = request.POST["signup-password2"]
        email = request.POST["signup-email"]
        first_name = request.POST["signup-firstname"]
        last_name = request.POST["signup-lastname"]

        # Check if passwords match
        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return render(request, "signup.html")

        # Check for existing username
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username is already taken.")
            return render(request, "signup.html")

        # Check for existing email
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email is already in use.")
            return render(request, "signup.html")

        try:
            user = User.objects.create_user(username=username, email=email, password=password1)
            user.first_name = first_name
            user.last_name = last_name
            user.save()
            messages.success(request, "Account created. Please log in.")
            return redirect("login")
        except IntegrityError:
            messages.error(request, "An error occurred. Try again.")
            return render(request, "signup.html")

    return render(request, "signup.html")

def login_view(request):
    if request.method == "POST":
        username = request.POST["login-username"]
        password = request.POST["login-password"]

        user = authenticate(request, username=username, password=password)
        if user:
            auth_login(request, user)
            return redirect('select_role')
        else:
            messages.error(request, 'Invalid credentials.')
            return render(request, 'login.html')

    return render(request, 'login.html')

@login_required
def select_role_view(request):
    if request.method == "POST":
        role = request.POST.get("selected_role")
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.role = role
        profile.save()

        if role == "organizer":
            return redirect('organizer_dashboard')
        else:
            return redirect('contributor_dashboard')

    return render(request, 'role.html')

@login_required
def organizer_dashboard(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        contribution_type = request.POST.get('contribution_type')
        photo = request.FILES.get('photo')

        group = AkawoGroup.objects.create(
            group_name=name,
            organizer=request.user,
            contribution_cycle=contribution_type,
            photo=photo,
            referral_code=generate_referral_code()
        )
        group.members.add(request.user)
        messages.success(request, 'Group created successfully.')
        return redirect('organizer_dashboard')
    
    

    groups = AkawoGroup.objects.filter(organizer=request.user).order_by('-created_at')
    return render(request, 'organizer_dashboard.html', {'groups': groups})


@login_required
def organizer_dash(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        contribution_type = request.POST.get('contribution_type')
        photo = request.FILES.get('photo')

        group = AkawoGroup.objects.create(
            group_name=name,
            organizer=request.user,
            contribution_cycle=contribution_type,
            photo=photo,
            referral_code=generate_referral_code()
        )
        group.members.add(request.user)
        messages.success(request, 'Group created successfully.')
        return redirect('organizer_dash')
    
    

    groups = AkawoGroup.objects.filter(organizer=request.user).order_by('-created_at')
    return render(request, 'organizer_dash.html', {'groups': groups})


@login_required
def group_manage_view(request):
    groups = AkawoGroup.objects.filter(organizer=request.user).order_by('-created_at')
    return render(request, 'group_manage.html', {'groups': groups})

@login_required
def manage_page(request, group_id):
    group = get_object_or_404(AkawoGroup, id=group_id, organizer=request.user)
    update_group_cycle(group)
    return render(request, 'manage.html', {'group': group})

@login_required
def group_detail(request, group_id):
    group = get_object_or_404(AkawoGroup, id=group_id, organizer=request.user)
    return render(request, 'group_detail.html', {'group': group})

@login_required
def remove_member(request, group_id, user_id):
    group = get_object_or_404(AkawoGroup, id=group_id, organizer=request.user)
    member = get_object_or_404(GroupMember, group=group, user_id=user_id)
    member.delete()
    return redirect('manage_page', group_id=group.id)



@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def account_settings(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "upload_avatar" and request.FILES.get("profile_picture"):
            profile.image = request.FILES["profile_picture"]
            profile.save()

        elif action == "remove_avatar":
            profile.image.delete(save=True)

        elif action == "delete_account":
            request.user.delete()
            logout(request)
            return redirect("signup")

        else:
            request.user.first_name = request.POST.get("first_name", "")
            request.user.last_name = request.POST.get("last_name", "")
            request.user.save()
            profile.phone_number = request.POST.get("phone_number", "")
            profile.save()

        return redirect("account_settings")

    return render(request, "account_settings.html", {"user": request.user})

@login_required
def organizer_reports(request):
    groups = AkawoGroup.objects.filter(organizer=request.user).order_by('-created_at')
    return render(request, 'organizer_reports.html', {'groups': groups})

@login_required
def reports_page(request, group_id):
    group = get_object_or_404(AkawoGroup, id=group_id, organizer=request.user)
    reports = Report.objects.filter(group=group).order_by('-created_at')
    return render(request, 'reports.html', {'group': group, 'reports': reports})

@login_required
def send_reminder(request, group_id):
    group = get_object_or_404(AkawoGroup, id=group_id)
    members = GroupMember.objects.filter(group=group)

    for member in members:
        print(f"Reminder sent to: {member.user.email}")

    messages.success(request, "Reminders sent to all group members.")
    return redirect('manage_page', group_id=group_id)

@login_required
def pay_for_contributor(request, group_id):
    if request.method == "POST":
        contributor_id = request.POST.get('contributor_id')
        amount = int(request.POST.get('amount')) * 100

        contributor = GroupMember.objects.get(id=contributor_id, group_id=group_id)
        reference = f"pay_{uuid.uuid4().hex[:10]}"

        Payment.objects.create(
            contributor=contributor,
            amount=amount / 100,
            reference=reference,
            status='initiated'
        )

        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }
        data = {
            "email": contributor.user.email,
            "amount": amount,
            "reference": reference,
            "callback_url": request.build_absolute_uri("/payment/callback/"),
        }

        response = requests.post("https://api.paystack.co/transaction/initialize", json=data, headers=headers)
        res_data = response.json()

        if res_data.get("status"):
            return redirect(res_data["data"]["authorization_url"])
        else:
            return render(request, "error.html", {"message": res_data.get("message", "Something went wrong.")})

@csrf_exempt
def paystack_webhook(request):
    payload = request.body
    signature = request.META.get('HTTP_X_PAYSTACK_SIGNATURE', '')
    secret = settings.PAYSTACK_SECRET_KEY.encode()
    expected_signature = hmac.new(secret, payload, hashlib.sha512).hexdigest()

    if signature != expected_signature:
        return HttpResponse(status=400)

    data = json.loads(payload)
    event = data.get('event')
    payment_data = data.get('data', {})

    if event == "charge.success":
        reference = payment_data.get('reference')
        try:
            payment = Payment.objects.get(reference=reference)
            if payment.status != "success":
                payment.status = "success"
                payment.save()

                Contribution.objects.create(
                    member=payment.contributor,
                    amount=payment.amount,
                    paid_by="webhook",
                    payment_reference=payment.reference,
                    status="completed"
                )
        except Payment.DoesNotExist:
            pass

    return HttpResponse(status=200)

def payment_callback(request):
    reference = request.GET.get('reference')

    if not reference:
        return render(request, "error.html", {"message": "Missing reference."})

    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
    }
    verify_url = f"https://api.paystack.co/transaction/verify/{reference}"
    response = requests.get(verify_url, headers=headers)
    res_data = response.json()

    if res_data.get("status") and res_data["data"]["status"] == "success":
        try:
            payment = Payment.objects.get(reference=reference)
            if payment.status != "success":
                payment.status = "success"
                payment.save()
                Contribution.objects.create(
                    member=payment.contributor,
                    amount=payment.amount,
                    paid_by="organizer",
                    payment_reference=payment.reference,
                    status="completed"
                )
        except Payment.DoesNotExist:
            return render(request, "error.html", {"message": "Payment not found."})

        return render(request, "success.html", {"message": "Payment verified and contribution recorded."})

    return render(request, "error.html", {"message": "Verification failed."})


@login_required
def organizer_contribution(request):
    groups = AkawoGroup.objects.filter(organizer=request.user)
    return render(request, 'organizer_contribution.html', {'groups': groups})




@login_required
def organizer_withdrawal(request):
    groups = AkawoGroup.objects.filter(organizer=request.user)
    return render(request, 'organizer_withdrawal.html', {
        'groups': groups
    })
    
  
def group_withdrawals(request, group_id):
    group = get_object_or_404(AkawoGroup, id=group_id, organizer=request.user)
    payouts = Payout.objects.filter(group=group).order_by('-paid_at')

    return render(request, 'withdrawals.html', {
        'group': group,
        'payouts': payouts,
    })

@login_required
def join_group(request):
    user = request.user
    if GroupMember.objects.filter(user=user).exists():
        return redirect('contributor_dashboard')

    if request.method == 'POST':
        code = request.POST.get('referral_code')
        try:
            group = AkawoGroup.objects.get(referral_code=code)
            GroupMember.objects.create(user=user, group=group)
            return redirect('contributor_dashboard')
        except AkawoGroup.DoesNotExist:
            return render(request, 'join_group.html', {'error': 'Invalid group code'})

    return render(request, 'join_group.html')

@login_required
def role_redirect(request):
    profile = request.user.profile
    if profile.role == 'organizer':
        return redirect('organizer_dashboard')
    elif profile.role == 'contributor':
        if GroupMember.objects.filter(user=request.user).exists():
            return redirect('contributor_dashboard')
        return redirect('join_group')


# Re-add this to fix the missing view issue in urls.py


# Re-add group_manage_list if you're linking to group_manage.html
@login_required
def group_manage_list(request):
    groups = AkawoGroup.objects.filter(organizer=request.user)
    return render(request, 'group_manage.html', {'groups': groups})

# Re-add this for group management page
@login_required
def manage_group(request, group_id):
    group = get_object_or_404(AkawoGroup, id=group_id, organizer=request.user)
    return render(request, 'manage.html', {'group': group})




def contributor_wallet(request):
    group_member = get_object_or_404(GroupMember, user=request.user)
    context = {
        "group_member": group_member,
        "group": group_member.group,
    }
    return render(request, "contributor_wallet.html", context)

def start_contribution_payment(request, member_id):
    group_member = get_object_or_404(GroupMember, id=member_id)

    # Unique reference
    reference = str(uuid.uuid4())

    amount = 500000  # in kobo = ₦5000.00
    callback_url = request.build_absolute_uri("/wallet/payment/callback/")

    # Prepare Paystack init
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "email": group_member.user.email,
        "amount": amount,
        "reference": reference,
        "callback_url": callback_url,
    }

    res = requests.post("https://api.paystack.co/transaction/initialize", headers=headers, data=json.dumps(data))
    response_data = res.json()

    if response_data.get("status"):
        Contribution.objects.create(member=group_member, amount=amount/100, reference=reference)
        return redirect(response_data["data"]["authorization_url"])
    else:
        return HttpResponse("Error initializing payment", status=400)

# Webhook endpoint to confirm payment
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def paystack_webhook(request):
    payload = json.loads(request.body)
    event = payload.get('event')

    if event == 'charge.success':
        data = payload['data']
        reference = data['reference']
        try:
            contribution = Contribution.objects.get(reference=reference)
            contribution.status = 'success'
            contribution.save()

            # Update wallet total
            contribution.member.total_contributed += contribution.amount
            contribution.member.save()

        except Contribution.DoesNotExist:
            pass

    return HttpResponse(status=200)

@login_required
def contributor_dashboard(request):
    user_groups = GroupMember.objects.filter(user=request.user).select_related('group')
    groups = [gm.group for gm in user_groups]
    group_count = len(groups)
    return render(request, 'contributor_dashboard.html', {'groups': groups, 'group_count': group_count})



@login_required
def contributor_dash(request):
    user_groups = GroupMember.objects.filter(user=request.user).select_related('group')
    groups = [gm.group for gm in user_groups]
    return render(request, 'contributor_dash.html', {'groups': groups})


from django.utils import timezone
from collections import defaultdict

@login_required
def contributor_wallet(request):
    # Simulated structure for demonstration
    payment_history = {
        2023: {1: "on_time", 2: "on_time", 3: "on_time", 4: "missed", 5: "on_time", 6: "on_time", 7: "on_time", 8: "on_time", 9: "on_time", 10: "on_time", 11: "on_time", 12: "on_time"},
        2022: {i: "on_time" for i in range(1, 13)},
        2021: {1: "on_time", 2: "missed", 3: "on_time", 4: "on_time", 5: "on_time", 6: "on_time", 7: "on_time", 8: "on_time", 9: "on_time", 10: "on_time", 11: "on_time", 12: "on_time"},
        2020: {i: "on_time" for i in range(1, 13)},
        2019: {1: "on_time", 2: "on_time", 3: "on_time"},
    }

    context = {
        'payment_history': payment_history,
    }
    return render(request, 'wallet_page.html', context)

from .models import Contribution

@login_required
def wallet_page(request, group_member_id):
    group_member = GroupMember.objects.get(id=group_member_id)
    transactions = Transaction.objects.filter(member=group_member).order_by('-date')[:10]  # latest 10

    context = {
        'group_member': group_member,
        'group': group_member.group,
        'member': member,
        'payment_history': group_member.payment_history_dict,  # this must be defined in your model
        'transactions': transactions,
    }
    return render(request, 'wallet_page.html', context)  # render to wallet_page.html


# views.py
import requests
from django.conf import settings
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

@login_required
def start_contribution_payment(request):
    email = request.user.email or "test@example.com"  # Use user email or dummy
    amount_naira = 100  # Change this value as needed
    amount_kobo = amount_naira * 100

    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "email": email,
        "amount": amount_kobo,
        "callback_url": settings.PAYSTACK_CALLBACK_URL,
    }

    response = requests.post("https://api.paystack.co/transaction/initialize", headers=headers, json=data)

    if response.status_code == 200:
        response_data = response.json()
        if response_data["status"]:
            authorization_url = response_data["data"]["authorization_url"]
            return redirect(authorization_url)
        else:
            return HttpResponse("Failed to initialize payment.")
    else:
        return HttpResponse("Paystack initialization error.")


# views.py
from django.http import HttpResponse

@login_required
def verify_payment(request):
    reference = request.GET.get('reference')
    if not reference:
        return HttpResponse("No payment reference provided.")

    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
    }

    url = f"https://api.paystack.co/transaction/verify/{reference}"
    response = requests.get(url, headers=headers)
    result = response.json()

    if result["status"] and result["data"]["status"] == "success":
        # Payment was successful
        return render(request, "success.html", {"message": "Payment successful!."})
        
    else:
        return render(request, "error.html", {"message": "Failed to initialize payment."})




# For withdrawal
@login_required
def start_contribution_withdrawal(request, member_id):
    # Logic to initiate Paystack withdrawal (via Paystack Transfer API)
    return redirect("https://api.paystack.co/transaction/initialize")  # Replace with logic to execute transfer

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth import logout
from core.models import UserProfile  # Update this import path if needed

@login_required
def contributor_setting(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "upload_avatar" and request.FILES.get("profile_picture"):
            profile.image = request.FILES["profile_picture"]
            profile.save()

        elif action == "remove_avatar":
            profile.image.delete(save=True)

        elif action == "delete_account":
            request.user.delete()
            logout(request)
            return redirect("signup")

        else:
            request.user.first_name = request.POST.get("first_name", "")
            request.user.last_name = request.POST.get("last_name", "")
            request.user.save()
            profile.phone_number = request.POST.get("phone_number", "")
            profile.save()

        return redirect("contributor_setting")  # Make sure this name exists in your urls.py

    return render(request, "contributor_setting.html", {"user": request.user})


@login_required
def contributor_paydetails(request):
    user = request.user
    groups = GroupMember.objects.filter(user=user)  # adjust as needed
    return render(request, 'paydetails.html', {'groups': groups})

# views.py

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import AkawoGroup, GroupMember

@login_required
def join_group(request):
    if request.method == 'POST':
        referral_code = request.POST.get('referral_code')  # ✅ FIXED here

        try:
            group = AkawoGroup.objects.get(referral_code=referral_code)
  # ✅ using referral_code

            # check if already joined
            if GroupMember.objects.filter(user=request.user, group=group).exists():
                messages.info(request, 'You already joined this group.')
                return redirect('contributor_dashboard')

            # join group
            GroupMember.objects.create(user=request.user, group=group)
            messages.success(request, 'You successfully joined the group.')
            return redirect('contributor_dashboard')

        except AkawoGroup.DoesNotExist:
            messages.error(request, 'Invalid referral code.')
            return redirect('contributor_dashboard')

    return redirect('contributor_dashboard')


@login_required
def all_contributor_groups(request):
    group_memberships = GroupMember.objects.filter(user=request.user)
    groups = [member.group for member in group_memberships]

    return render(request, "contributor_paydetails.html", {
        "groups": groups
    })
    
@login_required
def group_contributions(request, group_id):
    group = get_object_or_404(AkawoGroup, id=group_id)
    group_member = get_object_or_404(GroupMember, group=group, user=request.user)

    contributions = Contribution.objects.filter(member=group_member).order_by("-created_at")

    return render(request, "paydetails.html", {
        "group": group,
        "group_member": group_member,
        "contributions": contributions,
    })


    # Only this contributor's contributions
    contributions = Contribution.objects.filter(member=group_member).order_by("-created_at")

    return render(request, "paydetails.html", {
        "group": group,
        "group_member": group_member,
        "contributions": contributions,
    })
    
     
from .models import AkawoGroup, GroupMember, Contribution
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum

@login_required
def contributor_dashboard2(request, group_id):
    group = get_object_or_404(AkawoGroup, id=group_id)
    group_member = get_object_or_404(GroupMember, user=request.user, group=group)

    # Get all contributions for this member in the group
    contributions = Contribution.objects.filter(member=group_member).order_by('-contributed_at')

    # Total contributed so far
    total_contributions = contributions.aggregate(total=Sum('amount'))['total'] or 0

    # Last contribution record
    last_contribution = contributions.first()

    # Count how many contributions have been made
    num_contributions = contributions.count()

    # Estimate next due date based on cycle
    if group.contribution_cycle == "weekly":
        next_due_date = group_member.joined_at + timezone.timedelta(weeks=num_contributions + 1)
    elif group.contribution_cycle == "monthly":
        next_due_date = group_member.joined_at + timezone.timedelta(weeks=4 * (num_contributions + 1))
    else:
        next_due_date = None  # fallback if no cycle is set

    context = {
        "group": group,
        "group_member": group_member,
        "contributions": contributions,
        "total_contributions": total_contributions,
        "last_contribution": last_contribution,
        "next_due_date": next_due_date,
    }

    return render(request, "contributor_dashboard2.html", context)


def refer_view(request):
    return render(request, 'refer.html')

def help_support(request):
    return render(request, 'support.html')

def terms_and_conditions(request):
    return render(request, 'terms.html')

def privacy_policy(request):
    return render(request, 'policy.html')


from django.core.mail import send_mail
from django.contrib import messages
from django.conf import settings


def contributor_report(request, group_id):
    group = get_object_or_404(AkawoGroup, id=group_id)

    if request.method == "POST":
        subject = request.POST.get("subject")
        message = request.POST.get("message")
        contributor = request.user.username  

        # Email content
        email_subject = f"[Contributor Report] {subject} - {group.group_name}"
        email_message = f"""
        You have received a new report for your group "{group.group_name}".
        
        From Contributor: {contributor}
        Message:
        {message}
        """

        try:
            send_mail(
                email_subject,
                email_message,
                settings.DEFAULT_FROM_EMAIL,   # from email
                [group.organizer.email],       # organizer email
                fail_silently=False,
            )
            messages.success(request, "Report sent successfully!")
            return redirect("contributor_dashboard")
        except Exception as e:
            messages.error(request, f"Failed to send report: {e}")

    return render(request, "contributor_report.html", {"group": group})

@login_required
def contributor_groups(request):
    user = request.user
    # fetch actual groups the user is part of
    groups = AkawoGroup.objects.filter(group_members__user=user)
    return render(request, 'contributor_groups.html', {'groups': groups})


from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import reverse

@login_required
def me_view(request):
    user = request.user

    if user.profile.role == "organizer":
        profile_url = reverse("account_settings")
        reports_url = reverse("organizer_reports")
    else:
        profile_url = reverse("contributor_setting")
        reports_url = reverse("contributor_groups")

    return render(request, "me.html", {
        "profile_url": profile_url,
        "reports_url": reports_url,
    })

@login_required
def dashboard_redirect(request):
    user = request.user

    # Check if user is an organizer
    if AkawoGroup.objects.filter(organizer=user).exists():
        return redirect("organizer_dashboard")

    # Otherwise check if user is a contributor
    if GroupMember.objects.filter(user=user).exists():
        return redirect("contributor_dashboard")

    # Default fallback (e.g. no role yet)
    return redirect("select_role")

    # views.py

from django.contrib.auth.decorators import login_required
from .models import Notification

@login_required
def notifications_list(request):
    """List all notifications for the logged-in user"""
    notifications = Notification.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "notifications.html", {"notifications": notifications})

@login_required
def mark_as_read(request, notification_id):
    """Mark a notification as read"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    return redirect("notifications")


    

@login_required
def transaction_history(request):
    transactions = Transaction.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "transaction_history.html", {"transactions": transactions})

@login_required
def organizer_list(request):
    groups = AkawoGroup.objects.filter(organizer=request.user)
    return render(request, 'organizer_list.html', {'groups': groups})


@login_required
def organizer_wallet(request, group_id):
    group = get_object_or_404(AkawoGroup, id=group_id, organizer=request.user)

    # Get all GroupMember objects for this group
    group_members = GroupMember.objects.filter(group=group)

    # Fetch contributions for these group members
    contributions = Contribution.objects.filter(member__in=group_members)

    return render(request, 'organizer_wallet.html', {
        'group': group,
        'contributions': contributions
    })

@login_required
def contributor_groups2(request):
    """Show all groups where the logged-in user is a member"""
    groups = GroupMember.objects.filter(user=request.user)
    return render(request, "contributor_groups2.html", {"groups": groups})


@login_required
def contributor_withdrawals(request, group_id):
    group = get_object_or_404(AkawoGroup, id=group_id)

    # Get the GroupMember instance for this user in this group
    try:
        member = GroupMember.objects.get(user=request.user, group=group)
    except GroupMember.DoesNotExist:
        messages.error(request, "You are not a member of this group.")
        return redirect('contributor_dashboard')

    # Get all withdrawals for this member
    withdrawals = Withdrawal.objects.filter(member=member).order_by('-created_at')

    return render(request, 'contributor_withdrawals.html', {
        'group': group,
        'withdrawals': withdrawals
    })


