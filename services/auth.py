"""Authentication service for multi-user support."""

from functools import wraps
from flask import session, redirect, url_for, request
from typing import Optional, Dict, List
from db.models import users_collection, laws_collection, LAW_TYPES
from datetime import datetime


def get_current_user() -> Optional[str]:
    """
    Return user_id from session, or None if not logged in.
    
    Returns:
        str: user_id if logged in, None otherwise
    """
    return session.get('user_id')


def get_current_user_info() -> Optional[Dict]:
    """
    Return full user info dict from session.
    
    Returns:
        dict: User info with keys: user_id, username, display_name
        None: If not logged in
    """
    if 'user_id' not in session:
        return None
    
    return {
        'user_id': session['user_id'],
        'username': session['username'],
        'display_name': session['display_name']
    }


def login_required(f):
    """
    Decorator to require login for protected routes.
    Redirects to login page if not authenticated.
    Preserves the original URL to redirect back after login.
    
    Usage:
        @app.route('/protected')
        @login_required
        def protected_route():
            return "You are logged in"
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # Save the URL user was trying to access
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def validate_user(username: str) -> Optional[Dict]:
    """
    Validate username exists in database.
    
    Args:
        username: Username to validate
        
    Returns:
        dict: User document if valid, None if not found
    """
    user = users_collection.find_one({'username': username})
    return user


def create_session(user: Dict) -> None:
    """
    Create a Flask session for the authenticated user.
    Updates last_login timestamp in database.
    
    Args:
        user: User document from database
    """
    session['user_id'] = str(user['_id'])
    session['username'] = user['username']
    session['display_name'] = user['display_name']
    
    # Update last_login timestamp
    users_collection.update_one(
        {'_id': user['_id']},
        {'$set': {'last_login': datetime.utcnow()}}
    )


def clear_session() -> None:
    """Clear the current Flask session (logout)."""
    session.clear()


# ============================================================================
# Law Type Management (NEW for multi-law support)
# ============================================================================

def get_current_law_type() -> str:
    """
    Get current law type from session, default to patent-act.
    
    Returns:
        str: Current law type (e.g., "patent-act")
    """
    return session.get('current_law_type', 'patent-act')


def set_current_law_type(law_type: str) -> bool:
    """
    Set current law type in session.
    
    Args:
        law_type: Law type to set (must be valid type in LAW_TYPES)
        
    Returns:
        bool: True if successful, False if invalid law type
    """
    if law_type not in LAW_TYPES:
        return False
    
    session['current_law_type'] = law_type
    return True


def get_available_law_types() -> List[Dict]:
    """
    Get list of available law types with article counts.
    
    Returns:
        list: List of dicts with keys: type, name_zh, name_en, count_zh_tw, count_en
        
    Example:
        [
            {
                "type": "patent-act",
                "name_zh": "專利法",
                "name_en": "Patent Law",
                "count_zh_tw": 168,
                "count_en": 168
            }
        ]
    """
    result = []
    
    for law_type, info in LAW_TYPES.items():
        # Count articles for this law type
        count_zh_tw = laws_collection.count_documents({
            "type": law_type,
            "lang": "zh-TW"
        })
        count_en = laws_collection.count_documents({
            "type": law_type,
            "lang": "en"
        })
        
        result.append({
            "type": law_type,
            "name_zh": info["name_zh"],
            "name_en": info["name_en"],
            "count_zh_tw": count_zh_tw,
            "count_en": count_en,
            "total": count_zh_tw + count_en
        })
    
    return result
