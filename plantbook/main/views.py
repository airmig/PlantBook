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
from .utils import permapeople_api
from django.db.models import Q
from django.core.paginator import Paginator
from django.db.models import Count
from .forms import PlantForm, ObservationForm, PhotoForm, ProfileForm
from django.urls import reverse
import logging
from django.core.paginator import PageNotAnInteger, EmptyPage
import traceback

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
    try:
        logger.info("Starting home view")
        # Get all plants ordered by creation date
        plants = Plant.objects.select_related('owner').order_by('-created_at')[:12]
        # Get the most recent plants for the recent plants section
        recent_plants = Plant.objects.select_related('owner').order_by('-created_at')[:10]
        logger.debug(f"Retrieved {len(plants)} plants for home page")
        return render(request, 'main/home.html', {
            'plants': plants,
            'recent_plants': recent_plants
        })
    except Exception as e:
        logger.error(f"Error in home view: {str(e)}", exc_info=True)
        logger.error(f"Traceback: {traceback.format_exc()}")
        messages.error(request, 'An error occurred while loading the home page.')
        return redirect('main:login')

@login_required
@csrf_protect
def upload_plant(request):
    try:
        logger.info(f"Starting upload_plant view for user {request.user.id}")
        if request.method == 'POST':
            form = PlantForm(request.POST, request.FILES)
            if form.is_valid():
                plant = form.save(commit=False)
                plant.owner = request.user
                plant.save()
                logger.info(f"Successfully created plant {plant.id} for user {request.user.id}")
                messages.success(request, 'Plant uploaded successfully!')
                return redirect('main:plant_detail', plant.id)
            else:
                logger.warning(f"Invalid form submission for user {request.user.id}: {form.errors}")
        else:
            form = PlantForm()
        return render(request, 'main/upload_plant.html', {'form': form})
    except Exception as e:
        logger.error(f"Error in upload_plant view: {str(e)}", exc_info=True)
        logger.error(f"Traceback: {traceback.format_exc()}")
        messages.error(request, 'An error occurred while uploading the plant.')
        return redirect('main:home')

def plant_detail(request, plant_id):
    try:
        logger.info(f"Starting plant_detail view for plant {plant_id}")
        plant = get_object_or_404(Plant, id=plant_id)
        logger.debug(f"Retrieved plant {plant_id} owned by user {plant.owner.id}")
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
    except Exception as e:
        logger.error(f"Error in plant_detail view: {str(e)}", exc_info=True)
        logger.error(f"Traceback: {traceback.format_exc()}")
        messages.error(request, 'An error occurred while loading the plant details.')
        return redirect('main:home')

@login_required
def add_observation(request, plant_id):
    try:
        logger.info(f"Starting add_observation view for plant {plant_id}")
        plant = get_object_or_404(Plant, id=plant_id)
        if request.method == 'POST':
            form = ObservationForm(request.POST, request.FILES)
            if form.is_valid():
                observation = form.save(commit=False)
                observation.plant = plant
                observation.save()
                logger.info(f"Successfully added observation {observation.id} for plant {plant_id}")
                messages.success(request, 'Observation added successfully!')
                return redirect('main:plant_detail', plant_id)
            else:
                logger.warning(f"Invalid observation form submission for plant {plant_id}: {form.errors}")
        else:
            form = ObservationForm()
        return render(request, 'main/add_observation.html', {'form': form, 'plant': plant})
    except Exception as e:
        logger.error(f"Error in add_observation view: {str(e)}", exc_info=True)
        logger.error(f"Traceback: {traceback.format_exc()}")
        messages.error(request, 'An error occurred while adding the observation.')
        return redirect('main:plant_detail', plant_id)

@login_required
def add_photo(request, plant_id):
    try:
        logger.info(f"Starting add_photo view for plant {plant_id}")
        plant = get_object_or_404(Plant, id=plant_id)
        if request.method == 'POST':
            form = PhotoForm(request.POST, request.FILES)
            if form.is_valid():
                photo = form.save(commit=False)
                photo.plant = plant
                photo.save()
                logger.info(f"Successfully added photo {photo.id} for plant {plant_id}")
                messages.success(request, 'Photo added successfully!')
                return redirect('main:plant_detail', plant_id)
            else:
                logger.warning(f"Invalid photo form submission for plant {plant_id}: {form.errors}")
        else:
            form = PhotoForm()
        return render(request, 'main/add_photo.html', {'form': form, 'plant': plant})
    except Exception as e:
        logger.error(f"Error in add_photo view: {str(e)}", exc_info=True)
        logger.error(f"Traceback: {traceback.format_exc()}")
        messages.error(request, 'An error occurred while adding the photo.')
        return redirect('main:plant_detail', plant_id)

