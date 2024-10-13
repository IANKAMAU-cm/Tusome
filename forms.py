from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField, FileField
from wtforms.validators import DataRequired, EqualTo, ValidationError, Length
from models import User
from enum import Enum
from flask_wtf.file import FileAllowed


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