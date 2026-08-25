from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import db, User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        next_url = request.args.get('next') or request.form.get('next')

        if not identifier or not password:
            flash('Please provide both username/email and password.', 'warning')
            return render_template('customer/share/login.html', next=next_url)

        # Allow login by username OR email
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

        if user and user.check_password(password):
            # Save authenticated user details to session
            session.clear()
            session['user_id'] = user.id
            session['username'] = user.username
            session['email'] = user.email
            session['role'] = user.role
            session['profile_image'] = user.profile_image or 'no-profile.png'

            flash(f'Welcome back, {user.username}!', 'success')

            # Redirect to next URL if provided and safe
            if next_url and next_url.startswith('/'):
                return redirect(next_url)

            # Redirect admin and staff users directly to dashboard, otherwise home
            if user.can_access_admin():
                return redirect(url_for('admin_dashboard.admin_dashboard'))
            return redirect(url_for('customer.home'))
        else:
            flash('Invalid username/email or password.', 'danger')
            return render_template('customer/share/login.html', next=next_url)

    # GET request: if already logged in, redirect
    if session.get('user_id'):
        if (session.get('role') or '').lower() in ['admin', 'staff', 'editor']:
            return redirect(url_for('admin_dashboard.admin_dashboard'))
        return redirect(url_for('customer.home'))

    next_url = request.args.get('next', '')
    return render_template('customer/share/login.html', next=next_url)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not username or not email or not password:
            flash('All fields are required.', 'warning')
            return render_template('customer/share/register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('customer/share/register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'warning')
            return render_template('customer/share/register.html')

        if User.query.filter_by(username=username).first():
            flash('Username is already taken. Please choose another.', 'danger')
            return render_template('customer/share/register.html')

        if User.query.filter_by(email=email).first():
            flash('Email address is already registered. Please log in.', 'danger')
            return render_template('customer/share/register.html')

        try:
            new_user = User(
                username=username,
                email=email,
                role='user',
                profile_image='no-profile.png'
            )
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()

            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred during registration: {str(e)}', 'danger')
            return render_template('customer/share/register.html')

    # GET request
    if session.get('user_id'):
        return redirect(url_for('customer.home'))
    return render_template('customer/share/register.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))
