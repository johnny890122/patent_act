"""
Quiz Routes - Handles quiz session management, answer submission, and appeals.
Multi-user support: All routes require authentication and filter by user_id.
"""
import os
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from bson import ObjectId
from db.models import (
    questions_collection,
    user_progress_collection,
    user_law_stats_collection,
    user_question_stars_collection,
    laws_collection,
    db
)
from services.inventory import QuestionInventory
from services.grader import Grader
from services.auth import login_required, get_current_user, get_current_law_type

logger = logging.getLogger(__name__)

quiz_bp = Blueprint('quiz', __name__, url_prefix='/api/quiz')

# Initialize services
api_key = os.environ.get('OPENROUTER_API_KEY')
inventory_service = QuestionInventory(api_key=api_key)
grader_service = Grader(api_key=api_key)

# Sessions collection
sessions_collection = db.db['sessions']


@quiz_bp.route('/available', methods=['GET'])
@login_required
def check_available_questions():
    """
    Check how many questions are available for the current user.
    Requires authentication.
    
    Query Parameters:
        type: "MCQ" | "ShortAnswer" | "Mixed"
        mode: "new" | "review" | "mixed"
    
    Response:
        {
            "available": int
        }
    """
    try:
        # Get current user (convert string to ObjectId for DB queries)
        user_id_str = get_current_user()
        if not user_id_str:
            return jsonify({"error": "Not authenticated"}), 401
        user_id = ObjectId(user_id_str)
        
        question_type = request.args.get('type')
        session_mode = request.args.get('mode')
        
        # Validate parameters
        if not question_type or question_type not in ['MCQ', 'ShortAnswer', 'Mixed']:
            return jsonify({"error": "Invalid or missing 'type'. Must be MCQ, ShortAnswer, or Mixed"}), 400
        
        if not session_mode or session_mode not in ['new', 'review', 'mixed']:
            return jsonify({"error": "Invalid or missing 'mode'. Must be new, review, or mixed"}), 400
        
        # Count available questions for this user
        lang = request.args.get('lang', 'zh-TW')
        if lang not in ['zh-TW', 'en', 'both']:
            return jsonify({"error": "Invalid 'lang'. Must be 'zh-TW', 'en', or 'both'"}), 400
        
        # Get law type (NEW for multi-law support)
        law_type = request.args.get('law_type') or get_current_law_type()

        available = inventory_service.count_available_questions(
            question_type=question_type,
            session_mode=session_mode,
            lang=lang,
            user_id=user_id,
            law_type=law_type
        )
        
        logger.info(f"User {user_id}: Available questions check: type={question_type}, mode={session_mode}, available={available}")
        
        return jsonify({"available": available}), 200
        
    except Exception as e:
        logger.error(f"Error checking available questions: {e}")
        return jsonify({"error": "Internal server error"}), 500


