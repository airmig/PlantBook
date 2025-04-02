from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError
from .models import Plant, PlantDetail, Observation, PlantPhoto, Profile, Comment, Message
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from .utils import trefle_api, permapeople_api
from django.db.models import Q
from django.core.paginator import Paginator
from django.db.models import Count
from .forms import PlantForm, ObservationForm, PhotoForm
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)

@ensure_csrf_cookie
def register(request):
    """Handle user registration."""
    if request.method == 'POST':
        try:
            first_name = request.POST['first_name']
            last_name = request.POST['last_name']
            email = request.POST['email']
            password = request.POST['password']
            confirm_password = request.POST['confirm_password']

            if password != confirm_password:
                messages.error(request, 'Passwords do not match.')
                return redirect('main:register')

            # Check if user already exists
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Email already registered.')
                return redirect('main:register')

            # Create user - profile will be created automatically via signal
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )

            messages.success(request, 'Registration successful! Please login.')
            return redirect('main:login')

        except Exception as e:
            # If any error occurs, delete the user if it was created
            if 'user' in locals():
                user.delete()
            messages.error(request, f'Registration error: {str(e)}')
            return redirect('main:register')

    return render(request, 'main/register.html')

@ensure_csrf_cookie
def login_view(request):
    """Handle user login."""
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            login(request, user)
            # Clear any existing messages
            storage = messages.get_messages(request)
            for _ in storage:
                pass
            messages.success(request, 'Login successful!')
            return redirect('main:home')
        else:
            messages.error(request, 'Invalid email or password.')
    
    return render(request, 'main/login.html')

def home(request):
    """Home page view"""
    if request.user.is_authenticated:
        plants = Plant.objects.filter(user=request.user).order_by('-created_at')
    else:
        plants = []
    
    # Get the 20 most recent plants from all users
    recent_plants = Plant.objects.all().order_by('-created_at')[:20]
    
    return render(request, 'main/home.html', {
        'plants': plants,
        'recent_plants': recent_plants
    })

@login_required
@csrf_protect
def upload_plant(request):
    """Handle plant upload and creation."""
    if request.method == 'POST':
        form = PlantForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                plant = form.save(commit=False)
                plant.user = request.user
                plant.save()
                
                # Handle plant details
                detail_headers = request.POST.getlist('detail_header[]')
                detail_information = request.POST.getlist('detail_information[]')
                
                for header, info in zip(detail_headers, detail_information):
                    if header and info:
                        PlantDetail.objects.create(
                            plant=plant,
                            header=header,
                            information=info
                        )
                
                messages.success(request, 'Plant uploaded successfully!')
                return redirect('main:plant_detail', plant_id=plant.id)
                
            except Exception as e:
                messages.error(request, f'Error uploading plant: {str(e)}')
                return redirect('main:upload_plant')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
            return redirect('main:upload_plant')
    
    form = PlantForm()
    return render(request, 'main/upload_plant.html', {'form': form})

def plant_detail(request, plant_id):
    """Display detailed information about a specific plant."""
    try:
        plant = Plant.objects.get(id=plant_id)
        details = PlantDetail.objects.filter(plant=plant).order_by('-created_at')
        observations = Observation.objects.filter(plant=plant).order_by('-created_at')
        photos = PlantPhoto.objects.filter(plant=plant).order_by('-created_at')
        comments = Comment.objects.filter(plant=plant).order_by('-created_at')
        
        # Create forms for observations and photos
        observation_form = ObservationForm()
        photo_form = PhotoForm()
        
        # Get active tab from request or default to 'details'
        active_tab = request.GET.get('tab', 'details')
        
        context = {
            'plant': plant,
            'details': details,
            'observations': observations,
            'photos': photos,
            'comments': comments,
            'observation_form': observation_form,
            'photo_form': photo_form,
            'active_tab': active_tab,
        }
        return render(request, 'main/plant_detail.html', context)
    except Plant.DoesNotExist:
        messages.error(request, 'Plant not found.')
        return redirect('main:home')

