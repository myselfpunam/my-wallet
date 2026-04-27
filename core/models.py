from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum
from django.utils.crypto import get_random_string
from django.contrib.auth.hashers import make_password, check_password
from decimal import Decimal
from django.core.validators import FileExtensionValidator
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
    ('food', 'Food & Dining'),
    ('transport', 'Transport'),
    ('rent', 'Rent & Housing'),
    ('shopping', 'Shopping'),
    ('healthcare', 'Healthcare'),
    ('entertainment', 'Entertainment'),
    ('utilities', 'Utilities'),
    ('education', 'Education'),
    ('travel', 'Travel'),
    ('subscriptions', 'Subscriptions'),
    ('insurance', 'Insurance'),
    ('savings', 'Savings'),
    ('other', 'Other'),
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
        all_choices = dict(INCOME_SOURCES + EXPENSE_CATEGORIES)
        return all_choices.get(self.category, self.category.title())

    def get_category_icon(self):
        icons = {
            # Income
            'salary': '💼', 'freelance': '💻', 'gift': '🎁',
            'investment': '📈', 'business': '🏢', 'rental': '🏠',
            'bonus': '⭐', 'refund': '↩️', 
            # Expense
            'food': '🍽️', 'transport': '🚗', 'rent': '🏠',
            'shopping': '🛍️', 'healthcare': '🏥', 'entertainment': '🎬',
            'utilities': '⚡', 'education': '📚', 'travel': '✈️',
            'subscriptions': '📱', 'insurance': '🛡️', 'savings': '🏦',
            'other': '📋',
        }
        return icons.get(self.category, '💰')


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
