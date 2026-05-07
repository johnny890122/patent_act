"""
Frontend Routes - Serves HTML templates for the web interface.
All routes require authentication (multi-user support).
"""
from flask import Blueprint, render_template
from services.auth import login_required

frontend_bp = Blueprint('frontend', __name__)


@frontend_bp.route('/')
@login_required
def dashboard():
    """
    S-01 Home / Dashboard
    Entry point showing streak, starred laws count, and quick actions.
    Requires authentication.
    """
    return render_template('dashboard.html')


@frontend_bp.route('/laws')
@login_required
def laws_browser():
    """
    S-07 Law Article Browser
    Paginated list of all law articles with search and filter capabilities.
    Requires authentication.
    """
    return render_template('laws.html')


@frontend_bp.route('/laws/<law_id>')
@login_required
def law_detail(law_id):
    """
    S-08 Law Article Detail
    Single article view with question history and related questions.
    Requires authentication.
    """
    return render_template('law_detail.html', law_id=law_id)


@frontend_bp.route('/quiz/config')
@login_required
def quiz_config():
    """
    S-02 Quiz Config
    Configuration page for starting a new quiz session.
    Requires authentication.
    """
    return render_template('quiz_config.html')


@frontend_bp.route('/quiz/session/<session_id>')
@login_required
def quiz_session(session_id):
    """
    S-04, S-05 Quiz Session
    Question display and answer submission page.
    Handles both MCQ and Short Answer question types.
    Requires authentication.
    """
    return render_template('quiz_session.html')


@frontend_bp.route('/my-questions')
@login_required
def my_questions():
    """
    My Questions Page
    Display starred questions and wrong answers with tab switching.
    Requires authentication.
    """
    return render_template('my_questions.html')