@login_required
def add_observation(request, plant_id):
    """Add an observation to a plant."""
    plant = get_object_or_404(Plant, id=plant_id, user=request.user)
    
    if request.method == 'POST':
        form = ObservationForm(request.POST, request.FILES)
        if form.is_valid():
            observation = form.save(commit=False)
            observation.plant = plant
            observation.save()
            messages.success(request, 'Observation added successfully!')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
            
    return redirect(f"{reverse('main:plant_detail', kwargs={'plant_id': plant.id})}?tab=observations")

@login_required
def add_photo(request, plant_id):
    """Add a photo to a plant."""
    plant = get_object_or_404(Plant, id=plant_id, user=request.user)
    
    if request.method == 'POST':
        form = PhotoForm(request.POST, request.FILES)
        if form.is_valid():
            photo = form.save(commit=False)
            photo.plant = plant
            photo.save()
            messages.success(request, 'Photo added successfully!')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
            
    return redirect(f"{reverse('main:plant_detail', kwargs={'plant_id': plant.id})}?tab=photos")

@login_required
@csrf_protect
def profile(request):
    """Display and update user profile."""
    if request.method == 'POST':
        # Update profile information
        profile = request.user.profile
        
        # Update profile photo if provided
        if 'profile_photo' in request.FILES:
            profile.profile_photo = request.FILES['profile_photo']
        
        # Update other profile fields
        profile.bio = request.POST.get('bio', '')
        profile.location = request.POST.get('location', '')
        profile.save()
        
        # Update user information
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.email = request.POST.get('email', '')
        request.user.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('main:profile')
    
    # Get user's plants count and latest plants
    plants_count = Plant.objects.filter(user=request.user).count()
    latest_plants = Plant.objects.filter(user=request.user).order_by('-created_at')[:3]
    
    return render(request, 'main/profile.html', {
        'plants_count': plants_count,
        'latest_plants': latest_plants,
    })

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('main:login')

@login_required
@csrf_protect
def add_comment(request, plant_id):
    if request.method == 'POST':
        plant = get_object_or_404(Plant, id=plant_id)
        content = request.POST.get('content')
        
        if content:
            Comment.objects.create(
                plant=plant,
                user=request.user,
                content=content
            )
            messages.success(request, 'Comment added successfully!')
        else:
            messages.error(request, 'Comment cannot be empty.')
            
    return redirect(f"{reverse('main:plant_detail', kwargs={'plant_id': plant_id})}?tab=comments")

@login_required
@csrf_protect
def delete_comment(request, plant_id, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, plant__id=plant_id)
    if request.user == comment.plant.user:
        comment.delete()
        messages.success(request, 'Comment deleted successfully!')
    else:
        messages.error(request, 'You do not have permission to delete this comment.')
    return redirect(f"{reverse('main:plant_detail', kwargs={'plant_id': plant_id})}?tab=comments")

def search_plants_api(request):
    """API endpoint for plant search"""
    query = request.GET.get('q', '')
    try:
        results = trefle_api.search_plants(query, per_page=10)
        return JsonResponse(results)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def search_plants(request):
    """Search plants in our database and PermaPeople API"""
    query = request.GET.get('q', '')
    
    # Clear any existing messages when starting a new search
    storage = messages.get_messages(request)
    for _ in storage:
        pass
    
    if query:
        # First search in our database
        plants = Plant.objects.filter(
            Q(name__icontains=query) |
            Q(scientific_name__icontains=query)
        ).order_by('-created_at')
        
        # If no results found in our database, search PermaPeople API
        if not plants.exists():
            try:
                permapeople_results = permapeople_api.search_plants(query)
                if permapeople_results and 'plants' in permapeople_results:
                    # Process the PermaPeople results
                    processed_plants = []
                    for plant in permapeople_results['plants']:
                        # Extract data from key-value pairs
                        plant_data = {}
                        for item in plant.get('data', []):
                            key = item.get('key', '').lower().replace(' ', '_')
                            value = item.get('value', '')
                            plant_data[key] = value
                        
                        # Process the plant data
                        processed_plant = {
                            'id': plant.get('id'),
                            'name': plant.get('name', ''),
                            'scientific_name': plant.get('slug', '').replace('-', ' ').title(),
                            'image_url': plant.get('image_url'),
                            'description': plant.get('description', ''),
                            'edible': plant_data.get('edible', ''),
                            'water_requirement': plant_data.get('water_requirement', ''),
                            'light_requirement': plant_data.get('light_requirement', ''),
                            'hardiness_zone': plant_data.get('usda_hardiness_zone', ''),
                            'layer': plant_data.get('layer', ''),
                            'wikipedia': plant_data.get('wikipedia', ''),
                            'source': 'permapeople'
                        }
                        processed_plants.append(processed_plant)
                    
                    return render(request, 'main/permapeople_search.html', {
                        'plants': processed_plants,
                        'query': query
                    })
            except Exception as e:
                messages.error(request, f'Error searching PermaPeople API: {str(e)}')
                return render(request, 'main/search_results.html', {
                    'plants': [],
                    'query': query
                })
    else:
        plants = Plant.objects.all().order_by('-created_at')
    
    return render(request, 'main/search_results.html', {
        'plants': plants,
        'query': query
    })

