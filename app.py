# Standard library imports
import os
import json
from datetime import datetime
from functools import wraps

# Third-party imports
from flask import Flask, render_template, request, redirect, session, flash, jsonify, url_for
from werkzeug.utils import secure_filename
import psycopg2
from psycopg2.extras import RealDictCursor
from flask_apscheduler import APScheduler
from flask import send_from_directory
from flask import send_from_directory, flash, redirect, url_for, request
from psycopg2.extras import RealDictCursor
from flask import send_file, flash, redirect, request, url_for
from io import BytesIO
from psycopg2.extras import RealDictCursor


app = Flask(__name__)
app.secret_key = 'edu-boost-up-secret-key-2024'

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'database': 'eduboostup',  # Change to your actual database name
    'user': 'postgres',
    'password': 'Admin123',
    'port': '5432'
}

def get_db_connection():
    """Create and return a database connection"""
    try:
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            database=DB_CONFIG['database'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            port=DB_CONFIG['port']
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

# Initialize database tables (run once)
def init_db():
    """Initialize database tables"""
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            
            # Create tables
            tables = [
                """
                CREATE TABLE IF NOT EXISTS Admin (
                    admin_id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    role VARCHAR(50),
                    create_at DATE DEFAULT CURRENT_DATE
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS Student (
                    student_id VARCHAR(13) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    surname VARCHAR(100) NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    phone VARCHAR(20),
                    grade VARCHAR(10),
                    password VARCHAR(255) NOT NULL,
                    profile_image VARCHAR(255),
                    join_date DATE DEFAULT CURRENT_DATE,
                    status VARCHAR(20) DEFAULT 'active'
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS Content (
                    content_id SERIAL PRIMARY KEY,
                    mentor_id INTEGER,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    type VARCHAR(50),
                    file_url VARCHAR(255),
                    subject VARCHAR(100),
                    grade VARCHAR(10),
                    upload_date DATE DEFAULT CURRENT_DATE
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS Request (
                    request_id SERIAL PRIMARY KEY,
                    student_id VARCHAR(13),
                    mentor_id INTEGER,
                    topic VARCHAR(255),
                    message TEXT,
                    request_type VARCHAR(50),
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at DATE DEFAULT CURRENT_DATE,
                    pdf VARCHAR(255)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS Enrollment (
                    enrollment_id SERIAL PRIMARY KEY,
                    student_id VARCHAR(13),
                    class_id INTEGER,
                    enrollment_date DATE DEFAULT CURRENT_DATE
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS Payment (
                    payment_id SERIAL PRIMARY KEY,
                    student_id VARCHAR(13),
                    amount DECIMAL(10,2),
                    payment_date DATE DEFAULT CURRENT_DATE,
                    status VARCHAR(20),
                    billing_cycle_end DATE
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS Notification (
                    notification_id SERIAL PRIMARY KEY,
                    student_id VARCHAR(13),
                    message TEXT,
                    date_sent DATE DEFAULT CURRENT_DATE,
                    is_read BOOLEAN DEFAULT FALSE
                )
                """
            ]
            
            for table in tables:
                cur.execute(table)
            
            # Insert default admin user
            cur.execute("""
                INSERT INTO Admin (name, email, password, role) 
                VALUES ('System Admin', 'admin@eduboostup.com', 'admin123', 'superadmin')
                ON CONFLICT (email) DO NOTHING
            """)
            
            conn.commit()
            cur.close()
            print("✅ Database initialized successfully!")
            
        except Exception as e:
            print(f"❌ Database initialization error: {e}")
        finally:
            conn.close()
    else:
        print("❌ Failed to connect to database during initialization")

@app.route('/')
def index():
    return render_template('index.html')

UPLOAD_FOLDER = 'uploads'  # at the root of your project
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)  # create if not exists

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = get_db_connection()
        if conn:
            try:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                
                # Check Student Login
                cur.execute("""
                    SELECT * FROM Student 
                    WHERE email = %s AND password = %s AND status = 'active'
                """, (email, password))
                student = cur.fetchone()
                
                if student:
                    session['student_id'] = student['student_id']
                    session['student_name'] = f"{student['name']} {student['surname']}"
                    session['grade'] = student['grade']
                    session['user_role'] = 'student'   # ✅ ADD THIS
                    cur.close()
                    conn.close()
                    return redirect('/student/dashboard')
                
                # Check Admin Login
                cur.execute("""
                    SELECT * FROM Admin 
                    WHERE email = %s AND password = %s
                """, (email, password))
                admin = cur.fetchone()
                
                if admin:
                    session['admin_id'] = admin['admin_id']
                    session['admin_name'] = admin['name']
                    session['role'] = admin['role']
                    cur.close()
                    conn.close()
                    return redirect('/admin/dashboard')

                cur.close()
                conn.close()
                return render_template('studentLogin.html', error='Incorrect Email or Password')
                
            except Exception as e:
                print("LOGIN ERROR:", e)
                return render_template('studentLogin.html', error='Server Error, Please Try Again')

        return render_template('studentLogin.html', error='Database Connection Failed')
    
    return render_template('studentLogin.html')

