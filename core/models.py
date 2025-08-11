from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum
from django.utils import timezone
import string
import random

# --- User Role Profile ---
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


# --- Akawo Group ---
class AkawoGroup(models.Model):
    group_name = models.CharField(max_length=100)
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organized_groups')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    contribution_cycle = models.CharField(max_length=10, choices=[('weekly', 'Weekly'), ('monthly', 'Monthly')])
    fee_percent = models.FloatField(default=1.0)
    photo = models.ImageField(upload_to='group_photos/', null=True, blank=True)
    referral_code = models.CharField(max_length=20, unique=True, blank=True)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    members = models.ManyToManyField(User, related_name='akawo_groups')
    contribution_percentage_offset = models.FloatField(default=0)
    monthly_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unpaid_count = models.IntegerField(default=0)
    current_cycle_month = models.DateField(null=True, blank=True)
    contribution_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    withdrawal_schedule = models.CharField(max_length=100, blank=True, help_text="E.g. 25th of every month or every 4 weeks")
    

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        super().save(*args, **kwargs)

    def total_custom_payouts(self):
        return self.custom_payouts.filter(by_admin=True).count()

    def __str__(self):
        return self.group_name


# --- Group Member (Contributor) ---

class GroupMember(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    group = models.ForeignKey(AkawoGroup, on_delete=models.CASCADE, related_name='group_members')
   # total_contributed = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)  # Make sure this exists
    joined_at = models.DateTimeField(auto_now_add=True)  # Make sure this exists
    

    class Meta:
        unique_together = ('user', 'group')

    def __str__(self):
        return f"{self.user.username} - {self.group.group_name}"


# --- Contribution ---
class Contribution(models.Model):
    member = models.ForeignKey(GroupMember, on_delete=models.CASCADE, related_name='contributions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    

    
    created_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True, null=True)
    paid_by = models.CharField(
        max_length=20,
        choices=(('self', 'Self'), ('organizer', 'Organizer')),
        default='self'
    )
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=(('pending', 'Pending'), ('completed', 'Completed')),
        default='pending'
    )
    contributed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member.user.username} - ₦{self.amount}"


# --- Payment (Tracking Paystack) ---
class Payment(models.Model):
    contributor = models.ForeignKey(GroupMember, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, default='initiated')  # initiated, success, failed
    created_at = models.DateTimeField(auto_now_add=True)


# --- Report ---
class Report(models.Model):
    group = models.ForeignKey(AkawoGroup, on_delete=models.CASCADE, related_name='reports')
    contributor = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"Report by {self.contributor.username} for {self.group.group_name}"


# --- Custom Payout ---
class CustomPayout(models.Model):
    group = models.ForeignKey(AkawoGroup, on_delete=models.CASCADE, related_name='custom_payouts')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    to_member = models.ForeignKey(User, on_delete=models.CASCADE)
    by_admin = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Admin Payout - {self.to_member.username} ({self.amount})"


# --- Payout ---
class Payout(models.Model):
    group = models.ForeignKey(AkawoGroup, on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    fee_deducted = models.DecimalField(max_digits=12, decimal_places=2)
    paid_at = models.DateTimeField(auto_now_add=True)
    distributed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.group.group_name} - Paid: {self.distributed}"


# --- Contribution History ---
class ContributionHistory(models.Model):
    group = models.ForeignKey(AkawoGroup, on_delete=models.CASCADE, related_name='contribution_history')
    member = models.ForeignKey(GroupMember, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(
        max_length=10,
        choices=[('paid', 'Paid'), ('unpaid', 'Unpaid')],
        default='unpaid'
    )
    period = models.DateField()  # Month of the contribution period
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.group.group_name} - {self.member.user.username} - {self.period.strftime('%B %Y')}"
    
    

created_at = models.DateTimeField(default=timezone.now)
  
   
  