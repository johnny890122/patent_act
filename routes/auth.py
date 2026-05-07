"""Authentication routes for multi-user support."""

from urllib.parse import urlparse, urljoin
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from services.auth import validate_user, create_session, clear_session, get_current_user_info


def _is_safe_redirect_url(target: str) -> bool:
    """Return True only if target is a relative URL on the same host."""
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET'])
def login():
    """Show login page."""
    # If already logged in, redirect to dashboard
    if get_current_user_info():
        return redirect(url_for('frontend.dashboard'))
    
    # Get the 'next' parameter to redirect after login (validate to prevent open redirect)
    next_param = request.args.get('next', '')
    next_url = next_param if next_param and _is_safe_redirect_url(next_param) else url_for('frontend.dashboard')
    return render_template('login.html', next_url=next_url)


@auth_bp.route('/login', methods=['POST'])
def login_post():
    """
    Handle login form submission.
    Validates username and creates session if valid.
    """
    username = request.form.get('username', '').strip()
    next_param = request.form.get('next', '')
    next_url = next_param if next_param and _is_safe_redirect_url(next_param) else url_for('frontend.dashboard')
    
    if not username:
        flash('請輸入用戶名稱', 'error')
        return redirect(url_for('auth.login', next=next_url))
    
    # Validate username
    user = validate_user(username)
    
    if not user:
        flash('用戶名稱不存在，請聯繫管理員', 'error')
        return redirect(url_for('auth.login', next=next_url))
    
    # Create session
    create_session(user)
    
    # Redirect to original URL or dashboard
    return redirect(next_url)


@auth_bp.route('/logout', methods=['POST', 'GET'])
def logout():
    """Clear session and redirect to login page."""
    clear_session()
    flash('已登出', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/current', methods=['GET'])
def current():
    """
    Return current logged-in user info as JSON.
    Useful for frontend checks.
    
    Returns:
        JSON: { user_id, username, display_name } if logged in
        JSON: { error: "Not authenticated" } with 401 if not logged in
    """
    user_info = get_current_user_info()
    
    if not user_info:
        return jsonify({'error': 'Not authenticated'}), 401
    
    return jsonify(user_info)