@app.route("/student/dashboard")
def student_dashboard():
    if 'student_id' not in session:
        return redirect('/login')

    student_id = session['student_id']
    grade = session['grade']

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Get student info
    cur.execute("SELECT * FROM Student WHERE student_id = %s", (student_id,))
    student = cur.fetchone()

    # Check enrollment / create if missing
    cur.execute("""
        SELECT days_remaining FROM Enrollment 
        WHERE student_id = %s AND status = 'active'
        ORDER BY enrollment_id DESC LIMIT 1
    """, (student_id,))
    enroll = cur.fetchone()

    if not enroll:
        # Create new 20 day access
        cur.execute("""
            INSERT INTO Enrollment (student_id, enrollment_days, days_remaining, status)
            VALUES (%s, 0, 0, 'active')
            RETURNING days_remaining
        """, (student_id,))
        enroll = cur.fetchone()
        conn.commit()

    days_remaining = enroll['days_remaining']

    # Get mentors
    cur.execute("""
        SELECT name, surname, subject_speciality, bio 
        FROM Mentor WHERE status='active'
    """)
    mentors = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("student_dashboard.html", 
                           student=student, 
                           mentors=mentors, 
                           days_remaining=days_remaining)

@app.route("/student/classes")
def student_classes():
    if 'student_id' not in session:
        return redirect('/login')

    grade = session.get('grade')

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT C.class_id, C.title, C.topic, C.type, C.start_time,
               C.duration, C.upload_date, C.link,
               M.name AS mentor_name, M.surname AS mentor_surname
        FROM Class C
        LEFT JOIN Mentor M ON C.mentor_id = M.mentor_id
        WHERE C.grade = %s
        ORDER BY C.upload_date DESC;
    """, (grade,))

    classes = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("student_classes.html", classes=classes)

@app.route("/student/request", methods=['GET', 'POST'])
def student_request():
    if 'student_id' not in session:
        return redirect('/login')

    student_id = session['student_id']

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Fetch all active mentors
    cur.execute("SELECT mentor_id, name, surname FROM Mentor WHERE status='active' ORDER BY name")
    mentors = cur.fetchall()

    if request.method == 'POST':
        mentor_id = request.form.get('mentor_id')
        topic = request.form.get('topic')
        message = request.form.get('message')
        request_type = request.form.get('request_type')
        pdf_file = None

        # Handle PDF upload
        if 'pdf' in request.files:
            file = request.files['pdf']
            if file.filename != '':
                filename = secure_filename(file.filename)
                pdf_file = os.path.join(UPLOAD_FOLDER, filename)
                file.save(pdf_file)  # now it will work safely

        # Insert into Request table
        cur.execute("""
            INSERT INTO Request (student_id, mentor_id, topic, message, request_type, pdf_url)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (student_id, mentor_id, topic, message, request_type, pdf_file))
        conn.commit()

        cur.close()
        conn.close()
        # Redirect to a success page or show flash message
        return redirect('/student/dashboard')
    cur.close()
    conn.close()
    return render_template("student_request.html", mentors=mentors)


    if 'student_id' not in session:
        return redirect('/login')

    student_id = session['student_id']

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Fetch all active mentors for dropdown
    cur.execute("SELECT mentor_id, name, surname FROM Mentor WHERE status='active' ORDER BY name")
    mentors = cur.fetchall()

    if request.method == 'POST':
        mentor_id = request.form.get('mentor_id')
        topic = request.form.get('topic')
        message = request.form.get('message')
        request_type = request.form.get('request_type')
        pdf_file = None

        # handle pdf upload if any
        if 'pdf' in request.files:
            file = request.files['pdf']
            if file.filename != '':
                pdf_file = f"uploads/{file.filename}"
                file.save(pdf_file)  # make sure "uploads" folder exists

        # Insert into Request table
        cur.execute("""
            INSERT INTO Request (student_id, mentor_id, topic, message, request_type, pdf)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (student_id, mentor_id, topic, message, request_type, pdf_file))
        conn.commit()

        cur.close()
        conn.close()
        return render_template("student_request.html", mentors=mentors, success="Request sent successfully!")

    cur.close()
    conn.close()
    return render_template("student_request.html", mentors=mentors)

@app.route("/student/enrollment")
def student_enrollment():
    if 'student_id' not in session:
        return redirect('/login')

    student_id = session['student_id']

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Fetch enrollments for the student (without class info)
    cur.execute("""
        SELECT enrollment_id, enrollment_days, days_remaining, enrollment_date, status
        FROM Enrollment
        WHERE student_id = %s
        ORDER BY enrollment_date DESC
    """, (student_id,))

    enrollments = cur.fetchall()
    cur.close()
    conn.close()

    # Payment instructions (update with your banking details)
    payment_info = {
        "bank_name": "Your Bank Name",
        "account_name": "Edu Boost Up",
        "account_number": "1234567890",
        "reference": "Use your Student ID as reference"
    }

    return render_template(
        "student_enrollment.html",
        enrollments=enrollments,
        payment_info=payment_info
    )

@app.route("/student/profile", methods=['GET', 'POST'])
def student_profile():
    if 'student_id' not in session:
        return redirect('/login')

    student_id = session['student_id']

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Fetch current student info
    cur.execute("SELECT * FROM Student WHERE student_id = %s", (student_id,))
    student = cur.fetchone()

    if request.method == 'POST':
        # Get updated fields from form
        name = request.form.get('name')
        surname = request.form.get('surname')
        phone = request.form.get('phone')
        grade = request.form.get('grade')
        profile_image = student['profile_image']  # default to existing

        # Handle profile image upload
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file.filename != '':
                filename = secure_filename(file.filename)
                profile_image_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(profile_image_path)
                profile_image = profile_image_path

        # Update student info (excluding id and email)
        cur.execute("""
            UPDATE Student
            SET name = %s,
                surname = %s,
                phone = %s,
                grade = %s,
                profile_image = %s,
                join_date = join_date,  -- keep existing join_date
                status = status         -- keep existing status
            WHERE student_id = %s
        """, (name, surname, phone, grade, profile_image, student_id))

        conn.commit()
        cur.close()
        conn.close()

        # Update session info
        session['student_name'] = f"{name} {surname}"

        return redirect('/student/dashboard')

    cur.close()
    conn.close()
    return render_template("student_profile.html", student=student)

@app.route("/student/dashboard/courses")
def student_courses():
    if 'student_id' not in session:
        return redirect('/login')

    student_id = session['student_id']

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Check remaining days
    cur.execute("""
        SELECT days_remaining 
        FROM Enrollment
        WHERE student_id = %s AND status = 'active'
        LIMIT 1
    """, (student_id,))
    enrollment = cur.fetchone()

    # If no active enrollment or 0 days remaining -> Send to payment page
    if not enrollment or enrollment['days_remaining'] <= 0:
        cur.close()
        conn.close()
        return redirect('/student/payment?expired=1')

    # Get available subjects
    cur.execute("""
        SELECT DISTINCT subject 
        FROM Content
        WHERE subject IS NOT NULL
        ORDER BY subject
    """)
    subjects = cur.fetchall()

    cur.close()
    conn.close()
    return render_template("student_courses.html", subjects=subjects)

@app.route("/student/courses/<string:subject>/contents")
def course_contents(subject):
    if 'student_id' not in session:
        return redirect('/login')

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Get all content for the selected subject with mentor info
    cur.execute("""
        SELECT C.content_id, C.title, C.description, C.type, 
               C.pdf_file, C.file_name, C.file_size_mb, C.upload_date, 
               M.name AS mentor_name, M.surname AS mentor_surname
        FROM Content C
        LEFT JOIN Mentor M ON C.mentor_id = M.mentor_id
        WHERE C.subject = %s
        ORDER BY C.upload_date DESC
    """, (subject,))
    
    contents = cur.fetchall()

    # Get associated file links from ContentRecord
    content_links = {}
    for content in contents:
        cur.execute("""
            SELECT file_link, upload_date 
            FROM ContentRecord 
            WHERE content_id = %s
            ORDER BY upload_date DESC
        """, (content['content_id'],))
        links = cur.fetchall()
        content_links[content['content_id']] = links

    cur.close()
    conn.close()

    return render_template("course_contents.html", subject=subject, contents=contents, content_links=content_links)

@app.route('/download/<filename>')
def download_pdf(filename):
    """Serve PDF files for download"""
    try:
        # Assuming PDFs are stored in a 'pdfs' folder within static
        return send_from_directory('static/pdfs', filename, as_attachment=True)
    except FileNotFoundError:
        flash('File not found', 'error')
        return redirect(request.referrer or url_for('student_dashboard'))


@app.route('/view/content/<int:content_id>')
def view_content_pdf(content_id):
    if 'student_id' not in session:
        return redirect('/login')

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT pdf_file, file_name
        FROM Content
        WHERE content_id = %s
    """, (content_id,))

    file_data = cur.fetchone()

    cur.close()
    conn.close()

    if not file_data or not file_data['pdf_file']:
        flash("The requested PDF file is not available.", "error")
        return redirect(request.referrer or url_for('student_dashboard'))

    # Convert BYTEA to stream and return to browser
    return send_file(
        BytesIO(file_data['pdf_file']),
        mimetype='application/pdf',
        download_name=file_data['file_name'],
        as_attachment=False  # change to True if you want "Download" instead of "View"
    )


