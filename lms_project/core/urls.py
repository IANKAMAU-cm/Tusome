from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('student/register/', views.student_register, name='student_register'),
    path('instructor/register/', views.instructor_register, name='instructor_register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/courses/', views.student_courses, name='student_courses'),
    path('instructor/dashboard/', views.instructor_dashboard, name='instructor_dashboard'),
    path('manage-courses/', views.manage_courses, name='manage_courses'),
]

