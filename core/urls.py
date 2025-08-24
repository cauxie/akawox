from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView


urlpatterns = [

    # === AUTH ===
    path('', views.index, name='index'),
    path('signup/', views.signup_view, name='signup'),
    path('role/', views.select_role_view, name='select_role'),
    path('login/', views.login_view, name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    

    # Forgot password flow
    path("forgot-password/", auth_views.PasswordResetView.as_view(
        template_name="forgot_password.html"
    ), name="forgot_password"),

    path("forgot-password/done/", auth_views.PasswordResetDoneView.as_view(
        template_name="forgot_password_done.html"
    ), name="password_reset_done"),

    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="password_reset_confirm.html"
    ), name="password_reset_confirm"),

    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(
        template_name="password_reset_complete.html"
    ), name="password_reset_complete"),

    # Change password flow
    path("change-password/", auth_views.PasswordChangeView.as_view(
        template_name="change_password.html",
        success_url="/change-password/done/"
    ), name="change_password"),

    path("change-password/done/", auth_views.PasswordChangeDoneView.as_view(
        template_name="change_password_done.html"
    ), name="password_change_done"),

    # Notifications
    path("notifications/", views.notifications_list, name="notifications"),
    path("notifications/read/<int:notification_id>/", views.mark_as_read, name="mark_as_read"),

    # === ORGANIZER DASHBOARD ===
    path('dashboard/', views.dashboard_redirect, name='dashboard'),  # unified
    path('organizer/dashboard/', views.organizer_dashboard, name='organizer_dashboard'),
    path('organizer/dash/', views.organizer_dash, name='organizer_dash'),
    path('organizer/create-group/', views.create_group, name='create_group'),
    path('group/<int:group_id>/', views.group_detail, name='group_detail'),
    path('refer/', views.refer_view, name='refer'),
    path('support/', views.help_support, name='support'),
    path('notifications/', views.notifications_list, name='notification'),


    # === GROUP MANAGEMENT ===
    path('organizer/groups/', views.group_manage_view, name='group_manage_list'),
    path('organizer/groups/manage/', views.group_manage_view, name='group_manage'),
    path('organizer/groups/<int:group_id>/manage/', views.manage_page, name='manage_page'),
    path('organizer/groups/<int:group_id>/remove-member/<int:member_id>/', views.remove_member, name='remove_member'),

    # === CONTRIBUTIONS AND PAYMENTS ===
    path('pay/contribute/', views.start_contribution_payment, name='start_contribution_payment'),
    path('pay/withdraw/', views.start_contribution_withdrawal, name='start_contribution_withdrawal'),
    path('pay/contributor/<int:group_id>/', views.pay_for_contributor, name='pay_for_contributor'),
    path('payment/verify/', views.payment_callback, name='payment_callback'),
    path('payment/callback/', views.payment_callback, name='payment_callback'),
    path('wallet/payment/webhook/', views.paystack_webhook, name='paystack_webhook'),
    path('webhook/paystack/', views.paystack_webhook, name='paystack_webhook'),
    path('pay/verify/', views.verify_payment, name='verify_payment'),

    path('terms/', views.terms_and_conditions, name='terms'),
    path('policy/', views.privacy_policy, name='policy'), 
    path("me/", views.me_view, name="me"),

    # === ORGANIZER REPORTS & FINANCE ===
    path('organizer/contributions/<int:group_id>/', views.group_contributions, name='contributions'),
    path('organizer/withdrawals/<int:group_id>/', views.group_withdrawals, name='withdrawals'),
    path('organizer/withdrawal/', views.organizer_withdrawal, name='organizer_withdrawal'),
    path('organizer/contributions/', views.organizer_contribution, name='organizer_contribution'),
    path('organizer/reports/', views.organizer_reports, name='organizer_reports'),
    path('organizer/reports/<int:group_id>/', views.reports_page, name='reports_page'),
    path('organizer/groups/<int:group_id>/reminder/', views.send_reminder, name='send_reminder'),
    path("transactions/", views.transaction_history, name="transaction_history"),
    path("organizer-groups/", views.organizer_list, name="organizer_list"),
    path("organizer-wallet/<int:group_id>/", views.organizer_wallet, name="organizer_wallet"),

    # === CONTRIBUTOR DASHBOARD ===
    path('contributor/dashboard/', views.contributor_dashboard, name='contributor_dashboard'),
    path('contributor/dash/', views.contributor_dash, name='contributor_dash'),
    path('contributor/dashboard/group/<int:group_id>/', views.contributor_dashboard2, name='contributor_dashboard2'),
    path('contributor/wallet/', views.contributor_wallet, name='contributor_wallet'),
    path('wallet/contribute/<int:member_id>/', views.start_contribution_payment, name='wallet_contribute'),
    path("contributor/groups/", views.contributor_groups2, name="contributor_groups2"),
    path("contributor/groups/<int:group_id>/withdrawals/", views.contributor_withdrawals, name="contributor_withdrawals"),

    # === CONTRIBUTOR SETTINGS & GROUPS ===
    path('contributor/setting/', views.contributor_setting, name='contributor_setting'),
    path('contributor/paydetails/', views.contributor_paydetails, name='contributor_paydetails'),
    path('contributor/paydetails/<int:group_id>/', views.group_contributions, name='paydetails'),
    path('contributor/join-group/', views.join_group, name='join_group'),
    path('contributor/join/', views.join_group, name='join_group_alt'),
    path("my-groups/", views.contributor_groups, name="contributor_groups"),
    path("contributor/report/<int:group_id>/", views.contributor_report, name="contributor_report"),

    # === ACCOUNT SETTINGS ===
    path('settings/', views.account_settings, name='account_settings'),
]

# === MEDIA SERVING DURING DEBUG ===
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
