from flask import Flask, render_template, redirect, url_for, session, request, flash
from datetime import timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'eduboostup-secret-key-2023'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

# Database configuration
app.config['DATABASE_CONFIG'] = {
    'host': 'localhost',
    'database': 'eduboostup',  # You'll need to create this database
    'user': 'postgres',
    'password': 'Admin123',
    'port': '5432'
}

def get_db_connection():
    """Create and return a database connection"""
    try:
        conn = psycopg2.connect(**app.config['DATABASE_CONFIG'])
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def init_db():
    """Initialize the database with required tables"""
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            
            # Create users table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    user_type VARCHAR(50) NOT NULL,
                    grade VARCHAR(10),
                    student_id VARCHAR(50),
                    surname VARCHAR(255),
                    phone VARCHAR(20),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Insert demo users if they don't exist
            demo_users = [
                ('student@eduboostup.com', 'password123', 'John Student', 'student', '11', 'STU001', 'Doe', '1234567890'),
                ('admin@eduboostup.com', 'admin123', 'Admin User', 'admin', NULL, NULL, NULL, NULL),
                ('mentor@eduboostup.com', 'mentor123', 'Jane Mentor', 'mentor', NULL, NULL, 'Smith', NULL)
            ]
            
            for user in demo_users:
                cur.execute('''
                    INSERT INTO users (email, password, name, user_type, grade, student_id, surname, phone)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (email) DO NOTHING
                ''', user)
            
            conn.commit()
            cur.close()
            print("Database initialized successfully!")
            
        except Exception as e:
            print(f"Error initializing database: {e}")
            conn.rollback()
        finally:
            conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember')
        
        # Check if user exists in database
        conn = get_db_connection()
        if conn:
            try:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute(
                    'SELECT * FROM users WHERE email = %s AND password = %s',
                    (email, password)
                )
                user = cur.fetchone()
                cur.close()
                
                if user:
                    session['user_id'] = user['email']
                    session['user_name'] = user['name']
                    session['user_type'] = user['user_type']
                    
                    if remember:
                        session.permanent = True
                    
                    flash('Login successful!', 'success')
                    
                    # Redirect based on user type
                    if user['user_type'] == 'student':
                        return redirect(url_for('student_dashboard'))
                    elif user['user_type'] == 'admin':
                        return redirect(url_for('admin_dashboard'))
                    elif user['user_type'] == 'mentor':
                        return redirect(url_for('mentor_dashboard'))
                else:
                    flash('Invalid credentials. Please try again.', 'error')
                    
            except Exception as e:
                print(f"Database error: {e}")
                flash('Database error. Please try again.', 'error')
            finally:
                conn.close()
        else:
            flash('Database connection failed. Please try again.', 'error')
    
    return render_template('studentLogin.html')

@app.route('/student_dashboard')
def student_dashboard():
    # Check if user is logged in and is a student
    if 'user_id' not in session or session.get('user_type') != 'student':
        flash('Please log in to access the dashboard.', 'error')
        return redirect(url_for('student_login'))
    
    # Get user data from database
    conn = get_db_connection()
    user_data = {'name': session.get('user_name', 'Student'), 'grade': '11'}
    
    if conn:
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                'SELECT name, grade FROM users WHERE email = %s',
                (session['user_id'],)
            )
            user_db = cur.fetchone()
            if user_db:
                user_data = {
                    'name': user_db['name'],
                    'grade': user_db['grade'] or '11'
                }
            cur.close()
        except Exception as e:
            print(f"Database error: {e}")
        finally:
            conn.close()
    
    return render_template('student_deshboard.html', user=user_data)

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
        terms = request.form.get('terms')
        
        # Validate required fields
        if not all([email, password, name, surname, grade]):
            flash('Please fill in all required fields.', 'error')
            return render_template('signup.html')
        
        # Save to database
        conn = get_db_connection()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute('''
                    INSERT INTO users (email, password, name, user_type, grade, student_id, surname, phone)
                    VALUES (%s, %s, %s, 'student', %s, %s, %s, %s)
                ''', (email, password, f"{name} {surname}", grade, student_id, surname, phone))
                conn.commit()
                cur.close()
                
                flash('Account created successfully! Please log in.', 'success')
                return redirect(url_for('student_login'))
                
            except psycopg2.IntegrityError:
                flash('Email already exists. Please use a different email.', 'error')
            except Exception as e:
                print(f"Database error: {e}")
                flash('Error creating account. Please try again.', 'error')
            finally:
                conn.close()
        else:
            flash('Database connection failed. Please try again.', 'error')
    
    return render_template('signup.html')

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = get_db_connection()
        if conn:
            try:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute(
                    'SELECT * FROM users WHERE email = %s AND password = %s AND user_type = %s',
                    (email, password, 'admin')
                )
                user = cur.fetchone()
                cur.close()
                
                if user:
                    session['user_id'] = user['email']
                    session['user_name'] = user['name']
                    session['user_type'] = 'admin'
                    flash('Admin login successful!', 'success')
                    return redirect(url_for('admin_dashboard'))
                else:
                    flash('Invalid admin credentials.', 'error')
                    
            except Exception as e:
                print(f"Database error: {e}")
                flash('Database error. Please try again.', 'error')
            finally:
                conn.close()
        else:
            flash('Database connection failed. Please try again.', 'error')
    
    return render_template('adminLogin.html')

@app.route('/admin-dashboard')
def admin_dashboard():
    if 'user_id' not in session or session.get('user_type') != 'admin':
        flash('Please log in as admin.', 'error')
        return redirect(url_for('admin_login'))
    
    return render_template('admin_dashboard.html', user={'name': session.get('user_name', 'Admin')})

@app.route('/mentor-login', methods=['GET', 'POST'])
def mentor_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = get_db_connection()
        if conn:
            try:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute(
                    'SELECT * FROM users WHERE email = %s AND password = %s AND user_type = %s',
                    (email, password, 'mentor')
                )
                user = cur.fetchone()
                cur.close()
                
                if user:
                    session['user_id'] = user['email']
                    session['user_name'] = user['name']
                    session['user_type'] = 'mentor'
                    flash('Mentor login successful!', 'success')
                    return redirect(url_for('mentor_dashboard'))
                else:
                    flash('Invalid mentor credentials.', 'error')
                    
            except Exception as e:
                print(f"Database error: {e}")
                flash('Database error. Please try again.', 'error')
            finally:
                conn.close()
        else:
            flash('Database connection failed. Please try again.', 'error')
    
    return render_template('mentorLogin.html')

@app.route('/mentor-dashboard')
def mentor_dashboard():
    if 'user_id' not in session or session.get('user_type') != 'mentor':
        flash('Please log in as mentor.', 'error')
        return redirect(url_for('mentor_login'))
    
    return render_template('mentor_dashboard.html', user={'name': session.get('user_name', 'Mentor')})

@app.route('/book-lesson', methods=['POST'])
def book_lesson():
    if 'user_id' not in session or session.get('user_type') != 'student':
        return {'success': False, 'message': 'Please log in as student.'}, 401
    
    mentor_name = request.json.get('mentor_name')
    subject = request.json.get('subject')
    date = request.json.get('date')
    time = request.json.get('time')
    
    # In a real app, you would save this booking to a database
    # For demo purposes, we'll just return success
    
    return {
        'success': True, 
        'message': f'Lesson booked successfully with {mentor_name} for {subject} on {date} at {time}'
    }

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('student_login'))

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Initialize database when starting the app
    init_db()
    app.run(debug=True)