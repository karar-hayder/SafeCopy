from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from safecopy.db.dtos.userDTOs import UserCreateDTO, UserUpdateDTO
from safecopy.db.services.userService import UserService
from safecopy.web.api_utils import standard_response

service = UserService()


def login_route():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = service.get_user_model_by_username(username)
        if user:
            is_match = user.check_password(password)
            if is_match:
                login_user(user)
                flash("Logged in successfully", "success")
                next_page = request.args.get("next") or url_for("index")
                return redirect(next_page)

        flash("Invalid username or password", "danger")

    return render_template("login.html")


@login_required
def logout_route():
    logout_user()
    flash("Logged out successfully", "success")
    return redirect(url_for("login"))


@login_required
def users_route():
    return render_template("users.html")


@login_required
def get_users():
    """Get all users."""
    try:
        users = service.get_all()
        data = {"users": [u.model_dump() for u in users]}
        return standard_response(
            True, message="Users retrieved successfully", data=data
        )
    except Exception as e:
        return standard_response(False, error=str(e), status_code=500)


@login_required
def create_user():
    """Create a new user."""
    try:
        data = request.get_json()
        dto = UserCreateDTO(**data)
        if service.register(dto):
            return standard_response(True, message="User created successfully")
        return standard_response(
            False, error="Username already exists", status_code=400
        )
    except Exception as e:
        return standard_response(False, error=str(e), status_code=500)


@login_required
def change_password():
    """Change current user password."""
    try:
        data = request.get_json()
        # Ensure we are changing password for the current user
        data["username"] = current_user.username
        dto = UserUpdateDTO(**data)
        if service.change_password(dto):
            return standard_response(True, message="Password changed successfully")
        return standard_response(
            False, error="Failed to change password", status_code=400
        )
    except Exception as e:
        return standard_response(False, error=str(e), status_code=500)
