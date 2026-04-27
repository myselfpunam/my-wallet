"""
core/views.py — My Wallet

Authentication views implement a two-step flow for both registration and
password reset:

  Registration flow
  -----------------
  1. signup_view          -> collect user data, create INACTIVE user, send OTP via SMTP
  2. signup_verify_otp    -> verify OTP input, activate user, auto-login
  3. signup_resend_otp    -> regenerate & resend OTP (rate-limited to OTP_MAX_RESENDS)

  Password-reset flow
  -------------------
  1. forgot_password_request -> collect email, send OTP via SMTP
  2. verify_otp              -> verify OTP input, set session flag
  3. reset_password          -> accept new password, hash & save

Security guarantees:
  * Raw OTP is NEVER stored in the database -- only its bcrypt hash.
  * OTP is NEVER shown in any UI message or HTTP response.
  * Every OTP has a hard expiry (OTP_EXPIRY_MINUTES, default 10 min).
  * Wrong-attempt count is tracked per session (OTP_MAX_ATTEMPTS, default 5).
  * Resend requests are rate-limited (OTP_MAX_RESENDS, default 3).
  * Passwords are stored using Django's PBKDF2-SHA256 hasher (default).
"""

import json
import calendar
import logging
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .forms import (
    SignUpForm, LoginForm,
    IncomeForm, ExpenseForm,
    LoanForm, LoanPaymentForm,
    ForgotPasswordForm, VerifyOTPForm, ResetPasswordForm,
    SignUpOTPForm, EditProfileForm, ChangePasswordForm,
)
from .models import (
    Transaction, EXPENSE_CATEGORIES, INCOME_SOURCES,
    Loan, LoanPayment, PasswordResetToken, UserProfile,
)
from .utils import send_verification_email, send_password_reset_email

logger = logging.getLogger(__name__)

OTP_EXPIRY_MINUTES = getattr(settings, 'OTP_EXPIRY_MINUTES', 10)
OTP_MAX_ATTEMPTS   = getattr(settings, 'OTP_MAX_ATTEMPTS',   5)
OTP_MAX_RESENDS    = getattr(settings, 'OTP_MAX_RESENDS',    3)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_month_stats(user, year, month):
    transactions = Transaction.objects.filter(
        user=user, date__year=year, date__month=month
    )
    total_income = transactions.filter(type='income').aggregate(
        total=Sum('amount'))['total'] or Decimal('0.00')
    total_expense = transactions.filter(type='expense').aggregate(
        total=Sum('amount'))['total'] or Decimal('0.00')
    return {
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': total_income - total_expense,
        'transactions': transactions,
    }


def _clear_signup_session(request):
    for key in ('signup_user_id', 'signup_token', 'signup_otp_attempts'):
        request.session.pop(key, None)


def _clear_reset_session(request):
    for key in ('reset_token', 'reset_user_id', 'reset_token_valid', 'otp_attempts'):
        request.session.pop(key, None)


# ---------------------------------------------------------------------------
# Registration Step 1 — collect data, send OTP
# ---------------------------------------------------------------------------

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']

            # Remove stale inactive accounts sharing this email (previous incomplete signup)
            User.objects.filter(email=email, is_active=False).delete()

            if User.objects.filter(email=email, is_active=True).exists():
                messages.error(request, 'An account with this email already exists.')
                return render(request, 'core/signup.html', {'form': form})

            # Create inactive user — not usable until OTP verified
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=email,
                password=form.cleaned_data['password1'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                is_active=False,
            )

            # Generate OTP — raw code returned ONCE, never stored
            token, raw_otp = PasswordResetToken.create_for_user(
                user=user,
                token_type='email_verification',
                expiry_minutes=OTP_EXPIRY_MINUTES,
            )

            sent = send_verification_email(user, raw_otp)
            del raw_otp  # immediately discard after sending

            if not sent:
                user.delete()
                messages.error(
                    request,
                    'We could not send the verification email. '
                    'Please check your email address and try again.'
                )
                return render(request, 'core/signup.html', {'form': form})

            request.session['signup_user_id']     = user.id
            request.session['signup_token']       = token.token
            request.session['signup_otp_attempts'] = 0

            messages.success(
                request,
                f'A 6-digit verification code has been sent to {email}. '
                f'It expires in {OTP_EXPIRY_MINUTES} minutes.'
            )
            return redirect('signup_verify_otp')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = SignUpForm()

    return render(request, 'core/signup.html', {'form': form})


