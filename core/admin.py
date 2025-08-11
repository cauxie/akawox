from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    UserProfile,
    AkawoGroup,
    GroupMember,
    Contribution,
    Payout
)

# -----------------------------
# USER & PROFILE ADMIN
# -----------------------------
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'User Profile'
    fk_name = 'user'

class CustomUserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_role', 'is_staff', 'is_active')
    list_select_related = ('userprofile',)

    def get_role(self, instance):
        return instance.userprofile.role
    get_role.short_description = 'Role'

# Unregister default User admin, then register custom
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# -----------------------------
# AKAWO GROUP ADMIN
# -----------------------------
@admin.register(AkawoGroup)
class AkawoGroupAdmin(admin.ModelAdmin):
    list_display = ('group_name', 'organizer', 'contribution_cycle', 'fee_percent', 'created_at')
    list_filter = ('contribution_cycle', 'created_at')
    search_fields = ['group_name', 'organizer__username']
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Basic Info', {
            'fields': ('group_name', 'organizer', 'description', 'contribution_cycle', 'fee_percent')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

# -----------------------------
# GROUP MEMBER ADMIN (Registered only once!)
# -----------------------------
@admin.register(GroupMember)
class GroupMemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'group', 'joined_at')
   
    search_fields = ('user__username', 'group__group_name')
    ordering = ('-joined_at',)
    readonly_fields = ('joined_at',)

# -----------------------------
# CONTRIBUTION ADMIN
# -----------------------------
@admin.register(Contribution)
class ContributionAdmin(admin.ModelAdmin):
    list_display = ('member', 'amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('member__user__username',)

    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)

# -----------------------------
# PAYOUT ADMIN
# -----------------------------
@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ('group', 'total_amount', 'fee_deducted', 'distributed', 'paid_at')
    list_filter = ('distributed', 'paid_at')
    search_fields = ('group__group_name',)
    date_hierarchy = 'paid_at'
    ordering = ('-paid_at',)
    readonly_fields = ('paid_at',)
