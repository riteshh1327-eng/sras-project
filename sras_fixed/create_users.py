from django.contrib.auth import get_user_model

User = get_user_model()

if not User.objects.filter(username="teacher").exists():
    User.objects.create_user(username="teacher", password="1234")

if not User.objects.filter(username="student").exists():
    User.objects.create_user(username="student", password="1234")

print("Default users created successfully")
