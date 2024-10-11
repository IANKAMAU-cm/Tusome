from flask import Flask, render_template, redirect, url_for, flash, request, send_from_directory, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db  # Import db from extensions (correct place)
from models import User, Course, CourseMaterial, Submission, Enrollment, Student, Quiz, RoleEnum, Instructor  # Import your models
from forms import RegistrationForm, LoginForm, CourseForm, EnrollCourseForm, UploadMaterialForm
from functools import wraps
from werkzeug.utils import secure_filename
import os
from models import RoleEnum
from flask_wtf import CSRFProtect

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

    return render_template('instructor_dashboard.html', 
                           total_courses=total_courses, 
                           total_students=total_students,
                           pending_assignments=pending_assignments)

@app.route('/instructor/view_courses')
@login_required
def view_courses():
    """Instructor view courses route."""
    return render_template('view_courses.html')

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
@role_required(RoleEnum.STUDENT)
def course_details(course_id):
    """Route to view course details and materials."""
    # Check if the student is enrolled in the course
    enrollment = Enrollment.query.filter_by(student_id=current_user.student.id, course_id=course_id).first()
    if not enrollment:
        flash('You are not enrolled in this course.', 'danger')
        return redirect(url_for('browse_courses'))

    # Fetch course details
    course = Course.query.get_or_404(course_id)
    lessons = course.lessons
    materials = course.materials

    return render_template('course_details.html', course=course, lessons=lessons, materials=materials)


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
            instructor_id=current_user.instructor.id
        )

        db.session.add(course)
        db.session.commit()
        flash('Course created successfully!', 'success')
        return redirect(url_for('instructor_dashboard'))
    return render_template('create_course.html', form=form)

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



@app.route('/manage_students')
@role_required(RoleEnum.ADMIN)
def manage_students():
    """Admin manage students route."""
    students = Student.query.all()
    return render_template('manage_students.html', students=students)

@app.route('/grading')
def grading():
    return render_template('grading.html')

@app.route('/instructor_support')
def instructor_support():
    return render_template('instructor_support.html')

@app.route('/assignment_overview')
def assignment_overview():
    return render_template('assignment_overview.html')

@app.route('/')
def index():
    return render_template('index.html')

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