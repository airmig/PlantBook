from django import forms
from .models import Plant, Observation, PlantPhoto
from nudenet import NudeDetector
import tempfile
import os
import logging
from django.core.files.base import ContentFile
from PIL import Image
import io

logger = logging.getLogger(__name__)

class BaseImageForm(forms.ModelForm):
    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            try:
                # Save the image temporarily to run classification
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp:
                    for chunk in image.chunks():
                        temp.write(chunk)
                    temp_path = temp.name
                
                logger.info(f"Processing image: {temp_path}")

                # Run NudeNet classification
                classifier = NudeDetector()
                result = classifier.detect(temp_path)
                
                # Log the detection results
                logger.info(f"Detection results: {result}")
                
                # Check if any NSFW content is detected
                nsfw_detected = False
                for detection in result:
                    # Log each detection
                    logger.info(f"Detected: {detection['class']} with confidence: {detection['score']}")
                    
                    # Check for NSFW content with confidence threshold
                    if detection['score'] > 0.2:  # Adjust this threshold as needed
                        if detection['class'] in [
                            'FACE_FEMALE',
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
                    # Clean up the temporary file
                    os.unlink(temp_path)
                    raise forms.ValidationError('This image contains inappropriate content and cannot be uploaded.')
                
                # If no NSFW content, censor the image just in case
                logger.info("No NSFW content detected, proceeding with censoring")
                
                return image
                
            except Exception as e:
                # Log the error
                logger.error(f"Error processing image: {str(e)}", exc_info=True)
                
                # Clean up the temporary file if it exists
                if 'temp_path' in locals():
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
                raise forms.ValidationError(f'Error processing image: {str(e)}')
                
        return image

class PlantForm(BaseImageForm):
    class Meta:
        model = Plant
        fields = ['name', 'scientific_name', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'scientific_name': forms.TextInput(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'})
        }
        labels = {
            'name': 'Plant Name',
            'scientific_name': 'Scientific Name',
            'image': 'Plant Image'
        }
        help_texts = {
            'scientific_name': 'Optional: Enter the scientific name of your plant',
            'image': 'Upload a clear image of your plant'
        }

class ObservationForm(BaseImageForm):
    class Meta:
        model = Observation
        fields = ['note', 'image']
        widgets = {
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'image': forms.FileInput(attrs={'class': 'form-control'})
        }
        labels = {
            'note': 'Observation Note',
            'image': 'Observation Image'
        }
        help_texts = {
            'note': 'Enter your observation details',
            'image': 'Optional: Upload an image for your observation'
        }

class PhotoForm(BaseImageForm):
    class Meta:
        model = PlantPhoto
        fields = ['image', 'caption']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'caption': forms.TextInput(attrs={'class': 'form-control'})
        }
        labels = {
            'image': 'Photo',
            'caption': 'Caption'
        }
        help_texts = {
            'image': 'Upload a photo of your plant',
            'caption': 'Optional: Add a caption for your photo'
        } 
