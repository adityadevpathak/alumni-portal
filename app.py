from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import pytz
india = pytz.timezone('Asia/Kolkata')


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Database setup
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_FOLDER = os.path.join(BASE_DIR, 'instance')
if not os.path.exists(DB_FOLDER):
    os.makedirs(DB_FOLDER)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(DB_FOLDER, 'alumni.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ---------------------------
# Database Models
# ---------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    batch = db.Column(db.String(20))
    company = db.Column(db.String(150))
    role = db.Column(db.String(150))
    profile_image = db.Column(db.String(200), default="default.jpg")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(india))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(india))

    user = db.relationship('User', backref=db.backref('posts', lazy=True))

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(india))

    user = db.relationship('User', backref=db.backref('user_likes', lazy=True))
    post = db.relationship('Post', backref=db.backref('post_likes', lazy=True))

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    comment_text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(india))

    user = db.relationship('User', backref=db.backref('comments', lazy=True))
    post = db.relationship('Post', backref=db.backref('comments', lazy=True))


# ---------------------------
# Helper Function
# ---------------------------
def current_user():
    user_id = session.get('user_id')
    if user_id:
        return User.query.get(user_id)
    return None

# ---------------------------
# Routes
# ---------------------------
@app.route('/')
def index():
    posts = Post.query.order_by(Post.timestamp.desc()).limit(50).all()
    return render_template('index.html', posts=posts, user=current_user())

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        batch = request.form.get('batch')
        company = request.form.get('company')

        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please login or use another email.')
            return redirect(url_for('register'))

        user = User(name=name, email=email, batch=batch, company=company)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            flash('Logged in successfully.')
            return redirect(url_for('index'))
        flash('Invalid credentials. Please try again.')
        return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully.')
    return redirect(url_for('index'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    user = current_user()
    if not user:
        flash('Please login to access your profile.')
        return redirect(url_for('login'))

    if request.method == 'POST':
        user.name = request.form.get('name')
        user.batch = request.form.get('batch')
        user.company = request.form.get('company')
        user.role = request.form.get('role')
        db.session.commit()
        flash('Profile updated successfully.')
        return redirect(url_for('profile'))

    return render_template('profile.html', user=user)

@app.route('/search', methods=['GET', 'POST'])
def search():
    results = []
    if request.method == 'POST':
        q_name = request.form.get('name')
        q_batch = request.form.get('batch')
        q_company = request.form.get('company')

        query = User.query
        if q_name:
            query = query.filter(User.name.ilike(f"%{q_name}%"))
        if q_batch:
            query = query.filter_by(batch=q_batch)
        if q_company:
            query = query.filter(User.company.ilike(f"%{q_company}%"))

        results = query.all()

    return render_template('search.html', results=results)

@app.route('/create_post', methods=['POST'])
def create_post():
    user = current_user()
    if not user:
        flash('Please login to post.')
        return redirect(url_for('login'))

    content = request.form.get('content')
    if content:
        p = Post(user_id=user.id, content=content)
        db.session.add(p)
        db.session.commit()
        flash('Post created successfully.')

    return redirect(url_for('index'))

@app.route('/init_sample')
def init_sample():
    with app.app_context():
        db.create_all()
        if not User.query.first():
            u = User(name='Sample Alumni', email='sample@example.com', batch='2020', company='ABC Corp')
            u.set_password('password')
            db.session.add(u)
            db.session.commit()
            return 'Sample user created: sample@example.com / password'
        return 'Database already initialized.'

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
