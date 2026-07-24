from urllib.parse import urljoin, urlparse

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from forms import LoginForm
from models import User


auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/auth",
)


def is_safe_redirect_url(target: str) -> bool:
    """Allow redirects only to pages within this application."""
    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))

    return (
        redirect_url.scheme in {"http", "https"}
        and host_url.netloc == redirect_url.netloc
    )


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate admin, teacher, or student accounts."""
    if current_user.is_authenticated:
        return redirect(
            url_for(current_user.get_dashboard_endpoint())
        )

    form = LoginForm()

    if form.validate_on_submit():
        username = form.username.data.strip()

        user = User.query.filter_by(
            username=username,
        ).first()

        if user is None or not user.check_password(form.password.data):
            flash(
                "Invalid username or password.",
                "danger",
            )
            return render_template(
                "login.html",
                form=form,
            )

        if not user.is_active:
            flash(
                "Your account is inactive. Contact the administrator.",
                "warning",
            )
            return render_template(
                "login.html",
                form=form,
            )

        login_user(
            user,
            remember=form.remember_me.data,
        )

        flash(
            f"Login successful. Welcome, {user.username}.",
            "success",
        )

        next_page = request.args.get("next")

        if next_page and is_safe_redirect_url(next_page):
            return redirect(next_page)

        return redirect(
            url_for(user.get_dashboard_endpoint())
        )

    return render_template(
        "login.html",
        form=form,
    )


@auth_bp.post("/logout")
def logout():
    """End the current login session."""
    if current_user.is_authenticated:
        logout_user()
        flash(
            "You have been logged out successfully.",
            "success",
        )

    return redirect(url_for("auth.login"))