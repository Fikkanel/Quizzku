import os
import re
import json
import random
import functools
from datetime import datetime, timedelta

from flask import (
    Flask,
    render_template,
    make_response,
    request,
    jsonify,
    session,
    redirect,
    url_for,
    flash,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError

# Inisialisasi aplikasi
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quizapp.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config.update(
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=5)
)

db = SQLAlchemy(app)

# Quiz directory
SOAL_DIR = 'soal'
if not os.path.exists(SOAL_DIR):
    os.makedirs(SOAL_DIR)

# Model Database
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'student', 'teacher', atau 'admin'

class QuizResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quiz_title = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Float, nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.now)

# Decorator untuk admin login
def admin_login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('admin_login'))
        try:
            admin = User.query.get(session['admin_id'])
            if not admin or admin.role != 'admin':
                session.clear()
                return redirect(url_for('admin_login'))
        except Exception:
            session.clear()
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Decorator untuk regular user login
def login_required(view_func=None, *, role=None):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            
            try:
                user = User.query.get(session['user_id'])
                if not user:
                    session.clear()
                    return redirect(url_for('login'))
                
                if role and user.role != role:
                    session.clear()
                    return redirect(url_for('login'))
                
                return func(*args, **kwargs)
                
            except Exception as e:
                print(f"Auth error: {str(e)}")
                session.clear()
                return redirect(url_for('login'))
                
        return wrapper

    if view_func:
        return decorator(view_func)
    return decorator

# Fungsi utility
def get_quiz_list():
    """Mengambil daftar quiz dari folder soal"""
    quizzes = []
    for filename in os.listdir(SOAL_DIR):
        if filename.endswith('.json'):
            with open(os.path.join(SOAL_DIR, filename), 'r') as f:
                quiz = json.load(f)
                quizzes.append({
                    'title': quiz['title'],
                    'subject': quiz['subject'],
                    'total_questions': len(quiz['questions'])
                })
    return quizzes

def save_quiz(quiz_data):
    """Menyimpan quiz ke file JSON"""
    filename = f"{quiz_data['title'].lower().replace(' ', '_')}.json"
    filepath = os.path.join(SOAL_DIR, filename)
    with open(filepath, 'w') as f:
        json.dump(quiz_data, f, indent=4)

def get_quiz(quiz_title):
    """Mengambil data quiz berdasarkan judul"""
    try:
        filename = f"{quiz_title.lower().replace(' ', '_')}.json"
        filepath = os.path.join(SOAL_DIR, filename)
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
        return None
    except Exception as e:
        print(f"Error getting quiz: {str(e)}")
        return None

# Main routes
@app.route('/')
def index():
    if 'admin_id' in session:
        return redirect(url_for('admin_dashboard'))
    elif 'user_id' in session:
        try:
            user = User.query.get(session['user_id'])
            if user.role == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            return redirect(url_for('student_dashboard'))
        except Exception:
            session.clear()
    return redirect(url_for('login'))

# Regular user login
@app.route('/login', methods=['GET', 'POST'])
def login():
    # If already logged in as admin, redirect to admin dashboard
    if 'admin_id' in session:
        try:
            admin = User.query.get(session['admin_id'])
            if admin and admin.role == 'admin':
                return redirect(url_for('admin_dashboard'))
        except Exception:
            session.clear()

    # If already logged in as regular user, redirect to appropriate dashboard
    if 'user_id' in session:
        try:
            user = User.query.get(session['user_id'])
            if user:
                if user.role == 'teacher':
                    return redirect(url_for('teacher_dashboard'))
                return redirect(url_for('student_dashboard'))
        except Exception:
            session.clear()

    if request.method == 'GET':
        return render_template('login.html')

    try:
        data = request.form
        username = data.get('username')
        password = data.get('password')

        user = User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.password, password) or user.role == 'admin':
            return jsonify({
                'success': False,
                'message': 'Username atau password salah'
            }), 401

        session.clear()
        session.permanent = True
        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = user.role

        if user.role == 'teacher':
            redirect_url = url_for('teacher_dashboard')
        else:
            redirect_url = url_for('student_dashboard')

        return jsonify({
            'success': True,
            'redirect': redirect_url
        })

    except Exception as e:
        session.clear()
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500

