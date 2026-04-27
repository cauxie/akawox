# core/models.py

from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum
import uuid
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
    CYCLE_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly')
    ]

    group_name = models.CharField(max_length=100)
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organized_groups')

    description = models.TextField(blank=True)
    photo = models.ImageField(upload_to='group_photos/', null=True, blank=True)

    contribution_cycle = models.CharField(max_length=10, choices=CYCLE_CHOICES)
    contribution_amount = models.DecimalField(max_digits=10, decimal_places=2)

    fee_percent = models.FloatField(default=2.0)
    organizer_commission = models.FloatField(default=2.0)

    referral_code = models.CharField(max_length=10, unique=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        super().save(*args, **kwargs)

    def total_contributions(self):
        return Contribution.objects.filter(member__group=self).aggregate(
            total=Sum('amount')
        )['total'] or 0

    def __str__(self):
        return self.group_name


# =========================
# GROUP MEMBER
# =========================

class GroupMember(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(AkawoGroup, on_delete=models.CASCADE, related_name='members')

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'group')

    def total_contributed(self):
        return self.contributions.aggregate(total=Sum('amount'))['total'] or 0

    def __str__(self):
        return f"{self.user.username} - {self.group.group_name}"


# =========================
# PAYMENT (PAYSTACK / CASH INIT)
# =========================

class Payment(models.Model):
    PAYMENT_METHODS = (
        ('paystack', 'Paystack'),
        ('cash', 'Cash'),
    )

    member = models.ForeignKey(GroupMember, on_delete=models.CASCADE, related_name='payments')

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference = models.CharField(max_length=100, unique=True, default=uuid.uuid4)

    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='paystack')

    status = models.CharField(
        max_length=20,
        choices=(('pending', 'Pending'), ('success', 'Success'), ('failed', 'Failed')),
        default='pending'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member.user.username} - {self.amount}"


# =========================
# CONTRIBUTION (REAL MONEY RECORD)
# =========================

class Contribution(models.Model):
    member = models.ForeignKey(GroupMember, on_delete=models.CASCADE, related_name='contributions')

    amount = models.DecimalField(max_digits=12, decimal_places=2)

    paid_by = models.CharField(
        max_length=20,
        choices=(('self', 'Self'), ('organizer', 'Organizer')),
        default='self'
    )

    payment_reference = models.CharField(max_length=100, blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=(('pending', 'Pending'), ('completed', 'Completed')),
        default='completed'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member.user.username} - ₦{self.amount}"


# =========================
# TRANSACTION (USER HISTORY)
# =========================

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ("contribution", "Contribution"),
        ("withdrawal", "Withdrawal"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transactions")

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)

    reference = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    status = models.CharField(max_length=20, default="success")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.transaction_type} - {self.amount}"


# =========================
# WITHDRAWAL
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

    note = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member.user.username} - {self.amount}"


# =========================
# OPTIONAL (KEEP - SAFE)
# =========================

class Report(models.Model):
    group = models.ForeignKey(AkawoGroup, on_delete=models.CASCADE, related_name='reports')
    contributor = models.ForeignKey(User, on_delete=models.CASCADE)

    message = models.TextField()
    is_resolved = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.contributor.username} - {self.group.group_name}"
