from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import Transaction, INCOME_SOURCES, EXPENSE_CATEGORIES, Loan, LoanPayment, Receivable, ReceivablePayment, PaymentReminder, UserProfile


class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'Enter your email address',
            'autocomplete': 'email',
        }),
        error_messages={
            'unique': 'An account with this email already exists.',
        }
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter first name',
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter last name (optional)',
        })
    )

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = (
                'w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-xl '
                'text-white placeholder-slate-400 focus:outline-none focus:ring-2 '
                'focus:ring-indigo-500 focus:border-transparent transition-all duration-200'
            )
            if field_name not in ['first_name', 'last_name', 'username', 'email']:
                field.widget.attrs['placeholder'] = field.label
        
        # Set custom field labels
        self.fields['first_name'].widget.attrs['placeholder'] = 'First name'
        self.fields['last_name'].widget.attrs['placeholder'] = 'Last name'
        self.fields['username'].widget.attrs['placeholder'] = 'Username'
        self.fields['email'].widget.attrs['placeholder'] = 'Email address'

    def clean_email(self):
        """Block only verified (active) accounts. Unverified/pending accounts are replaced on re-signup."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email, is_active=True).exists():
            raise forms.ValidationError(
                'An account with this email already exists.',
                code='email_exists'
            )
        return email


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = (
                'w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-xl '
                'text-white placeholder-slate-400 focus:outline-none focus:ring-2 '
                'focus:ring-indigo-500 focus:border-transparent transition-all duration-200'
            )
        self.fields['username'].label = 'Username or Email'
        self.fields['username'].widget.attrs['placeholder'] = 'Username or email address'
        self.fields['password'].widget.attrs['placeholder'] = 'Password'


class IncomeForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['amount', 'category', 'date', 'note']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'note': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].choices = INCOME_SOURCES
        self.fields['category'].label = 'Source'
        input_class = (
            'w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-xl '
            'text-white placeholder-slate-400 focus:outline-none focus:ring-2 '
            'focus:ring-green-500 focus:border-transparent transition-all duration-200'
        )
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = input_class
        self.fields['note'].widget.attrs['placeholder'] = 'Optional note...'
        self.fields['amount'].widget.attrs['placeholder'] = '0.00'


class ExpenseForm(forms.ModelForm):
    title = forms.CharField(
        max_length=100,
        required=True,
        label='Title',
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Monthly groceries, London trip...'}),
    )
    category = forms.ChoiceField(
        choices=[('', '— Select category —')] + list(EXPENSE_CATEGORIES),
        label='Category',
    )

    class Meta:
        model = Transaction
        fields = ['title', 'amount', 'category', 'date', 'note']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'note': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        input_class = (
            'w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-xl '
            'text-white placeholder-slate-400 focus:outline-none focus:ring-2 '
            'focus:ring-red-500 focus:border-transparent transition-all duration-200'
        )
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = input_class
        self.fields['category'].widget.attrs['class'] += ' cursor-pointer'
        self.fields['note'].widget.attrs['placeholder'] = 'Optional note...'
        self.fields['amount'].widget.attrs['placeholder'] = '0.00'


class LoanForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = ['lender_name', 'amount', 'date', 'note']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'note': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        input_class = (
            'w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-xl '
            'text-white placeholder-slate-400 focus:outline-none focus:ring-2 '
            'focus:ring-blue-500 focus:border-transparent transition-all duration-200'
        )
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = input_class
        self.fields['lender_name'].widget.attrs['placeholder'] = 'Enter lender name'
        self.fields['amount'].widget.attrs['placeholder'] = '0.00 (৳)'
        self.fields['note'].widget.attrs['placeholder'] = 'Optional note...'
        self.fields['date'].widget.attrs['class'] += ' cursor-pointer'


class LoanPaymentForm(forms.ModelForm):
    class Meta:
        model = LoanPayment
        fields = ['loan', 'amount', 'date', 'note']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'note': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            # Get loans for this user that have remaining balance
            all_loans = Loan.objects.filter(user=user)
            # Filter to only those with remaining balance
            loan_ids_with_balance = []
            for loan in all_loans:
                if loan.get_remaining() > 0:
                    loan_ids_with_balance.append(loan.id)
            self.fields['loan'].queryset = Loan.objects.filter(id__in=loan_ids_with_balance)
        input_class = (
            'w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-xl '
            'text-white placeholder-slate-400 focus:outline-none focus:ring-2 '
            'focus:ring-blue-500 focus:border-transparent transition-all duration-200'
        )
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = input_class
        self.fields['loan'].widget.attrs['class'] += ' cursor-pointer'
        self.fields['amount'].widget.attrs['placeholder'] = '0.00 (৳)'
        self.fields['note'].widget.attrs['placeholder'] = 'Optional note...'
        self.fields['date'].widget.attrs['class'] += ' cursor-pointer'


class ReceivableForm(forms.ModelForm):
    class Meta:
        model = Receivable
        fields = ['debtor_name', 'amount', 'date', 'note']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'note': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        input_class = (
            'w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-xl '
            'text-white placeholder-slate-400 focus:outline-none focus:ring-2 '
            'focus:ring-teal-500 focus:border-transparent transition-all duration-200'
        )
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = input_class
        self.fields['debtor_name'].widget.attrs['placeholder'] = 'Enter person name'
        self.fields['amount'].widget.attrs['placeholder'] = '0.00 (৳)'
        self.fields['note'].widget.attrs['placeholder'] = 'Optional note...'
        self.fields['date'].widget.attrs['class'] += ' cursor-pointer'


class ReceivablePaymentForm(forms.ModelForm):
    class Meta:
        model = ReceivablePayment
        fields = ['receivable', 'amount', 'date', 'note']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'note': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            all_receivables = Receivable.objects.filter(user=user)
            ids_with_balance = [r.id for r in all_receivables if r.get_remaining() > 0]
            self.fields['receivable'].queryset = Receivable.objects.filter(id__in=ids_with_balance)
        input_class = (
            'w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-xl '
            'text-white placeholder-slate-400 focus:outline-none focus:ring-2 '
            'focus:ring-teal-500 focus:border-transparent transition-all duration-200'
        )
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = input_class
        self.fields['receivable'].widget.attrs['class'] += ' cursor-pointer'
        self.fields['amount'].widget.attrs['placeholder'] = '0.00 (৳)'
        self.fields['note'].widget.attrs['placeholder'] = 'Optional note...'
        self.fields['date'].widget.attrs['class'] += ' cursor-pointer'


class PaymentReminderForm(forms.ModelForm):
    class Meta:
        model = PaymentReminder
        fields = ['title', 'category', 'amount', 'description', 'due_date', 'frequency', 'remind_days_before']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 2}),
            'remind_days_before': forms.Select(choices=[
                (1, '1 day before'),
                (2, '2 days before'),
                (3, '3 days before'),
                (5, '5 days before'),
                (7, '7 days before'),
            ]),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        input_class = (
            'w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-xl '
            'text-white placeholder-slate-400 focus:outline-none focus:ring-2 '
            'focus:ring-violet-500 focus:border-transparent transition-all duration-200'
        )
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = input_class
        self.fields['title'].widget.attrs['placeholder'] = 'e.g. House Rent, Netflix, Electricity'
        self.fields['amount'].widget.attrs['placeholder'] = '0.00 (£) — optional'
        self.fields['description'].widget.attrs['placeholder'] = 'Optional notes...'
        self.fields['due_date'].widget.attrs['class'] += ' cursor-pointer'
        self.fields['frequency'].widget.attrs['class'] += ' cursor-pointer'
        self.fields['category'].widget.attrs['class'] += ' cursor-pointer'
        self.fields['remind_days_before'].widget.attrs['class'] += ' cursor-pointer'


class ForgotPasswordForm(forms.Form):
    """Form for requesting password reset - email input only."""
    email = forms.EmailField(
        label='Registered Email Address',
        widget=forms.EmailInput(attrs={
            'placeholder': 'Enter your registered email',
            'autocomplete': 'email',
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        input_class = (
            'w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-xl '
            'text-white placeholder-slate-400 focus:outline-none focus:ring-2 '
            'focus:ring-indigo-500 focus:border-transparent transition-all duration-200'
        )
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = input_class
        self.fields['email'].widget.attrs['placeholder'] = 'Enter your registered email'


class VerifyOTPForm(forms.Form):
    """Form for verifying OTP code received via email."""
    otp_code = forms.CharField(
        label='6-Digit Verification Code',
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter 6-digit code',
            'autocomplete': 'one-time-code',
            'pattern': '[0-9]{6}',
            'inputmode': 'numeric',
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        input_class = (
            'w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-xl '
            'text-white placeholder-slate-400 focus:outline-none focus:ring-2 '
            'focus:ring-indigo-500 focus:border-transparent transition-all duration-200 '
            'text-center text-xl tracking-widest'
        )
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = input_class
        self.fields['otp_code'].widget.attrs['placeholder'] = '000000'


class ResetPasswordForm(forms.Form):
    """
    New-password form used after OTP verification.

    Runs Django's full AUTH_PASSWORD_VALIDATORS chain so the same rules that
    apply at registration (min length, common-password check, similarity check)
    are enforced here too.
    """
    new_password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter new password',
            'autocomplete': 'new-password',
        }),
    )
    new_password2 = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirm new password',
            'autocomplete': 'new-password',
        }),
    )

    def __init__(self, *args, user=None, **kwargs):
        """
        Accept an optional `user` kwarg so Django's UserAttributeSimilarityValidator
        can compare the new password against the user's attributes.
        """
        self._user = user
        super().__init__(*args, **kwargs)
        input_class = (
            'w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-xl '
            'text-white placeholder-slate-400 focus:outline-none focus:ring-2 '
            'focus:ring-indigo-500 focus:border-transparent transition-all duration-200'
        )
        for field in self.fields.values():
            field.widget.attrs['class'] = input_class
        self.fields['new_password1'].widget.attrs['placeholder'] = 'Enter new password'
        self.fields['new_password2'].widget.attrs['placeholder'] = 'Confirm new password'

    def clean_new_password1(self):
        password = self.cleaned_data.get('new_password1')
        if password:
            try:
                validate_password(password, user=self._user)
            except DjangoValidationError as exc:
                raise forms.ValidationError(exc.messages)
        return password

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('new_password1')
        p2 = cleaned_data.get('new_password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('The two password fields do not match.')
        return cleaned_data


class SignUpOTPForm(forms.Form):
    """OTP verification form for signup email verification."""
    otp_code = forms.CharField(
        label='6-Digit Verification Code',
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter 6-digit code',
            'autocomplete': 'one-time-code',
            'pattern': '[0-9]{6}',
            'inputmode': 'numeric',
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        input_class = (
            'w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-xl '
            'text-white placeholder-slate-400 focus:outline-none focus:ring-2 '
            'focus:ring-indigo-500 focus:border-transparent transition-all duration-200 '
            'text-center text-xl tracking-widest'
        )
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = input_class
        self.fields['otp_code'].widget.attrs['placeholder'] = '000000'


class SignupDataForm(forms.Form):
    """Temporary storage form for signup data before email verification."""
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30, required=False)
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.HiddenInput())


class EditProfileForm(forms.ModelForm):
    """Form for editing user profile information."""
    first_name = forms.CharField(
        max_length=30,
        required=True,
        label='First Name',
        widget=forms.TextInput(attrs={'placeholder': 'Enter your first name'}),
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        label='Last Name',
        widget=forms.TextInput(attrs={'placeholder': 'Enter your last name (optional)'}),
    )
    username = forms.CharField(
        max_length=150,
        required=True,
        label='Username',
        widget=forms.TextInput(attrs={'placeholder': 'Choose a unique username'}),
    )

    class Meta:
        model = UserProfile
        fields = ['address', 'phone_number', 'profile_picture']
        widgets = {
            'address': forms.TextInput(attrs={
                'placeholder': 'Street address, city, postal code',
            }),
            'phone_number': forms.TextInput(attrs={
                'placeholder': 'Contact phone number',
                'type': 'tel',
            }),
            'profile_picture': forms.FileInput(attrs={
                'accept': '.jpg,.jpeg,.png',
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        
        # Set first/last name and username from User model if provided
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['username'].initial = user.username
        
        input_class = (
            'w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-xl '
            'text-white placeholder-slate-400 focus:outline-none focus:ring-2 '
            'focus:ring-indigo-500 focus:border-transparent transition-all duration-200'
        )
        for field_name, field in self.fields.items():
            if field_name not in ['profile_picture']:
                field.widget.attrs['class'] = input_class
            else:
                field.widget.attrs['class'] = 'block w-full text-sm text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-indigo-600 file:text-white hover:file:bg-indigo-700 cursor-pointer'

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not username:
            raise forms.ValidationError('Username cannot be blank.')
        qs = User.objects.filter(username__iexact=username)
        if self.user:
            qs = qs.exclude(pk=self.user.pk)
        if qs.exists():
            raise forms.ValidationError('This username is already taken. Please choose another.')
        return username

    def clean_profile_picture(self):
        """Validate profile picture file size (max 5MB)."""
        profile_picture = self.cleaned_data.get('profile_picture')
        if profile_picture:
            # Check file size (5MB = 5242880 bytes)
            if profile_picture.size > 5 * 1024 * 1024:
                raise forms.ValidationError(
                    'Profile picture must be less than 5MB. '
                    f'Your file is {profile_picture.size / (1024*1024):.2f}MB.'
                )
        return profile_picture

    def save(self, commit=True):
        """
        Save the profile and also update the User's first_name and last_name.

        Ordering matters:
          1. Delete old picture file before overwriting the path in the DB.
          2. Save UserProfile FIRST - this runs FileField.pre_save() which
             physically writes the uploaded file to MEDIA_ROOT.
          3. Save User AFTER - this fires the save_user_profile signal which
             calls profile.save() again, but _committed=True by then so no
             second file write is attempted.

        The previous order (user.save before instance.save) fired the signal
        before the file was committed, storing the path in the DB while the
        actual file bytes were never written to disk.
        """
        instance = super().save(commit=False)

        if commit:
            # Step 1: purge old picture file if a new one is being uploaded
            if 'profile_picture' in self.changed_data and self.instance.pk:
                try:
                    stale = self.instance.__class__.objects.get(pk=self.instance.pk)
                    if stale.profile_picture:
                        stale.profile_picture.delete(save=False)
                except Exception:
                    pass  # Never block the save due to a stale-file error

            # Step 2: write UserProfile to DB; FileField.pre_save() runs here
            # and physically writes the uploaded bytes to MEDIA_ROOT.
            instance.save()

        # Step 3: write User name fields. post_save signal will call
        # profile.save() again but FieldFile._committed is True by now,
        # so it is a harmless no-op for file I/O.
        if self.user:
            self.user.first_name = self.cleaned_data.get('first_name', '')
            self.user.last_name = self.cleaned_data.get('last_name', '')
            self.user.username = self.cleaned_data.get('username', self.user.username)
            if commit:
                self.user.save()

        return instance


class ChangePasswordForm(forms.Form):
    """Form for changing user password with current password verification."""
    current_password = forms.CharField(
        label='Current Password',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter your current password',
            'autocomplete': 'current-password',
        }),
    )
    new_password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter your new password',
            'autocomplete': 'new-password',
        }),
    )
    new_password2 = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirm your new password',
            'autocomplete': 'new-password',
        }),
    )

    def __init__(self, *args, user=None, **kwargs):
        """Accept optional user kwarg for password validation."""
        self.user = user
        super().__init__(*args, **kwargs)
        
        input_class = (
            'w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-xl '
            'text-white placeholder-slate-400 focus:outline-none focus:ring-2 '
            'focus:ring-indigo-500 focus:border-transparent transition-all duration-200'
        )
        for field in self.fields.values():
            field.widget.attrs['class'] = input_class

    def clean_current_password(self):
        """Verify that current password is correct."""
        current_password = self.cleaned_data.get('current_password')
        if self.user and not self.user.check_password(current_password):
            raise forms.ValidationError(
                'Your current password is incorrect.',
                code='password_incorrect',
            )
        return current_password

    def clean_new_password1(self):
        """Validate new password against Django's validators."""
        new_password = self.cleaned_data.get('new_password1')
        if new_password:
            try:
                validate_password(new_password, user=self.user)
            except DjangoValidationError as exc:
                raise forms.ValidationError(exc.messages)
        return new_password

    def clean(self):
        """Ensure new passwords match and are different from current."""
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')
        current_password = cleaned_data.get('current_password')

        if new_password1 and new_password2:
            if new_password1 != new_password2:
                raise forms.ValidationError(
                    'The new passwords do not match.',
                    code='password_mismatch',
                )
            
            # Ensure new password is different from current
            if current_password and self.user and self.user.check_password(new_password1):
                raise forms.ValidationError(
                    'Your new password cannot be the same as your current password.',
                    code='password_unchanged',
                )

        return cleaned_data

    def save(self):
        """Set the new password on the user."""
        if self.user:
            new_password = self.cleaned_data.get('new_password1')
            self.user.set_password(new_password)
            self.user.save()
            return self.user
        return None
