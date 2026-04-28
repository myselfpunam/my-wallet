from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum
from django.utils.crypto import get_random_string
from django.contrib.auth.hashers import make_password, check_password
from decimal import Decimal
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
import os


INCOME_SOURCES = [
    ('salary', 'Salary'),
    ('freelance', 'Freelance'),
    ('gift', 'Gift'),
    ('investment', 'Investment'),
    ('business', 'Business'),
    ('rental', 'Rental Income'),
    ('bonus', 'Bonus'),
    ('refund', 'Refund'),
    ('other', 'Other'),
]

EXPENSE_CATEGORIES = [
    ('food', 'Food'),
    ('travel', 'Travel'),
    ('rent', 'House Rent'),
    ('personal', 'Personal'),
    ('family_support', 'Family Support'),
    ('lifestyle', 'Lifestyle'),
    ('other', 'Others'),
]

TRANSACTION_TYPES = [
    ('income', 'Income'),
    ('expense', 'Expense'),
]


class Loan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loans')
    lender_name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.TextField(blank=True, null=True)
    date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"Loan from {self.lender_name} - £{self.amount} ({self.date})"

    def get_total_paid(self):
        return self.loan_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    def get_remaining(self):
        return self.amount - self.get_total_paid()


class UserProfile(models.Model):
    """
    Extended user profile with additional information like address, phone, and profile picture.
    
    Features:
    - One-to-one relationship with Django User
    - Profile picture upload with validation (JPG, PNG, max 5MB)
    - Address and phone number fields
    - Automatic creation on user signup
    - Profile picture URL getter with default avatar fallback
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    address = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Street address, city, postal code"
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Contact phone number"
    )
    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])],
        help_text="Upload JPG or PNG (max 5MB)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"Profile for {self.user.username}"

    def get_profile_picture_url(self):
        """Return profile picture URL or empty string if not set."""
        if self.profile_picture:
            return self.profile_picture.url
        return ""

    def get_display_name(self):
        """Return user's display name (first name or username)."""
        return self.user.first_name or self.user.username

    def delete_profile_picture(self):
        """Delete the profile picture from storage."""
        if self.profile_picture and hasattr(self.profile_picture, 'delete'):
            self.profile_picture.delete(save=False)
            self.profile_picture = None
            self.save()


class LoanPayment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loan_payments')
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='loan_payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.TextField(blank=True, null=True)
    date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"Payment £{self.amount} for {self.loan.lender_name} ({self.date})"


class Receivable(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='receivables')
    debtor_name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.TextField(blank=True, null=True)
    date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"Receivable from {self.debtor_name} - £{self.amount} ({self.date})"

    def get_total_received(self):
        return self.receivable_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    def get_remaining(self):
        return self.amount - self.get_total_received()


class ReceivablePayment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='receivable_payments')
    receivable = models.ForeignKey(Receivable, on_delete=models.CASCADE, related_name='receivable_payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.TextField(blank=True, null=True)
    date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"Received £{self.amount} from {self.receivable.debtor_name} ({self.date})"


class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    title = models.CharField(max_length=100, blank=True, null=True)
    category = models.CharField(max_length=50)  # source for income, category for expense
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.now)
    note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.type.title()} - {self.category} - £{self.amount} ({self.date})"

    def get_category_display_name(self):
        _all = dict(INCOME_SOURCES)
        _all.update({
            'food': 'Food', 'travel': 'Travel', 'rent': 'House Rent',
            'personal': 'Personal', 'family_support': 'Family Support',
            'lifestyle': 'Lifestyle', 'other': 'Others',
            # legacy keys
            'tour': 'Tour', 'transport': 'Transport',
            'shopping': 'Shopping', 'healthcare': 'Healthcare',
            'entertainment': 'Entertainment', 'utilities': 'Utilities',
            'education': 'Education', 'subscriptions': 'Subscriptions',
            'insurance': 'Insurance', 'savings': 'Savings',
        })
        return _all.get(self.category, self.category.replace('_', ' ').title())

    def get_category_icon(self):
        icons = {
            # Income
            'salary': '💼', 'freelance': '💻', 'gift': '🎁',
            'investment': '📈', 'business': '🏢', 'rental': '🏠',
            'bonus': '⭐', 'refund': '↩️',
            # Expense
            'food': '🍽️', 'travel': '✈️', 'rent': '🏠',
            'personal': '👤', 'family_support': '👨‍👩‍👧', 'other': '📋',
            # legacy
            'tour': '🗺️', 'lifestyle': '✨', 'transport': '🚗',
            'shopping': '🛍️', 'healthcare': '🏥', 'entertainment': '🎬',
            'utilities': '⚡', 'education': '📚', 'subscriptions': '📱',
            'insurance': '🛡️', 'savings': '🏦',
        }
        return icons.get(self.category, '💰')


