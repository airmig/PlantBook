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
from .utils import trefle_api
from django.db.models import Q
from django.core.paginator import Paginator
from django.db.models import Count
from .forms import PlantForm, ObservationForm, PhotoForm

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
        
        context = {
            'plant': plant,
            'details': details,
            'observations': observations,
            'photos': photos,
            'comments': comments,
            'observation_form': observation_form,
            'photo_form': photo_form,
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
            
    return redirect('main:plant_detail', plant_id=plant.id)

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
            
    return redirect('main:plant_detail', plant_id=plant.id)

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
            
    return redirect('main:plant_detail', plant_id=plant_id)

@login_required
@csrf_protect
def delete_comment(request, plant_id, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    plant = get_object_or_404(Plant, id=plant_id)
    
    # Only allow the plant owner to delete comments
    if request.user == plant.user:
        comment.delete()
        messages.success(request, 'Comment deleted successfully!')
    else:
        messages.error(request, 'You do not have permission to delete this comment.')
        
    return redirect('main:plant_detail', plant_id=plant_id)

def search_plants_api(request):
    """API endpoint for plant search"""
    query = request.GET.get('q', '')
    try:
        results = trefle_api.search_plants(query, per_page=10)
        return JsonResponse(results)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def search_plants(request):
    """Search plants in our database"""
    query = request.GET.get('q', '')
    if query:
        plants = Plant.objects.filter(
            Q(name__icontains=query) |
            Q(scientific_name__icontains=query)
        ).order_by('-created_at')
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
    
    return redirect('main:plant_detail', plant_id=plant.id)

@login_required
def delete_detail(request, plant_id, detail_id):
    """Delete a plant detail."""
    detail = get_object_or_404(PlantDetail, id=detail_id, plant__id=plant_id)
    if request.user == detail.plant.user:
        detail.delete()
        messages.success(request, 'Detail deleted successfully!')
    else:
        messages.error(request, 'You do not have permission to delete this detail.')
    return redirect('main:plant_detail', plant_id=plant_id)

@login_required
def delete_observation(request, plant_id, observation_id):
    """Delete a plant observation."""
    observation = get_object_or_404(Observation, id=observation_id, plant__id=plant_id)
    if request.user == observation.plant.user:
        observation.delete()
        messages.success(request, 'Observation deleted successfully!')
    else:
        messages.error(request, 'You do not have permission to delete this observation.')
    return redirect('main:plant_detail', plant_id=plant_id)

@login_required
def delete_photo(request, plant_id, photo_id):
    """Delete a plant photo."""
    photo = get_object_or_404(PlantPhoto, id=photo_id, plant__id=plant_id)
    if request.user == photo.plant.user:
        photo.delete()
        messages.success(request, 'Photo deleted successfully!')
    else:
        messages.error(request, 'You do not have permission to delete this photo.')
    return redirect('main:plant_detail', plant_id=plant_id)

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
