import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from main.models import Profile
from faker import Faker
import random

class Command(BaseCommand):
    help = 'Creates 50 test users with random data'

    def handle(self, *args, **kwargs):
        fake = Faker()
        
        # List of plant-related words for usernames
        plant_words = ['flower', 'leaf', 'tree', 'garden', 'plant', 'seed', 'root', 'stem', 'petal', 'bloom']
        
        # File to store user credentials
        output_file = 'test_users_passwords.txt'
        
        with open(output_file, 'w') as f:
            f.write("Test Users Credentials:\n\n")
            
            for i in range(50):
                try:
                    # Generate username
                    username = f"{random.choice(plant_words)}_{fake.user_name()}_{random.randint(1, 999)}"
                    
                    # Generate password
                    password = fake.password(length=12)
                    
                    # Create user
                    user = User.objects.create_user(
                        username=username,
                        email=fake.email(),
                        password=password,
                        first_name=fake.first_name(),
                        last_name=fake.last_name()
                    )
                    
                    # Save credentials to file
                    f.write(f"User {i+1}:\n")
                    f.write(f"Username: {username}\n")
                    f.write(f"Password: {password}\n")
                    f.write(f"Email: {user.email}\n")
                    f.write(f"Name: {user.get_full_name()}\n\n")
                    
                    self.stdout.write(self.style.SUCCESS(f'Successfully created user: {username}'))
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Failed to create user {i+1}: {str(e)}'))
                    continue
            
        self.stdout.write(self.style.SUCCESS(f'\nCreated users and saved credentials to {output_file}')) 