# ---------------------------------------------------------------------------
# Registration Step 2 — verify OTP, activate account
# ---------------------------------------------------------------------------

def signup_verify_otp(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    signup_user_id = request.session.get('signup_user_id')
    signup_token   = request.session.get('signup_token')

    if not signup_user_id or not signup_token:
        messages.error(request, 'Please start the sign-up process first.')
        return redirect('signup')

    try:
        user = User.objects.get(id=signup_user_id, is_active=False)
    except User.DoesNotExist:
        _clear_signup_session(request)
        messages.error(request, 'Verification session expired. Please sign up again.')
        return redirect('signup')

    otp_attempts = request.session.get('signup_otp_attempts', 0)
    if otp_attempts >= OTP_MAX_ATTEMPTS:
        _clear_signup_session(request)
        user.delete()
        messages.error(request, 'Too many incorrect attempts. Please sign up again.')
        return redirect('signup')

    if request.method == 'POST':
        form = SignUpOTPForm(request.POST)
        if form.is_valid():
            entered_otp = form.cleaned_data['otp_code']

            try:
                token_obj = PasswordResetToken.objects.get(
                    token=signup_token,
                    token_type='email_verification',
                    used=False,
                    user=user,
                )
            except PasswordResetToken.DoesNotExist:
                _clear_signup_session(request)
                user.delete()
                messages.error(request, 'Invalid verification request. Please sign up again.')
                return redirect('signup')

            if token_obj.is_expired:
                token_obj.used = True
                token_obj.save(update_fields=['used'])
                _clear_signup_session(request)
                user.delete()
                messages.error(request, 'Verification code expired. Please sign up again.')
                return redirect('signup')

            if token_obj.verify_otp(entered_otp):
                # Correct OTP — activate account
                user.is_active = True
                user.save(update_fields=['is_active'])
                token_obj.used = True
                token_obj.save(update_fields=['used'])
                _clear_signup_session(request)
                login(request, user)
                messages.success(
                    request,
                    f'Account created and verified! '
                    f'Welcome to My Wallet, {user.first_name or user.username}!'
                )
                return redirect('dashboard')
            else:
                otp_attempts += 1
                request.session['signup_otp_attempts'] = otp_attempts
                remaining = OTP_MAX_ATTEMPTS - otp_attempts
                if remaining <= 0:
                    _clear_signup_session(request)
                    user.delete()
                    messages.error(request, 'Too many incorrect attempts. Registration cancelled.')
                    return redirect('signup')
                messages.error(request, f'Invalid code. {remaining} attempt(s) remaining.')
    else:
        form = SignUpOTPForm()

    return render(request, 'core/signup_verify_otp.html', {
        'form': form,
        'email': user.email,
        'attempts_left': OTP_MAX_ATTEMPTS - otp_attempts,
        'max_attempts': OTP_MAX_ATTEMPTS,
    })


# ---------------------------------------------------------------------------
# Registration — Resend OTP
# ---------------------------------------------------------------------------

def signup_resend_otp(request):
    signup_user_id = request.session.get('signup_user_id')
    if not signup_user_id:
        messages.error(request, 'Please sign up first.')
        return redirect('signup')

    try:
        user = User.objects.get(id=signup_user_id, is_active=False)
    except User.DoesNotExist:
        _clear_signup_session(request)
        messages.error(request, 'Session expired. Please sign up again.')
        return redirect('signup')

    # Count total tokens ever created for this user (first + resends)
    total_tokens = PasswordResetToken.objects.filter(
        user=user, token_type='email_verification'
    ).count()
    actual_resends = max(total_tokens - 1, 0)

    if actual_resends >= OTP_MAX_RESENDS:
        _clear_signup_session(request)
        user.delete()
        messages.error(
            request,
            'Maximum resend limit reached. Please sign up again with a valid email.'
        )
        return redirect('signup')

    token, raw_otp = PasswordResetToken.create_for_user(
        user=user,
        token_type='email_verification',
        expiry_minutes=OTP_EXPIRY_MINUTES,
    )
    sent = send_verification_email(user, raw_otp)
    del raw_otp

    if not sent:
        messages.error(request, 'Failed to resend. Please try again shortly.')
        return redirect('signup_verify_otp')

    request.session['signup_token']        = token.token
    request.session['signup_otp_attempts'] = 0

    remaining_resends = OTP_MAX_RESENDS - (actual_resends + 1)
    messages.success(
        request,
        f'New code sent to {user.email}. '
        f'({remaining_resends} resend(s) remaining.)'
    )
    return redirect('signup_verify_otp')


# ---------------------------------------------------------------------------
# Login / Logout
# ---------------------------------------------------------------------------

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    return render(request, 'core/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


# ---------------------------------------------------------------------------
# Forgot Password Step 1 — email -> OTP
# ---------------------------------------------------------------------------

def forgot_password_request(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']

            try:
                user = User.objects.get(email=email, is_active=True)
                token, raw_otp = PasswordResetToken.create_for_user(
                    user=user,
                    token_type='password_reset',
                    expiry_minutes=OTP_EXPIRY_MINUTES,
                )
                sent = send_password_reset_email(user, raw_otp)
                del raw_otp

                if sent:
                    request.session['reset_token']   = token.token
                    request.session['reset_user_id'] = user.id
                    messages.success(
                        request,
                        f'A password reset code has been sent to {email}. '
                        f'It expires in {OTP_EXPIRY_MINUTES} minutes.'
                    )
                    return redirect('verify_otp')
                else:
                    token.used = True
                    token.save(update_fields=['used'])
                    messages.error(
                        request,
                        'Could not send reset email. Please try again in a few minutes.'
                    )
                    return render(request, 'core/forgot_password.html', {'form': form})

            except User.DoesNotExist:
                pass  # Fall through to generic message below

            # Generic message — prevents email enumeration
            messages.info(
                request,
                'If an account with that email exists, a reset code has been sent to it.'
            )
            return redirect('forgot_password')
    else:
        form = ForgotPasswordForm()

    return render(request, 'core/forgot_password.html', {'form': form})


# ---------------------------------------------------------------------------
# Forgot Password Step 2 — verify OTP
# ---------------------------------------------------------------------------

def verify_otp(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    reset_token_value = request.session.get('reset_token')
    if not reset_token_value:
        messages.error(request, 'Please request a password reset first.')
        return redirect('forgot_password')

    try:
        reset_token = PasswordResetToken.objects.select_related('user').get(
            token=reset_token_value,
            token_type='password_reset',
            used=False,
        )
    except PasswordResetToken.DoesNotExist:
        _clear_reset_session(request)
        messages.error(request, 'Invalid or expired reset request. Please try again.')
        return redirect('forgot_password')

    if reset_token.is_expired:
        reset_token.used = True
        reset_token.save(update_fields=['used'])
        _clear_reset_session(request)
        messages.error(request, 'Reset code expired. Please request a new one.')
        return redirect('forgot_password')

    if request.method == 'POST':
        form = VerifyOTPForm(request.POST)
        if form.is_valid():
            entered_otp = form.cleaned_data['otp_code']
            attempts = request.session.get('otp_attempts', 0)

            if attempts >= OTP_MAX_ATTEMPTS:
                reset_token.used = True
                reset_token.save(update_fields=['used'])
                _clear_reset_session(request)
                messages.error(request, 'Too many attempts. Please request a new code.')
                return redirect('forgot_password')

            if reset_token.verify_otp(entered_otp):
                reset_token.used = True
                reset_token.save(update_fields=['used'])
                request.session['reset_token_valid'] = True
                request.session['reset_user_id']     = reset_token.user.id
                request.session.pop('otp_attempts', None)
                request.session.pop('reset_token', None)
                messages.success(request, 'Code verified! Please set your new password.')
                return redirect('reset_password')
            else:
                attempts += 1
                request.session['otp_attempts'] = attempts
                remaining = OTP_MAX_ATTEMPTS - attempts
                if remaining <= 0:
                    reset_token.used = True
                    reset_token.save(update_fields=['used'])
                    _clear_reset_session(request)
                    messages.error(request, 'Too many attempts. Please request a new code.')
                    return redirect('forgot_password')
                messages.error(request, f'Invalid code. {remaining} attempt(s) remaining.')
    else:
        form = VerifyOTPForm()
        request.session.pop('otp_attempts', None)

    return render(request, 'core/verify_otp.html', {
        'form': form,
        'email': reset_token.user.email,
    })


# ---------------------------------------------------------------------------
# Forgot Password Step 3 — set new password
# ---------------------------------------------------------------------------

def reset_password(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if not request.session.get('reset_token_valid'):
        messages.error(request, 'Please verify your reset code first.')
        return redirect('forgot_password')

    user_id = request.session.get('reset_user_id')
    if not user_id:
        messages.error(request, 'Invalid session. Please start over.')
        return redirect('forgot_password')

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        _clear_reset_session(request)
        messages.error(request, 'User not found.')
        return redirect('forgot_password')

    if request.method == 'POST':
        form = ResetPasswordForm(request.POST, user=user)
        if form.is_valid():
            user.set_password(form.cleaned_data['new_password1'])
            user.save()
            PasswordResetToken.objects.filter(user=user).update(used=True)
            _clear_reset_session(request)
            logger.info("Password reset for user %s (id=%s)", user.username, user.id)
            messages.success(
                request,
                'Password reset successful! You can now sign in with your new password.'
            )
            return redirect('login')
    else:
        form = ResetPasswordForm(user=user)

    return render(request, 'core/reset_password.html', {
        'form': form,
        'email': user.email,
    })


# ===========================================================================
# Dashboard
# ===========================================================================

@login_required
def dashboard_view(request):
    today = date.today()
    year  = int(request.GET.get('year',  today.year))
    month = int(request.GET.get('month', today.month))

    stats = get_month_stats(request.user, year, month)
    recent_transactions = stats['transactions'].order_by('-date', '-created_at')[:5]

    all_income  = Transaction.objects.filter(user=request.user, type='income').aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    all_expense = Transaction.objects.filter(user=request.user, type='expense').aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    overall_balance = all_income - all_expense

    all_loans = Loan.objects.filter(user=request.user).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    all_paid  = LoanPayment.objects.filter(user=request.user).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    outstanding_loan = all_loans - all_paid
    
    active_lenders_count = 0
    seen_lenders = set()
    for loan in Loan.objects.filter(user=request.user):
        if loan.lender_name not in seen_lenders:
            seen_lenders.add(loan.lender_name)
            if loan.get_remaining() > 0:
                active_lenders_count += 1

    monthly_data = []
    for i in range(5, -1, -1):
        if month - i <= 0:
            m = month - i + 12
            y = year - 1
        else:
            m = month - i
            y = year
        s = get_month_stats(request.user, y, m)
        monthly_data.append({
            'month': calendar.month_abbr[m],
            'income': float(s['total_income']),
            'expense': float(s['total_expense']),
        })

    expense_breakdown = Transaction.objects.filter(
        user=request.user, type='expense', date__year=year, date__month=month
    ).values('category').annotate(total=Sum('amount')).order_by('-total')

    category_labels = []
    category_data   = []
    category_colors = [
        '#ef4444','#f97316','#eab308','#22c55e','#06b6d4',
        '#6366f1','#ec4899','#8b5cf6','#14b8a6','#f43f5e','#84cc16','#0ea5e9',
    ]
    for item in expense_breakdown:
        all_choices = dict(EXPENSE_CATEGORIES)
        category_labels.append(all_choices.get(item['category'], item['category'].title()))
        category_data.append(float(item['total']))

    months_list = [{'value': i, 'name': calendar.month_name[i]} for i in range(1, 13)]
    years_list  = list(range(today.year - 3, today.year + 2))

    context = {
        'stats': stats,
        'recent_transactions': recent_transactions,
        'selected_month': month,
        'selected_year': year,
        'months_list': months_list,
        'years_list': years_list,
        'monthly_data_json': json.dumps(monthly_data),
        'category_labels_json': json.dumps(category_labels),
        'category_data_json': json.dumps(category_data),
        'category_colors_json': json.dumps(category_colors[:len(category_data)]),
        'total_income_float': float(stats['total_income']),
        'total_expense_float': float(stats['total_expense']),
        'overall_balance': overall_balance,
        'overall_balance_float': float(overall_balance),
        'outstanding_loan': outstanding_loan,
        'outstanding_loan_float': float(outstanding_loan),
        'active_lenders_count': active_lenders_count,
    }
    return render(request, 'core/dashboard.html', context)


# ===========================================================================
# Transactions
# ===========================================================================

@login_required
def add_income_view(request):
    if request.method == 'POST':
        form = IncomeForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.type = 'income'
            transaction.save()
            messages.success(request, f'Income of £{transaction.amount} added successfully!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = IncomeForm(initial={'date': date.today()})
    return render(request, 'core/add_income.html', {'form': form})


@login_required
def add_expense_view(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.type = 'expense'
            transaction.save()
            messages.success(request, f'Expense of £{transaction.amount} recorded successfully!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = ExpenseForm(initial={'date': date.today()})
    return render(request, 'core/add_expense.html', {'form': form})


@login_required
def transactions_view(request):
    today = date.today()
    year  = int(request.GET.get('year',  today.year))
    month = int(request.GET.get('month', today.month))
    filter_type = request.GET.get('type', 'all')

    transactions = Transaction.objects.filter(
        user=request.user, date__year=year, date__month=month
    ).order_by('-date', '-created_at')

    if filter_type == 'income':
        transactions = transactions.filter(type='income')
    elif filter_type == 'expense':
        transactions = transactions.filter(type='expense')

    stats = get_month_stats(request.user, year, month)
    months_list = [{'value': i, 'name': calendar.month_name[i]} for i in range(1, 13)]
    years_list  = list(range(today.year - 3, today.year + 2))

    context = {
        'transactions': transactions,
        'stats': stats,
        'selected_month': month,
        'selected_year': year,
        'filter_type': filter_type,
        'months_list': months_list,
        'years_list': years_list,
    }
    return render(request, 'core/transactions.html', context)


@login_required
def edit_transaction_view(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
    if request.method == 'POST':
        form = (IncomeForm if transaction.type == 'income' else ExpenseForm)(
            request.POST, instance=transaction
        )
        if form.is_valid():
            form.save()
            messages.success(request, 'Transaction updated successfully!')
            return redirect('transactions')
    else:
        form = (IncomeForm if transaction.type == 'income' else ExpenseForm)(
            instance=transaction
        )
    return render(request, 'core/edit_transaction.html', {
        'form': form, 'transaction': transaction
    })


@login_required
def delete_transaction_view(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
    if request.method == 'POST':
        amount = transaction.amount
        ttype  = transaction.type
        transaction.delete()
        messages.success(request, f'{ttype.title()} of £{amount} deleted.')
        return redirect('transactions')
    return render(request, 'core/delete_confirm.html', {'transaction': transaction})


# ===========================================================================
# Analytics
# ===========================================================================

@login_required
def analytics_view(request):
    today = date.today()
    year  = int(request.GET.get('year',  today.year))
    month = int(request.GET.get('month', today.month))

    stats = get_month_stats(request.user, year, month)

    monthly_trend = []
    for m in range(1, 13):
        s = get_month_stats(request.user, year, m)
        monthly_trend.append({
            'month': calendar.month_abbr[m],
            'income': float(s['total_income']),
            'expense': float(s['total_expense']),
            'balance': float(s['balance']),
        })

    expense_breakdown = Transaction.objects.filter(
        user=request.user, type='expense', date__year=year, date__month=month
    ).values('category').annotate(total=Sum('amount')).order_by('-total')

    income_breakdown = Transaction.objects.filter(
        user=request.user, type='income', date__year=year, date__month=month
    ).values('category').annotate(total=Sum('amount')).order_by('-total')

    expense_cats = dict(EXPENSE_CATEGORIES)
    income_cats  = dict(INCOME_SOURCES)

    context = {
        'stats': stats,
        'selected_month': month,
        'selected_year': year,
        'months_list': [{'value': i, 'name': calendar.month_name[i]} for i in range(1, 13)],
        'years_list': list(range(today.year - 3, today.year + 2)),
        'monthly_trend_json': json.dumps(monthly_trend),
        'expense_labels_json': json.dumps([expense_cats.get(i['category'], i['category'].title()) for i in expense_breakdown]),
        'expense_data_json':   json.dumps([float(i['total']) for i in expense_breakdown]),
        'income_labels_json':  json.dumps([income_cats.get(i['category'],  i['category'].title()) for i in income_breakdown]),
        'income_data_json':    json.dumps([float(i['total']) for i in income_breakdown]),
        'total_income_float':  float(stats['total_income']),
        'total_expense_float': float(stats['total_expense']),
    }
    return render(request, 'core/analytics.html', context)


# ===========================================================================
# Loans
# ===========================================================================

@login_required
def loans_view(request):
    all_loan_objects = Loan.objects.filter(user=request.user)
    total_loaned = all_loan_objects.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_paid   = LoanPayment.objects.filter(user=request.user).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    outstanding  = total_loaned - total_paid

    filter_status  = request.GET.get('filter', 'all')
    all_loans_list = list(all_loan_objects.order_by('-date', '-created_at'))

    if filter_status == 'active':
        loans = [l for l in all_loans_list if l.get_remaining() > 0]
    elif filter_status == 'paid':
        loans = [l for l in all_loans_list if l.get_remaining() <= 0]
    else:
        loans = all_loans_list

    loan_details = [{
        'id': l.id,
        'lender': l.lender_name,
        'borrowed': float(l.amount),
        'paid': float(l.get_total_paid()),
        'due': float(l.get_remaining()),
        'date': l.date,
        'note': l.note,
    } for l in loans]

    payment_history = []
    for p in LoanPayment.objects.filter(user=request.user).select_related('loan').order_by('-date', '-created_at'):
        rl = Loan.objects.filter(user=request.user, lender_name=p.loan.lender_name).first()
        payment_history.append({
            'lender': p.loan.lender_name,
            'paid': float(p.amount),
            'date': p.date,
            'note': p.note,
            'remaining': float(rl.get_remaining()) if rl else 0,
        })

    context = {
        'loans': loans,
        'total_loaned': total_loaned,
        'total_paid': total_paid,
        'outstanding': outstanding,
        'total_loaned_count': len(all_loans_list),
        'active_count': len([l for l in all_loans_list if l.get_remaining() > 0]),
        'paid_count':   len([l for l in all_loans_list if l.get_remaining() <= 0]),
        'filter_status': filter_status,
        'loan_details': loan_details,
        'payment_history': payment_history,
    }
    return render(request, 'core/loans.html', context)


@login_required
def add_loan_view(request):
    if request.method == 'POST':
        form = LoanForm(request.POST)
        if form.is_valid():
            loan = form.save(commit=False)
            loan.user = request.user
            loan.save()
            messages.success(request, f'Loan of £{loan.amount} from {loan.lender_name} added successfully!')
            return redirect('loans')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = LoanForm(initial={'date': date.today()})
    return render(request, 'core/add_loan.html', {'form': form})


@login_required
def loan_payment_view(request):
    if request.method == 'POST':
        form = LoanPaymentForm(request.POST, user=request.user)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.user = request.user
            payment.save()
            messages.success(request, f'Payment of £{payment.amount} to {payment.loan.lender_name} recorded successfully!')
            return redirect('loans')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = LoanPaymentForm(user=request.user, initial={'date': date.today()})
    return render(request, 'core/loan_payment.html', {'form': form})


@login_required
def edit_loan_view(request, pk):
    loan = get_object_or_404(Loan, pk=pk, user=request.user)
    if request.method == 'POST':
        form = LoanForm(request.POST, instance=loan)
        if form.is_valid():
            form.save()
            messages.success(request, 'Loan updated successfully!')
            return redirect('loans')
    else:
        form = LoanForm(instance=loan)
    return render(request, 'core/edit_loan.html', {'form': form, 'loan': loan})


@login_required
def delete_loan_view(request, pk):
    loan = get_object_or_404(Loan, pk=pk, user=request.user)
    if request.method == 'POST':
        lender = loan.lender_name
        amount = loan.amount
        loan.delete()
        messages.success(request, f'Loan of £{amount} from {lender} deleted.')
        return redirect('loans')
    return render(request, 'core/delete_loan_confirm.html', {'loan': loan})


# ---------------------------------------------------------------------------
# Profile Management
# ---------------------------------------------------------------------------

@login_required
def profile_view(request):
    """Display user profile with all their information."""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        # Create profile if it doesn't exist (for existing users)
        profile = UserProfile.objects.create(user=request.user)
    
    context = {
        'profile': profile,
        'page_title': 'My Profile',
    }
    return render(request, 'core/profile.html', context)


@login_required
def edit_profile_view(request):
    """Allow user to edit their profile information."""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    
    if request.method == 'POST':
        form = EditProfileForm(
            request.POST,
            request.FILES,
            instance=profile,
            user=request.user
        )
        
        if form.is_valid():
            form.save(commit=True)
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = EditProfileForm(instance=profile, user=request.user)
    
    context = {
        'form': form,
        'profile': profile,
        'page_title': 'Edit Profile',
    }
    return render(request, 'core/edit_profile.html', context)


@login_required
def change_password_view(request):
    """Allow user to change their password securely."""
    if request.method == 'POST':
        form = ChangePasswordForm(request.POST, user=request.user)
        
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Password changed successfully!')
            # Redirect to login to re-authenticate with new password
            return redirect('login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')
    else:
        form = ChangePasswordForm(user=request.user)
    
    context = {
        'form': form,
        'page_title': 'Change Password',
    }
    return render(request, 'core/change_password.html', context)


@login_required
def delete_profile_picture_view(request):
    """Delete user's profile picture."""
    if request.method == 'POST':
        try:
            profile = request.user.profile
            if profile.profile_picture:
                profile.delete_profile_picture()
                messages.success(request, 'Profile picture deleted successfully!')
            else:
                messages.warning(request, 'No profile picture to delete.')
        except UserProfile.DoesNotExist:
            messages.error(request, 'Profile not found.')
        
        return redirect('profile')
    
    return redirect('profile')
