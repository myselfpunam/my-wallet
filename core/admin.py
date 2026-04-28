from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.db.models import Sum, Count

from .models import (
    Transaction, UserProfile, Loan, LoanPayment,
    Receivable, ReceivablePayment, PaymentReminder,
    ReminderEntry, PasswordResetToken, RentSetup, RentEntry,
)


# ── Inline: show UserProfile inside User detail page ──────────────────────────
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = ['phone_number', 'address', 'profile_picture']
    extra = 0


# ── Custom User admin ──────────────────────────────────────────────────────────
class CustomUserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]

    list_display = [
        'username', 'email', 'first_name', 'last_name',
        'is_active', 'is_staff', 'date_joined', 'transaction_count',
    ]
    list_filter   = ['is_active', 'is_staff', 'is_superuser', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering      = ['-date_joined']
    actions       = ['activate_users', 'deactivate_users']

    # Annotate queryset once for the transaction_count column
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_tx_count=Count('transactions'))

    def transaction_count(self, obj):
        return obj._tx_count
    transaction_count.short_description = 'Transactions'
    transaction_count.admin_order_field = '_tx_count'

    @admin.action(description='Activate selected users')
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} user(s) activated.')

    @admin.action(description='Deactivate selected users')
    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} user(s) deactivated.')


# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


# ── UserProfile ────────────────────────────────────────────────────────────────
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ['user', 'phone_number', 'address', 'created_at']
    search_fields = ['user__username', 'user__email', 'phone_number']
    ordering      = ['-created_at']


# ── Transaction ────────────────────────────────────────────────────────────────
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display  = ['user', 'type', 'title', 'category', 'amount', 'date', 'created_at']
    list_filter   = ['type', 'category', 'date']
    search_fields = ['user__username', 'user__email', 'title', 'category', 'note']
    ordering      = ['-date']
    date_hierarchy = 'date'


# ── Loan ───────────────────────────────────────────────────────────────────────
class LoanPaymentInline(admin.TabularInline):
    model  = LoanPayment
    extra  = 0
    fields = ['amount', 'date', 'note']

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display  = ['user', 'lender_name', 'amount', 'remaining', 'date']
    search_fields = ['user__username', 'lender_name']
    ordering      = ['-date']
    inlines       = [LoanPaymentInline]

    def remaining(self, obj):
        return f'£{obj.get_remaining():.2f}'
    remaining.short_description = 'Remaining'


@admin.register(LoanPayment)
class LoanPaymentAdmin(admin.ModelAdmin):
    list_display  = ['user', 'loan', 'amount', 'date']
    search_fields = ['user__username', 'loan__lender_name']
    ordering      = ['-date']


# ── Receivable ─────────────────────────────────────────────────────────────────
class ReceivablePaymentInline(admin.TabularInline):
    model  = ReceivablePayment
    extra  = 0
    fields = ['amount', 'date', 'note']

@admin.register(Receivable)
class ReceivableAdmin(admin.ModelAdmin):
    list_display  = ['user', 'debtor_name', 'amount', 'remaining', 'date']
    search_fields = ['user__username', 'debtor_name']
    ordering      = ['-date']
    inlines       = [ReceivablePaymentInline]

    def remaining(self, obj):
        return f'£{obj.get_remaining():.2f}'
    remaining.short_description = 'Remaining'


@admin.register(ReceivablePayment)
class ReceivablePaymentAdmin(admin.ModelAdmin):
    list_display  = ['user', 'receivable', 'amount', 'date']
    search_fields = ['user__username', 'receivable__debtor_name']
    ordering      = ['-date']


# ── Payment Reminders ──────────────────────────────────────────────────────────
@admin.register(PaymentReminder)
class PaymentReminderAdmin(admin.ModelAdmin):
    list_display  = ['user', 'title', 'category', 'amount', 'due_date', 'frequency', 'is_active']
    list_filter   = ['category', 'frequency', 'is_active']
    search_fields = ['user__username', 'title']
    ordering      = ['due_date']


@admin.register(ReminderEntry)
class ReminderEntryAdmin(admin.ModelAdmin):
    list_display  = ['user', 'reminder', 'due_date', 'amount', 'status', 'payment_date']
    list_filter   = ['status', 'due_date']
    search_fields = ['user__username', 'reminder__title']
    ordering      = ['due_date']


# ── OTP Tokens ─────────────────────────────────────────────────────────────────
@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display  = ['user', 'token_type', 'created_at', 'expires_at', 'used', 'resend_count']
    list_filter   = ['token_type', 'used']
    search_fields = ['user__username', 'user__email']
    ordering      = ['-created_at']
    readonly_fields = ['token', 'otp_hash', 'created_at']


# ── Rent ───────────────────────────────────────────────────────────────────────
@admin.register(RentSetup)
class RentSetupAdmin(admin.ModelAdmin):
    list_display  = ['user', 'property_name', 'amount', 'due_day', 'start_date', 'is_active']
    list_filter   = ['is_active']
    search_fields = ['user__username', 'property_name']


@admin.register(RentEntry)
class RentEntryAdmin(admin.ModelAdmin):
    list_display  = ['user', 'rent_setup', 'month', 'year', 'amount', 'status', 'payment_date']
    list_filter   = ['status', 'year']
    search_fields = ['user__username', 'rent_setup__property_name']
    ordering      = ['-year', '-month']


# ── Site header customisation ──────────────────────────────────────────────────
admin.site.site_header = 'My Wallet — Admin'
admin.site.site_title  = 'My Wallet Admin'
admin.site.index_title = 'Site Administration'
