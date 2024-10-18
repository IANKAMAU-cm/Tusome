# models.py

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from enum import Enum
from extensions import db

class RoleEnum(Enum):
    ADMIN = 'admin'
    INSTRUCTOR = 'instructor'
    STUDENT = 'student'

class User(UserMixin, db.Model):
    """Model for User."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.Enum(RoleEnum), nullable=False)  # Using Enum for roles

    # Define one-to-one relationships with Instructor and Student
    instructor = db.relationship('Instructor', back_populates='user', uselist=False)
    student = db.relationship('Student', back_populates='user', uselist=False)

    def __repr__(self):
        return f'<User {self.username}>'

class Instructor(db.Model):
    __tablename__ = 'instructor'
    """Model for Instructor, extends User."""
    id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)

    # Define relationship with User
    user = db.relationship('User', back_populates='instructor')

    # Define one-to-many relationship with Course
    courses = db.relationship('Course', back_populates='instructor', lazy=True)

class Student(db.Model):
    __tablename__ = 'student'
    """Model for Student, extends User."""
    id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)

    # Define relationship with User
    user = db.relationship('User', back_populates='student')

    # Define one-to-many relationship with Enrollment
    enrollments = db.relationship('Enrollment', back_populates='student', lazy=True)

    # Define one-to-many relationship with Submission
    submissions = db.relationship('Submission', back_populates='student', lazy=True)

    quiz_submissions = db.relationship('QuizSubmission', back_populates='student', lazy=True)

class Course(db.Model):
    """Model for Course."""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    is_featured = db.Column(db.Boolean, default=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey('instructor.id'), nullable=False)

    # Define relationship with Instructor
    instructor = db.relationship('Instructor', back_populates='courses')

    # Define one-to-many relationships with Lesson, Quiz, CourseMaterial, Enrollment, Submission
    lessons = db.relationship('Lesson', back_populates='course', lazy=True)
    quizzes = db.relationship('Quiz', back_populates='course', lazy=True)
    materials = db.relationship('CourseMaterial', back_populates='course', lazy=True)
    enrollments = db.relationship('Enrollment', back_populates='course', lazy=True)
    submissions = db.relationship('Submission', back_populates='course', lazy=True)

class Lesson(db.Model):
    """Model for Lesson."""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)  # Use this for the URL
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)

    # Define relationship with Course
    course = db.relationship('Course', back_populates='lessons')

class Enrollment(db.Model):
    """Model for Enrollment of Students in Courses."""
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    progress = db.Column(db.Float, default=0.0)

    __table_args__ = (db.UniqueConstraint('student_id', 'course_id', name='unique_enrollment'),)

    # Define relationships
    student = db.relationship('Student', back_populates='enrollments')
    course = db.relationship('Course', back_populates='enrollments')

class Quiz(db.Model):
    """Model for Quiz associated with a Course."""
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), nullable=False)

    # Define relationship with Course
    course = db.relationship('Course', back_populates='quizzes')

    # Define one-to-many relationship with Question
    questions = db.relationship('Question', back_populates='quiz', lazy=True)

    quiz_submissions = db.relationship('QuizSubmission', back_populates='quiz', lazy=True)

class Question(db.Model):
    """Model for Questions in a Quiz."""
    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.String(200), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)

    # Define relationship with Quiz
    quiz = db.relationship('Quiz', back_populates='questions')

    quiz_submissions = db.relationship('QuizSubmission', back_populates='question', lazy=True)

class CourseMaterial(db.Model):
    """Model for Course Materials uploaded by Instructors."""
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

    # Define relationship with Course
    course = db.relationship('Course', back_populates='materials')

class Submission(db.Model):
    """Model for Student Submissions."""
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    submission_file = db.Column(db.String(100), nullable=False)
    submission_date = db.Column(db.DateTime, default=datetime.utcnow)
    grade = db.Column(db.Float, nullable=True)  # Changed to Float for possible decimal grades

    # Define relationships
    student = db.relationship('Student', back_populates='submissions')
    course = db.relationship('Course', back_populates='submissions')

class QuizSubmission(db.Model):
    """Model to store student submissions for quizzes."""
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    selected_answer = db.Column(db.String(200), nullable=False)
    submission_date = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    student = db.relationship('Student', back_populates='quiz_submissions')
    quiz = db.relationship('Quiz', back_populates='quiz_submissions')
    question = db.relationship('Question', back_populates='quiz_submissions')
