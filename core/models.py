from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import string
import random


# =========================
# USER PROFILE
# =========================
class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('organizer', 'Organizer'),
        ('contributor', 'Contributor'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='contributor')
    image = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"


# =========================
# GROUP
# =========================
class AkawoGroup(models.Model):
    group_name = models.CharField(max_length=100)
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organized_groups')
    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    contribution_cycle = models.CharField(
        max_length=10,
        choices=[('weekly', 'Weekly'), ('monthly', 'Monthly')]
    )

    contribution_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    withdrawal_schedule = models.CharField(max_length=100, blank=True)

    photo = models.ImageField(upload_to='group_photos/', null=True, blank=True)

    referral_code = models.CharField(max_length=20, unique=True, blank=True)

    members = models.ManyToManyField(User, related_name='akawo_groups', blank=True)

    # Tracking system
    monthly_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unpaid_count = models.IntegerField(default=0)
    current_cycle_month = models.DateField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = ''.join(
                random.choices(string.ascii_uppercase + string.digits, k=6)
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.group_name


# =========================
# GROUP MEMBER (FIXED)
# =========================
class GroupMember(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # ✅ FIXED (was OneToOne ❌)
    group = models.ForeignKey(AkawoGroup, on_delete=models.CASCADE, related_name='group_members')

    total_contributed = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'group')

    def __str__(self):
        return f"{self.user.username} - {self.group.group_name}"


# =========================
# PAYMENT (PAYSTACK TRACKING)
# =========================
class Payment(models.Model):
    contributor = models.ForeignKey(GroupMember, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    reference = models.CharField(max_length=100, unique=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ('initiated', 'Initiated'),
            ('success', 'Success'),
            ('failed', 'Failed')
        ],
        default='initiated'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.reference} - {self.status}"


# =========================
# CONTRIBUTION
# =========================
class Contribution(models.Model):
    member = models.ForeignKey(GroupMember, on_delete=models.CASCADE, related_name='contributions')

    amount = models.DecimalField(max_digits=12, decimal_places=2)

    reference = models.CharField(max_length=100, unique=True, null=True, blank=True)

    payment_reference = models.CharField(max_length=100, blank=True, null=True)

    paid_by = models.CharField(
        max_length=20,
        choices=(('self', 'Self'), ('organizer', 'Organizer')),
        default='self'
    )

    status = models.CharField(
        max_length=20,
        choices=(('pending', 'Pending'), ('completed', 'Completed')),
        default='pending'
    )

    note = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    contributed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member.user.username} - ₦{self.amount}"


# =========================
# WITHDRAWALS
# =========================
class Withdrawal(models.Model):
    member = models.ForeignKey(GroupMember, on_delete=models.CASCADE, related_name='withdrawals')
    group = models.ForeignKey(AkawoGroup, on_delete=models.CASCADE, related_name='withdrawals')

    amount = models.DecimalField(max_digits=12, decimal_places=2)

    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected')
        ],
        default='pending'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.member.user.username} - {self.amount}"


# =========================
# CONTRIBUTION HISTORY
# =========================
class ContributionHistory(models.Model):
    group = models.ForeignKey(AkawoGroup, on_delete=models.CASCADE, related_name='contribution_history')
    member = models.ForeignKey(GroupMember, on_delete=models.CASCADE)

    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    status = models.CharField(
        max_length=10,
        choices=[('paid', 'Paid'), ('unpaid', 'Unpaid')],
        default='unpaid'
    )

    period = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.group.group_name} - {self.member.user.username}"


# =========================
# REPORT
# =========================
class Report(models.Model):
    group = models.ForeignKey(AkawoGroup, on_delete=models.CASCADE, related_name='reports')
    contributor = models.ForeignKey(User, on_delete=models.CASCADE)

    message = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.contributor.username} - {self.group.group_name}"


# =========================
# PAYOUTS
# =========================
class Payout(models.Model):
    group = models.ForeignKey(AkawoGroup, on_delete=models.CASCADE)

    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    fee_deducted = models.DecimalField(max_digits=12, decimal_places=2)

    paid_at = models.DateTimeField(auto_now_add=True)
    distributed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.group.group_name} payout"


class CustomPayout(models.Model):
    group = models.ForeignKey(AkawoGroup, on_delete=models.CASCADE, related_name='custom_payouts')

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    to_member = models.ForeignKey(User, on_delete=models.CASCADE)

    by_admin = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)


# =========================
# TRANSACTIONS
# =========================
class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ("contribution", "Contribution"),
        ("withdrawal", "Withdrawal"),
        ("payment", "Payment"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transactions")

    amount = models.DecimalField(max_digits=12, decimal_places=2)

    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)

    reference = models.CharField(max_length=100, unique=True, null=True, blank=True)

    status = models.CharField(max_length=20, default="pending")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.transaction_type}"


# =========================
# NOTIFICATIONS
# =========================
class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('contribution', 'Contribution'),
        ('payment', 'Payment'),
        ('payout', 'Payout'),
        ('report', 'Report'),
        ('general', 'General'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")

    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='general')

    message = models.TextField()

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    contribution = models.ForeignKey(Contribution, null=True, blank=True, on_delete=models.SET_NULL)
    payment = models.ForeignKey(Payment, null=True, blank=True, on_delete=models.SET_NULL)
    payout = models.ForeignKey(Payout, null=True, blank=True, on_delete=models.SET_NULL)
    report = models.ForeignKey(Report, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.user.username} - {self.notification_type}"
