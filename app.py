from flask import Flask, render_template, redirect, url_for, flash, request, send_from_directory, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db  # Import db from extensions (correct place)
from models import User, Course, CourseMaterial, Submission, Enrollment, Student, Quiz, RoleEnum, Instructor, Lesson, Question, QuizSubmission  # Import your models
from forms import RegistrationForm, LoginForm, CourseForm, EnrollCourseForm, UploadMaterialForm, LessonForm, DeleteLessonForm, QuestionForm, QuizForm
from functools import wraps
from werkzeug.utils import secure_filename
import os
from enum import Enum
from models import RoleEnum
from flask_wtf.csrf import CSRFProtect
from slugify import slugify
from datetime import datetime
import re
from flask_wtf import CSRFProtect
from collections import defaultdict

# Initialize the app
app = Flask(__name__)

# Load the configuration from config.py
app.config.from_object('config.Config')

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Initialize the database with the app
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect to login page if not authenticated


# Custom filter to convert newlines to <br> tags
def nl2br(value):
    return re.sub(r'\n', '<br>\n', value)

# Register the filter with Jinja2
app.jinja_env.filters['nl2br'] = nl2br

@app.context_processor
def inject_current_year():
    return {'current_year': datetime.utcnow().year}

# Define user loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_tables():
    """Create the database tables if they don't exist."""
    with app.app_context():
        #db.drop_all()
        db.create_all()
        create_admin()
        
def create_admin():
    admin_user = User.query.filter_by(username='admin', role=RoleEnum.ADMIN).first()
    if not admin_user:
        hashed_password = generate_password_hash('admin', method='pbkdf2:sha256')
        new_admin = User(username='admin', password=hashed_password, role=RoleEnum.ADMIN)
        db.session.add(new_admin)
        db.session.commit()


# Call the create_tables function to ensure tables are created at startup
create_tables()

@app.context_processor
def inject_roleenum():
    return dict(RoleEnum=RoleEnum)


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login route."""
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = User.query.filter_by(username=username, role='admin').first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('admin_login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration route."""
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            # Create a new user
            hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
            # Ensure the role is passed correctly as an enum
            role_enum = RoleEnum[form.role.data.upper()]
        except KeyError:
            flash('Invalid role selected.', 'danger')
            return render_template('register.html', form=form)

        new_user = User(username=form.username.data, password=hashed_password, role=role_enum)
        db.session.add(new_user)
        db.session.commit()

        # Create Instructor or Student record based on role
        if new_user.role == RoleEnum.INSTRUCTOR:
            new_instructor = Instructor(id=new_user.id)  # Use 'id' instead of 'user_id'
            db.session.add(new_instructor)
        elif new_user.role == RoleEnum.STUDENT:
            new_student = Student(id=new_user.id)  # Use 'id' instead of 'user_id'
            db.session.add(new_student)

        db.session.commit()
        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)
