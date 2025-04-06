from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.files.storage import default_storage
import logging
from cloudinary.models import CloudinaryField

logger = logging.getLogger(__name__)

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)
    profile_photo = CloudinaryField('image', null=True, blank=True)
    location = models.CharField(max_length=100, blank=True)
    joined_date = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s profile"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.profile_photo:
            logger.info(f"Profile photo URL: {self.profile_photo.url}")
        else:
            logger.info("No profile photo set")

    @property
    def profile_photo_url(self):
        if self.profile_photo:
            return self.profile_photo.url
        return None

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.profile.save()
    except Profile.DoesNotExist:
        Profile.objects.create(user=instance)

class Plant(models.Model):
    name = models.CharField(max_length=100)
    scientific_name = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    plant_photo = CloudinaryField('plant_photo', null=True, blank=True)
    is_public = models.BooleanField(default=False)
    likes = models.ManyToManyField(User, related_name='liked_plants', blank=True)
    comments = models.ManyToManyField('Comment', related_name='plants', blank=True)

    def __str__(self):
        return f"{self.name} ({self.scientific_name})"

    @property
    def plant_photo_url(self):
        if self.plant_photo:
            return self.plant_photo.url
        return None

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.plant_photo:
            print(f"Plant photo URL: {self.plant_photo.url}")

class PlantDetail(models.Model):
    plant = models.ForeignKey(Plant, related_name='details', on_delete=models.CASCADE)
    header = models.CharField(max_length=100)
    information = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.header} - {self.plant.name}"

class Observation(models.Model):
    """Model for plant observations."""
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name='observations')
    note = models.TextField()
    image = CloudinaryField('image', null=True, blank=True)  # Use CloudinaryField instead of URLField
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Observation for {self.plant.name} at {self.created_at}"

    @property
    def image_url(self):
        if self.image:
            return self.image.url
        return None

class PlantPhoto(models.Model):
    plant = models.ForeignKey(Plant, related_name='photos', on_delete=models.CASCADE)
    image = CloudinaryField('image', null=True, blank=True)  # Use CloudinaryField instead of ImageField
    caption = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Photo of {self.plant.name} - {self.created_at.strftime('%Y-%m-%d')}"

    @property
    def image_url(self):
        if self.image:
            return self.image.url
        return None

class Comment(models.Model):
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name='plant_comments')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment by {self.author.username} on {self.plant.name}"

    def get_replies(self):
        return self.replies.all().order_by('created_at')

class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f'Message from {self.sender} to {self.recipient}'