def directory(request):
    search_query = request.GET.get('q', '')
    per_page = int(request.GET.get('per_page', 12))
    page = request.GET.get('page', 1)

    # Get all users with their plant counts
    users = User.objects.annotate(plant_count=Count('plant')).order_by('-plant_count')

    # Apply search filter if query exists
    if search_query:
        users = users.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    # Paginate results
    paginator = Paginator(users, per_page)
    users = paginator.get_page(page)

    context = {
        'users': users,
        'search_query': search_query,
    }
    return render(request, 'main/directory.html', context)

@login_required
def my_plants(request):
    """Display all plants owned by the current user."""
    plants = Plant.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'main/my_plants.html', {
        'plants': plants
    })

def user_profile(request, user_id):
    """Display a user's profile and their plants."""
    try:
        user = User.objects.get(id=user_id)
        plants = Plant.objects.filter(user=user).order_by('-created_at')
        
        context = {
            'profile_user': user,
            'plants': plants,
        }
        return render(request, 'main/user_profile.html', context)
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('main:directory')

@login_required
def edit_plant(request, plant_id):
    """Edit a specific plant."""
    plant = get_object_or_404(Plant, id=plant_id, user=request.user)
    
    if request.method == 'POST':
        form = PlantForm(request.POST, request.FILES, instance=plant)
        if form.is_valid():
            form.save()
            messages.success(request, 'Plant updated successfully!')
            return redirect('main:plant_detail', plant_id=plant.id)
    else:
        form = PlantForm(instance=plant)
    
    return render(request, 'main/edit_plant.html', {
        'form': form,
        'plant': plant
    })

@login_required
def add_detail(request, plant_id):
    """Add a detail to a plant."""
    plant = get_object_or_404(Plant, id=plant_id)
    
    if request.method == 'POST':
        header = request.POST.get('header')
        information = request.POST.get('information')
        
        if header and information:
            PlantDetail.objects.create(
                plant=plant,
                header=header,
                information=information
            )
            messages.success(request, 'Detail added successfully!')
        else:
            messages.error(request, 'Please provide both title and information.')
    
    return redirect(f"{reverse('main:plant_detail', kwargs={'plant_id': plant.id})}?tab=details")

@login_required
def delete_detail(request, plant_id, detail_id):
    """Delete a plant detail."""
    detail = get_object_or_404(PlantDetail, id=detail_id, plant__id=plant_id)
    if request.user == detail.plant.user:
        detail.delete()
        messages.success(request, 'Detail deleted successfully!')
    else:
        messages.error(request, 'You do not have permission to delete this detail.')
    return redirect(f"{reverse('main:plant_detail', kwargs={'plant_id': plant_id})}?tab=details")

@login_required
def delete_observation(request, plant_id, observation_id):
    """Delete a plant observation."""
    observation = get_object_or_404(Observation, id=observation_id, plant__id=plant_id)
    if request.user == observation.plant.user:
        observation.delete()
        messages.success(request, 'Observation deleted successfully!')
    else:
        messages.error(request, 'You do not have permission to delete this observation.')
    return redirect(f"{reverse('main:plant_detail', kwargs={'plant_id': plant_id})}?tab=observations")