@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login route."""
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        # Check if user exists and password is correct
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)

            # Redirect based on user role
            if user.role == RoleEnum.ADMIN:
                return redirect(url_for('admin_dashboard'))
            elif user.role == RoleEnum.INSTRUCTOR:
                return redirect(url_for('instructor_dashboard'))
            elif user.role == RoleEnum.STUDENT:
                return redirect(url_for('student_dashboard'))
            else:
                return redirect(url_for('logout'))  # Fallback for unhandled roles
        else:
            flash('Login failed. Please check your username and password.', 'danger')
    return render_template('login.html', form=form)

def role_required(role):
    """Decorator to restrict access based on user role."""
    def decorator(f):
        @wraps(f)
        @login_required  # Ensure the user is logged in
        def decorated_function(*args, **kwargs):
            if current_user.role != role:
                flash('Access denied.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Admin Dashboard
@app.route('/admin/dashboard')
@role_required(RoleEnum.ADMIN)
def admin_dashboard():
    """Admin dashboard route."""
    return render_template('admin_dashboard.html')

@app.route('/manage_courses')
@login_required
def manage_courses():
    courses = Course.query.all()  # Fetch all courses from the database
    return render_template('manage_courses.html', courses=courses)

@app.route('/delete_course/<int:course_id>', methods=['POST'])
@login_required
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    db.session.delete(course)
    db.session.commit()
    flash('Course deleted successfully.', 'success')
    return redirect(url_for('manage_courses'))

# Instructor Dashboard
@app.route('/instructor_dashboard')
@role_required(RoleEnum.INSTRUCTOR)
def instructor_dashboard():
    """Instructor dashboard route."""
    # Access the instructor record linked to the current user
    instructor = current_user.instructor  # This should now work correctly

    # Example: Fetch stats from the database
    total_courses = Course.query.filter_by(instructor_id=instructor.id).count()
    # To get total students related to the instructor's courses:
    total_students = Student.query.join(Enrollment).join(Course).filter(Course.instructor_id == instructor.id).distinct().count()
    pending_assignments = Quiz.query.filter_by(status='pending').count()
    courses = instructor.courses  # Fetch all courses associated with the instructor

    return render_template('instructor_dashboard.html', 
                           total_courses=total_courses, 
                           total_students=total_students,
                           pending_assignments=pending_assignments,
                           courses=courses)

@app.route('/instructor/view_courses')
@role_required(RoleEnum.INSTRUCTOR)
def view_courses():
    """Route for instructors to view their courses."""
    instructor = current_user.instructor
    if not instructor:
        flash('Instructor profile not found.', 'danger')
        return redirect(url_for('index'))
    
    courses = instructor.courses  # Access the related courses
    return render_template('view_courses.html', courses=courses)


# 2.1. Route to Create a Lesson
@app.route('/instructor/create_lesson/<int:course_id>', methods=['GET', 'POST'])
@role_required(RoleEnum.INSTRUCTOR)
def create_lesson(course_id):
    """Route for instructors to create a new lesson for a specific course."""
    course = Course.query.get_or_404(course_id)
    
    # Ensure the current instructor owns the course
    if course.instructor_id != current_user.instructor.id:
        abort(403)  # Forbidden

    form = LessonForm()
    if form.validate_on_submit():
        # Generate slug from the lesson title
        slug = slugify(form.title.data)
        
        new_lesson = Lesson(
            title=form.title.data,
            content=form.content.data,
            course_id=course.id,
            slug=slug  # Save the slug in the lesson model
        )
        db.session.add(new_lesson)
        db.session.commit()
        flash(f'Lesson "{new_lesson.title}" has been created successfully.', 'success')
        return redirect(url_for('lesson_detail', slug=slug))  # Redirect to the lesson detail page
    return render_template('create_lesson.html', form=form, course=course)

# 2.2. Route to Edit a Lesson
@app.route('/instructor/edit_lesson/<int:lesson_id>', methods=['GET', 'POST'])
@role_required(RoleEnum.INSTRUCTOR)
def edit_lesson(lesson_id):
    """Route for instructors to edit an existing lesson."""
    lesson = Lesson.query.get_or_404(lesson_id)
    course = lesson.course
    
    # Ensure the current instructor owns the course
    if course.instructor_id != current_user.instructor.id:
        abort(403)  # Forbidden

    form = LessonForm(obj=lesson)
    if form.validate_on_submit():
        lesson.title = form.title.data
        lesson.content = form.content.data
        db.session.commit()
        flash(f'Lesson "{lesson.title}" has been updated successfully.', 'success')
        return redirect(url_for('instructor_dashboard'))
    return render_template('edit_lesson.html', form=form, lesson=lesson)

# 2.3. Route to Delete a Lesson
@app.route('/instructor/delete_lesson/<int:lesson_id>', methods=['POST'])
@role_required(RoleEnum.INSTRUCTOR)
def delete_lesson(lesson_id):
    """Route for instructors to delete a lesson."""
    lesson = Lesson.query.get_or_404(lesson_id)
    course = lesson.course
    
    # Ensure the current instructor owns the course
    if course.instructor_id != current_user.instructor.id:
        abort(403)  # Forbidden

    form = DeleteLessonForm()
    if form.validate_on_submit():
        db.session.delete(lesson)
        db.session.commit()
        flash(f'Lesson "{lesson.title}" has been deleted successfully.', 'success')
    else:
        flash('Failed to delete the lesson. Please try again.', 'danger')
    return redirect(url_for('instructor_dashboard'))

@app.route('/lesson/<slug>')
def lesson_detail(slug):
    lesson = Lesson.query.filter_by(slug=slug).first_or_404()
    return render_template('lesson_detail.html', lesson=lesson)

# Student Dashboard
@app.route('/student_dashboard')
@role_required(RoleEnum.STUDENT)
def student_dashboard():
    """Student dashboard route."""
    enrollments = current_user.student.enrollments
    courses = [enrollment.course for enrollment in enrollments]
    return render_template('student_dashboard.html', courses=courses)

@app.route('/browse_courses')
@role_required(RoleEnum.STUDENT)
def browse_courses():
    """Route for students to browse available courses."""
    # Get the student's enrolled course IDs
    enrolled_course_ids = [enrollment.course_id for enrollment in current_user.student.enrollments]

    # Fetch courses that the student is not enrolled in
    available_courses = Course.query.filter(~Course.id.in_(enrolled_course_ids)).all()

    # Instantiate the enrollment form
    form = EnrollCourseForm()

    return render_template('browse_courses.html', courses=available_courses, form=form)

@app.route('/enroll/<int:course_id>', methods=['POST'])
@role_required(RoleEnum.STUDENT)
def enroll(course_id):
    """Route for students to enroll in a course."""
    form = EnrollCourseForm()
    if form.validate_on_submit():
        # Check if the course exists
        course = Course.query.get_or_404(course_id)
        
        # Check if the student is already enrolled
        existing_enrollment = Enrollment.query.filter_by(student_id=current_user.student.id, course_id=course_id).first()
        if existing_enrollment:
            flash('You are already enrolled in this course.', 'warning')
            return redirect(url_for('browse_courses'))
        
        # Create a new enrollment
        new_enrollment = Enrollment(student_id=current_user.student.id, course_id=course_id)
        db.session.add(new_enrollment)
        db.session.commit()
        flash(f'You have successfully enrolled in {course.title}!', 'success')
        return redirect(url_for('my_courses'))
    else:
        # If form validation fails, flash an error message
        flash('Enrollment failed. Please try again.', 'danger')
        return redirect(url_for('browse_courses'))

@app.route('/my_courses')
@role_required(RoleEnum.STUDENT)
def my_courses():
    """Route for students to view their enrolled courses."""
    enrollments = current_user.student.enrollments
    courses = [enrollment.course for enrollment in enrollments]
    return render_template('my_courses.html', courses=courses)


@app.route('/course/<int:course_id>')
@login_required
def course_details(course_id):
    """Route to view course details and manage materials."""
    course = Course.query.get_or_404(course_id)

    if current_user.role == RoleEnum.STUDENT:
        # Check if the student is enrolled in the course
        enrollment = Enrollment.query.filter_by(student_id=current_user.student.id, course_id=course_id).first()
        if not enrollment:
            flash('You are not enrolled in this course.', 'danger')
            return redirect(url_for('browse_courses'))
        
        lessons = course.lessons
        materials = course.materials
        quizzes = course.quizzes
        return render_template('course_details.html', course=course, lessons=lessons, materials=materials, quizzes=quizzes)
    
    elif current_user.role == RoleEnum.INSTRUCTOR:
        # Ensure the instructor owns the course
        if course.instructor_id != current_user.instructor.id:
            flash('You do not have permission to view this course.', 'danger')
            return redirect(url_for('instructor_dashboard'))
        
        lessons = course.lessons
        materials = course.materials
        quizzes = course.quizzes
        delete_form = DeleteLessonForm()
        return render_template('course_details.html', course=course, lessons=lessons, materials=materials, quizzes=quizzes, form=delete_form)
    
    else:
        # For other roles, deny access
        flash('Access denied.', 'danger')
        abort(403)

@app.route('/download_material/<int:material_id>')
@role_required(RoleEnum.STUDENT)
def download_material(material_id):
    """Route to download course material."""
    material = CourseMaterial.query.get_or_404(material_id)

    # Check if the student is enrolled in the course
    enrollment = Enrollment.query.filter_by(student_id=current_user.student.id, course_id=material.course_id).first()
    if not enrollment:
        flash('You are not authorized to access this material.', 'danger')
        return redirect(url_for('browse_courses'))

    # Send the file from the upload directory
    try:
        return send_from_directory(directory=app.config['UPLOAD_FOLDER'], filename=material.filename, as_attachment=True)
    except FileNotFoundError:
        abort(404)



@app.route('/student/submit_assignment/<int:course_id>', methods=['POST'])
@login_required
def submit_assignment(course_id):
    """Student submit assignment route."""
    if current_user.role == 'student':
        file = request.files['file']
        if file:
            filename = secure_filename(file.filename)
            submission_path = os.path.join(app.config['SUBMISSIONS_FOLDER'], filename)
            file.save(submission_path)
            submission = Submission(student_id=current_user.student.id, course_id=course_id, submission_file=filename)
            db.session.add(submission)
            db.session.commit()
            flash('Assignment submitted successfully!', 'success')
            return redirect(url_for('view_course', course_id=course_id))
    flash('Failed to submit assignment.', 'danger')
    return redirect(url_for('home'))

@app.route('/student/view_enrolled_courses')
@login_required
def view_enrolled_courses():
    """View enrolled courses route."""
    return render_template('view_enrolled_courses.html')

# Admin manage users
@app.route('/admin/manage_users')
@role_required(RoleEnum.ADMIN)
def manage_users():
    """Admin manage users route."""
    users = User.query.all()
    return render_template('manage_users.html', users=users)

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully.', 'success')
    return redirect(url_for('manage_users'))

@app.route('/instructor/create_course', methods=['GET', 'POST'])
@role_required(RoleEnum.INSTRUCTOR)
def create_course():
    """Instructor create course route."""
    form = CourseForm()
    if form.validate_on_submit():
        course = Course(
            title=form.title.data,
            description=form.description.data,
            is_featured=form.is_featured.data,
            instructor_id=current_user.instructor.id
        )

        db.session.add(course)
        db.session.commit()
        flash('Course created successfully!', 'success')
        return redirect(url_for('instructor_dashboard'))
    return render_template('create_course.html', form=form)


@app.route('/instructor/edit_course/<int:course_id>', methods=['GET', 'POST'])
@role_required(RoleEnum.INSTRUCTOR)
def edit_course(course_id):
    """Route for instructors to edit an existing course."""
    course = Course.query.get_or_404(course_id)
    
    # Ensure the current instructor owns the course
    if course.instructor_id != current_user.instructor.id:
        flash('You do not have permission to edit this course.', 'danger')
        return redirect(url_for('view_courses'))
    
    form = CourseForm(obj=course)  # Pre-populate form with existing course data
    if form.validate_on_submit():
        course.title = form.title.data
        course.description = form.description.data
        course.is_featured = form.is_featured.data 
        db.session.commit()
        flash(f'Course "{course.title}" has been updated successfully.', 'success')
        return redirect(url_for('view_courses'))
    
    return render_template('edit_course.html', form=form, course=course)


@app.route('/upload_material', methods=['GET', 'POST'])
@login_required
@role_required(RoleEnum.INSTRUCTOR)
def upload_material():
    """Route for instructors to upload course materials."""
    form = UploadMaterialForm()

    # Populate course choices dynamically
    form.course.choices = [(course.id, course.title) for course in Course.query.filter_by(instructor_id=current_user.instructor.id).all()]

    if form.validate_on_submit():
        # Get the file from the form
        file = form.material.data
        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            # Add the file to the database
            new_material = CourseMaterial(filename=filename, course_id=form.course.data)
            db.session.add(new_material)
            db.session.commit()

            flash('Course material uploaded successfully!', 'success')
            return redirect(url_for('instructor_dashboard'))

    return render_template('upload_material.html', form=form)


@app.route('/view_course_materials/<int:course_id>')
@login_required
def view_course_materials(course_id):
    materials = CourseMaterial.query.filter_by(course_id=course_id).all()
    course = Course.query.get_or_404(course_id)
    return render_template('view_course_materials.html', materials=materials, course=course)



#@app.route('/manage_students')
#@role_required(RoleEnum.ADMIN)
#def manage_students():
    #"""Admin manage students route."""
    #students = Student.query.all()
    #return render_template('manage_students.html', students=students)

@app.route('/instructor/manage_students')
@login_required
def manage_students():
    # Fetch all students
    students = db.session.query(Student).all()

    # Prepare a list of students with their enrolled courses and taken quizzes
    student_courses_quizzes = []
    for student in students:
        # Fetch the titles of the courses the student is enrolled in
        courses = [enrollment.course.title for enrollment in student.enrollments]

        # Use a dictionary to store only the first quiz submission per quiz
        quiz_dict = {}
        for quiz_submission in student.quiz_submissions:
            quiz = quiz_submission.quiz
            if quiz.id not in quiz_dict:
                quiz_dict[quiz.id] = (quiz.title, quiz_submission.grade)

        # Append student data to the list
        student_courses_quizzes.append({
            'student': student,
            'courses': courses,
            'quizzes': list(quiz_dict.values())  # Convert dictionary back to list
        })

    return render_template('manage_students.html', student_courses_quizzes=student_courses_quizzes)

@app.route('/create_quiz/<int:course_id>', methods=['GET', 'POST'])
@login_required
def create_quiz(course_id):
    if current_user.role != RoleEnum.INSTRUCTOR:
        flash('You are not authorized to access this page.')
        return redirect(url_for('index'))

    form = QuizForm()
    
    if form.validate_on_submit():
        # Create the quiz object
        quiz = Quiz(title=form.title.data, status=form.status.data, course_id=course_id)
        db.session.add(quiz)
        db.session.commit()

        # Add questions to the quiz
        for question in form.questions:
            # Ensure that each question has valid data
            question_data = question.data
            question_model = Question(
                question_text=question_data['question_text'],
                correct_answer=question_data['correct_answer'],
                quiz_id=quiz.id
            )
            db.session.add(question_model)

        db.session.commit()
        flash('Quiz created successfully!', 'success')
        return redirect(url_for('instructor_dashboard'))

    return render_template('create_quiz.html', form=form, course_id=course_id)


@app.route('/course/<int:course_id>/quiz/<int:quiz_id>', methods=['GET', 'POST'])
@login_required
def take_quiz(course_id, quiz_id):
    if current_user.role != RoleEnum.STUDENT:
        flash('You are not authorized to access this page.')
        return redirect(url_for('index'))

    course = Course.query.get_or_404(course_id)
    quiz = Quiz.query.get_or_404(quiz_id)

    # Initialize the quiz form
    form = QuizForm()

    if request.method == 'GET':
        # Clear the form.questions before appending to avoid duplicates
        form.questions.entries.clear()

        # Append questions to the form
        for question in quiz.questions:
            question_form = QuestionForm()
            question_form.question_text.data = question.question_text  # This should set the correct question text
            form.questions.append_entry(question_form)

    # Handle form submission
    if form.validate_on_submit():
        # Process the submitted answers
        for idx, question_form in enumerate(form.questions):
            selected_answer = question_form.answer.data
            question = quiz.questions[idx]

            # Save the student's submission
            submission = QuizSubmission(
                student_id=current_user.id,
                quiz_id=quiz.id,
                question_id=question.id,
                selected_answer=selected_answer
            )
            db.session.add(submission)

        db.session.commit()
        flash('Quiz submitted successfully!', 'success')
        return redirect(url_for('student_dashboard'))

    return render_template('take_quiz.html', course=course, quiz=quiz, form=form)

@app.route('/course/<int:course_id>/quiz/<int:quiz_id>/submit', methods=['POST'])
@login_required
def submit_quiz(course_id, quiz_id):
    """Handles quiz submission and automatic grading."""
    # Get the quiz by quiz_id
    quiz = Quiz.query.get_or_404(quiz_id)
    course = Course.query.get_or_404(course_id)
    form = QuizForm(request.form)

    total_grade = 0  # Initialize total grade

    if form.validate_on_submit():
        for idx, question_form in enumerate(form.questions):
            selected_answer = question_form.answer.data
            question = quiz.questions[idx]

            # Check for existing submission before adding a new one
            existing_submission = QuizSubmission.query.filter_by(
                student_id=current_user.id,
                quiz_id=quiz.id,
                question_id=question.id
            ).first()

            if not existing_submission:
                # Save the student's submission if it doesn't already exist
                submission = QuizSubmission(
                    student_id=current_user.id,
                    quiz_id=quiz.id,
                    question_id=question.id,
                    selected_answer=selected_answer
                )

                # Automatic grading: Compare the selected answer with the correct answer
                if question.correct_answer == selected_answer:
                    submission.grade = 1  # 1 point for correct answer
                    total_grade += 1  # Add to total grade
                else:
                    submission.grade = 0  # 0 points for incorrect answer

                db.session.add(submission)

        db.session.commit()

        flash(f"Quiz submitted successfully! Your total score: {total_grade}/{len(quiz.questions)}", "success")
        return redirect(url_for('course_details', course_id=course_id))

    if not form.validate_on_submit():
        print(f"Form data: {request.form}")
        for field, errors in form.errors.items():
            print(f"Error in the {field} field - {errors}")
        flash("There was an error with your submission. Please try again.", "danger")

    return render_template('take_quiz.html', course=course, quiz=quiz, form=form)

@app.route('/instructor/view_submissions/<int:course_id>/<int:quiz_id>', methods=['GET'])
@login_required
def view_submissions(course_id, quiz_id):
    if current_user.role != RoleEnum.INSTRUCTOR:
        flash('You are not authorized to access this page.')
        return redirect(url_for('index'))

    quiz = Quiz.query.get_or_404(quiz_id)

    # Retrieve all submissions for this quiz and group them by student
    submissions = QuizSubmission.query.filter_by(quiz_id=quiz_id).all()

    grouped_submissions = defaultdict(list)
    for submission in submissions:
        grouped_submissions[submission.student_id].append(submission)

    # Pass the grouped submissions to the template
    return render_template('view_submissions.html', quiz=quiz, grouped_submissions=grouped_submissions)

@app.route('/grade_submission/<int:submission_id>', methods=['POST'])
@login_required
def grade_submission(submission_id):
    """Handles manual grading for quiz submissions."""
    submission = QuizSubmission.query.get_or_404(submission_id)
    grade = request.form.get('grade')

    if grade.isdigit():  # Ensure the grade is a valid number
        submission.grade = int(grade)
        db.session.commit()

        flash('Grade assigned successfully!', 'success')
    else:
        flash('Invalid grade input. Please enter a number.', 'danger')

    # Pass both course_id and quiz_id to the redirect URL
    return redirect(url_for('view_submissions', course_id=submission.quiz.course_id, quiz_id=submission.quiz_id))

@app.route('/grading')
def grading():
    return render_template('grading.html')

@app.route('/instructor_support')
def instructor_support():
    return render_template('instructor_support.html')

@app.route('/assignment_overview')
def assignment_overview():
    return render_template('assignment_overview.html')

@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@app.route('/terms-of-service')
def terms_of_service():
    return render_template('terms_of_service.html')

@app.route('/')
def index():
    courses = Course.query.filter_by(is_featured=True).all()  # Assuming there's an is_featured field
    return render_template('index.html', courses=courses)

@app.route('/logout')
@login_required
def logout():
    """User logout route."""
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

# Start the application
if __name__ == '__main__':
    app.run(debug=True)