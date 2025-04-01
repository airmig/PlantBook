from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('upload/', views.upload_plant, name='upload_plant'),
    path('upload-plant/', views.upload_plant, name='upload_plant'),
    path('search-plants/', views.search_plants, name='search_plants'),
    path('search-plants-api/', views.search_plants_api, name='search_plants_api'),
    path('plant/<int:plant_id>/', views.plant_detail, name='plant_detail'),
    path('plant/<int:plant_id>/edit/', views.edit_plant, name='edit_plant'),
    path('plant/<int:plant_id>/delete/', views.delete_plant, name='delete_plant'),
    path('plant/<int:plant_id>/add-observation/', views.add_observation, name='add_observation'),
    path('plant/<int:plant_id>/add-photo/', views.add_photo, name='add_photo'),
    path('plant/<int:plant_id>/add-comment/', views.add_comment, name='add_comment'),
    path('plant/<int:plant_id>/delete-comment/<int:comment_id>/', views.delete_comment, name='delete_comment'),
    path('profile/', views.profile, name='profile'),
    path('directory/', views.directory, name='directory'),
    path('my-plants/', views.my_plants, name='my_plants'),
    path('user/<int:user_id>/', views.user_profile, name='user_profile'),
    path('plant/<int:plant_id>/add-detail/', views.add_detail, name='add_detail'),
    path('plant/<int:plant_id>/delete-detail/<int:detail_id>/', views.delete_detail, name='delete_detail'),
    path('plant/<int:plant_id>/delete-observation/<int:observation_id>/', views.delete_observation, name='delete_observation'),
    path('plant/<int:plant_id>/delete-photo/<int:photo_id>/', views.delete_photo, name='delete_photo'),
] 