class PaymentReminder(models.Model):
    """
    User-configured reminder for any recurring or one-time payment.
    Works for rent, bills, subscriptions, personal payments, etc.
    """
    FREQ_ONE_TIME = 'one_time'
    FREQ_MONTHLY  = 'monthly'
    FREQUENCY_CHOICES = [
        (FREQ_ONE_TIME, 'One-time'),
        (FREQ_MONTHLY,  'Monthly (Recurring)'),
    ]

    CATEGORY_CHOICES = [
        ('rent',         'House Rent'),
        ('electricity',  'Electricity Bill'),
        ('internet',     'Internet Bill'),
        ('gas',          'Gas Bill'),
        ('water',        'Water Bill'),
        ('subscription', 'Subscription'),
        ('insurance',    'Insurance'),
        ('loan_payment', 'Loan Payment'),
        ('personal',     'Personal Payment'),
        ('other',        'Other'),
    ]

    CATEGORY_ICONS = {
        'rent': '🏠', 'electricity': '⚡', 'internet': '🌐',
        'gas': '🔥', 'water': '💧', 'subscription': '📱',
        'insurance': '🛡️', 'loan_payment': '💳', 'personal': '👤', 'other': '📋',
    }

    user              = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_reminders')
    title             = models.CharField(max_length=200)
    category          = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='other')
    amount            = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    description       = models.TextField(blank=True, null=True)
    due_date          = models.DateField(help_text='First (or only) due date for this payment')
    frequency         = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default=FREQ_MONTHLY)
    remind_days_before = models.PositiveSmallIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(7)],
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date', 'title']

    def __str__(self):
        return f"{self.title} ({self.get_frequency_display()})"

    def get_icon(self):
        return self.CATEGORY_ICONS.get(self.category, '📋')

    def get_amount_display(self):
        return f"£{self.amount}" if self.amount else '—'


