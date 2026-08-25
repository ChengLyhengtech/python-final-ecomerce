import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from models import db, User
from upload_config import save_uploaded_file
from auth_decorators import login_required, admin_required

user_bp = Blueprint('admin_user', __name__, url_prefix='/admin')


@user_bp.route('/users')
@login_required
@admin_required
def admin_users():
    users = User.query.order_by(User.id.desc()).all()
    return render_template('admin/users.html', users=users)


@user_bp.route('/users/<int:user_id>')
@login_required
@admin_required
def user_details(user_id):
    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin_user.admin_users'))

    return render_template('admin/user_detail.html', user=user)


@user_bp.route('/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        phone_number = request.form.get('phone_number', '').strip()
        role = request.form.get('role', 'user')

        if not username or not email or not password:
            flash('Username, Email, and Password are required.', 'danger')
            return render_template('admin/add_user.html')

        # Check for duplicates
        if User.query.filter_by(username=username).first():
            flash(f'Username "{username}" is already taken.', 'danger')
            return render_template('admin/add_user.html')

        if User.query.filter_by(email=email).first():
            flash(f'Email "{email}" is already registered.', 'danger')
            return render_template('admin/add_user.html')

        try:
            # Handle file upload using reusable helper
            profile_file = request.files.get('profile')
            upload_folder = current_app.config.get('UPLOAD_FOLDER')
            filename = save_uploaded_file(profile_file, upload_folder=upload_folder, default_filename='no-profile.png')

            new_user = User(
                username=username,
                email=email,
                phone_number=phone_number,
                role=role,
                profile_image=filename
            )
            # Hash password securely
            new_user.set_password(password)

            db.session.add(new_user)
            db.session.commit()

            flash(f'User "{username}" created successfully with role "{role}"!', 'success')
            return redirect(url_for('admin_user.admin_users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding user: {str(e)}', 'danger')

    return render_template('admin/add_user.html')


@user_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin_user.admin_users'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        phone_number = request.form.get('phone_number', '').strip()
        role = request.form.get('role', user.role)

        if not username or not email:
            flash('Username and email are required.', 'danger')
            return render_template('admin/edit_user.html', user=user)

        # Check duplicate username/email excluding current user
        existing_user = User.query.filter(User.username == username, User.id != user_id).first()
        if existing_user:
            flash(f'Username "{username}" is already in use by another account.', 'danger')
            return render_template('admin/edit_user.html', user=user)

        existing_email = User.query.filter(User.email == email, User.id != user_id).first()
        if existing_email:
            flash(f'Email "{email}" is already in use by another account.', 'danger')
            return render_template('admin/edit_user.html', user=user)

        try:
            profile_file = request.files.get('profile')
            upload_folder = current_app.config.get('UPLOAD_FOLDER')

            # Returns None if no new image was selected
            filename = save_uploaded_file(profile_file, upload_folder=upload_folder)

            if filename:
                # Remove old image file if it's not the default placeholder
                if user.profile_image and user.profile_image != 'no-profile.png':
                    old_path = os.path.join(upload_folder, user.profile_image)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                user.profile_image = filename

            user.username = username
            user.email = email
            user.phone_number = phone_number
            user.role = role

            # Update password only if a new one was provided
            if password.strip():
                user.set_password(password.strip())

            db.session.commit()

            # If editing own profile, update session as well
            if session.get('user_id') == user.id:
                session['username'] = user.username
                session['email'] = user.email
                session['role'] = user.role
                session['profile_image'] = user.profile_image

            flash(f'User "{username}" updated successfully!', 'success')
            return redirect(url_for('admin_user.admin_users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating user: {str(e)}', 'danger')

    return render_template('admin/edit_user.html', user=user)


@user_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get(user_id)
    if user:
        if session.get('user_id') == user.id:
            flash('You cannot delete your own logged-in account.', 'warning')
            return redirect(url_for('admin_user.admin_users'))

        try:
            # Check and delete the profile image if it exists and is not the default
            upload_folder = current_app.config.get('UPLOAD_FOLDER')
            if user.profile_image and user.profile_image != 'no-profile.png':
                file_path = os.path.join(upload_folder, user.profile_image)
                if os.path.exists(file_path):
                    os.remove(file_path)

            db.session.delete(user)
            db.session.commit()
            flash(f'User "{user.username}" deleted successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error deleting user: {str(e)}', 'danger')
    else:
        flash('User not found.', 'danger')

    return redirect(url_for('admin_user.admin_users'))