#signup is done
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Get form data
        student_id = request.form.get('student_id')
        name = request.form.get('name')
        surname = request.form.get('surname')
        email = request.form.get('email')
        phone = request.form.get('phone')
        grade = request.form.get('grade')
        password = request.form.get('password')
        
        # Age validation from South African ID number
        def calculate_age_from_id(id_number):
            """
            Calculate age from South African ID number
            Format: YYMMDDSSSSCAZ
            YY: Year of birth (last two digits)
            MM: Month of birth
            DD: Day of birth
            """
            try:
                if len(id_number) != 13 or not id_number.isdigit():
                    return None
                
                # Extract birth date parts
                year_part = id_number[0:2]  # YY
                month = id_number[2:4]      # MM
                day = id_number[4:6]        # DD
                
                # Determine century (1900s or 2000s)
                year_int = int(year_part)
                if year_int <= 21:  # Born in 2000-2021
                    full_year = 2000 + year_int
                else:  # Born in 1922-1999
                    full_year = 1900 + year_int
                
                # Calculate age
                today = datetime.now()
                birth_date = datetime(full_year, int(month), int(day))
                
                age = today.year - birth_date.year
                # Adjust if birthday hasn't occurred this year
                if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
                    age -= 1
                
                return age
                
            except (ValueError, IndexError):
                return None
        
        # Validate ID number and calculate age
        if not student_id or len(student_id) != 13 or not student_id.isdigit():
            return render_template('singuperror.html', 
                                error_message="Invalid ID number format. Please enter a valid 13-digit South African ID number.")
        
        age = calculate_age_from_id(student_id)
        
        if age is None:
            return render_template('singuperror.html', 
                                error_message="Invalid ID number. Please check the format and try again.")
        
        # Age validation: between 14 and 20 years old
        if age < 14 or age > 20:
            return render_template('singuperror.html', 
                                error_message=f"You must be between 14 and 20 years old to register. Your current age is {age}. Please contact support if this is an error.")
        
        # Grade validation
        try:
            grade_num = int(grade)
            if grade_num < 10 or grade_num > 12:
                return render_template('singuperror.html', 
                                    error_message="Invalid grade selection. Please select a grade between 10 and 12.")
        except (ValueError, TypeError):
            return render_template('singuperror.html', 
                                error_message="Invalid grade selection. Please select a valid grade.")
        
        conn = get_db_connection()
        if conn:
            try:
                cur = conn.cursor()
                
                # Check if email already exists
                cur.execute("SELECT student_id FROM Student WHERE email = %s", (email,))
                if cur.fetchone():
                    cur.close()
                    conn.close()
                    return render_template('singupIdUsed.html',  
                                        error_message="This email is already registered. Please use a different email or login.")
                
                # Check if student ID already exists
                cur.execute("SELECT student_id FROM Student WHERE student_id = %s", (student_id,))
                if cur.fetchone():
                    cur.close()
                    conn.close()
                    return render_template('singupIdUsed.html',  
                                        error_message="This Student ID is already registered. Please use your correct Student ID or contact support.")
                


                # Insert new student
                cur.execute("""
                    INSERT INTO Student (student_id, name, surname, email, password, grade, phone) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (student_id, name, surname, email, password, grade, phone))
                
                # Create free 20-day trial enrollment for all available classes in the student's grade
                cur.execute("""
                INSERT INTO Enrollment (student_id, enrollment_days, days_remaining, status)
                VALUES (%s, 20, 20, 'active')
                """, (student_id,))
                
                conn.commit()
                cur.close()
                conn.close()
                
                # Get the new student's data
                conn = get_db_connection()
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("SELECT * FROM Student WHERE email = %s", (email,))
                student = cur.fetchone()
                
                # Set session data
                session['user_id'] = student['student_id']
                session['user_name'] = f"{student['name']} {student['surname']}"
                session['user_role'] = 'student'
                session['user_email'] = student['email']
                session['grade'] = student['grade']
                session['age'] = age
                
                cur.close()
                conn.close()
                
                # Redirect to success page
                return render_template('successfullsingup.html', 
                                    student_name=f"{name} {surname}",
                                    student_id=student_id,
                                    grade=grade,
                                    age=age)
                
            except Exception as e:
                print(f"Signup error: {e}")
                if conn:
                    conn.close()
                return render_template('singuperror.html', 
                                    error_message=f"Registration failed: {str(e)}")
        
        return render_template('singuperror.html', 
                            error_message="Database connection failed. Please try again later.")
    
    # GET request - show signup form
    return render_template('signup.html')



# You can call this function daily using:
# reduce_enrollment_days()
scheduler = APScheduler()

@scheduler.task('interval', id='reduce_days', hours=24)
def scheduled_reduce():
    reduce_enrollment_days()

    scheduler = APScheduler()
    scheduler.init_app(app)
    scheduler.start()

    scheduler.add_job(id='reduce_enrollment_days', func=reduce_daily, trigger='interval', hours=24)

def reduce_enrollment_days():
    """Reduce enrollment days by 1 for all active enrollments with days remaining > 0"""
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()

            # 1. Reduce days first
            cur.execute("""
                UPDATE Enrollment 
                SET days_remaining = days_remaining - 1,
                    last_updated = CURRENT_TIMESTAMP
                WHERE status = 'active' 
                AND days_remaining > 0
            """)

            # 2. Mark expired where days reached 0
            cur.execute("""
                UPDATE Enrollment 
                SET status = 'expired',
                    last_updated = CURRENT_TIMESTAMP
                WHERE status = 'active'
                AND days_remaining <= 0
            """)

            conn.commit()

            # Logging (optional)
            cur.execute("SELECT COUNT(*) FROM Enrollment WHERE status = 'active' AND days_remaining > 0")
            active_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM Enrollment WHERE status = 'expired'")
            expired_count = cur.fetchone()[0]

            cur.close()
            print("✅ Enrollment days updated successfully.")
            print(f"   Remaining active: {active_count}")
            print(f"   Expired: {expired_count}")

        except Exception as e:
            print(f"❌ Error reducing enrollment days: {e}")
        finally:
            conn.close()


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    
    user_data = {
        'name': session.get('user_name'),
        'email': session.get('user_email'),
        'role': session.get('user_role'),
        'grade': session.get('grade')
    }
    
    # Get student-specific data if user is a student
    if session.get('user_role') == 'student':
        conn = get_db_connection()
        if conn:
            try:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                
                # Get enrolled courses count
                cur.execute(
                    "SELECT COUNT(*) as course_count FROM Enrollment WHERE student_id = %s",
                    (session['user_id'],)
                )
                course_count = cur.fetchone()['course_count']
                
                # Get notifications
                cur.execute(
                    "SELECT * FROM Notification WHERE student_id = %s ORDER BY date_sent DESC LIMIT 5",
                    (session['user_id'],)
                )
                notifications = cur.fetchall()
                
                user_data['course_count'] = course_count
                user_data['notifications'] = notifications
                
                cur.close()
                conn.close()
                
            except Exception as e:
                print(f"Dashboard data error: {e}")
                if conn:
                    conn.close()
    
    template_map = {
        'student': 'student_dashboard.html',
        'admin': 'admin_dashboard.html'
    }
    
    template = template_map.get(session.get('user_role'), 'student_dashboard.html')
    return render_template(template, user=user_data)

@app.route('/api/courses')
def get_courses():
    """Get courses based on student's grade"""
    if 'user_id' not in session or session.get('user_role') != 'student':
        return jsonify([])
    
    grade = session.get('grade', '12')
    conn = get_db_connection()
    
    if conn:
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get content for student's grade
            cur.execute("""
                SELECT * FROM Content 
                WHERE grade = %s OR grade = 'All'
                ORDER BY upload_date DESC
            """, (grade,))
            
            content_items = cur.fetchall()
            
            courses = []
            for item in content_items:
                courses.append({
                    'id': item['content_id'],
                    'title': item['title'],
                    'description': item['description'],
                    'subject': item['subject'],
                    'type': item['type'],
                    'progress': 0,
                    'thumbnail': item['file_url'] or '/static/images/default-course.jpg'
                })
            
            cur.close()
            conn.close()
            return jsonify(courses)
            
        except Exception as e:
            print(f"Courses API error: {e}")
            if conn:
                conn.close()
    
    # Fallback to sample data
    return jsonify([
        {
            'id': 1,
            'title': 'Mathematics Grade 12',
            'description': 'Algebra, Calculus, and Geometry',
            'progress': 25,
            'thumbnail': '/static/images/math.jpg'
        },
        {
            'id': 2,
            'title': 'Accounting Grade 12',
            'description': 'Financial Statements and Managerial Accounting',
            'progress': 10,
            'thumbnail': '/static/images/accounting.jpg'
        }
    ])

@app.route('/api/notifications')
def get_notifications():
    """Get notifications for the current student"""
    if 'user_id' not in session or session.get('user_role') != 'student':
        return jsonify([])
    
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT * FROM Notification 
                WHERE student_id = %s 
                ORDER BY date_sent DESC
            """, (session['user_id'],))
            
            notifications = cur.fetchall()
            cur.close()
            conn.close()
            
            return jsonify(notifications)
            
        except Exception as e:
            print(f"Notifications API error: {e}")
            if conn:
                conn.close()
    
    return jsonify([])


# ---------------- ADMIN LOGIN -------------------
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password_input = request.form.get('password')

        conn = get_db_connection()
        cur = conn.cursor()

        # Match your table structure
        cur.execute("""
            SELECT admin_id, name, surname, email, password, role 
            FROM Admin WHERE email = %s
        """, (email,))
        admin = cur.fetchone()

        cur.close()
        conn.close()

        if admin:
            db_password = admin[4]  # password column index

            # Direct string comparison (NO hash)
            if db_password == password_input:
                session['admin_id'] = admin[0]
                session['admin_name'] = admin[1]
                session['admin_email'] = admin[3]
                session['user_role'] = admin[5] if admin[5] else "superadmin"
                return redirect('/admin/dashboard')

        # If wrong password or email not found
        return render_template('admin_login.html', error_message="Invalid email or password")

    return render_template('admin_login.html')

# --------------- ADMIN PROTECTOR ---------------
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        role = session.get('user_role')
        if role not in ['admin', 'superadmin']:
            flash("Please login as admin.", "warning")
            return redirect('/admin-login')
        return f(*args, **kwargs)
    return decorated


# --------------- ADMIN DASHBOARD ---------------
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    stats = {}
    if conn:
        try:
            cur = conn.cursor()
            
            # Count students
            cur.execute("SELECT COUNT(*) FROM Student")
            stats['students'] = cur.fetchone()[0]
            
            # Count mentors (if you have a Mentor table)
            cur.execute("SELECT COUNT(*) FROM Mentor")
            stats['mentors'] = cur.fetchone()[0]
            
            # Count enrollments
            cur.execute("SELECT COUNT(*) FROM Enrollment")
            stats['enrollments'] = cur.fetchone()[0]
            
            cur.close()
        except Exception as e:
            print(f"Admin dashboard stats error: {e}")
        finally:
            conn.close()
    
    return render_template(
        'admin_dashboard.html', 
        admin_name=session.get('admin_name'), 
        stats=stats
    )

# ----------------- LOGOUT ----------------------
@app.route('/admin/logout')
def admin_logout():
    for key in ['admin_id', 'admin_name', 'admin_email', 'user_role']:
        session.pop(key, None)
    flash("Logged out successfully.", "info")
    return redirect('/admin-login')


# Example skeleton route for notifications
@app.route('/admin/notifications', methods=['GET', 'POST'])
@admin_required
def admin_notifications():
    if request.method == 'POST':
        title = request.form.get('title')
        message = request.form.get('message')
        # Save to DB and/or queue for sending
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO Notifications (title, message, created_at) VALUES (%s, %s, CURRENT_TIMESTAMP)", (title, message))
        conn.commit()
        cur.close()
        conn.close()
        flash("Notification created.", "success")
        return redirect('/admin/notifications')

    # GET
    return render_template('admin_notifications.html')


# Allowed image extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
UPLOAD_FOLDER = 'static/uploads/mentors'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# --- Add employee (mentor/staff) form + POST handler ---
@app.route('/admin/mentors/add', methods=['GET', 'POST'])
@admin_required
def admin_add_mentor():
    if request.method == 'POST':
        name = request.form.get('name')
        surname = request.form.get('surname')
        email = request.form.get('email')
        phone = request.form.get('phone')
        subject_speciality = request.form.get('subject_speciality')  # Updated field name
        bio = request.form.get('bio')
        password = request.form.get('password') or 'changeme123'

        # Handle image upload
        profile_image = None
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                profile_image = filepath  # optional: store path

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO Mentor (name, surname, email, phone, subject_speciality, password, bio, join_date, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_DATE, 'active') RETURNING mentor_id
            """, (name, surname, email, phone, subject_speciality, password, bio))
            mentor_id = cur.fetchone()[0]

            # Optional: if you want to store image path, you need to first add column profile_image
            if profile_image:
                cur.execute("ALTER TABLE Mentor ADD COLUMN IF NOT EXISTS profile_image VARCHAR(255)")
                cur.execute("UPDATE Mentor SET profile_image = %s WHERE mentor_id = %s", (profile_image, mentor_id))

            conn.commit()
            flash("Mentor account created successfully.", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Error creating mentor: {e}", "error")
            print(f"Add mentor error: {e}")
        finally:
            cur.close()
            conn.close()

        return redirect('/admin/mentors')

    return render_template('admin_add_mentor.html')

# --- View all employees / mentors (example) ---
@app.route('/admin/mentors')
@admin_required
def admin_view_mentors():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT mentor_id, name, surname, email, subject_speciality, status, join_date FROM Mentor ORDER BY join_date DESC")
    mentors = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('admin_view_mentors.html', mentors=mentors)


    # --- Edit mentor ---


@app.route('/admin/mentors/edit/<int:mentor_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_mentor(mentor_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM Mentor WHERE mentor_id = %s", (mentor_id,))
    mentor = cur.fetchone()

    if request.method == 'POST':
        name = request.form.get('name')
        surname = request.form.get('surname')
        email = request.form.get('email')
        phone = request.form.get('phone')
        subject_speciality = request.form.get('subject_speciality')
        bio = request.form.get('bio')
        status = request.form.get('status')

        # Handle image upload
        file = request.files.get('profile_image')
        image_path = mentor.get('profile_image', None)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_path = f"{app.config['UPLOAD_FOLDER']}/{filename}"

        cur.execute("""
            UPDATE Mentor
            SET name=%s, surname=%s, email=%s, phone=%s,
                subject_speciality=%s, bio=%s, status=%s, profile_image=%s
            WHERE mentor_id=%s
        """, (name, surname, email, phone, subject_speciality, bio, status, image_path, mentor_id))

        conn.commit()
        cur.close()
        conn.close()
        flash("Mentor updated successfully.", "success")
        return redirect('/admin/mentors')

    cur.close()
    conn.close()
    return render_template('admin_edit_mentor.html', mentor=mentor)


# --- Delete mentor ---
@app.route('/admin/mentors/delete/<int:mentor_id>', methods=['GET'])
@admin_required
def admin_delete_mentor(mentor_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM Mentor WHERE mentor_id=%s", (mentor_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("Mentor deleted successfully.", "success")
    return redirect('/admin/mentors')


@app.route('/admin/enrollments/add-days', methods=['POST'])
@admin_required
def add_enrollment_days():
    enrollment_id = request.form.get('enrollment_id')
    additional_days = request.form.get('additional_days')

    if not enrollment_id or not additional_days:
        flash("Missing enrollment ID or days.", "error")
        return redirect('/admin/enrollments')

    try:
        additional_days = int(additional_days)
        if additional_days <= 0:
            flash("Days must be positive.", "error")
            return redirect('/admin/enrollments')
    except ValueError:
        flash("Invalid number of days.", "error")
        return redirect('/admin/enrollments')

    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            # Update enrollment days and remaining days
            cur.execute("""
                UPDATE Enrollment
                SET enrollment_days = enrollment_days + %s,
                    days_remaining = days_remaining + %s,
                    last_updated = CURRENT_TIMESTAMP
                WHERE enrollment_id = %s
            """, (additional_days, additional_days, enrollment_id))
            conn.commit()
            cur.close()
            flash(f"Successfully added {additional_days} days to enrollment.", "success")
        except Exception as e:
            flash(f"Error updating enrollment: {e}", "error")
            print(f"Add enrollment days error: {e}")
        finally:
            conn.close()

    return redirect('/admin/enrollments')


# --- View student enrollments (example) ---
@app.route('/admin/enrollments')
@admin_required
def admin_view_enrollments():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT e.enrollment_id, e.student_id, s.name, s.surname, e.enrollment_days, e.days_remaining, e.status, e.enrollment_date, e.last_updated
        FROM Enrollment e
        LEFT JOIN Student s ON s.student_id = e.student_id
        ORDER BY e.last_updated DESC
    """)
    enrollments = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('admin_view_enrollments.html', enrollments=enrollments)


@app.route('/admin/students')
@admin_required
def admin_view_students():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT student_id, name, surname, email, grade, status FROM Student ORDER BY name")
    students = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('admin_view_students.html', students=students)



# --- Additional endpoints you can expand later ---
# - /admin/content  (Content oversight)
# - /admin/classes  (Class management)
# - /admin/requests (Student requests)
# - /admin/notifications (Create/send notifications)
# - /admin/system (Platform settings & audit)
# --- end of sample admin routes ---

  # MENTOR THINGS

def mentor_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('user_role') != 'mentor':
            flash("Please login as mentor first.", "warning")
            return redirect('/mentor-login')
        return f(*args, **kwargs)
    return decorated

# MENTOR / EMPLOYEE DASHBOARD
@app.route('/employee/dashboard')
def employee_dashboard():
    if 'mentor_id' not in session:
        return redirect('/mentor-login')

    conn = get_db_connection()  # ← correct function
    if not conn:
        return "❌ Failed to connect to database", 500

    cur = conn.cursor()
    cur.execute("SELECT name, surname, subject_speciality FROM Mentor WHERE mentor_id = %s", (session['mentor_id'],))
    mentor = cur.fetchone()
    cur.close()
    conn.close()

    return render_template('employee_dashboard.html', mentor=mentor)

@app.route('/mentor-login', methods=['GET', 'POST'])
def mentor_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password_input = request.form.get('password')

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT mentor_id, name, surname, email, password, status
            FROM Mentor
            WHERE email = %s AND status = 'active'
        """, (email,))
        mentor = cur.fetchone()

        cur.close()
        conn.close()

        if mentor:
            db_password = mentor[4]  # password column

            # Compare raw password directly (no hashing)
            if db_password == password_input:
                session['mentor_id'] = mentor[0]
                session['mentor_name'] = mentor[1] + " " + mentor[2]
                session['mentor_email'] = mentor[3]
                session['user_role'] = 'mentor'

                return redirect('/employee/dashboard')

        return render_template('employee_login.html', error_message="Invalid email or password")

    return render_template('employee_login.html')


@app.route('/employee/content/upload/pdf', methods=['GET', 'POST'])
@mentor_required
def upload_pdf():
    grade = request.args.get('grade')
    if not grade:
        flash("Select a grade first.", "warning")
        return redirect('/employee/dashboard')

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        subject = request.form['subject']

        file = request.files['pdf_file']

        if not file:
            flash("Please upload a PDF file.", "danger")
            return redirect(request.url)

        pdf_data = file.read()
        file_name = secure_filename(file.filename)
        file_size_mb = round(len(pdf_data) / (1024 * 1024), 2)

        if file_size_mb > 25:
            flash("PDF exceeds 25MB limit.", "danger")
            return redirect(request.url)

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
    INSERT INTO Content (mentor_id, title, description, subject, grade, pdf_file, file_name, file_size_mb)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING content_id
""", (session["mentor_id"], title, description, subject, grade, pdf_path, file_name, file_size_mb))

        conn.commit()
        cur.close()
        conn.close()

        flash("✅ PDF uploaded successfully for Grade " + grade, "success")
        return redirect('/employee/dashboard')

    return render_template('upload_pdf.html', grade=grade)

UPLOAD_PDF_FOLDER = "static/uploads/pdfs"

@app.route("/employee/content/upload", methods=["GET", "POST"])
@mentor_required
def employee_content_upload():
    
    grade = request.args.get("grade")
    
    if not grade:
        flash("Please select a grade first.", "warning")
        return redirect("/employee/dashboard")

    if request.method == "POST":
        title = request.form["title"]
        description = request.form.get("description")
        subject = request.form["subject"]
        video_link = request.form.get("video_link")  # ✅ New: Take video link input

        # ==== PDF Upload ====
        pdf_file = request.files.get("pdf_file")
        file_name = None
        file_size_mb = None

        if pdf_file and pdf_file.filename != "":
            file_name = secure_filename(pdf_file.filename)
            os.makedirs(UPLOAD_PDF_FOLDER, exist_ok=True)
            pdf_path = os.path.join(UPLOAD_PDF_FOLDER, file_name)
            pdf_file.save(pdf_path)
            file_size_mb = round(os.path.getsize(pdf_path) / (1024 * 1024), 2)
        else:
            pdf_path = None

        conn = get_db_connection()
        cur = conn.cursor()

        # Insert main content record
        file = request.files['pdf']
        pdf_bytes = file.read()
        cur.execute("""
            INSERT INTO Content (mentor_id, title, description, subject, grade, pdf_file, file_name, file_size_mb)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING content_id
        """, (session["mentor_id"], title, description, subject, grade, pdf_path, file_name, file_size_mb))
        
        content_id = cur.fetchone()[0]
        conn.commit()

        # ==== Insert Video Link ====
        if video_link:
            cur.execute("""
                INSERT INTO ContentRecord (content_id, file_link)
                VALUES (%s, %s)
            """, (content_id, video_link))

        conn.commit()
        cur.close()
        conn.close()

        # ✅ Redirect to success confirmation page
        return redirect("/employee/content/uploaded")

    return render_template("upload_content.html", grade=grade)

@app.route("/employee/requests")
def employee_requests():
    # Ensure mentor or admin is logged in
    if 'mentor_id' not in session and 'admin_id' not in session:
        return redirect("/mentor-login")

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Fetch all requests with student info
    cur.execute("""
    SELECT R.request_id, R.topic, R.message, R.request_type, R.status, R.created_at, R.pdf_url,
           S.name AS student_name, S.surname AS student_surname, S.phone AS student_email
    FROM Request R
    LEFT JOIN Student S ON R.student_id = S.student_id::varchar
    ORDER BY R.created_at DESC
""")
    requests = cur.fetchall()

    cur.close()
    conn.close()
    return render_template("employee_requests.html", requests=requests)


@app.route("/employee/profile/edit", methods=["GET", "POST"])
def employee_profile_edit():
    if 'mentor_id' not in session:
        return redirect('/mentor-login')

    mentor_id = session['mentor_id']

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    if request.method == "POST":
        name = request.form.get("name")
        surname = request.form.get("surname")
        phone = request.form.get("phone")
        subject_speciality = request.form.get("subject_speciality")
        bio = request.form.get("bio")

        cur.execute("""
            UPDATE Mentor
            SET name = %s, surname = %s, phone = %s, subject_speciality = %s, bio = %s
            WHERE mentor_id = %s
        """, (name, surname, phone, subject_speciality, bio, mentor_id))
        conn.commit()

        cur.close()
        conn.close()
        return redirect("/employee/dashboard")

    # Load existing data
    cur.execute("SELECT * FROM Mentor WHERE mentor_id = %s", (mentor_id,))
    mentor = cur.fetchone()

    cur.close()
    conn.close()
    return render_template("employee_profile_edit.html", mentor=mentor)

@app.route("/employee/profile/password", methods=["GET", "POST"])
def employee_change_password():
    if 'mentor_id' not in session:
        return redirect('/mentor-login')

    mentor_id = session['mentor_id']

    if request.method == "POST":
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT password FROM Mentor WHERE mentor_id = %s", (mentor_id,))
        db_password = cur.fetchone()[0]

        # No hashing → direct comparison
        if db_password != current_password:
            cur.close()
            conn.close()
            return render_template("employee_change_password.html", error="Current password incorrect")

        cur.execute("UPDATE Mentor SET password = %s WHERE mentor_id = %s", (new_password, mentor_id))
        conn.commit()

        cur.close()
        conn.close()
        return redirect("/employee/dashboard")

    return render_template("employee_change_password.html")



@app.route("/employee/content/uploaded")
def upload_success():
    return render_template("employee_content_uploaded.html")

@app.route("/employee/class/new", methods=["GET", "POST"])
@mentor_required
def create_new_class():

    if request.method == "POST":
        title = request.form["title"]
        topic = request.form.get("topic")
        class_type = request.form.get("type")
        start_time = request.form.get("start_time")
        duration = request.form.get("duration")
        grade = request.form["grade"]
        link = request.form.get("link")

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO Class (mentor_id, title, topic, type, start_time, duration, grade, link)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (session["mentor_id"], title, topic, class_type, start_time, duration, grade, link))

        conn.commit()
        cur.close()
        conn.close()

        flash("✅ Class posted successfully!", "success")
        return redirect('/employee/dashboard')

    return render_template("employee_class_new.html")

@app.route("/employee/classes")
@mentor_required
def view_classes():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT class_id, title, topic, type, start_time, duration, grade, link, upload_date
        FROM Class
        WHERE mentor_id = %s
        ORDER BY start_time DESC
    """, (session["mentor_id"],))

    classes = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("employee_classes.html", classes=classes)


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    print("🚀 Edu Boost Up Server Starting...")
    print("📧 Test Login: Use your registered email or register new account")
    
    # Initialize database on startup
    init_db()
    
    app.run(debug=True, host='0.0.0.0', port=5000)