@login_required
def delete_photo(request, plant_id, photo_id):
    """Delete a plant photo."""
    photo = get_object_or_404(PlantPhoto, id=photo_id, plant__id=plant_id)
    if request.user == photo.plant.user:
        photo.delete()
        messages.success(request, 'Photo deleted successfully!')
    else:
        messages.error(request, 'You do not have permission to delete this photo.')
    return redirect(f"{reverse('main:plant_detail', kwargs={'plant_id': plant_id})}?tab=photos")

@login_required
def delete_plant(request, plant_id):
    """Delete a plant and all its associated data."""
    plant = get_object_or_404(Plant, id=plant_id, user=request.user)
    
    if request.method == 'POST':
        try:
            # Delete the plant (this will cascade delete all related objects)
            plant.delete()
            messages.success(request, 'Plant deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting plant: {str(e)}')
    
    return redirect('main:home')

@login_required
def get_messages(request):
    """Get all messages for the current user."""
    messages = Message.objects.filter(
        Q(sender=request.user) | Q(recipient=request.user)
    ).select_related('sender', 'recipient')
    
    messages_data = [{
        'id': msg.id,
        'content': msg.content,
        'sender': msg.sender.username,
        'recipient': msg.recipient.username,
        'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'is_read': msg.is_read,
        'is_sent': msg.sender == request.user
    } for msg in messages]
    
    return JsonResponse({'messages': messages_data})

