"""
Migration 0005 – Secure OTP storage upgrade
============================================
Changes to PasswordResetToken:
  • Replaces plaintext `otp_code` field with `otp_hash` (bcrypt hash, max 128 chars).
  • Adds `resend_count` (PositiveSmallIntegerField, default=0) for rate-limiting resend requests.

Security rationale:
  The raw OTP is now NEVER stored in the database.  Only its bcrypt hash is persisted,
  so a database dump cannot leak live OTP codes.  Verification uses check_password().
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_passwordresettoken_token_type_and_more'),
    ]

    operations = [
        # 1. Add the hashed-OTP column (nullable while we transition)
        migrations.AddField(
            model_name='passwordresettoken',
            name='otp_hash',
            field=models.CharField(
                max_length=128,
                blank=True,
                null=True,
                help_text='bcrypt hash of the 6-digit OTP.  The raw code is never stored.',
            ),
        ),

        # 2. Add resend rate-limiting counter
        migrations.AddField(
            model_name='passwordresettoken',
            name='resend_count',
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text='Number of times the OTP has been resent for this token chain.',
            ),
        ),

        # 3. Remove the old plaintext otp_code column
        migrations.RemoveField(
            model_name='passwordresettoken',
            name='otp_code',
        ),
    ]
