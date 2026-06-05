from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User, Invite
from app import bcrypt

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/confirm/<token>")
def confirm_email(token):
    """Confirm email address via token link."""
    from app.models import User
    user = User.query.filter_by(confirm_token=token).first()

    if not user:
        flash("Invalid confirmation link.", "danger")
        return redirect(url_for("auth.login"))

    if not user.confirm_token_valid():
        flash(
            "This confirmation link has expired. "
            "Please contact support for a new link.",
            "warning"
        )
        return redirect(url_for("auth.login"))

    user.email_confirmed      = True
    user.confirm_token        = None
    user.confirm_token_expires = None
    db.session.commit()

    flash(
        "Email confirmed! You can now log in.",
        "success"
    )
    return redirect(url_for("auth.login") + "?next=/welcome")


@auth_bp.route("/home")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("main.landing"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Public registration is disabled — redirect to login."""
    flash("Registration is by invitation only. Please contact the administrator.", "warning")
    return redirect(url_for("auth.login"))


@auth_bp.route("/register/<token>", methods=["GET", "POST"])
def register_with_token(token):
    """Invite-only registration. Token must be valid and unused."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    invite = Invite.query.filter_by(token=token).first()

    if not invite or not invite.is_valid():
        flash("This invite link is invalid or has expired. Please request a new one.", "danger")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        name     = request.form.get("name",     "").strip()
        email    = request.form.get("email",    "").strip().lower()
        password = request.form.get("password", "").strip()
        confirm  = request.form.get("confirm",  "").strip()

        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("register.html", invite=invite)

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("register.html", invite=invite)

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "danger")
            return render_template("register.html", invite=invite)

        if User.query.filter_by(email=email).first():
            flash("That email is already registered. Please log in.", "warning")
            return redirect(url_for("auth.login"))

        # Create the user
        hashed = bcrypt.generate_password_hash(password).decode("utf-8")
        user   = User(name=name, email=email, password=hashed)
        user.start_trial()
        db.session.add(user)
        db.session.flush()  # Get user.id before commit

        # Mark invite as used
        from datetime import datetime, timezone
        invite.used_at = datetime.now(timezone.utc)
        invite.used_by = user.id
        db.session.commit()

        flash("Account created! Please log in.", "success")
        return redirect(url_for("auth.login") + "?next=/welcome")

    return render_template("register.html", invite=invite)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email    = request.form.get("email",    "").strip().lower()
        password = request.form.get("password", "").strip()
        remember = request.form.get("remember") == "on"

        user = User.query.filter_by(email=email).first()

        if not user or not bcrypt.check_password_hash(user.password, password):
            flash("Invalid email or password.", "danger")
            return render_template("login.html")

        if not user.is_active:
            if user.subscription_status == "deactivated":
                flash(
                    "Your account is deactivated. "
                    "Please reactivate to continue.",
                    "warning"
                )
            else:
                flash(
                    "Your account has been disabled. "
                    "Please contact the administrator.",
                    "warning"
                )
            return render_template("login.html")

        if not user.email_confirmed:
            flash(
                "Please confirm your email address before logging in. "
                "Check your inbox for the confirmation link.",
                "warning"
            )
            return render_template("login.html")

        login_user(user, remember=remember)
        flash(f"Welcome back, {user.name}!", "success")
        next_page = request.args.get("next")
        return redirect(next_page or url_for("main.dashboard"))

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user  = User.query.filter_by(email=email).first()

        if user and user.is_active:
            token     = user.generate_reset_token()
            db.session.commit()
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            from app.email import send_reset_email
            send_reset_email(user, reset_url)

        flash("If that email is registered you will receive a reset link shortly.", "info")
        return redirect(url_for("auth.login"))

    return render_template("forgot_password.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    user = User.query.filter_by(reset_token=token).first()

    if not user or not user.reset_token_valid():
        flash("This reset link is invalid or has expired.", "danger")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "").strip()
        confirm  = request.form.get("confirm",  "").strip()

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "danger")
            return render_template("reset_password.html", token=token)

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("reset_password.html", token=token)

        user.password            = bcrypt.generate_password_hash(password).decode("utf-8")
        user.reset_token         = None
        user.reset_token_expires = None
        db.session.commit()

        flash("Password updated. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html", token=token)
