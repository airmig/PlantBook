from django import forms
from .models import Plant, Observation, PlantPhoto, Profile, Comment, Message
from nudenet import NudeDetector
import tempfile
import os
import logging
from django.core.files.base import ContentFile
from PIL import Image
import io
from django.core.files.storage import default_storage
import cloudinary
import time
from cloudinary.forms import CloudinaryFileField
import requests
import numpy as np
import cv2

logger = logging.getLogger(__name__)

class PlantForm(forms.ModelForm):
    """Form for creating and editing plants."""
    plant_photo = CloudinaryFileField(
        options={
            'folder': 'plantbook/plants',
            'resource_type': 'image',
            'allowed_formats': ['jpg', 'jpeg', 'png', 'gif']
        }
    )

    class Meta:
        model = Plant
        fields = ['name', 'scientific_name', 'description', 'plant_photo', 'is_public']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
        }

class ObservationForm(forms.ModelForm):
    """Form for creating observations."""
    image = CloudinaryFileField(
        options={
            'folder': 'plantbook/observations',
            'resource_type': 'image',
            'allowed_formats': ['jpg', 'jpeg', 'png', 'gif']
        }
    )

    class Meta:
        model = Observation
        fields = ['note', 'image']
        widgets = {
            'note': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'note': 'Observation Note',
            'image': 'Observation Image'
        }
        help_texts = {
            'note': 'Enter your observation details',
            'image': 'Optional: Upload an image for your observation'
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            try:
                # Get the image URL from Cloudinary
                image_url = image.url
                
                # Download the image
                response = requests.get(image_url)
                if response.status_code != 200:
                    raise forms.ValidationError("Failed to download image")
                
                # Convert the image data to a numpy array
                image_data = np.frombuffer(response.content, np.uint8)
                img = cv2.imdecode(image_data, cv2.IMREAD_COLOR)
                
                if img is None:
                    raise forms.ValidationError("Invalid image format")
                
                # Save the image temporarily
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                cv2.imwrite(temp_file.name, img)
                
                try:
                    # Run NSFW detection
                    detector = NudeDetector()
                    result = detector.detect(temp_file.name)
                    
                    # Log detection results
                    logger.info(f"NSFW detection results: {result}")
                    
                    # Check if any NSFW content was detected
                    nsfw_detected = False
                    for detection in result:
                        # Log each detection
                        logger.info(f"Detected: {detection['class']} with confidence: {detection['score']}")
                        
                        # Check for NSFW content with confidence threshold
                        if detection['score'] > 0.2:  # Adjust this threshold as needed
                            if detection['class'] in [
                                'NSFW',
                                'EXPOSED_BREAST_F',
                                'EXPOSED_GENITALIA_F',
                                'EXPOSED_GENITALIA_M',
                                'EXPOSED_ANUS',
                                'EXPOSED_BUTTOCKS',
                                'EXPOSED_FEET',
                                'EXPOSED_BREAST_M',
                                'FEMALE_GENITALIA_EXPOSED',
                                'MALE_GENITALIA_EXPOSED',
                                'FEMALE_BREAST_EXPOSED',
                                'MALE_BREAST_EXPOSED',
                                'BELLY_EXPOSED'
                            ]:
                                nsfw_detected = True
                                logger.warning(f"NSFW content detected: {detection['class']}")
                                break
                    
                    if nsfw_detected:
                        raise forms.ValidationError("This image contains inappropriate content and cannot be uploaded.")
                    
                finally:
                    # Clean up the temporary file
                    os.unlink(temp_file.name)
                
            except Exception as e:
                logger.error(f"Error processing observation image: {str(e)}")
                raise forms.ValidationError(f"Error processing image: {str(e)}")
        
        return image

class PhotoForm(forms.ModelForm):
    """Form for adding photos to a plant."""
    image = CloudinaryFileField(
        options={
            'folder': 'plantbook/photos',
            'resource_type': 'image',
            'allowed_formats': ['jpg', 'jpeg', 'png', 'gif']
        }
    )

    class Meta:
        model = PlantPhoto
        fields = ['image', 'caption']
        widgets = {
            'caption': forms.Textarea(attrs={'rows': 2}),
        }
        labels = {
            'image': 'Photo',
            'caption': 'Caption'
        }
        help_texts = {
            'image': 'Upload a photo of your plant',
            'caption': 'Optional: Add a caption for your photo'
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            try:
                # Get the image URL from Cloudinary
                image_url = image.url
                
                # Download the image
                response = requests.get(image_url)
                if response.status_code != 200:
                    raise forms.ValidationError("Failed to download image")
                
                # Convert the image data to a numpy array
                image_data = np.frombuffer(response.content, np.uint8)
                img = cv2.imdecode(image_data, cv2.IMREAD_COLOR)
                
                if img is None:
                    raise forms.ValidationError("Invalid image format")
                
                # Save the image temporarily
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                cv2.imwrite(temp_file.name, img)
                
                try:
                    # Run NSFW detection
                    detector = NudeDetector()
                    result = detector.detect(temp_file.name)
                    
                    # Log detection results
                    logger.info(f"NSFW detection results: {result}")
                    
                    # Check if any NSFW content was detected
                    nsfw_detected = False
                    for detection in result:
                        # Log each detection
                        logger.info(f"Detected: {detection['class']} with confidence: {detection['score']}")
                        
                        # Check for NSFW content with confidence threshold
                        if detection['score'] > 0.2:  # Adjust this threshold as needed
                            if detection['class'] in [
                                'NSFW',
                                'EXPOSED_BREAST_F',
                                'EXPOSED_GENITALIA_F',
                                'EXPOSED_GENITALIA_M',
                                'EXPOSED_ANUS',
                                'EXPOSED_BUTTOCKS',
                                'EXPOSED_FEET',
                                'EXPOSED_BREAST_M',
                                'FEMALE_GENITALIA_EXPOSED',
                                'MALE_GENITALIA_EXPOSED',
                                'FEMALE_BREAST_EXPOSED',
                                'MALE_BREAST_EXPOSED',
                                'BELLY_EXPOSED'
                            ]:
                                nsfw_detected = True
                                logger.warning(f"NSFW content detected: {detection['class']}")
                                break
                    
                    if nsfw_detected:
                        raise forms.ValidationError("This image contains inappropriate content and cannot be uploaded.")
                    
                finally:
                    # Clean up the temporary file
                    os.unlink(temp_file.name)
                
            except Exception as e:
                logger.error(f"Error processing photo image: {str(e)}")
                raise forms.ValidationError(f"Error processing image: {str(e)}")
        
        return image

class ProfileForm(forms.ModelForm):
    profile_photo = CloudinaryFileField(
        options={
            'folder': 'plantbook/profiles',
            'resource_type': 'image',
            'allowed_formats': ['jpg', 'jpeg', 'png', 'gif']
        },
        required=False
    )

    class Meta:
        model = Profile
        fields = ['bio', 'location', 'profile_photo']

    def clean_profile_photo(self):
        photo = self.cleaned_data.get('profile_photo')
        if photo:
            try:
                # Get the image URL from Cloudinary
                image_url = photo.url
                
                # Download the image
                response = requests.get(image_url)
                if response.status_code != 200:
                    raise forms.ValidationError("Failed to download image")
                
                # Convert the image data to a numpy array
                image_data = np.frombuffer(response.content, np.uint8)
                img = cv2.imdecode(image_data, cv2.IMREAD_COLOR)
                
                if img is None:
                    raise forms.ValidationError("Invalid image format")
                
                # Save the image temporarily
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                cv2.imwrite(temp_file.name, img)
                
                try:
                    # Run NSFW detection
                    detector = NudeDetector()
                    result = detector.detect(temp_file.name)
                    
                    # Log detection results
                    logger.info(f"NSFW detection results: {result}")
                    
                    # Check if any NSFW content was detected
                    nsfw_detected = False
                    for detection in result:
                        # Log each detection
                        logger.info(f"Detected: {detection['class']} with confidence: {detection['score']}")
                        
                        # Check for NSFW content with confidence threshold
                        if detection['score'] > 0.2:  # Adjust this threshold as needed
                            if detection['class'] in [
                                'NSFW',
                                'EXPOSED_BREAST_F',
                                'EXPOSED_GENITALIA_F',
                                'EXPOSED_GENITALIA_M',
                                'EXPOSED_ANUS',
                                'EXPOSED_BUTTOCKS',
                                'EXPOSED_FEET',
                                'EXPOSED_BREAST_M',
                                'FEMALE_GENITALIA_EXPOSED',
                                'MALE_GENITALIA_EXPOSED',
                                'FEMALE_BREAST_EXPOSED',
                                'MALE_BREAST_EXPOSED',
                                'BELLY_EXPOSED'
                            ]:
                                nsfw_detected = True
                                logger.warning(f"NSFW content detected: {detection['class']}")
                                break
                    
                    if nsfw_detected:
                        raise forms.ValidationError("This image contains inappropriate content and cannot be uploaded.")
                    
                finally:
                    # Clean up the temporary file
                    os.unlink(temp_file.name)
                
            except Exception as e:
                logger.error(f"Error processing profile photo: {str(e)}")
                raise forms.ValidationError(f"Error processing image: {str(e)}")
        
        return photo

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
        return instance

class CommentForm(forms.ModelForm):
    """Form for creating comments."""
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3}),
        }

class MessageForm(forms.ModelForm):
    """Form for creating messages."""
    class Meta:
        model = Message
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3}),
        } 