# Admin routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    # If already logged in as admin, redirect to admin dashboard
    if 'admin_id' in session:
        try:
            admin = User.query.get(session['admin_id'])
            if admin and admin.role == 'admin':
                return redirect(url_for('admin_dashboard'))
        except Exception:
            session.clear()

    # If already logged in as regular user, redirect to appropriate dashboard
    if 'user_id' in session:
        try:
            user = User.query.get(session['user_id'])
            if user:
                if user.role == 'teacher':
                    return redirect(url_for('teacher_dashboard'))
                return redirect(url_for('student_dashboard'))
        except Exception:
            session.clear()

    if request.method == 'GET':
        return render_template('admin/login.html')

    try:
        data = request.form
        username = data.get('username')
        password = data.get('password')

        admin = User.query.filter_by(username=username, role='admin').first()

        if not admin or not check_password_hash(admin.password, password):
            return jsonify({
                'success': False,
                'message': 'Invalid admin credentials'
            }), 401

        session.clear()
        session.permanent = True
        session['admin_id'] = admin.id
        session['admin_username'] = admin.username

        return jsonify({
            'success': True,
            'redirect': url_for('admin_dashboard')
        })

    except Exception as e:
        session.clear()
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/admin/dashboard')
@admin_login_required
def admin_dashboard():
    try:
        admin = User.query.get(session['admin_id'])
        
        # Get system statistics
        total_users = User.query.count()
        total_students = User.query.filter_by(role='student').count()
        total_teachers = User.query.filter_by(role='teacher').count()
        total_quizzes = len([f for f in os.listdir(SOAL_DIR) if f.endswith('.json')])
        total_quiz_attempts = QuizResult.query.count()
        
        # Get recent quiz results
        recent_results = db.session.query(
            QuizResult,
            User.username
        ).join(
            User, QuizResult.student_id == User.id
        ).order_by(
            QuizResult.submitted_at.desc()
        ).limit(10).all()
        
        # Get user statistics
        user_stats = db.session.query(
            User.username,
            User.role,
            db.func.count(QuizResult.id).label('quiz_count'),
            db.func.avg(QuizResult.score).label('avg_score')
        ).outerjoin(
            QuizResult, User.id == QuizResult.student_id
        ).group_by(User.id).all()

        return render_template(
            'admin/dashboard.html',
            admin=admin,
            total_users=total_users,
            total_students=total_students,
            total_teachers=total_teachers,
            total_quizzes=total_quizzes,
            total_quiz_attempts=total_quiz_attempts,
            recent_results=recent_results,
            user_stats=user_stats
        )

    except Exception as e:
        session.clear()
        return redirect(url_for('admin_login'))

@app.route('/admin/users')
@admin_login_required
def admin_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/add_user', methods=['POST'])
@admin_login_required
def admin_add_user():
    try:
        data = request.form
        username = data.get('username')
        password = data.get('password')
        role = data.get('role')

        if role not in ['student', 'teacher', 'admin']:
            return jsonify({'success': False, 'message': 'Invalid role'})

        user = User(
            username=username,
            password=generate_password_hash(password),
            role=role
        )
        db.session.add(user)
        db.session.commit()

        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/edit_user/<int:user_id>', methods=['POST'])
@admin_login_required
def admin_edit_user(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})

        data = request.form
        username = data.get('username')
        password = data.get('password')
        role = data.get('role')

        if role not in ['student', 'teacher', 'admin']:
            return jsonify({'success': False, 'message': 'Invalid role'})

        user.username = username
        if password:
            user.password = generate_password_hash(password)
        user.role = role
        db.session.commit()

        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@admin_login_required