@login_required
@require_POST
def send_message(request):
    """Send a new message."""
    try:
        data = json.loads(request.body)
        recipient = User.objects.get(username=data['recipient'])
        content = data['content']
        
        message = Message.objects.create(
            sender=request.user,
            recipient=recipient,
            content=content
        )
        
        return JsonResponse({
            'status': 'success',
            'message': {
                'id': message.id,
                'content': message.content,
                'sender': message.sender.username,
                'recipient': message.recipient.username,
                'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'is_read': message.is_read,
                'is_sent': True
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
@require_POST
def mark_message_read(request, message_id):
    """Mark a message as read."""
    try:
        message = Message.objects.get(id=message_id, recipient=request.user)
        message.is_read = True
        message.save()
        return JsonResponse({'status': 'success'})
    except Message.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Message not found'}, status=404)

@login_required
@require_POST
def add_permaplant(request):
    """Add a new plant from PermaPeople to the user's collection"""
    try:
        data = json.loads(request.body)
        permaplant_id = data.get('permaplant_id')
        
        if not permaplant_id:
            return JsonResponse({'success': False, 'error': 'Missing permaplant_id'})
        
        # Get details from PermaPeople API
        try:
            # Log the request parameters
            logger.info(f"Fetching plant details for PermaPeople ID: {permaplant_id}")
            
            plant_details = permapeople_api.get_plant(permaplant_id)
            logger.info(f"Received plant details: {json.dumps(plant_details, indent=2)}")
            
            if not plant_details:
                logger.error("Empty response from PermaPeople API")
                return JsonResponse({'success': False, 'error': 'Could not fetch plant details'})
            
            # Extract basic plant information
            name = plant_details.get('name', '')
            scientific_name = plant_details.get('scientific_name', '')
            description = plant_details.get('description', '')
            image_url = plant_details.get('image_url', '')
            
            if not name:
                logger.error("Missing required field: name")
                return JsonResponse({'success': False, 'error': 'Missing required field: name'})
            
            # Create the plant
            plant = Plant.objects.create(
                user=request.user,
                name=name,
                scientific_name=scientific_name,
                image=image_url,
                source='permapeople',
                external_id=permaplant_id
            )
            logger.info(f"Created plant: ID={plant.id}, name={plant.name}")
            
            # Add description as a plant detail if it exists
            if description:
                try:
                    PlantDetail.objects.create(
                        plant=plant,
                        header='Description',
                        information=description
                    )
                    logger.debug("Added description as plant detail")
                except Exception as e:
                    logger.error(f"Error creating description detail: {str(e)}")
            
            # Process additional details
            details = plant_details.get('data', [])
            if not details:
                logger.warning("No additional details found in response")
                return JsonResponse({'success': True, 'plant_id': plant.id})
            
            details_added = 0
            logger.info(f"Processing {len(details)} details")
            
            for detail in details:
                if isinstance(detail, dict):
                    key = detail.get('key', '').lower().replace(' ', '_')
                    value = detail.get('value', '')
                    
                    logger.debug(f"Processing detail: key={key}, value={value}")
                    
                    # Skip empty values
                    if not value:
                        logger.debug(f"Skipping empty value for key: {key}")
                        continue
                    
                    try:
                        # Create plant detail
                        plant_detail = PlantDetail.objects.create(
                            plant=plant,
                            header=key.replace('_', ' ').title(),
                            information=value
                        )
                        details_added += 1
                        logger.debug(f"Created plant detail: ID={plant_detail.id}, header={plant_detail.header}")
                    except Exception as e:
                        logger.error(f"Error creating plant detail: {str(e)}")
                else:
                    logger.warning(f"Invalid detail format: {detail}")
            
            logger.info(f"Successfully added {details_added} details to plant ID={plant.id}")
            return JsonResponse({
                'success': True, 
                'plant_id': plant.id, 
                'details_added': details_added
            })
            
        except Exception as e:
            logger.error(f"Error fetching additional details: {str(e)}")
            # If we have a plant object, return success with warning
            if 'plant' in locals():
                return JsonResponse({
                    'success': True, 
                    'plant_id': plant.id,
                    'warning': f'Error fetching additional details: {str(e)}'
                })
            # If we don't have a plant object, return error
            return JsonResponse({
                'success': False,
                'error': f'Error fetching plant details: {str(e)}'
            })
    
    except Exception as e:
        logger.error(f"Error in add_permaplant: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def get_user_plants(request):
    """Get all plants in the user's collection for the modal selection."""
    plants = Plant.objects.filter(user=request.user).order_by('name')
    plants_data = [{'id': plant.id, 'name': plant.name, 'scientific_name': plant.scientific_name} for plant in plants]
    return JsonResponse({'plants': plants_data})

@login_required
@require_POST
def import_permaplant(request):
    """Import data from a PermaPeople plant to an existing plant in the user's collection."""
    try:
        data = json.loads(request.body)
        permaplant_id = data.get('permaplant_id')
        plant_id = data.get('plant_id')
        
        if not all([permaplant_id, plant_id]):
            return JsonResponse({'success': False, 'error': 'Missing required fields'})
        
        # Get the existing plant
        plant = get_object_or_404(Plant, id=plant_id, user=request.user)
        
        # Get details from PermaPeople API
        try:
            # Log the request parameters
            logger.info(f"Fetching plant details for PermaPeople ID: {permaplant_id}")
            
            plant_details = permapeople_api.get_plant(permaplant_id)
            
            # Log the raw response for debugging
            logger.debug(f"Raw API response: {plant_details}")
            
            if not plant_details:
                logger.error("Empty response from PermaPeople API")
                return JsonResponse({'success': False, 'error': 'Empty response from API'})
            
            if 'data' not in plant_details:
                logger.error(f"Unexpected API response format: {plant_details}")
                return JsonResponse({'success': False, 'error': 'Unexpected API response format'})
            
            # Extract data from key-value pairs
            for item in plant_details['data']:
                key = item.get('key', '').lower().replace(' ', '_')
                value = item.get('value', '')
                
                # Skip empty values
                if not value:
                    continue
                
                # Check if detail already exists
                existing_detail = PlantDetail.objects.filter(
                    plant=plant,
                    header=key.replace('_', ' ').title()
                ).first()
                
                if existing_detail:
                    # Update existing detail
                    existing_detail.information = value
                    existing_detail.save()
                else:
                    # Create new detail
                    PlantDetail.objects.create(
                        plant=plant,
                        header=key.replace('_', ' ').title(),
                        information=value
                    )
            
            # Update plant source if not already set
            if not plant.source:
                plant.source = 'permapeople'
                plant.external_id = permaplant_id
                plant.save()
            
            return JsonResponse({'success': True})
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            return JsonResponse({'success': False, 'error': 'Invalid JSON response from API'})
        except Exception as e:
            logger.error(f"Error fetching plant details: {str(e)}")
            return JsonResponse({'success': False, 'error': f'Error fetching plant details: {str(e)}'})
    
    except Exception as e:
        logger.error(f"Error in import_permaplant: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})
