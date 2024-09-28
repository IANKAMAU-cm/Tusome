from django.contrib import admin
from .models import CustomUser, Course, Quiz, Question, Grade
# Register your models here.
# Register the CustomUser model
admin.site.register(CustomUser)

# Register the Course model
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'instructor')
    search_fields = ('title',)

# Register the Quiz model
@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'created_at')
    search_fields = ('title',)

# Register the Question model
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'quiz')
    search_fields = ('text',)

# Register the Grade model
@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('student', 'quiz', 'score', 'date_taken')
    search_fields = ('student__username', 'quiz__title')