def admin_delete_user(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})

        db.session.delete(user)
        db.session.commit()

        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

# Regular user routes (remaining unchanged)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')

    try:
        data = request.form
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        confirm_password = data.get('confirm_password', '').strip()
        role = data.get('role', 'student').strip().lower()

        if not username or len(username) < 3:
            return jsonify({'success': False, 'message': 'Username minimal 3 karakter'}), 400
        
        if not password or len(password) < 6:
            return jsonify({'success': False, 'message': 'Password minimal 6 karakter'}), 400
        
        if password != confirm_password:
            return jsonify({'success': False, 'message': 'Password tidak cocok'}), 400
        
        if role not in ['student', 'teacher']:
            return jsonify({'success': False, 'message': 'Role tidak valid'}), 400

        if User.query.filter_by(username=username).first():
            return jsonify({'success': False, 'message': 'Username sudah digunakan'}), 400

        new_user = User(
            username=username,
            password=generate_password_hash(password),
            role=role
        )
        db.session.add(new_user)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Registrasi berhasil',
            'redirect': url_for('login')
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/student_dashboard')
@login_required(role='student')
def student_dashboard():
    print(f"Session data at student dashboard: {session}")  # Debug log
    
    try:
        # Verifikasi ulang user dan role
        user = User.query.get(session.get('user_id'))
        if not user or user.role != 'student':
            session.clear()
            return redirect(url_for('login'))

        # Ambil daftar quiz dari folder soal
        available_quizzes = []
        for filename in os.listdir(SOAL_DIR):
            if filename.endswith('.json'):
                with open(os.path.join(SOAL_DIR, filename), 'r') as f:
                    quiz = json.load(f)
                    available_quizzes.append(quiz)

        # Ambil hasil quiz yang sudah dikerjakan
        completed_results = QuizResult.query.filter_by(student_id=user.id).all()

        # Filter quiz yang belum dikerjakan
        completed_quiz_titles = {result.quiz_title for result in completed_results}
        uncompleted_quizzes = [
            quiz for quiz in available_quizzes 
            if quiz['title'] not in completed_quiz_titles
        ]

        return render_template(
            'student_dashboard.html',
            user=user,
            available_quizzes=uncompleted_quizzes,
            completed_results=completed_results
        )

    except Exception as e:
        print(f"Student dashboard error: {str(e)}")  # Debug log
        session.clear()
        return redirect(url_for('login'))

# Perbaiki route teacher_dashboard untuk menangani error view_quiz dengan lebih baik
@app.route('/teacher_dashboard')
@login_required(role='teacher')
def teacher_dashboard():
    try:
        user = User.query.get(session['user_id'])
        if not user or user.role != 'teacher':
            session.clear()
            return redirect(url_for('login'))

        # Hitung total quiz dan siswa
        quiz_files = [f for f in os.listdir(SOAL_DIR) if f.endswith('.json')]
        total_quizzes = len(quiz_files)
        total_students = User.query.filter_by(role='student').count()

        # Ambil quiz terbaru dengan error handling yang lebih baik
        recent_quizzes = []
        for filename in sorted(quiz_files, key=lambda x: os.path.getmtime(os.path.join(SOAL_DIR, x)), reverse=True)[:5]:
            try:
                with open(os.path.join(SOAL_DIR, filename), 'r') as f:
                    quiz = json.load(f)
                    created_at = quiz.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    if isinstance(created_at, str):
                        created_at = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                    
                    recent_quizzes.append({
                        'title': quiz['title'],
                        'subject': quiz.get('subject', 'Tidak ada subjek'),
                        'created_at': created_at
                    })
            except Exception as e:
                print(f"Error loading quiz {filename}: {str(e)}")
                continue

        return render_template(
            'teacher_dashboard.html',
            user=user,
            total_quizzes=total_quizzes,
            total_students=total_students,
            recent_quizzes=recent_quizzes
        )

    except Exception as e:
        print(f"Dashboard error: {str(e)}")
        flash(f'Terjadi kesalahan: {str(e)}', 'error')
        return redirect(url_for('login'))

