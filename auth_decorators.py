from functools import wraps
from flask import session, flash, redirect, url_for, request


def login_required(view):
    """
    Decorator to protect routes requiring an authenticated user.
    Saves next URL parameter so user can be redirected after successful login.
    """
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in first.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    """
    Decorator strictly requiring 'admin' role (e.g. for User Management).
    Redirects unauthenticated users to login, and unauthorized staff to admin dashboard.
    """
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in first.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        
        user_role = (session.get("role") or "").lower()
        if user_role != "admin":
            flash("Access denied. User Management is restricted to Administrators only.", "danger")
            # If they are staff/editor, redirect to dashboard, else home
            if user_role in ["staff", "editor"]:
                return redirect(url_for("admin_dashboard.admin_dashboard"))
            return redirect(url_for("customer.home"))
            
        return view(*args, **kwargs)

    return wrapped


def staff_required(view):
    """
    Decorator allowing both 'admin' and 'staff' (and 'editor') to access management panels.
    """
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in first.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        
        user_role = (session.get("role") or "").lower()
        if user_role not in ["admin", "staff", "editor"]:
            flash("Access denied. Staff or Admin privileges required.", "danger")
            return redirect(url_for("customer.home"))
            
        return view(*args, **kwargs)

    return wrapped


def role_required(*allowed_roles):
    """
    Decorator to protect routes requiring specific roles.
    Example: @role_required('admin', 'staff', 'editor')
    """
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                flash("Please log in first.", "warning")
                return redirect(url_for("auth.login", next=request.path))
            
            user_role = (session.get("role") or "").lower()
            normalized_roles = [r.lower() for r in allowed_roles]
            if user_role not in normalized_roles:
                flash("Access denied. You do not have permission to view this resource.", "danger")
                if user_role in ["admin", "staff", "editor"]:
                    return redirect(url_for("admin_dashboard.admin_dashboard"))
                return redirect(url_for("customer.home"))
                
            return view(*args, **kwargs)

        return wrapped
    return decorator
