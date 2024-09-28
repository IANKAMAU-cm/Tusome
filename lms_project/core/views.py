from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from .forms import StudentSignUpForm, InstructorSignUpForm, CustomAuthenticationForm, AdminUserCreationForm, UserCreationForm
from django.contrib import messages
from django.contrib.auth.models import User

# Create your views here.
def home(request):
    return render(request, 'core/home.html')
def student_register(request):
    if request.method == 'POST':
        form = StudentSignUpForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Registration successful. You can now log in.')
            return redirect('login')
    else:
        form = StudentSignUpForm()
    return render(request, 'core/student_register.html', {'form': form})

def student_dashboard(request):
    return render(request, 'core/student_dashboard.html')

def student_courses(request):
    # Your logic for rendering the student courses page
    return render(request, 'student/courses.html')

def instructor_register(request):
    if request.method == 'POST':
        form = InstructorSignUpForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Registration successful. You can now log in.')
            return redirect('login')
    else:
        form = InstructorSignUpForm()
    return render(request, 'core/instructor_register.html', {'form': form})

def instructor_dashboard(request):
    # Your logic here
    return render(request, 'instructor_dashboard.html')

def manage_courses(request):
    # Your logic for managing courses
    return render(request, 'your_template.html')     # Replace 'your_template' with the actual name of your template for managing courses

def user_login(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.info(request, f'You are now logged in as {username}.')
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = CustomAuthenticationForm()
    return render(request, 'core/login.html', {'form': form})

@login_required
def register_admin(request):
    if not request.user.is_superuser:
        return redirect('admin_dashboard')  # Redirect if not admin
    if request.method == 'POST':
        form = AdminUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.is_superuser = True  # Make the user an admin
            user.is_staff = True  # Allow admin access
            user.save()
            messages.success(request, 'Admin user created successfully!')
            return redirect('admin_dashboard')  # Redirect to admin dashboard or any desired page
    else:
        form = AdminUserCreationForm()
    return render(request, 'admin/register_admin.html', {'form': form})

@login_required
def user_logout(request):
    logout(request)
    messages.info(request, 'You have successfully logged out.')
    return redirect('login')

@login_required
def dashboard(request):
    user = request.user
    if user.is_student:
        return render(request, 'core/student_dashboard.html')
    elif user.is_instructor:
        return render(request, 'core/instructor_dashboard.html')
    elif user.is_admin or user.is_staff:
        return render(request, 'core/admin_dashboard.html')
    else:
        return render(request, 'core/base.html', {'message': 'No dashboard available for your role.'})