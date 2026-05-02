"""
Quiz Routes - Handles quiz session management, answer submission, and appeals.
"""
import os
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from bson import ObjectId
from db.models import (
    questions_collection, 
    user_progress_collection,
    laws_collection,
    db
)
from services.inventory import QuestionInventory
from services.grader import Grader

logger = logging.getLogger(__name__)

quiz_bp = Blueprint('quiz', __name__, url_prefix='/api/quiz')

# Initialize services
api_key = os.environ.get('OPENROUTER_API_KEY')
inventory_service = QuestionInventory(api_key=api_key)
grader_service = Grader(api_key=api_key)

# Sessions collection
sessions_collection = db.db['sessions']


@quiz_bp.route('/available', methods=['GET'])
def check_available_questions():
    """
    Check how many questions are available for a given type and mode.
    
    Query Parameters:
        type: "MCQ" | "ShortAnswer" | "Mixed"
        mode: "new" | "review" | "mixed"
    
    Response:
        {
            "available": int
        }
    """
    try:
        question_type = request.args.get('type')
        session_mode = request.args.get('mode')
        
        # Validate parameters
        if not question_type or question_type not in ['MCQ', 'ShortAnswer', 'Mixed']:
            return jsonify({"error": "Invalid or missing 'type'. Must be MCQ, ShortAnswer, or Mixed"}), 400
        
        if not session_mode or session_mode not in ['new', 'review', 'mixed']:
            return jsonify({"error": "Invalid or missing 'mode'. Must be new, review, or mixed"}), 400
        
        # Count available questions
        available = inventory_service.count_available_questions(
            question_type=question_type,
            session_mode=session_mode
        )
        
        logger.info(f"Available questions check: type={question_type}, mode={session_mode}, available={available}")
        
        return jsonify({"available": available}), 200
        
    except Exception as e:
        logger.error(f"Error checking available questions: {e}")
        return jsonify({"error": "Internal server error"}), 500


@quiz_bp.route('/session', methods=['POST'])
def create_session():
    """
    Start a new quiz session.
    
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
        
        # Get questions using inventory service
        questions, is_loading = inventory_service.get_session_questions(
            question_type=question_type,
            session_mode=session_mode,
            count=count
        )
        
        if not questions:
            return jsonify({"error": "Unable to fetch questions. Please try again later."}), 503
        
        # Create session document
        session_doc = {
            "type": question_type,
            "mode": session_mode,
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
            # Include options for MCQ
            if q["type"] == "MCQ" and "options" in q:
                safe_q["options"] = q["options"]
            safe_questions.append(safe_q)
        
        logger.info(f"Created session {session_id} with {len(questions)} questions")
        
        return jsonify({
            "session_id": session_id,
            "questions": safe_questions,
            "is_loading": is_loading
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        return jsonify({"error": "Internal server error"}), 500


@quiz_bp.route('/session/<session_id>/answer', methods=['POST'])
def submit_answer(session_id):
    """
    Submit an answer for a question in a session.
    
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
        data = request.get_json()
        question_id = data.get('question_id')
        user_answer = data.get('user_answer')
        
        if not question_id or not user_answer:
            return jsonify({"error": "Missing question_id or user_answer"}), 400
        
        # Validate session exists
        try:
            session = sessions_collection.find_one({"_id": ObjectId(session_id)})
        except:
            return jsonify({"error": "Invalid session_id format"}), 400
        
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
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
        
        # Update user progress
        progress = user_progress_collection.find_one({"question_id": question_id})
        
        if progress:
            # Update existing progress
            new_streak = progress.get('correct_streak', 0) + 1 if score >= 1.0 else 0
            needs_review = new_streak < 3  # Need to get it right 3 times in a row
            
            user_progress_collection.update_one(
                {"question_id": question_id},
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
                "question_id": question_id,
                "correct_streak": 1 if score >= 1.0 else 0,
                "needs_review": score < 1.0,
                "last_score": score,
                "is_appealed": False
            })
        
        # Update law statistics
        law_id = question['law_id']
        law = laws_collection.find_one({"_id": ObjectId(law_id)})
        if law:
            new_total = law.get('total_score', 0.0) + score
            new_count = law.get('attempt_count', 0) + 1
            new_avg = new_total / new_count
            
            laws_collection.update_one(
                {"_id": ObjectId(law_id)},
                {
                    "$set": {
                        "total_score": new_total,
                        "attempt_count": new_count,
                        "avg_score": new_avg
                    }
                }
            )
        
        # Generate answer_id from the index in answers array
        answer_id = len(session.get('answers', []))
        
        logger.info(f"Answer submitted for session {session_id}, question {question_id}, score: {score}")
        
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
def appeal_answer(session_id, answer_id):
    """
    Appeal a graded answer to reverse the score.
    
    Response:
        {
            "message": str,
            "new_score": float,
            "is_appealed": bool
        }
    """
    try:
        # Validate and get session
        try:
            session = sessions_collection.find_one({"_id": ObjectId(session_id)})
        except:
            return jsonify({"error": "Invalid session_id format"}), 400
        
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
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
        
        # Update user progress
        progress = user_progress_collection.find_one({"question_id": question_id})
        if progress:
            user_progress_collection.update_one(
                {"question_id": question_id},
                {
                    "$set": {
                        "is_appealed": True,
                        "last_score": new_score
                    }
                }
            )
        
        # Update law statistics (adjust for score change)
        question = questions_collection.find_one({"_id": ObjectId(question_id)})
        if question:
            law_id = question['law_id']
            law = laws_collection.find_one({"_id": ObjectId(law_id)})
            if law:
                score_diff = new_score - old_score
                new_total = law.get('total_score', 0.0) + score_diff
                count = law.get('attempt_count', 1)
                new_avg = new_total / count if count > 0 else 0
                
                laws_collection.update_one(
                    {"_id": ObjectId(law_id)},
                    {
                        "$set": {
                            "total_score": new_total,
                            "avg_score": new_avg
                        }
                    }
                )
        
        logger.info(f"Answer appealed for session {session_id}, answer {answer_id}, new score: {new_score}")
        
        return jsonify({
            "message": "申訴成功！分數已更新。",
            "new_score": new_score,
            "is_appealed": True
        }), 200
        
    except Exception as e:
        logger.error(f"Error appealing answer: {e}")
        return jsonify({"error": "Internal server error"}), 500


@quiz_bp.route('/questions/<question_id>', methods=['DELETE'])
def delete_question(question_id):
    """
    Soft delete a question (mark as deleted).
    
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
def toggle_star_question(question_id):
    """
    Toggle starred status for a question.
    
    Response:
        {
            "is_starred": bool,
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
        
        # Toggle starred status
        current_starred = question.get('is_starred', False)
        new_starred = not current_starred
        
        questions_collection.update_one(
            {"_id": ObjectId(question_id)},
            {"$set": {"is_starred": new_starred}}
        )
        
        action = "收藏" if new_starred else "取消收藏"
        logger.info(f"Question {question_id} starred status toggled to {new_starred}")
        
        return jsonify({
            "is_starred": new_starred,
            "message": f"已{action}題目"
        }), 200
        
    except Exception as e:
        logger.error(f"Error toggling star for question: {e}")
        return jsonify({"error": "Internal server error"}), 500