class ReminderEntry(models.Model):
    """
    A single due-date instance generated from a PaymentReminder.
    One-time reminders → one entry.  Monthly reminders → one per month.
    """
    STATUS_PENDING = 'pending'
    STATUS_PAID    = 'paid'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PAID,    'Paid'),
    ]

    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reminder_entries')
    reminder    = models.ForeignKey(PaymentReminder, on_delete=models.CASCADE, related_name='entries')
    due_date    = models.DateField()
    amount      = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    status      = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    payment_date     = models.DateField(blank=True, null=True)
    transaction      = models.OneToOneField(
        'Transaction', on_delete=models.SET_NULL,
        blank=True, null=True, related_name='reminder_entry',
    )
    last_reminder_date = models.DateField(blank=True, null=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering  = ['due_date']
        unique_together = [('reminder', 'due_date')]

    def __str__(self):
        return f"{self.reminder.title} — due {self.due_date} ({self.status})"

    def is_overdue(self):
        from datetime import date
        return self.status == self.STATUS_PENDING and self.due_date < date.today()

    def days_until_due(self):
        from datetime import date
        return (self.due_date - date.today()).days

    def status_label(self):
        if self.status == self.STATUS_PAID:
            return 'paid'
        if self.is_overdue():
            return 'overdue'
        return 'pending'


class PasswordResetToken(models.Model):
    """
    Stores OTP tokens with hashed codes for secure password reset and email verification.

    Security design:
    - The raw OTP is NEVER stored; only its bcrypt hash is persisted.
    - The raw OTP is generated, returned to the caller once, and must be emailed immediately.
    - Verification is done via check_password(raw_input, stored_hash).
    - Each token has a hard expiry and is marked `used` after one successful verification.
    - Resend attempts are tracked per token chain to enforce rate limits.
    """

    TOKEN_TYPE_CHOICES = [
        ('password_reset', 'Password Reset'),
        ('email_verification', 'Email Verification'),
    ]

    # --- Core fields ---
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verification_tokens')
    token = models.CharField(max_length=64, unique=True)  # session lookup key
    otp_hash = models.CharField(max_length=128, blank=True, null=True)  # bcrypt hash of the 6-digit OTP
    token_type = models.CharField(max_length=20, choices=TOKEN_TYPE_CHOICES, default='password_reset')

    # --- Lifecycle ---
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    # --- Rate-limiting ---
    resend_count = models.PositiveSmallIntegerField(default=0)  # how many times OTP was resent

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user', 'used', 'expires_at']),
            models.Index(fields=['token_type', 'used']),
        ]

    def __str__(self):
        return f"{self.token_type} token for {self.user.username} (expires: {self.expires_at})"

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_valid(self):
        return not self.used and not self.is_expired

    # ------------------------------------------------------------------
    # OTP verification
    # ------------------------------------------------------------------
    def verify_otp(self, raw_otp: str) -> bool:
        """Verify a plaintext OTP against the stored bcrypt hash."""
        if not self.otp_hash or not raw_otp:
            return False
        return check_password(raw_otp, self.otp_hash)

    # ------------------------------------------------------------------
    # Class-level helpers
    # ------------------------------------------------------------------
    @classmethod
    def cleanup_expired(cls):
        """Permanently remove all expired tokens (safe to call via cron)."""
        cls.objects.filter(expires_at__lt=timezone.now()).delete()

    @classmethod
    def create_for_user(cls, user, token_type='password_reset', expiry_minutes=10):
        """
        Create a new OTP token for *user*, revoke all prior unused tokens of the
        same type, and return (token_instance, raw_otp_string).

        The raw OTP MUST be emailed immediately and never stored or logged.

        Args:
            user            : Django User instance
            token_type      : 'password_reset' | 'email_verification'
            expiry_minutes  : Lifetime of the OTP (default 10 min)

        Returns:
            (PasswordResetToken, str)  — instance and 6-digit plaintext OTP
        """
        # Revoke every prior unused token of the same type for this user
        cls.objects.filter(user=user, token_type=token_type, used=False).update(used=True)

        raw_otp = get_random_string(length=6, allowed_chars='0123456789')
        token_value = get_random_string(length=64)
        expires_at = timezone.now() + timezone.timedelta(minutes=expiry_minutes)

        instance = cls.objects.create(
            user=user,
            token=token_value,
            otp_hash=make_password(raw_otp),   # hash immediately; raw value never persisted
            token_type=token_type,
            expires_at=expires_at,
        )
        return instance, raw_otp


class RentSetup(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rent_setups')
    property_name = models.CharField(max_length=100, blank=True, null=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_day = models.PositiveSmallIntegerField(
        help_text='Day of month rent is due (1–28)',
        validators=[MinValueValidator(1), MaxValueValidator(28)],
    )
    start_date = models.DateField()
    remind_days_before = models.PositiveSmallIntegerField(
        default=3,
        help_text='Send reminder this many days before due date',
        validators=[MinValueValidator(1), MaxValueValidator(7)],
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        name = self.property_name or 'Rent'
        return f"{name} (due day {self.due_day})"


class RentEntry(models.Model):
    STATUS_CHOICES = [('unpaid', 'Unpaid'), ('paid', 'Paid')]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rent_entries')
    rent_setup = models.ForeignKey(RentSetup, on_delete=models.CASCADE, related_name='entries')
    month = models.PositiveSmallIntegerField()
    year = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unpaid')
    payment_date = models.DateField(blank=True, null=True)
    last_reminder_date = models.DateField(blank=True, null=True)
    transaction = models.OneToOneField(
        'Transaction', on_delete=models.SET_NULL, null=True, blank=True, related_name='rent_entry'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-year', '-month']
        unique_together = [('rent_setup', 'month', 'year')]

    def __str__(self):
        return f"{self.rent_setup} — {self.month}/{self.year} ({self.status})"