@quiz_bp.route('/session', methods=['POST'])
@login_required
def create_session():
    """
    Start a new quiz session for the current user.
    Requires authentication.
    
    Request Body:
        {
            "type": "MCQ" | "ShortAnswer" | "Mixed",
            "mode": "new" | "review" | "mixed",
            "count": int (number of questions)
        }
    
    Response:
        {
            "session_id": str,
            "questions": [...],
            "is_loading": bool (true if had to generate synchronously)
        }
    """
    try:
        # Get current user (convert string to ObjectId for DB queries)
        user_id_str = get_current_user()
        if not user_id_str:
            return jsonify({"error": "Not authenticated"}), 401
        user_id = ObjectId(user_id_str)
        
        data = request.get_json()
        
        # Validate required fields
        question_type = data.get('type')
        session_mode = data.get('mode')
        count = data.get('count')
        
        if not question_type or question_type not in ['MCQ', 'ShortAnswer', 'Mixed']:
            return jsonify({"error": "Invalid or missing 'type'. Must be MCQ, ShortAnswer, or Mixed"}), 400
        
        if not session_mode or session_mode not in ['new', 'review', 'mixed']:
            return jsonify({"error": "Invalid or missing 'mode'. Must be new, review, or mixed"}), 400
        
        if not count or not isinstance(count, int) or count <= 0:
            return jsonify({"error": "Invalid or missing 'count'. Must be a positive integer"}), 400
        # Language selection (optional)
        lang = data.get('lang', 'zh-TW')
        if lang not in ['zh-TW', 'en', 'both']:
            return jsonify({"error": "Invalid 'lang'. Must be 'zh-TW', 'en', or 'both'"}), 400
        
        # Get law type (NEW for multi-law support)
        law_type = data.get('law_type') or get_current_law_type()

        # Get questions using inventory service (pass user_id and law_type)
        questions, is_loading = inventory_service.get_session_questions(
            question_type=question_type,
            session_mode=session_mode,
            count=count,
            lang=lang,
            user_id=user_id,
            law_type=law_type
        )
        
        if not questions:
            return jsonify({"error": "Unable to fetch questions. Please try again later."}), 503
        
        # Create session document (include user_id and law_type)
        session_doc = {
            "user_id": user_id,
            "type": question_type,
            "mode": session_mode,
            "law_type": law_type,  # NEW: Store law type with session
            "question_ids": [q["_id"] for q in questions],
            "answers": [],  # Will be populated as user submits answers
            "created_at": datetime.utcnow(),
            "status": "active"
        }
        
        session_result = sessions_collection.insert_one(session_doc)
        session_id = str(session_result.inserted_id)
        
        # Prepare questions for response (remove sensitive data like correct_answer)
        safe_questions = []
        for q in questions:
            safe_q = {
                "_id": q["_id"],
                "type": q["type"],
                "content": q["content"],
                "law_id": q["law_id"]
            }
            # include language metadata if present
            if q.get('lang'):
                safe_q['lang'] = q.get('lang')
            # Include options for MCQ
            if q["type"] == "MCQ" and "options" in q:
                safe_q["options"] = q["options"]
            safe_questions.append(safe_q)
        
        logger.info(f"User {user_id}: Created session {session_id} with {len(questions)} questions")
        
        return jsonify({
            "session_id": session_id,
            "questions": safe_questions,
            "is_loading": is_loading
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        return jsonify({"error": "Internal server error"}), 500


@quiz_bp.route('/session/<session_id>/answer', methods=['POST'])
@login_required
def submit_answer(session_id):
    """
    Submit an answer for a question in the current user's session.
    Requires authentication.
    
    Request Body:
        {
            "question_id": str,
            "user_answer": str
        }
    
    Response:
        {
            "answer_id": str,
            "score": float (0, 0.5, or 1),
            "feedback": str (for ShortAnswer),
            "correct_answer": str,
            "ai_explanation": str
        }
    """
    try:
        # Get current user (convert string to ObjectId for DB queries)
        user_id_str = get_current_user()
        if not user_id_str:
            return jsonify({"error": "Not authenticated"}), 401
        user_id = ObjectId(user_id_str)
        
        data = request.get_json()
        question_id = data.get('question_id')
        user_answer = data.get('user_answer')
        
        if not question_id or not user_answer:
            return jsonify({"error": "Missing question_id or user_answer"}), 400
        
        # Validate session exists and belongs to current user
        try:
            session = sessions_collection.find_one({
                "_id": ObjectId(session_id),
                "user_id": user_id
            })
        except:
            return jsonify({"error": "Invalid session_id format"}), 400
        
        if not session:
            return jsonify({"error": "Session not found or access denied"}), 404
        
        if session.get('status') != 'active':
            return jsonify({"error": "Session is not active"}), 400
        
        # Validate question belongs to session
        if question_id not in session.get('question_ids', []):
            return jsonify({"error": "Question does not belong to this session"}), 400
        
        # Get question details
        try:
            question = questions_collection.find_one({"_id": ObjectId(question_id)})
        except:
            return jsonify({"error": "Invalid question_id format"}), 400
        
        if not question:
            return jsonify({"error": "Question not found"}), 404
        
        # Grade the answer
        score = 0.0
        feedback = ""
        
        if question['type'] == 'MCQ':
            # Extract option letter from user answer (e.g., "D. 文字..." -> "D")
            user_option = user_answer.strip()
            correct_option = question['correct_answer'].strip()
            
            # If user_answer contains a dot, extract the letter before it
            if '.' in user_option:
                user_option = user_option.split('.')[0].strip()
            
            # If correct_answer contains a dot, extract the letter before it
            if '.' in correct_option:
                correct_option = correct_option.split('.')[0].strip()
            
            # Compare the option letters (case-insensitive)
            if user_option.upper() == correct_option.upper():
                score = 1.0
                feedback = "答案正確！"
            else:
                score = 0.0
                feedback = f"答案錯誤。正確答案是：{question['correct_answer']}"
            
            # Find full option text for display (if correct_answer is just a letter)
            full_correct_answer = question['correct_answer']
            if question.get('options') and '.' not in full_correct_answer:
                # correct_answer is just a letter, find the full option
                for option in question['options']:
                    if option.strip().upper().startswith(full_correct_answer.upper() + '.'):
                        full_correct_answer = option
                        break
        
        elif question['type'] == 'ShortAnswer':
            # Use LLM grading for short answers
            try:
                # Get law content for context
                law = laws_collection.find_one({"_id": ObjectId(question['law_id'])})
                law_content = law['content'] if law else None
                
                grading_result = grader_service.grade_answer(
                    question=question['content'],
                    user_answer=user_answer,
                    correct_answer=question['correct_answer'],
                    law_content=law_content
                )
                score = grading_result['score']
                feedback = grading_result['feedback']
            except Exception as e:
                logger.error(f"Grading failed: {e}")
                return jsonify({"error": "Grading service unavailable"}), 503
        
        # Create answer document
        answer_doc = {
            "question_id": question_id,
            "user_answer": user_answer,
            "score": score,
            "feedback": feedback,
            "is_appealed": False,
            "submitted_at": datetime.utcnow()
        }
        
        # Update session with answer
        sessions_collection.update_one(
            {"_id": ObjectId(session_id)},
            {"$push": {"answers": answer_doc}}
        )
        
        # Update user progress (per-user)
        progress = user_progress_collection.find_one({
            "user_id": user_id,
            "question_id": question_id
        })
        
        if progress:
            # Update existing progress
            new_streak = progress.get('correct_streak', 0) + 1 if score >= 1.0 else 0
            needs_review = new_streak < 3  # Need to get it right 3 times in a row
            
            user_progress_collection.update_one(
                {
                    "user_id": user_id,
                    "question_id": question_id
                },
                {
                    "$set": {
                        "correct_streak": new_streak,
                        "needs_review": needs_review,
                        "last_score": score
                    }
                }
            )
        else:
            # Create new progress entry
            user_progress_collection.insert_one({
                "user_id": user_id,
                "question_id": question_id,
                "correct_streak": 1 if score >= 1.0 else 0,
                "needs_review": score < 1.0,
                "last_score": score,
                "is_appealed": False
            })
        
        # Update per-user law statistics
        law_id = question['law_id']
        user_law_stat = user_law_stats_collection.find_one({
            "user_id": user_id,
            "law_id": law_id
        })
        
        if user_law_stat:
            new_total = user_law_stat.get('total_score', 0.0) + score
            new_count = user_law_stat.get('attempt_count', 0) + 1
            new_avg = new_total / new_count
            
            user_law_stats_collection.update_one(
                {"user_id": user_id, "law_id": law_id},
                {
                    "$set": {
                        "total_score": new_total,
                        "attempt_count": new_count,
                        "avg_score": new_avg
                    }
                }
            )
        else:
            # Create new stat entry
            user_law_stats_collection.insert_one({
                "user_id": user_id,
                "law_id": law_id,
                "total_score": score,
                "attempt_count": 1,
                "avg_score": score
            })
        
        # Generate answer_id from the index in answers array
        answer_id = len(session.get('answers', []))
        
        logger.info(f"User {user_id}: Answer submitted for session {session_id}, question {question_id}, score: {score}")
        
        # Prepare correct_answer for response (use full option text for MCQ if available)
        display_correct_answer = question['correct_answer']
        if question['type'] == 'MCQ':
            display_correct_answer = full_correct_answer if 'full_correct_answer' in locals() else question['correct_answer']
        
        return jsonify({
            "answer_id": str(answer_id),
            "score": score,
            "feedback": feedback,
            "correct_answer": display_correct_answer,
            "ai_explanation": question['ai_explanation']
        }), 200
        
    except Exception as e:
        logger.error(f"Error submitting answer: {e}")
        return jsonify({"error": "Internal server error"}), 500


@quiz_bp.route('/session/<session_id>/answer/<answer_id>/appeal', methods=['POST'])
@login_required
def appeal_answer(session_id, answer_id):
    """
    Appeal a graded answer to reverse the score for the current user.
    Requires authentication.
    
    Response:
        {
            "message": str,
            "new_score": float,
            "is_appealed": bool
        }
    """
    try:
        # Get current user (convert string to ObjectId for DB queries)
        user_id_str = get_current_user()
        if not user_id_str:
            return jsonify({"error": "Not authenticated"}), 401
        user_id = ObjectId(user_id_str)
        
        # Validate and get session (must belong to user)
        try:
            session = sessions_collection.find_one({
                "_id": ObjectId(session_id),
                "user_id": user_id
            })
        except:
            return jsonify({"error": "Invalid session_id format"}), 400
        
        if not session:
            return jsonify({"error": "Session not found or access denied"}), 404
        
        # Get answer by index
        try:
            answer_idx = int(answer_id)
        except:
            return jsonify({"error": "Invalid answer_id format"}), 400
        
        answers = session.get('answers', [])
        if answer_idx < 0 or answer_idx >= len(answers):
            return jsonify({"error": "Answer not found"}), 404
        
        answer = answers[answer_idx]
        
        # Check if already appealed
        if answer.get('is_appealed', False):
            return jsonify({"error": "Answer has already been appealed"}), 400
        
        question_id = answer['question_id']
        old_score = answer['score']
        
        # Reverse the score logic: 0 -> 1, 0.5 -> 1, 1 -> 0
        new_score = 0.0 if old_score >= 1.0 else 1.0
        
        # Update answer in session
        sessions_collection.update_one(
            {"_id": ObjectId(session_id)},
            {
                "$set": {
                    f"answers.{answer_idx}.score": new_score,
                    f"answers.{answer_idx}.is_appealed": True,
                    f"answers.{answer_idx}.feedback": f"[已申訴] {answer['feedback']}"
                }
            }
        )
        
        # Update user progress (per-user)
        progress = user_progress_collection.find_one({
            "user_id": user_id,
            "question_id": question_id
        })
        if progress:
            # Recalculate streak/review based on new_score after appeal
            if new_score >= 1.0:
                new_streak = progress.get('correct_streak', 0) + 1
                needs_review = new_streak < 3
            else:
                new_streak = 0
                needs_review = True
            user_progress_collection.update_one(
                {
                    "user_id": user_id,
                    "question_id": question_id
                },
                {
                    "$set": {
                        "is_appealed": True,
                        "last_score": new_score,
                        "correct_streak": new_streak,
                        "needs_review": needs_review
                    }
                }
            )

        # Update per-user law statistics (adjust for score change)
        question = questions_collection.find_one({"_id": ObjectId(question_id)})
        if question:
            law_id = question['law_id']
            user_law_stat = user_law_stats_collection.find_one({
                "user_id": user_id,
                "law_id": law_id
            })
            if user_law_stat:
                score_diff = new_score - old_score
                new_total = user_law_stat.get('total_score', 0.0) + score_diff
                count = user_law_stat.get('attempt_count', 1)
                new_avg = new_total / count if count > 0 else 0
                
                user_law_stats_collection.update_one(
                    {"user_id": user_id, "law_id": law_id},
                    {
                        "$set": {
                            "total_score": new_total,
                            "avg_score": new_avg
                        }
                    }
                )
        
        logger.info(f"User {user_id}: Answer appealed for session {session_id}, answer {answer_id}, new score: {new_score}")
        
        return jsonify({
            "message": "申訴成功！分數已更新。",
            "new_score": new_score,
            "is_appealed": True
        }), 200
        
    except Exception as e:
        logger.error(f"Error appealing answer: {e}")
        return jsonify({"error": "Internal server error"}), 500


@quiz_bp.route('/questions/<question_id>', methods=['DELETE'])
@login_required
def delete_question(question_id):
    """
    Soft delete a question (mark as deleted).
    Requires authentication.
    
    Response:
        {
            "message": str
        }
    """
    try:
        # Validate and get question
        try:
            question = questions_collection.find_one({"_id": ObjectId(question_id)})
        except:
            return jsonify({"error": "Invalid question_id format"}), 400
        
        if not question:
            return jsonify({"error": "Question not found"}), 404
        
        # Check if already deleted
        if question.get('is_deleted', False):
            return jsonify({"error": "Question is already deleted"}), 400
        
        # Soft delete
        questions_collection.update_one(
            {"_id": ObjectId(question_id)},
            {"$set": {"is_deleted": True}}
        )
        
        logger.info(f"Question {question_id} soft deleted")
        
        return jsonify({
            "message": "題目已刪除"
        }), 200
        
    except Exception as e:
        logger.error(f"Error deleting question: {e}")
        return jsonify({"error": "Internal server error"}), 500


@quiz_bp.route('/questions/<question_id>/star', methods=['POST'])
@login_required
def toggle_star_question(question_id):
    """
    Toggle starred status for a question (per-user).
    Requires authentication.
    
    Response:
        {
            "is_starred": bool,
            "message": str
        }
    """
    try:
        # Get current user (convert string to ObjectId for DB queries)
        user_id_str = get_current_user()
        if not user_id_str:
            return jsonify({"error": "Not authenticated"}), 401
        user_id = ObjectId(user_id_str)
        
        # Validate question exists
        try:
            question = questions_collection.find_one({"_id": ObjectId(question_id)})
        except:
            return jsonify({"error": "Invalid question_id format"}), 400
        
        if not question:
            return jsonify({"error": "Question not found"}), 404
        
        # Check if user has starred this question
        existing_star = user_question_stars_collection.find_one({
            "user_id": user_id,
            "question_id": question_id
        })
        
        if existing_star:
            # Remove star
            user_question_stars_collection.delete_one({"_id": existing_star["_id"]})
            new_starred = False
            action = "取消收藏"
        else:
            # Add star
            user_question_stars_collection.insert_one({
                "user_id": user_id,
                "question_id": question_id,
                "created_at": datetime.utcnow()
            })
            new_starred = True
            action = "收藏"
        
        logger.info(f"User {user_id}: Question {question_id} starred status toggled to {new_starred}")
        
        return jsonify({
            "is_starred": new_starred,
            "message": f"已{action}題目"
        }), 200
        
    except Exception as e:
        logger.error(f"Error toggling star for question: {e}")
        return jsonify({"error": "Internal server error"}), 500