@login_required
@csrf_protect
def profile(request):
    try:
        logger.info(f"Starting profile view for user {request.user.id}")
        if request.method == 'POST':
            form = ProfileForm(request.POST, request.FILES, instance=request.user.profile)
            if form.is_valid():
                form.save()
                logger.info(f"Successfully updated profile for user {request.user.id}")
                messages.success(request, 'Profile updated successfully!')
                return redirect('main:profile')
            else:
                logger.warning(f"Invalid profile form submission for user {request.user.id}: {form.errors}")
        else:
            form = ProfileForm(instance=request.user.profile)
        
        plants_count = Plant.objects.filter(owner=request.user).count()
        logger.debug(f"Retrieved {plants_count} plants for user {request.user.id}")
        
        return render(request, 'main/profile.html', {
            'form': form,
            'plants_count': plants_count
        })
    except Exception as e:
        logger.error(f"Error in profile view: {str(e)}", exc_info=True)
        logger.error(f"Traceback: {traceback.format_exc()}")
        messages.error(request, 'An error occurred while loading your profile.')
        return redirect('main:home')

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
    try:
        logger.info("Starting search_plants view")
        query = request.GET.get('q', '')
        if query:
            plants = Plant.objects.filter(
                Q(name__icontains=query) |
                Q(scientific_name__icontains=query)
            ).select_related('owner')
            logger.debug(f"Found {plants.count()} plants matching query: {query}")
            
            # If no local plants found, redirect to PermaPeople search
            if not plants.exists():
                logger.info(f"No local plants found for query '{query}', redirecting to PermaPeople search")
                return redirect(f"{reverse('main:permapeople_search')}?q={query}")
        else:
            plants = []
            logger.debug("No search query provided")
        
        return render(request, 'main/search_results.html', {
            'plants': plants,
            'query': query
        })
    except Exception as e:
        logger.error(f"Error in search_plants view: {str(e)}", exc_info=True)
        logger.error(f"Traceback: {traceback.format_exc()}")
        messages.error(request, 'An error occurred while searching for plants.')
        return redirect('main:home')

def directory(request):
    try:
        logger.info("Starting directory view")
        search_query = request.GET.get('q', '')
        per_page = int(request.GET.get('per_page', 12))
        page = request.GET.get('page', 1)

        # Get all users with their plant counts and prefetch profiles
        users = User.objects.select_related('profile').annotate(plant_count=Count('plant')).order_by('-plant_count')
        logger.debug(f"Retrieved {users.count()} users for directory")

        # Apply search filter if query exists
        if search_query:
            users = users.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query)
            )
            logger.debug(f"Applied search filter: {search_query}")

        # Paginate results
        paginator = Paginator(users, per_page)
        try:
            users = paginator.get_page(page)
            logger.debug(f"Retrieved page {page} of {paginator.num_pages}")
        except (PageNotAnInteger, EmptyPage):
            users = paginator.get_page(1)
            logger.warning(f"Invalid page number {page}, defaulting to page 1")

        context = {
            'users': users,
            'search_query': search_query,
        }
        return render(request, 'main/directory.html', context)
    except Exception as e:
        logger.error(f"Error in directory view: {str(e)}", exc_info=True)
        logger.error(f"Traceback: {traceback.format_exc()}")
        messages.error(request, 'An error occurred while loading the directory.')
        return redirect('main:home')

@login_required
def my_plants(request):
    try:
        logger.info(f"Starting my_plants view for user {request.user.id}")
        plants = Plant.objects.filter(owner=request.user).order_by('-created_at')
        logger.debug(f"Retrieved {plants.count()} plants for user {request.user.id}")
        return render(request, 'main/my_plants.html', {'plants': plants})
    except Exception as e:
        logger.error(f"Error in my_plants view: {str(e)}", exc_info=True)
        logger.error(f"Traceback: {traceback.format_exc()}")
        messages.error(request, 'An error occurred while loading your plants.')
        return redirect('main:home')

def user_profile(request, user_id):
    try:
        logger.info(f"Starting user_profile view for user {user_id}")
        profile_user = get_object_or_404(User, id=user_id)
        plants = Plant.objects.filter(owner=profile_user)
        logger.debug(f"Retrieved {plants.count()} plants for user {user_id}")
        return render(request, 'main/user_profile.html', {
            'profile_user': profile_user,
            'plants': plants
        })
    except Exception as e:
        logger.error(f"Error in user_profile view: {str(e)}", exc_info=True)
        logger.error(f"Traceback: {traceback.format_exc()}")
        messages.error(request, 'An error occurred while loading the user profile.')
        return redirect('main:directory')

@login_required
def edit_plant(request, plant_id):
    """Edit a specific plant."""
    plant = get_object_or_404(Plant, id=plant_id, owner=request.user)
    
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
    try:
        logger.info(f"Starting delete_observation view for observation {observation_id}")
        observation = get_object_or_404(Observation, id=observation_id, plant_id=plant_id)
        observation.delete()
        logger.info(f"Successfully deleted observation {observation_id}")
        messages.success(request, 'Observation deleted successfully!')
        return redirect('main:plant_detail', plant_id)
    except Exception as e:
        logger.error(f"Error in delete_observation view: {str(e)}", exc_info=True)
        logger.error(f"Traceback: {traceback.format_exc()}")
        messages.error(request, 'An error occurred while deleting the observation.')
        return redirect('main:plant_detail', plant_id)

