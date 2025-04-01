import os
import django
import random
from datetime import datetime, timedelta
from faker import Faker

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'plantbook.settings')
django.setup()

from django.contrib.auth.models import User
from main.models import Profile

# Initialize Faker
fake = Faker()

# List of common plant-related usernames
plant_usernames = [
    'plantlover', 'gardenmaster', 'greenthumb', 'plantwhisperer', 'botanical',
    'herbgarden', 'succulent', 'flowerpower', 'plantlife', 'gardenlife',
    'plantcare', 'gardenlove', 'plantparent', 'gardenbuddy', 'plantfriend',
    'gardenpro', 'plantexpert', 'gardenlover', 'plantguide', 'gardenhelp',
    'planttips', 'gardenjoy', 'plantjoy', 'gardenpeace', 'plantpeace',
    'gardenzen', 'plantzen', 'gardenflow', 'plantflow', 'gardenbloom',
    'plantbloom', 'gardenrise', 'plantrise', 'gardenpath', 'plantpath',
    'gardenwalk', 'plantwalk', 'gardenrest', 'plantrest', 'gardenhome',
    'planthome', 'gardenlife', 'plantlife', 'gardenlove', 'plantlove',
    'gardenjoy', 'plantjoy', 'gardenpeace', 'plantpeace', 'gardenzen'
]

# List of common plant-related passwords
plant_passwords = [
    'Garden123!', 'PlantLife1!', 'GreenThumb1!', 'FlowerPower1!', 'Botanical1!',
    'HerbGarden1!', 'Succulent1!', 'PlantCare1!', 'GardenLove1!', 'PlantLife1!',
    'GardenBuddy1!', 'PlantExpert1!', 'GardenLover1!', 'PlantGuide1!', 'GardenHelp1!',
    'PlantTips1!', 'GardenJoy1!', 'PlantJoy1!', 'GardenPeace1!', 'PlantPeace1!',
    'GardenZen1!', 'PlantZen1!', 'GardenFlow1!', 'PlantFlow1!', 'GardenBloom1!',
    'PlantBloom1!', 'GardenRise1!', 'PlantRise1!', 'GardenPath1!', 'PlantPath1!',
    'GardenWalk1!', 'PlantWalk1!', 'GardenRest1!', 'PlantRest1!', 'GardenHome1!',
    'PlantHome1!', 'GardenLife1!', 'PlantLife1!', 'GardenLove1!', 'PlantLove1!',
    'GardenJoy1!', 'PlantJoy1!', 'GardenPeace1!', 'PlantPeace1!', 'GardenZen1!',
    'PlantZen1!', 'GardenFlow1!', 'PlantFlow1!', 'GardenBloom1!', 'PlantBloom1!'
]

# Save passwords to a file
with open('test_users_passwords.txt', 'w') as f:
    f.write("Test Users Credentials\n")
    f.write("=====================\n\n")
    
    for i in range(50):
        # Generate random user data
        first_name = fake.first_name()
        last_name = fake.last_name()
        email = f"{plant_usernames[i]}@example.com"
        password = plant_passwords[i]
        username = plant_usernames[i]
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        # Create profile with random data
        profile = Profile.objects.create(
            user=user,
            bio=fake.text(max_nb_chars=200),
            location=fake.city(),
            website=fake.url(),
            date_of_birth=fake.date_of_birth(minimum_age=18, maximum_age=80),
            profile_photo=None  # You can add profile photos later if needed
        )
        
        # Save credentials to file
        f.write(f"User {i+1}:\n")
        f.write(f"Username: {username}\n")
        f.write(f"Email: {email}\n")
        f.write(f"Password: {password}\n")
        f.write(f"Name: {first_name} {last_name}\n")
        f.write(f"Location: {profile.location}\n")
        f.write(f"Website: {profile.website}\n")
        f.write(f"Bio: {profile.bio}\n")
        f.write("-" * 50 + "\n\n")
        
        print(f"Created user {i+1}: {username}")

print("\nAll test users have been created successfully!")
print("Credentials have been saved to 'test_users_passwords.txt'") 