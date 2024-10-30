from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField, FileField, BooleanField, FieldList, FormField
from wtforms.validators import DataRequired, EqualTo, ValidationError, Length
from models import User
from enum import Enum
from flask_wtf.file import FileAllowed
from flask import request


class RoleEnum(Enum):
    STUDENT = 'student'
    INSTRUCTOR = 'instructor'

class RegistrationForm(FlaskForm):
    """Form for registering a new user."""
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=150)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match.')])
    role = SelectField('Role', choices=[(role.value, role.name.capitalize()) for role in RoleEnum], validators=[DataRequired()])
    submit = SubmitField('Register')

    def validate_username(self, username):
        """Validate that the username is unique."""
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is already taken.')

class LoginForm(FlaskForm):
    """Form for user login."""
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class CourseForm(FlaskForm):
    """Form for creating a new course."""
    title = StringField('Course Title', validators=[DataRequired()])
    description = TextAreaField('Course Description', validators=[DataRequired()])
    is_featured = BooleanField('Featured Course')
    submit = SubmitField('Create Course')

class EnrollCourseForm(FlaskForm):
    #course = SelectField('Select Course', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Enroll')

class UploadMaterialForm(FlaskForm):
    course = SelectField('Course', coerce=int, validators=[DataRequired()])
    material = FileField('Course Material', validators=[DataRequired(), FileAllowed(['pdf', 'docx', 'pptx'], 'Documents only!')])
    submit = SubmitField('Upload Material')

class LessonForm(FlaskForm):
    """Form for creating and editing lessons."""
    title = StringField('Lesson Title', validators=[DataRequired(), Length(max=200)])
    content = TextAreaField('Lesson Content', validators=[DataRequired()])
    submit = SubmitField('Save Lesson')

class DeleteLessonForm(FlaskForm):
    """Form for deleting a lesson."""
    submit = SubmitField('Delete Lesson')

class QuestionForm(FlaskForm):
    """Form for creating a question."""
    question_text = TextAreaField('Question', validators=[DataRequired()])
    answer = StringField('Your Answer')
    correct_answer = StringField('Correct Answer', validators=[DataRequired()])
    submit = SubmitField('Add Question')

class QuizForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    status = SelectField('Status', choices=[('Active', 'Active'), ('Inactive', 'Inactive')], validators=[DataRequired()])
    questions = FieldList(FormField(QuestionForm), min_entries=1)
    submit = SubmitField('Create Quiz')
 
    # Accept the extra_validators argument
    def validate(self, extra_validators=None):
        if request.endpoint == 'submit_quiz':  # Only validate answers when submitting the quiz
            for question in self.questions:
                if not question.answer.data:
                    self.errors['questions'] = [{'answer': ['This field is required.']}]
                    return False
            return True
        else:
            # Default validation for creating/editing the quiz
            return super(QuizForm, self).validate(extra_validators=extra_validators)

    