@app.route('/manage_quizzes')
@login_required(role='teacher')
def manage_quizzes():
    try:
        # Ambil semua quiz yang ada di folder soal
        quizzes = []
        for filename in os.listdir(SOAL_DIR):
            if filename.endswith('.json'):
                with open(os.path.join(SOAL_DIR, filename), 'r') as f:
                    quiz = json.load(f)
                    # Tambahkan statistik untuk setiap quiz
                    results = QuizResult.query.filter_by(quiz_title=quiz['title']).all()
                    quiz_stats = {
                        'total_attempts': len(results),
                        'avg_score': sum(r.score for r in results) / len(results) if results else 0,
                        'total_questions': len(quiz['questions']),
                        'created_at': quiz.get('created_at', 'Tidak ada data'),
                        'created_by': quiz.get('created_by', 'Admin')
                    }
                    quizzes.append({**quiz, 'stats': quiz_stats})

        return render_template('manage_quizzes.html', quizzes=quizzes)
    except Exception as e:
        flash(f'Terjadi kesalahan: {str(e)}', 'error')
        return redirect(url_for('teacher_dashboard'))

@app.route('/create_quiz', methods=['GET', 'POST'])
@login_required(role='teacher')
def create_quiz():
    if request.method == 'GET':
        return render_template('create_quiz.html')

    try:
        data = request.get_json()
        
        # Validasi input
        title = data.get('title', '').strip()
        subject = data.get('subject', '').strip()
        description = data.get('description', '').strip()

        if not title or not subject:
            return jsonify({
                'success': False,
                'message': 'Judul dan mata pelajaran harus diisi'
            }), 400

        # Buat file quiz baru
        quiz_data = {
            'title': title,
            'subject': subject,
            'description': description,
            'created_by': session.get('username', 'Unknown'),
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'questions': []  # Questions akan ditambahkan nanti
        }

        # Simpan ke file
        save_quiz(quiz_data)

        return jsonify({
            'success': True,
            'message': 'Quiz berhasil dibuat',
            'redirect': url_for('add_questions', quiz_title=title)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500

@app.route('/edit_quiz/<quiz_title>', methods=['GET', 'POST'])
@login_required(role='teacher')
def edit_quiz(quiz_title):
    try:
        # Ambil data quiz
        quiz = get_quiz(quiz_title)
        if not quiz:
            flash('Quiz tidak ditemukan', 'error')
            return redirect(url_for('teacher_dashboard'))

        if request.method == 'POST':
            try:
                data = request.get_json()
                quiz.update({
                    'title': data['title'],
                    'subject': data['subject'],
                    'questions': data['questions']
                })
                save_quiz(quiz)
                return jsonify({
                    'success': True,
                    'message': 'Quiz berhasil diupdate'
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'Gagal mengupdate quiz: {str(e)}'
                }), 500

        return render_template('edit_quiz.html', quiz=quiz)

    except Exception as e:
        flash(f'Terjadi kesalahan: {str(e)}', 'error')
        return redirect(url_for('teacher_dashboard'))

# Pastikan fungsi get_quiz dan save_quiz sudah terdefinisi dengan benar
def get_quiz(quiz_title):
    """Mengambil data quiz berdasarkan judul"""
    try:
        filename = f"{quiz_title.lower().replace(' ', '_')}.json"
        filepath = os.path.join(SOAL_DIR, filename)
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
        return None
    except Exception as e:
        print(f"Error getting quiz: {str(e)}")
        return None

def save_quiz(quiz_data):
    """Menyimpan quiz ke file JSON"""
    try:
        filename = f"{quiz_data['title'].lower().replace(' ', '_')}.json"
        filepath = os.path.join(SOAL_DIR, filename)
        with open(filepath, 'w') as f:
            json.dump(quiz_data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving quiz: {str(e)}")
        return False

@app.route('/delete_quiz/<quiz_title>')
@login_required(role='teacher')
def delete_quiz(quiz_title):
    try:
        filename = f"{quiz_title.lower().replace(' ', '_')}.json"
        filepath = os.path.join(SOAL_DIR, filename)
        
        if os.path.exists(filepath):
            # Hapus file quiz
            os.remove(filepath)
            
            # Hapus semua hasil quiz terkait dari database
            QuizResult.query.filter_by(quiz_title=quiz_title).delete()
            db.session.commit()
            
            flash('Quiz berhasil dihapus', 'success')
        else:
            flash('Quiz tidak ditemukan', 'error')
            
        return redirect(url_for('manage_quizzes'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal menghapus quiz: {str(e)}', 'error')
        return redirect(url_for('manage_quizzes'))

@app.route('/add_questions/<quiz_title>', methods=['GET', 'POST'])
@login_required(role='teacher')
def add_questions(quiz_title):
    try:
        # Baca file quiz
        quiz = get_quiz(quiz_title)
        
        if not quiz:
            flash('Quiz tidak ditemukan', 'error')
            return redirect(url_for('teacher_dashboard'))

        if request.method == 'POST':
            data = request.get_json()
            if not data or 'questions' not in data:
                return jsonify({
                    'success': False,
                    'message': 'Data pertanyaan tidak valid'
                }), 400

            # Validasi format soal
            questions = data['questions']
            for q in questions:
                if not all(key in q for key in ['question_text', 'options', 'correct_answer']):
                    return jsonify({
                        'success': False,
                        'message': 'Format soal tidak valid'
                    }), 400
                if not all(key in q['options'] for key in ['A', 'B', 'C', 'D']):
                    return jsonify({
                        'success': False,
                        'message': 'Format pilihan jawaban tidak valid'
                    }), 400

            # Update questions di quiz
            quiz['questions'] = questions
            save_quiz(quiz)

            return jsonify({
                'success': True,
                'message': 'Soal berhasil disimpan',
                'redirect': url_for('manage_quizzes')
            })

        return render_template('add_questions.html', quiz=quiz)

    except Exception as e:
        print(f"Error in add_questions: {str(e)}")  # Debug log
        flash(f'Terjadi kesalahan: {str(e)}', 'error')
        return redirect(url_for('teacher_dashboard'))

@app.route('/quiz_list')
@login_required(role='student')
def quiz_list():
    try:
        # Ambil data user
        user = User.query.get(session['user_id'])
        if not user:
            flash('Data user tidak ditemukan', 'error')
            return redirect(url_for('logout'))

        # Ambil semua quiz dari folder
        quizzes = []
        for filename in os.listdir(SOAL_DIR):
            if filename.endswith('.json'):
                with open(os.path.join(SOAL_DIR, filename), 'r') as f:
                    quiz = json.load(f)
                    quizzes.append(quiz)

        # Ambil hasil quiz yang sudah dikerjakan
        completed_results = QuizResult.query.filter_by(
            student_id=user.id
        ).all()

        # Buat set dari judul quiz yang sudah dikerjakan
        completed_quiz_titles = {result.quiz_title for result in completed_results}

        # Ambil hasil quiz untuk ditampilkan
        quiz_results = {}
        for result in completed_results:
            quiz_results[result.quiz_title] = {
                'id': result.id,
                'score': result.score,
                'submitted_at': result.submitted_at
            }

        return render_template(
            'quiz_list.html',
            user=user,
            quizzes=quizzes,
            completed_quiz_titles=completed_quiz_titles,
            quiz_results=quiz_results
        )

    except Exception as e:
        print(f"Quiz list error: {str(e)}")  # Debug log
        flash(f'Terjadi kesalahan: {str(e)}', 'error')
        return redirect(url_for('student_dashboard'))
    
@app.route('/view_quiz/<quiz_title>')
@login_required(role='teacher')
def view_quiz(quiz_title):
    try:
        # Ambil data quiz
        quiz = get_quiz(quiz_title)
        if not quiz:
            flash('Quiz tidak ditemukan', 'error')
            return redirect(url_for('teacher_dashboard'))

        # Pastikan format created_at
        if isinstance(quiz.get('created_at'), str):
            quiz['created_at'] = datetime.strptime(quiz['created_at'], '%Y-%m-%d %H:%M:%S').strftime('%d %B %Y')
        else:
            quiz['created_at'] = datetime.now().strftime('%d %B %Y')

        # Ambil statistik quiz
        results = QuizResult.query.filter_by(quiz_title=quiz_title).all()
        total_attempts = len(results)
        avg_score = sum(r.score for r in results) / total_attempts if total_attempts > 0 else 0

        # Ambil questions
        questions = quiz.get('questions', [])
        
        return render_template(
            'view_quiz.html',
            quiz=quiz,
            questions=questions,
            total_attempts=total_attempts,
            avg_score=round(avg_score, 2)
        )

    except Exception as e:
        print(f"Error viewing quiz: {str(e)}")  # Debug log
        flash('Terjadi kesalahan saat memuat quiz', 'error')
        return redirect(url_for('teacher_dashboard'))

@app.route('/take_quiz/<quiz_title>')
@login_required(role='student')
def take_quiz(quiz_title):
    try:
        # Verifikasi user
        user = User.query.get(session['user_id'])
        if not user or user.role != 'student':
            return redirect(url_for('login'))

        # Cek apakah sudah pernah mengerjakan
        existing_result = QuizResult.query.filter_by(
            student_id=session['user_id'],
            quiz_title=quiz_title
        ).first()

        if existing_result:
            flash('Anda sudah mengerjakan quiz ini', 'warning')
            return redirect(url_for('student_dashboard'))

        # Ambil data quiz
        quiz = get_quiz(quiz_title)
        if not quiz:
            flash('Quiz tidak ditemukan', 'error')
            return redirect(url_for('student_dashboard'))

        # Debug print untuk melihat struktur data
        print(f"Quiz data: {quiz}")
        print(f"First question: {quiz['questions'][0] if quiz.get('questions') else 'No questions'}")

        return render_template(
            'take_quiz.html',
            quiz=quiz,
            questions=quiz.get('questions', [])
        )

    except Exception as e:
        print(f"Error in take_quiz: {str(e)}")
        flash('Terjadi kesalahan saat memuat quiz', 'error')
        return redirect(url_for('student_dashboard'))

@app.route('/submit_quiz', methods=['POST'])
@login_required(role='student')
def submit_quiz():
    try:
        data = request.get_json()
        quiz_title = data['quiz_title']
        answers = data['answers']

        quiz = get_quiz(quiz_title)
        if not quiz:
            return jsonify({
                'success': False,
                'message': 'Quiz tidak ditemukan'
            }), 404

        # Hitung skor
        correct = 0
        total = len(quiz['questions'])

        for q_idx, answer in answers.items():
            q_idx = int(q_idx)
            if q_idx < total and answer == quiz['questions'][q_idx]['correct_answer']:
                correct += 1

        score = (correct / total) * 100

        # Simpan hasil
        result = QuizResult(
            student_id=session['user_id'],
            quiz_title=quiz_title,
            score=score
        )
        db.session.add(result)
        db.session.commit()

        return jsonify({
            'success': True,
            'score': score,
            'redirect': url_for('view_result', result_id=result.id)
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/view_result/<int:result_id>')
@login_required(role='student')
def view_result(result_id):
    try:
        # Get the quiz result
        result = QuizResult.query.get_or_404(result_id)
        
        # Verify the result belongs to the logged-in student
        if result.student_id != session['user_id']:
            flash('Unauthorized access', 'error')
            return redirect(url_for('student_dashboard'))
        
        # Get the quiz data
        quiz = get_quiz(result.quiz_title)
        if not quiz:
            flash('Quiz data not found', 'error')
            return redirect(url_for('student_dashboard'))
        
        # Get student data
        student = User.query.get(result.student_id)
        
        return render_template(
            'quiz_result.html',
            result=result,
            quiz=quiz,
            student=student
        )
        
    except Exception as e:
        flash(f'Error viewing result: {str(e)}', 'error')
        return redirect(url_for('student_dashboard'))
    
@app.route('/student_results')
@login_required(role='teacher')
def student_results():
    try:
        # Query all results with student info
        results = db.session.query(
            QuizResult,
            User.username,
            QuizResult.quiz_title,
            QuizResult.score,
            QuizResult.submitted_at
        ).join(User, QuizResult.student_id == User.id).all()

        # Group results by quiz
        quiz_results = {}
        for result, username, quiz_title, score, submitted_at in results:
            if quiz_title not in quiz_results:
                quiz = get_quiz(quiz_title)
                if quiz:
                    quiz_results[quiz_title] = {
                        'title': quiz_title,
                        'subject': quiz.get('subject', 'Tidak ada subjek'),
                        'date': quiz.get('created_at', 'Tidak ada tanggal'),
                        'students': []
                    }

            if quiz_title in quiz_results:
                quiz_results[quiz_title]['students'].append({
                    'student_id': result.student_id,
                    'student_name': username,
                    'score': score
                })

        return render_template('student_results.html', 
                             quiz_results=list(quiz_results.values()))

    except Exception as e:
        flash(f'Terjadi kesalahan: {str(e)}', 'error')
        return redirect(url_for('teacher_dashboard'))

@app.route('/reset_quiz/<quiz_title>', methods=['POST'])
@login_required(role='teacher')
def reset_quiz(quiz_title):
    try:
        # Convert URL-friendly format back to normal
        quiz_title = quiz_title.replace('-', ' ')
        
        # Delete all results for this quiz
        QuizResult.query.filter_by(quiz_title=quiz_title).delete()
        db.session.commit()
        
        flash('Semua hasil quiz berhasil direset', 'success')
        return redirect(url_for('student_results'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal mereset quiz: {str(e)}', 'error')
        return redirect(url_for('student_results'))

@app.route('/reset_student_quiz/<int:student_id>/<quiz_title>', methods=['POST'])
@login_required(role='teacher')
def reset_student_quiz(student_id, quiz_title):
    try:
        # Convert URL-friendly format back to normal
        quiz_title = quiz_title.replace('-', ' ')
        
        # Delete specific student result
        QuizResult.query.filter_by(
            student_id=student_id,
            quiz_title=quiz_title
        ).delete()
        db.session.commit()
        
        flash('Hasil quiz siswa berhasil direset', 'success')
        return redirect(url_for('student_results'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal mereset quiz siswa: {str(e)}', 'error')
        return redirect(url_for('student_results'))

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# Database initialization
def init_db():
    with app.app_context():
        db.create_all()
        # Create admin account if it doesn't exist
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                password=generate_password_hash('admin123'),
                role='admin'
            )
            db.session.add(admin)
            
            # Create default teacher account
            teacher = User.query.filter_by(username='teacher').first()
            if not teacher:
                teacher = User(
                    username='teacher',
                    password=generate_password_hash('teacher123'),
                    role='teacher'
                )
                db.session.add(teacher)
            
            # Create default student account for testing
            student = User.query.filter_by(username='student').first()
            if not student:
                student = User(
                    username='student',
                    password=generate_password_hash('student123'),
                    role='student'
                )
                db.session.add(student)
            
            db.session.commit()

@app.route('/logout')
def logout():
    # Store the appropriate login route based on user type
    if 'admin_id' in session:
        login_route = 'admin_login'
    else:
        login_route = 'login'
    
    # Clear all session data
    session.clear()
    
    # Delete session cookie
    response = make_response(redirect(url_for(login_route)))
    response.delete_cookie('session')
    
    flash('Anda telah keluar dari sistem', 'info')
    return response

@app.route('/profile')
@login_required
def profile():
    try:
        user = User.query.get(session['user_id'])
        if not user:
            flash('Data user tidak ditemukan', 'error')
            return redirect(url_for('logout'))

        context = {'user': user}

        if user.role == 'student':
            results = QuizResult.query.filter_by(student_id=user.id).all()
            total_quizzes_taken = len(results)
            
            if total_quizzes_taken > 0:
                average_score = sum(result.score for result in results) / total_quizzes_taken
                highest_score = max(result.score for result in results)
                lowest_score = min(result.score for result in results)
            else:
                average_score = highest_score = lowest_score = 0

            recent_results = QuizResult.query.filter_by(
                student_id=user.id
            ).order_by(
                QuizResult.submitted_at.desc()
            ).limit(5).all()

            context.update({
                'total_quizzes_taken': total_quizzes_taken,
                'average_score': round(average_score, 2),
                'highest_score': round(highest_score, 2),
                'lowest_score': round(lowest_score, 2),
                'recent_results': recent_results
            })

        elif user.role == 'teacher':
            total_quizzes = len([f for f in os.listdir(SOAL_DIR) if f.endswith('.json')])
            
            quiz_stats = []
            for filename in os.listdir(SOAL_DIR):
                if filename.endswith('.json'):
                    with open(os.path.join(SOAL_DIR, filename), 'r') as f:
                        quiz = json.load(f)
                        results = QuizResult.query.filter_by(quiz_title=quiz['title']).all()
                        total_attempts = len(results)
                        avg_score = sum(r.score for r in results) / total_attempts if total_attempts > 0 else 0
                        quiz_stats.append({
                            'title': quiz['title'],
                            'total_attempts': total_attempts,
                            'average_score': round(avg_score, 2)
                        })

            unique_students = db.session.query(
                db.func.count(db.distinct(QuizResult.student_id))
            ).scalar() or 0

            context.update({
                'total_quizzes': total_quizzes,
                'total_students': unique_students,
                'quiz_stats': quiz_stats
            })

        return render_template('profile.html', **context)

    except Exception as e:
        flash(f'Terjadi kesalahan: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/check_session')
def check_session():
    if 'admin_id' in session:
        try:
            admin = User.query.get(session['admin_id'])
            if admin and admin.role == 'admin':
                return jsonify({'valid': True, 'role': 'admin'})
        except Exception:
            pass
    elif 'user_id' in session:
        try:
            user = User.query.get(session['user_id'])
            if user:
                return jsonify({'valid': True, 'role': user.role})
        except Exception:
            pass
    
    return jsonify({'valid': False}), 401

@app.after_request
def add_header(response):
    if request.path not in ['/static']:  # Don't add headers for static files
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
    return response

@app.before_request
def before_request():
    if request.endpoint and request.endpoint != 'static':
        # Routes that don't need authentication
        public_routes = ['login', 'admin_login', 'register', 'static']
        
        if request.endpoint not in public_routes:
            # Check if it's an admin route
            if request.endpoint.startswith('admin_'):
                if 'admin_id' not in session:
                    return redirect(url_for('admin_login'))
                try:
                    admin = User.query.get(session['admin_id'])
                    if not admin or admin.role != 'admin':
                        session.clear()
                        return redirect(url_for('admin_login'))
                except Exception:
                    session.clear()
                    return redirect(url_for('admin_login'))
            # Regular route authentication
            elif 'user_id' not in session:
                return redirect(url_for('login'))
            else:
                try:
                    user = User.query.get(session['user_id'])
                    if not user:
                        session.clear()
                        return redirect(url_for('login'))
                except Exception:
                    session.clear()
                    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5500, debug=True)