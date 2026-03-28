from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User
from app import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('stocks.home'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        # Check if user exists AND password is correct
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Login Successful!', 'success')
            return redirect(url_for('stocks.home'))
        else:
            flash('Invalid email or password.', 'danger')
            
    return render_template('login.html')

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('stocks.home'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if email already exists
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists. Please log in.', 'warning')
            return redirect(url_for('auth.login'))
        
        # Create new user
        new_user = User(
            username=username, 
            email=email, 
            password_hash=generate_password_hash(password)
        )
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user)
        flash('Account created successfully!', 'success')
        return redirect(url_for('stocks.home'))

    return render_template('signup.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('stocks.home'))