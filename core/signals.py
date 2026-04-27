"""
Signal handlers for core models.

Automatically creates a UserProfile when a new User is created, ensuring
every user has an associated profile without manual intervention.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create a UserProfile when a new User is created.
    
    This ensures that every user has an associated profile.
    """
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, created, **kwargs):
    """
    Keep the UserProfile in sync when the User is saved.

    Only runs for *existing* users (created=False) to avoid a double-save
    on new registrations (create_user_profile already handles those).
    Also skips saving if the profile's picture field has an uncommitted
    UploadedFile attached — that means a form save is in progress and
    FileField.pre_save() has not run yet; saving here would store the DB
    path before the file bytes are written to disk.
    """
    if created:
        return  # handled by create_user_profile

    try:
        profile = instance.profile
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=instance)
        return

    # Safety check: if a fresh UploadedFile is still attached (not yet
    # committed to storage), skip the save so we don't write a broken path.
    from django.core.files.uploadedfile import UploadedFile
    pic = profile.__dict__.get('profile_picture')
    if isinstance(pic, UploadedFile):
        return  # form's instance.save() will handle this

    profile.save()
