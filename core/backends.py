from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User


class EmailOrUsernameBackend(ModelBackend):
    """
    Authenticate with either username or email address.
    Falls back to Django's default username check so existing behaviour is preserved.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        # Email path
        if '@' in username:
            try:
                user = User.objects.get(email__iexact=username, is_active=True)
            except User.DoesNotExist:
                return None
            except User.MultipleObjectsReturned:
                # If somehow two active accounts share an email, refuse silently
                return None
        else:
            # Username path
            try:
                user = User.objects.get(username__iexact=username)
            except User.DoesNotExist:
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
