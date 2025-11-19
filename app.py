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
from datetime import datetime
from functools import wraps
from flask import session, redirect
from urllib.parse import urlparse


app = Flask(__name__)
app.secret_key = 'edu-boost-up-secret-key-2024'

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'database': 'eduboostup',  # Change to your actual database name
    'user': 'postgres',
    'password': 'Admin2023',
    'port': '5432'
}

# ✅ Initialize scheduler
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()


def get_db_connection():
    """Connect to Railway PostgreSQL using DATABASE_URL"""
    try:
        DATABASE_URL = os.getenv("DATABASE_URL")

        if not DATABASE_URL:
            raise Exception("❌ DATABASE_URL not found in environment variables.")

        result = urlparse(DATABASE_URL)

        conn = psycopg2.connect(
            database=result.path[1:],  # remove '/' at start
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )

        print("✅ Connected to Railway PostgreSQL")
        return conn

    except Exception as e:
        print(f"❌ Database connection error: {e}")
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
                CREATE TABLE IF NOT EXISTS Mentor (
                    mentor_id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    surname VARCHAR(100) NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    phone VARCHAR(20),
                    subject_speciality VARCHAR(100),
                    password VARCHAR(255) NOT NULL,
                    bio TEXT,
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
                CREATE TABLE IF NOT EXISTS ContentRecord (
                    record_id SERIAL PRIMARY KEY,
                    content_id INTEGER,
                    file_link VARCHAR(255),
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS Class (
                    class_id SERIAL PRIMARY KEY,
                    mentor_id INTEGER,
                    title VARCHAR(255) NOT NULL,
                    topic VARCHAR(255),
                    type VARCHAR(50),
                    start_time TIMESTAMP,
                    duration VARCHAR(50),
                    grade VARCHAR(10),
                    link VARCHAR(255),
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                    pdf_url VARCHAR(255)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS Enrollment (
                    enrollment_id SERIAL PRIMARY KEY,
                    student_id VARCHAR(13),
                    class_id INTEGER,
                    enrollment_days INTEGER DEFAULT 20,
                    days_remaining INTEGER DEFAULT 20,
                    status VARCHAR(20) DEFAULT 'active',
                    enrollment_date DATE DEFAULT CURRENT_DATE,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            
            
            conn.commit()
            cur.close()
            print("✅ Database initialized successfully!")
            
        except Exception as e:
            print(f"❌ Database initialization error: {e}")
        finally:
            conn.close()
    else:
        print("❌ Failed to connect to database during initialization")

# ✅ Automatic Day Reduction System
def reduce_enrollment_days():
    """Reduce enrollment days by 1 for all active enrollments with days remaining > 0"""
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            print("🔄 Starting daily enrollment reduction...")

            # 1. Reduce days for active enrollments
            cur.execute("""
                UPDATE Enrollment 
                SET days_remaining = days_remaining - 1,
                    last_updated = CURRENT_TIMESTAMP
                WHERE status = 'active' 
                AND days_remaining > 0
            """)
            reduced_count = cur.rowcount

            # 2. Mark expired where days reached 0
            cur.execute("""
                UPDATE Enrollment 
                SET status = 'expired',
                    last_updated = CURRENT_TIMESTAMP
                WHERE status = 'active'
                AND days_remaining <= 0
            """)
            expired_count = cur.rowcount

            conn.commit()
            cur.close()

            print(f"✅ Daily Enrollment Reduction Complete: {reduced_count} updated, {expired_count} expired")

        except Exception as e:
            print(f"❌ Error reducing enrollment days: {e}")
            if conn:
                conn.rollback()
        finally:
            conn.close()
    else:
        print("❌ No database connection for enrollment reduction")

# ✅ Schedule job to run daily at midnight
@scheduler.task('cron', id='reduce_days_job', hour=0, minute=0)
def scheduled_reduce_days():
    print("⏰ Running scheduled enrollment reduction...")
    reduce_enrollment_days()

@app.route('/')
def index():
    return render_template('index.html')


# ---------- Step 1: Identity confirmation (Email only) ----------
@app.route("/reset", methods=["GET", "POST"])
def reset_request():
    if request.method == "POST":
        email = request.form.get("email").strip()

        if not email:
            flash("❌ Please enter your email.", "danger")
            return render_template("reset_request.html")

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            # Check if student exists
            cur.execute("""
                SELECT student_id, email 
                FROM Student 
                WHERE email = %s
            """, (email,))
            student = cur.fetchone()

            if student:
                # Save temporary session info for reset
                session['reset_student_id'] = student['student_id']
                session['reset_email'] = student['email']
                flash("✅ Identity confirmed. You can now reset your password.", "success")
                return redirect("/reset/password")
            else:
                flash("❌ Email not found. Please check and try again.", "danger")
        finally:
            cur.close()
            conn.close()

    return render_template("reset_request.html")


# ---------- Step 2: Reset password ----------
@app.route("/reset/password", methods=["GET", "POST"])
def reset_password():
    if 'reset_student_id' not in session or 'reset_email' not in session:
        flash("Please confirm your email first.", "warning")
        return redirect("/reset")

    if request.method == "POST":
        new_password = request.form.get("new_password").strip()
        confirm_password = request.form.get("confirm_password").strip()

        if not new_password or not confirm_password:
            flash("Please fill in all fields.", "danger")
        elif new_password != confirm_password:
            flash("Passwords do not match.", "danger")
        else:
            student_id = session['reset_student_id']
            email = session['reset_email']

            conn = get_db_connection()
            cur = conn.cursor()
            try:
                # Update student password (hashing recommended!)
                cur.execute("""
                    UPDATE Student 
                    SET password = %s 
                    WHERE student_id = %s AND email = %s
                """, (new_password, student_id, email))
                conn.commit()

                flash("✅ Password reset successful. Please log in.", "success")

                # Clear session info
                session.pop('reset_student_id')
                session.pop('reset_email')

                return redirect("/login")
            finally:
                cur.close()
                conn.close()

    return render_template("reset_password.html")


# ✅ Manual test route for day reduction
@app.route('/admin/test-reduce-days')
def test_reduce_days():
    """Manual test endpoint for day reduction"""
    reduce_enrollment_days()
    flash("Day reduction executed manually", "success")
    return redirect('/admin/dashboard')

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
        if not conn:
            return render_template('studentLogin.html', error='Database Connection Failed')

        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)

            # -------------------------
            # 1️⃣ Check Student Login
            # -------------------------
            cur.execute("""
                SELECT * FROM Student 
                WHERE email = %s AND password = %s AND status = 'active'
            """, (email, password))
            student = cur.fetchone()

            if student:
                session['user_id'] = student['student_id']
                session['user_name'] = f"{student['name']} {student['surname']}"
                session['grade'] = student['grade']
                session['user_role'] = 'student'

                cur.close()
                conn.close()
                return redirect('/student/dashboard')

            # -------------------------
            # 2️⃣ Check Mentor Login
            # -------------------------
            cur.execute("""
                SELECT * FROM Mentor
                WHERE email = %s AND password = %s AND status = 'active'
            """, (email, password))
            mentor = cur.fetchone()

            if mentor:
                session['user_id'] = mentor['mentor_id']
                session['user_name'] = f"{mentor['name']} {mentor['surname']}"
                session['user_role'] = 'mentor'

                cur.close()
                conn.close()
                return redirect('/employee/dashboard')  # Mentor dashboard

            # -------------------------
            # 3️⃣ Check Admin Login
            # -------------------------
            cur.execute("""
                SELECT * FROM Admin 
                WHERE email = %s AND password = %s
            """, (email, password))
            admin = cur.fetchone()

            if admin:
                session['user_id'] = admin['admin_id']
                session['user_name'] = admin['name']
                session['user_role'] = 'admin'
                session['role'] = admin['role']

                cur.close()
                conn.close()
                return redirect('/admin/dashboard')

            # -------------------------
            # Login Failed
            # -------------------------
            cur.close()
            conn.close()
            return render_template('studentLogin.html', error='Incorrect Email or Password')

        except Exception as e:
            print("LOGIN ERROR:", e)
            return render_template('studentLogin.html', error='Server Error, Please Try Again')

    # GET request
    return render_template('studentLogin.html')

@app.route("/student/dashboard")
def student_dashboard():
    # ----------------------------
    # 1️⃣ Check if logged in as student
    # ----------------------------
    if 'user_role' not in session or session['user_role'] != 'student':
        return redirect('/login')

    student_id = session['user_id']
    grade = session.get('grade')

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # ----------------------------
        # 2️⃣ Get student info
        # ----------------------------
        cur.execute("SELECT * FROM Student WHERE student_id = %s", (student_id,))
        student = cur.fetchone()

        if not student:
            # In case student record was deleted
            session.clear()
            return redirect('/login')

        # ----------------------------
        # 3️⃣ Check enrollment / create if missing
        # ----------------------------
        cur.execute("""
            SELECT days_remaining FROM Enrollment 
            WHERE student_id = %s AND status = 'active'
            ORDER BY enrollment_id DESC LIMIT 1
        """, (student_id,))
        enroll = cur.fetchone()

        if not enroll:
            # Create new 20-day access if missing
            cur.execute("""
                INSERT INTO Enrollment (student_id, enrollment_days, days_remaining, status)
                VALUES (%s, 20, 20, 'active')
                RETURNING days_remaining
            """, (student_id,))
            enroll = cur.fetchone()
            conn.commit()

        days_remaining = enroll['days_remaining']

        # ----------------------------
        # 4️⃣ Get active mentors with images and phone numbers
        # ----------------------------
        cur.execute("""
            SELECT name, surname, subject_speciality, bio, profile_image, phone
            FROM Mentor
            WHERE status='active'
            ORDER BY name
        """)
        mentors = cur.fetchall()

        # ----------------------------
        # 5️⃣ Get courses/subjects for this student's grade
        # ----------------------------
        cur.execute("""
            SELECT DISTINCT subject
            FROM Content
            WHERE grade = %s
            ORDER BY subject
        """, (grade,))
        courses = cur.fetchall()

    finally:
        cur.close()
        conn.close()

    # ----------------------------
    # 6️⃣ Render dashboard
    # ----------------------------
    return render_template(
        "student_dashboard.html",
        student=student,
        mentors=mentors,
        courses=courses,
        days_remaining=days_remaining
    )


@app.route("/student/classes")
def student_classes():
    # 1️⃣ Ensure student is logged in
    if 'user_role' not in session or session['user_role'] != 'student' or 'user_id' not in session:
        return redirect('/login')

    student_id = session['user_id']
    grade = session.get('grade')  # get student's grade

    # 2️⃣ Connect to DB
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 3️⃣ Fetch classes for this grade
        cur.execute("""
            SELECT C.class_id, C.title, C.topic, C.type, C.start_time,
                   C.duration, C.upload_date, C.link,
                   M.name AS mentor_name, M.surname AS mentor_surname
            FROM Class C
            LEFT JOIN Mentor M ON C.mentor_id = M.mentor_id
            WHERE C.grade = %s
            ORDER BY C.upload_date DESC
        """, (grade,))

        classes = cur.fetchall()

    except Exception as e:
        print(f"Error fetching classes: {e}")
        flash("Failed to load classes. Please try again.", "error")
        classes = []

    finally:
        cur.close()
        conn.close()

    # 4️⃣ Render template
    return render_template("student_classes.html", classes=classes)

@app.route("/student/request", methods=['GET', 'POST'])
def student_request():
    # 1️⃣ Ensure student is logged in
    if 'user_role' not in session or session['user_role'] != 'student' or 'user_id' not in session:
        return redirect('/login')

    student_id = session['user_id']  # use consistent session key

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 2️⃣ Fetch all active mentors for dropdown
        cur.execute("""
            SELECT mentor_id, name, surname 
            FROM Mentor 
            WHERE status='active' 
            ORDER BY name
        """)
        mentors = cur.fetchall()

        if request.method == 'POST':
            mentor_id = request.form.get('mentor_id')
            topic = request.form.get('topic')
            message = request.form.get('message')
            request_type = request.form.get('request_type')
            pdf_file_url = None

            # 3️⃣ Handle PDF upload
            if 'pdf' in request.files:
                file = request.files['pdf']
                if file.filename != '':
                    filename = secure_filename(file.filename)
                    pdf_file_path = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(pdf_file_path)
                    pdf_file_url = f"uploads/{filename}"  # store relative path in DB

            # 4️⃣ Insert request into DB
            cur.execute("""
                INSERT INTO Request (student_id, mentor_id, topic, message, request_type, pdf_url)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (student_id, mentor_id, topic, message, request_type, pdf_file_url))
            conn.commit()

            flash("Request sent successfully!", "success")
            return render_template("student_request.html", mentors=mentors, success=True)

    except Exception as e:
        print(f"Error sending request: {e}")
        flash("Failed to send request. Please try again.", "error")

    finally:
        cur.close()
        conn.close()

    # 5️⃣ Render the form if GET or POST fails
    return render_template("student_request.html", mentors=mentors)

@app.route("/student/enrollment")
def student_enrollment():
    if 'user_role' not in session or session['user_role'] != 'student' or 'user_id' not in session:
        return redirect('/login')

    student_id = session['user_id']

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            SELECT e.enrollment_id, e.days_remaining, e.status, e.last_updated AS enrollment_date,
                   s.name, s.surname, s.grade
            FROM Enrollment e
            JOIN Student s ON e.student_id = s.student_id
            WHERE e.student_id = %s
            ORDER BY e.enrollment_id DESC
            LIMIT 1
        """, (student_id,))
        enrollment = cur.fetchone()

    finally:
        cur.close()
        conn.close()

    if not enrollment:
        return redirect("/student/payment?no_enrollment=1")
    if enrollment["status"] != "active" or enrollment["days_remaining"] <= 0:
        return redirect("/student/payment?expired=1")

    # ✅ Pass a list so the template can loop
    return render_template(
    "student_enrollment.html",
    enrollments=[enrollment],
    payment_info={
        "bank_name": "ABSA\n/ CAPITEC",          # line break between banks
        "account_name": "EduBoost / Baloyi",     # remove invalid backslash
        "account_number": "4103751120\n/ 1843987021",  # line break between account numbers
        "reference": f"STU-{student_id}"
    }
)


@app.route("/student/profile", methods=['GET', 'POST'])
def student_profile():
    # Ensure user is logged in AND is a student
    if 'user_role' not in session or session['user_role'] != 'student':
        return redirect('/login')

    student_id = session['user_id']  # ✅ Correct session key

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Fetch current student info
    cur.execute("SELECT * FROM Student WHERE student_id = %s", (student_id,))
    student = cur.fetchone()

    if not student:
        session.clear()
        return redirect('/login')

    if request.method == 'POST':
        name = request.form.get('name')
        surname = request.form.get('surname')
        phone = request.form.get('phone')
        grade = request.form.get('grade')
        profile_image = request.form.get('profile_image')  # ✅ TAKE AS LINK (no file upload)

        # Update student info
        cur.execute("""
            UPDATE Student
            SET name = %s,
                surname = %s,
                phone = %s,
                grade = %s,
                profile_image = %s
            WHERE student_id = %s
        """, (name, surname, phone, grade, profile_image, student_id))

        conn.commit()
        cur.close()
        conn.close()

        # ✅ Update session name and grade
        session['user_name'] = f"{name} {surname}"
        session['grade'] = grade

        return redirect('/student/dashboard')

    cur.close()
    conn.close()

    return render_template("student_profile.html", student=student)



@app.route("/student/dashboard/courses")
def student_courses():
    # Make sure user is logged in as student
    if 'user_role' not in session or session['user_role'] != 'student':
        return redirect('/login')

    student_id = session['user_id']      # ✅ FIXED: use user_id
    grade = session.get('grade')         # ✅ get grade for filtering

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

    # ✅ Get subjects available only for this student's grade
    cur.execute("""
        SELECT DISTINCT subject 
        FROM Content
        WHERE grade = %s
        ORDER BY subject
    """, (grade,))
    subjects = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("student_courses.html", subjects=subjects, grade=grade)

@app.route("/student/courses/<string:subject>/contents")
def student_course_contents(subject):
    # Ensure student is logged in
    if 'user_role' not in session or session['user_role'] != 'student' or 'user_id' not in session:
        return redirect('/login')

    student_id = session['user_id']

    conn = get_db_connection()
    if not conn:
        return "❌ Failed to connect to database", 500

    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # Get student's grade
        cur.execute("""
            SELECT grade
            FROM Student
            WHERE student_id = %s AND status='active'
            LIMIT 1
        """, (student_id,))
        grade_result = cur.fetchone()
        if not grade_result:
            return "❌ Student not found or inactive", 404

        grade = grade_result['grade']

        # Get all content for this subject and grade
        cur.execute("""
            SELECT C.content_id, C.title, C.description, C.type,
                   C.file_url, C.file_name, C.file_size_mb, C.upload_date,
                   M.name AS mentor_name, M.surname AS mentor_surname
            FROM Content C
            LEFT JOIN Mentor M ON C.mentor_id = M.mentor_id
            WHERE C.subject = %s AND C.grade = %s
            ORDER BY C.upload_date DESC
        """, (subject, grade))
        contents = cur.fetchall()

        # Get multiple video links for each content
        content_links = {}
        for content in contents:
            cur.execute("""
                SELECT file_link, upload_date 
                FROM ContentRecord 
                WHERE content_id = %s
                ORDER BY upload_date DESC
            """, (content['content_id'],))
            content_links[content['content_id']] = cur.fetchall()

    finally:
        cur.close()
        conn.close()

    return render_template(
        "course_contents.html",
        subject=subject,
        grade=grade,
        contents=contents,
        content_links=content_links
    )


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
# ---------------- ID Scoring Function ----------------
def calculate_id_score(id_number):
    """
    Validates South African ID number and calculates a score out of 50.
    Returns a dict with:
    - score: integer
    - age: calculated age
    - messages: list of validation messages
    - passed: boolean
    """
    results = {'score': 0, 'age': None, 'messages': [], 'passed': False}

    # Basic format check
    if len(id_number) != 13 or not id_number.isdigit():
        results['messages'].append("ID must be 13 digits")
        return results

    results['score'] += 10  # basic format passed

    # Birth date check
    try:
        year_part = int(id_number[0:2])
        month = int(id_number[2:4])
        day = int(id_number[4:6])

        # Determine century
        full_year = 2000 + year_part if year_part <= 21 else 1900 + year_part
        birth_date = datetime(full_year, month, day)
        today = datetime.now()
        age = today.year - birth_date.year
        if (today.month, today.day) < (birth_date.month, birth_date.day):
            age -= 1
        results['age'] = age

        if 13 <= age <= 25:
            results['score'] += 15
        else:
            results['messages'].append(f"Age {age} not in 13-25 range")
    except ValueError:
        results['messages'].append("Invalid birth date in ID")
        return results

    # Citizenship check (11th digit)
    if id_number[10] in ['0', '1']:
        results['score'] += 5
    else:
        results['messages'].append("Invalid citizenship digit")

    # Checksum (Luhn algorithm)
    try:
        def luhn_checksum(idn):
            digits = [int(d) for d in idn]
            odd_sum = sum(digits[::2])
            even_digits = digits[1::2]
            even_sum = sum(int(d*2//10 + d*2%10) for d in even_digits)
            total = odd_sum + even_sum
            return total % 10 == 0

        if luhn_checksum(id_number):
            results['score'] += 20
        else:
            results['messages'].append("Checksum invalid")
    except Exception:
        results['messages'].append("Checksum calculation failed")

    results['passed'] = results['score'] >= 40
    return results

# ---------------- Signup Route ----------------
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

        # ---------------- Validate ID ----------------
        score_info = calculate_id_score(student_id)
        score = score_info['score']
        age = score_info['age']
        MIN_SCORE_ACCEPT = 40

        if score < MIN_SCORE_ACCEPT:
            err_msg = f"ID validation failed (score {score}/50). " + " ".join(score_info['messages'])
            return render_template('singuperror.html', error_message=err_msg)

        if age is None:
            return render_template('singuperror.html', error_message="Could not determine age from ID")

        # Age validation
        if age < 13 or age > 25:
            return render_template('singuperror.html', 
                                   error_message=f"You must be between 13 and 25 years old. Your age: {age}")

        # Grade validation
        try:
            grade_num = int(grade)
            if grade_num < 10 or grade_num > 12:
                return render_template('singuperror.html', 
                                       error_message="Invalid grade selection. Select between 10 and 12.")
        except (ValueError, TypeError):
            return render_template('singuperror.html', error_message="Invalid grade selection.")

        # ---------------- Database Operations ----------------
        conn = get_db_connection()
        if conn:
            try:
                cur = conn.cursor()

                # Check if email exists
                cur.execute("SELECT student_id FROM Student WHERE email=%s", (email,))
                if cur.fetchone():
                    cur.close()
                    conn.close()
                    return render_template('singupIdUsed.html', 
                                           error_message="Email already registered.")

                # Check if student ID exists
                cur.execute("SELECT student_id FROM Student WHERE student_id=%s", (student_id,))
                if cur.fetchone():
                    cur.close()
                    conn.close()
                    return render_template('singupIdUsed.html', 
                                           error_message="Student ID already registered.")

                # Insert student (password hashed)
                cur.execute("""
                    INSERT INTO Student (student_id, name, surname, email, password, grade, phone)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                """, (student_id, name, surname, email, password, grade, phone))

                # ✅ Create enrollment with new structure
                cur.execute("""
                    INSERT INTO Enrollment (student_id, enrollment_days, days_remaining, status)
                    VALUES (%s, 20, 20, 'active')
                """, (student_id,))

                conn.commit()
                cur.close()
                conn.close()

                # Set session
                session['user_id'] = student_id
                session['user_name'] = f"{name} {surname}"
                session['user_role'] = 'student'
                session['user_email'] = email
                session['grade'] = grade
                session['age'] = age

                return render_template('successfullsingup.html', 
                                       student_name=f"{name} {surname}",
                                       student_id=student_id,
                                       grade=grade,
                                       age=age)

            except Exception as e:
                print(f"Signup error: {e}")
                if conn:
                    conn.close()
                return render_template('singuperror.html', error_message=f"Registration failed: {str(e)}")

        return render_template('singuperror.html', error_message="Database connection failed.")

    # GET request
    return render_template('signup.html')


def luhn_check(id_num):
    """
    Luhn-style check used for South African ID numbers.
    Works with the first 12 digits and compares computed check digit to 13th.
    """
    digits = [int(d) for d in id_num]
    # first 12 digits
    first12 = digits[:12]

    # sum of digits in odd positions (1,3,5,...) -> indexes 0,2,4,...
    sum_odd = sum(first12[0::2])

    # even-position digits concatenated into a number, then *2 and sum the digits of result
    even_digits = ''.join(str(d) for d in first12[1::2])  # indexes 1,3,5,...
    if even_digits == '':
        return False
    even_mult = int(even_digits) * 2
    sum_even_digits = sum(int(ch) for ch in str(even_mult))

    total = sum_odd + sum_even_digits
    computed_check = (10 - (total % 10)) % 10

    return computed_check == digits[12]




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
        subject_speciality = request.form.get('subject_speciality')
        bio = request.form.get('bio')
        password = request.form.get('password') or 'changeme123'
        profile_image = request.form.get('profile_image')  # ← image URL here

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO Mentor (name, surname, email, phone, subject_speciality, password, bio, profile_image, join_date, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_DATE, 'active')
            """, (name, surname, email, phone, subject_speciality, password, bio, profile_image))

            conn.commit()
            flash("Mentor account created successfully.", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Error creating mentor: {e}", "error")
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

    # Get current mentor
    cur.execute("SELECT * FROM Mentor WHERE mentor_id = %s", (mentor_id,))
    mentor = cur.fetchone()
    if not mentor:
        flash("Mentor not found.", "danger")
        return redirect('/admin/mentors')

    if request.method == 'POST':
        name = request.form.get('name')
        surname = request.form.get('surname')
        email = request.form.get('email')
        phone = request.form.get('phone')
        subject_speciality = request.form.get('subject_speciality')
        bio = request.form.get('bio')
        status = request.form.get('status')

        # Handle profile image upload only if a new one is provided
        file = request.files.get('profile_image')
        image_path = mentor['profile_image']  # Keep current image

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(upload_path)

            # Only store filename in DB, not full path
            image_path = filename

        # Update mentor details
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
        # ✅ Ensure user is logged in as mentor
        if 'user_role' not in session or session['user_role'] != 'mentor':
            flash("Please login as a mentor first.", "warning")
            return redirect('/login')  # unified login page
        return f(*args, **kwargs)
    return decorated

# MENTOR / EMPLOYEE DASHBOARD
# ----------------------------
# Mentor / Employee Dashboard
# ----------------------------

@app.route('/employee/dashboard')
def employee_dashboard():
    # ✅ Ensure user is logged in as mentor
    if 'user_role' not in session or session['user_role'] != 'mentor':
        flash("Please login as mentor first.", "warning")
        return redirect('/login')  # unified login page

    mentor_id = session['user_id']  # use 'user_id' set during login

    conn = get_db_connection()
    if not conn:
        return "❌ Failed to connect to database", 500

    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # Fetch mentor details
        cur.execute("""
            SELECT name, surname, subject_speciality, bio, profile_image, phone
            FROM Mentor
            WHERE mentor_id = %s AND status='active'
        """, (mentor_id,))
        mentor = cur.fetchone()

        if not mentor:
            return "❌ Mentor not found or inactive", 404
    finally:
        cur.close()
        conn.close()

    # Render template with mentor dictionary
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


@app.route("/employee/content/upload", methods=["GET", "POST"])
def employee_content_upload():
    # ----------------------------
    # 1️⃣ Ensure logged in as mentor
    # ----------------------------
    if 'user_role' not in session or session['user_role'] != 'mentor':
        flash("Please login as a mentor first.", "warning")
        return redirect("/login")

    mentor_id = session['user_id']  # ✅ unified session key
    grade = request.args.get("grade")

    if not grade:
        flash("Please select a grade first.", "warning")
        return redirect("/employee/dashboard")

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        subject = request.form.get("subject")
        file_url = request.form.get("file_url")  # PDF link
        video_links = request.form.getlist("video_links[]")  # multiple videos

        # Validate required fields
        if not title or not subject:
            flash("Title and Subject are required.", "danger")
            return redirect(request.url)

        conn = get_db_connection()
        cur = conn.cursor()

        try:
            # Insert main content record (PDF stored as link)
            cur.execute("""
                INSERT INTO Content (mentor_id, title, description, subject, grade, file_url)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING content_id
            """, (mentor_id, title, description, subject, grade, file_url))

            content_id = cur.fetchone()[0]
            conn.commit()

            # Insert video links if provided
            for link in video_links:
                if link.strip() != "":
                    cur.execute("""
                        INSERT INTO ContentRecord (content_id, file_link)
                        VALUES (%s, %s)
                    """, (content_id, link))
            conn.commit()

            flash(f"✅ Content uploaded successfully for Grade {grade}", "success")
            return redirect("/employee/content/uploaded")

        except Exception as e:
            conn.rollback()
            flash(f"Failed to upload content: {e}", "danger")
            print(f"Error uploading content: {e}")

        finally:
            cur.close()
            conn.close()

    return render_template("upload_content.html", grade=grade)


@app.route("/employee/manage-contents")
def employee_manage_contents():
    # Ensure logged in as mentor
    if 'user_role' not in session or session['user_role'] != 'mentor':
        flash("Please login as a mentor first.", "warning")
        return redirect("/login")

    mentor_id = session['user_id']  # Unified session key

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Get all content uploaded by this mentor
    cur.execute("""
        SELECT C.content_id, C.title, C.subject, C.grade, C.file_url, C.upload_date
        FROM Content C
        WHERE C.mentor_id = %s
        ORDER BY C.upload_date DESC
    """, (mentor_id,))
    contents = cur.fetchall()

    # Get multiple resource/video links for each content
    content_links = {}
    for c in contents:
        cur.execute("""
            SELECT file_link 
            FROM ContentRecord 
            WHERE content_id = %s
        """, (c['content_id'],))
        content_links[c['content_id']] = [row['file_link'] for row in cur.fetchall()]

    cur.close()
    conn.close()

    return render_template(
        "manage_contents.html",
        contents=contents,
        content_links=content_links
    )

    # Ensure logged in as mentor
    if 'user_role' not in session or session['user_role'] != 'mentor':
        flash("Please login as a mentor first.", "warning")
        return redirect("/login")

    mentor_id = session['user_id']  # Unified session key

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Get all content uploaded by this mentor
    cur.execute("""
        SELECT C.content_id, C.title, C.subject, C.grade, C.file_url, C.upload_date
        FROM Content C
        WHERE C.mentor_id = %s
        ORDER BY C.upload_date DESC
    """, (mentor_id,))
    contents = cur.fetchall()

    # Get multiple video links per content
    content_links = {}
    for c in contents:
        cur.execute("""
            SELECT file_link 
            FROM ContentRecord 
            WHERE content_id = %s
        """, (c['content_id'],))
        content_links[c['content_id']] = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "manage_contents.html",
        contents=contents,
        content_links=content_links
    )

@app.route("/employee/manage-contents/delete/<int:content_id>", methods=["POST"])
def delete_content(content_id):
    if 'user_role' not in session or session['user_role'] != 'mentor':
        flash("Unauthorized", "danger")
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor()

    # Delete associated extra links first
    cur.execute("DELETE FROM ContentRecord WHERE content_id = %s", (content_id,))
    # Delete main content
    cur.execute("DELETE FROM Content WHERE content_id = %s", (content_id,))
    
    conn.commit()
    cur.close()
    conn.close()

    flash("Content deleted successfully.", "success")
    return redirect("/employee/manage-contents")


@app.route("/employee/requests")
def employee_requests():
    # Check if user is logged in as mentor or admin
    if 'user_role' not in session or session.get('user_role') not in ['mentor', 'admin'] or 'user_id' not in session:
        flash("Please login first.", "warning")
        return redirect("/login")  # unified login page

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            SELECT R.request_id, R.topic, R.message, R.request_type, R.status, R.created_at, R.pdf_url,
                   S.name AS student_name, S.surname AS student_surname, S.phone AS student_phone, S.email AS student_email
            FROM Request R
            LEFT JOIN Student S ON R.student_id = S.student_id
            ORDER BY R.created_at DESC
        """)
        requests = cur.fetchall()
    except Exception as e:
        print(f"Error fetching requests: {e}")
        flash("Failed to load requests.", "danger")
        requests = []
    finally:
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
    # Ensure user is logged in as mentor
    if 'user_role' not in session or session['user_role'] != 'mentor' or 'user_id' not in session:
        return redirect("/login")

    mentor_id = session['user_id']
    error = None

    if request.method == "POST":
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")

        if not current_password or not new_password:
            error = "Both fields are required."
            return render_template("employee_change_password.html", error=error)

        conn = get_db_connection()
        cur = conn.cursor()

        # Fetch current password from DB
        cur.execute("SELECT password FROM Mentor WHERE mentor_id = %s", (mentor_id,))
        result = cur.fetchone()

        if not result:
            cur.close()
            conn.close()
            error = "Mentor not found."
            return render_template("employee_change_password.html", error=error)

        db_password = result[0]

        # Direct comparison
        if db_password != current_password:
            cur.close()
            conn.close()
            error = "Current password is incorrect."
            return render_template("employee_change_password.html", error=error)

        # Update password
        cur.execute("UPDATE Mentor SET password = %s WHERE mentor_id = %s", (new_password, mentor_id))
        conn.commit()
        cur.close()
        conn.close()

        # Redirect after successful change
        return redirect("/employee/dashboard")

    return render_template("employee_change_password.html", error=error)


@app.route("/employee/content/uploaded")
def upload_success():
    return render_template("employee_content_uploaded.html")

@app.route("/employee/class/new", methods=["GET", "POST"])
def create_new_class():
    # ----------------------------
    # 1️⃣ Ensure user is logged in as mentor
    # ----------------------------
    if 'user_role' not in session or session['user_role'] != 'mentor':
        flash("Please login as a mentor first.", "warning")
        return redirect("/login")

    mentor_id = session['user_id']  # ✅ unified session key

    if request.method == "POST":
        title = request.form.get("title")
        topic = request.form.get("topic")
        class_type = request.form.get("type")
        start_time = request.form.get("start_time")
        duration = request.form.get("duration")
        grade = request.form.get("grade")
        link = request.form.get("link")

        if not title or not grade:
            flash("Title and Grade are required.", "danger")
            return redirect(request.url)

        conn = get_db_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                INSERT INTO Class (mentor_id, title, topic, type, start_time, duration, grade, link)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (mentor_id, title, topic, class_type, start_time, duration, grade, link))
            conn.commit()
            flash("✅ Class posted successfully!", "success")
            return redirect('/employee/dashboard')

        except Exception as e:
            flash(f"Failed to post class: {e}", "danger")
            print(f"Error creating new class: {e}")

        finally:
            cur.close()
            conn.close()

    return render_template("employee_class_new.html")


@app.route("/employee/classes")
def view_classes():
    # ----------------------------
    # 1️⃣ Ensure user is logged in as mentor
    # ----------------------------
    if 'user_role' not in session or session['user_role'] != 'mentor':
        flash("Please login as a mentor first.", "warning")
        return redirect("/login")

    mentor_id = session['user_id']  # ✅ use unified session key

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            SELECT class_id, title, topic, type, start_time, duration, grade, link, upload_date
            FROM Class
            WHERE mentor_id = %s
            ORDER BY start_time DESC
        """, (mentor_id,))

        classes = cur.fetchall()

    except Exception as e:
        flash(f"Failed to fetch classes: {e}", "danger")
        print(f"Error fetching mentor classes: {e}")
        classes = []

    finally:
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