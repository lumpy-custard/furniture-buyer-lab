import secrets
from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from . import db, login_manager
from .models import User, BankAccount

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

RESET_TOKEN_VALID_MINUTES = 60


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.assistant_home"))

    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("main.assistant_home"))

        flash("Invalid email or password.")

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.assistant_home"))

    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        if User.query.filter_by(email=email).first():
            flash("Email already registered.")
            return render_template("register.html")

        user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
        )
        db.session.add(user)
        db.session.commit()

        account = BankAccount(user_id=user.id)
        db.session.add(account)
        db.session.commit()

        login_user(user)
        return redirect(url_for("main.assistant_home"))

    return render_template("register.html")


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("main.assistant_home"))

    if request.method == "POST":
        email = request.form["email"].strip().lower()
        user = User.query.filter_by(email=email).first()

        if user:
            user.reset_token = secrets.token_urlsafe(32)
            user.reset_token_expires_at = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_VALID_MINUTES)
            db.session.commit()

            reset_url = url_for("auth.reset_password", token=user.reset_token, _external=True)
            # No email provider is configured yet, so the reset link is surfaced directly
            # here instead of being emailed.
            print(f"Password reset link for {user.email}: {reset_url}")
            flash(f"Password reset link (no email is configured): {reset_url}")
        else:
            flash("If that email is registered, a reset link has been generated.")

        return redirect(url_for("auth.forgot_password"))

    return render_template("forgot_password.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("main.assistant_home"))

    user = User.query.filter_by(reset_token=token).first()
    if not user or not user.reset_token_expires_at or user.reset_token_expires_at < datetime.utcnow():
        flash("That reset link is invalid or has expired.")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        if password != confirm_password:
            flash("Passwords do not match.")
            return render_template("reset_password.html", token=token)

        user.password_hash = generate_password_hash(password)
        user.reset_token = None
        user.reset_token_expires_at = None
        db.session.commit()

        flash("Your password has been reset. Please log in.")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html", token=token)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