@login_required
def delete_photo(request, plant_id, photo_id):
    try:
        logger.info(f"Starting delete_photo view for photo {photo_id}")
        photo = get_object_or_404(PlantPhoto, id=photo_id, plant_id=plant_id)
        photo.delete()
        logger.info(f"Successfully deleted photo {photo_id}")
        messages.success(request, 'Photo deleted successfully!')
        return redirect('main:plant_detail', plant_id)
    except Exception as e:
        logger.error(f"Error in delete_photo view: {str(e)}", exc_info=True)
        logger.error(f"Traceback: {traceback.format_exc()}")
        messages.error(request, 'An error occurred while deleting the photo.')
        return redirect('main:plant_detail', plant_id)

@login_required
def delete_plant(request, plant_id):
    try:
        logger.info(f"Starting delete_plant view for plant {plant_id}")
        plant = get_object_or_404(Plant, id=plant_id, owner=request.user)
        plant.delete()
        logger.info(f"Successfully deleted plant {plant_id}")
        messages.success(request, 'Plant deleted successfully!')
        return redirect('main:my_plants')
    except Exception as e:
        logger.error(f"Error in delete_plant view: {str(e)}", exc_info=True)
        logger.error(f"Traceback: {traceback.format_exc()}")
        messages.error(request, 'An error occurred while deleting the plant.')
        return redirect('main:my_plants')

@login_required
def get_messages(request):
    """Get all messages for the current user."""
    messages = Message.objects.filter(
        Q(sender=request.user) | Q(recipient=request.user)
    ).select_related('sender', 'recipient', 'sender__profile', 'recipient__profile')
    
    messages_data = [{
        'id': msg.id,
        'content': msg.content,
        'sender': msg.sender.username,
        'recipient': msg.recipient.username,
        'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'is_read': msg.is_read,
        'is_sent': msg.sender == request.user,
        'sender_photo_url': msg.sender.profile.profile_photo.url if msg.sender.profile.profile_photo else None,
        'recipient_photo_url': msg.recipient.profile.profile_photo.url if msg.recipient.profile.profile_photo else None
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
                'is_sent': True,
                'sender_photo_url': message.sender.profile.profile_photo.url if message.sender.profile.profile_photo else None,
                'recipient_photo_url': message.recipient.profile.profile_photo.url if message.recipient.profile.profile_photo else None
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
            
            # Create the plant with empty plant_photo initially
            plant = Plant.objects.create(
                owner=request.user,
                name=name,
                scientific_name=scientific_name,
                description=description,
                plant_photo=None  # We'll handle the photo separately
            )
            logger.info(f"Created plant: ID={plant.id}, name={plant.name}")
            
            # If we have an image URL, upload it to Cloudinary
            if image_url:
                try:
                    # Download the image from the URL
                    import requests
                    response = requests.get(image_url)
                    if response.status_code == 200:
                        # Upload to Cloudinary
                        from cloudinary.uploader import upload
                        from cloudinary.utils import cloudinary_url
                        
                        # Upload the image
                        upload_result = upload(
                            response.content,
                            folder='plantbook/plants',
                            public_id=f'plant_{plant.id}'
                        )
                        
                        # Update the plant with the Cloudinary URL
                        plant.plant_photo = upload_result['public_id']
                        plant.save()
                        logger.info(f"Successfully uploaded plant photo to Cloudinary: {plant.plant_photo}")
                    else:
                        logger.warning(f"Failed to download image from URL: {image_url}")
                except Exception as e:
                    logger.error(f"Error uploading plant photo to Cloudinary: {str(e)}")
            
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
    plants = Plant.objects.filter(owner=request.user).order_by('name')
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
        plant = get_object_or_404(Plant, id=plant_id, owner=request.user)
        
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
            
            # Try to update source and external_id if they exist
            try:
                if hasattr(plant, 'source') and not plant.source:
                    plant.source = 'permapeople'
                if hasattr(plant, 'external_id') and not plant.external_id:
                    plant.external_id = permaplant_id
                plant.save()
            except Exception as e:
                logger.warning(f"Could not update source/external_id fields: {str(e)}")
            
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

def permapeople_search(request):
    """Search for plants using the PermaPeople API"""
    try:
        logger.info("Starting permapeople_search view")
        query = request.GET.get('q', '')
        
        if query:
            logger.info(f"Searching PermaPeople API with query: {query}")
            plants = permapeople_api.search_plants(query)
            logger.debug(f"Found {len(plants)} plants matching query: {query}")
        else:
            plants = []
            logger.debug("No search query provided")
        
        return render(request, 'main/permapeople_search.html', {
            'plants': plants,
            'query': query
        })
    except Exception as e:
        logger.error(f"Error in permapeople_search view: {str(e)}", exc_info=True)
        logger.error(f"Traceback: {traceback.format_exc()}")
        messages.error(request, 'An error occurred while searching the PermaPeople database.')
        return redirect('main:home')
