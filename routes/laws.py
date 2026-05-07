"""
Laws Routes - Handles law article browsing and starring functionality.
Multi-user support: All routes require authentication and use per-user data.
"""
import logging
from flask import Blueprint, request, jsonify
from bson import ObjectId
from datetime import datetime
from db.models import (
    laws_collection,
    i18n_mapping_collection,
    user_law_stars_collection,
    user_law_stats_collection,
    user_question_stars_collection,
    questions_collection,
    user_progress_collection
)
from services.auth import login_required, get_current_user

logger = logging.getLogger(__name__)

laws_bp = Blueprint('laws', __name__, url_prefix='/api/laws')


@laws_bp.route('', methods=['GET'])
@login_required
def get_laws():
    """
    Get paginated list of law articles for the current user.
    Shows per-user starred status and statistics.
    Requires authentication.
    
    Query Parameters:
        page: int (default: 1)
        per_page: int (default: 10, max: 50)
        chapter: str (optional filter by chapter)
        starred: bool (optional filter by is_starred)
        sort: str (default: "article_number", options: "article_number", "avg_score", "attempt_count")
        order: str (default: "asc", options: "asc", "desc")
    
    Response:
        {
            "laws": [...],
            "total": int,
            "page": int,
            "per_page": int,
            "total_pages": int
        }
    """
    try:
        # Get current user
        user_id = get_current_user()
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
        
        # Get query parameters
        page = max(1, int(request.args.get('page', 1)))
        per_page = min(50, max(1, int(request.args.get('per_page', 10))))
        chapter = request.args.get('chapter')
        starred_param = request.args.get('starred')
        # Normalize language query param (accept zh-tw, zh-TW, en, both)
        req_lang = request.args.get('lang')
        lang = None
        if req_lang:
            nl = req_lang.lower()
            if nl in ['zh-tw', 'zh_tw', 'zh']:
                lang = 'zh-TW'
            elif nl in ['en', 'english']:
                lang = 'en'
            elif nl in ['both', 'all']:
                lang = None
        sort_field = request.args.get('sort', 'article_number_int')
        order = request.args.get('order', 'asc')
        
        # Build filter
        query_filter = {}
        if chapter:
            query_filter['chapter'] = chapter
        if lang in ['zh-TW', 'en']:
            query_filter['lang'] = lang
        
        # Validate sort field (保留 article_number 作為相容選項，但實際使用 article_number_int)
        valid_sort_fields = ['article_number', 'article_number_int', 'avg_score', 'attempt_count']
        if sort_field not in valid_sort_fields:
            sort_field = 'article_number_int'
        
        # 如果使用者指定 article_number，自動轉換為 article_number_int
        if sort_field == 'article_number':
            sort_field = 'article_number_int'
        
        # Sort direction
        sort_direction = 1 if order == 'asc' else -1
        
        # Get total count
        total = laws_collection.count_documents(query_filter)
        total_pages = (total + per_page - 1) // per_page
        
        # Get paginated results
        skip = (page - 1) * per_page
        
        # Handle starred filter for per-user stars
        if starred_param is not None:
            starred = starred_param.lower() in ['true', '1', 'yes']
            if starred:
                # Get user's starred law IDs
                user_stars = list(user_law_stars_collection.find({"user_id": user_id}))
                starred_law_ids = [ObjectId(s['law_id']) for s in user_stars]
                query_filter['_id'] = {'$in': starred_law_ids}
        
        laws = list(laws_collection.find(query_filter)
                   .sort(sort_field, sort_direction)
                   .skip(skip)
                   .limit(per_page))
        
        # Get user's starred laws and stats
        law_ids = [law['_id'] for law in laws]
        user_stars = list(user_law_stars_collection.find({
            "user_id": user_id,
            "law_id": {"$in": [str(lid) for lid in law_ids]}
        }))
        starred_law_ids_set = {s['law_id'] for s in user_stars}
        
        user_stats = list(user_law_stats_collection.find({
            "user_id": user_id,
            "law_id": {"$in": [str(lid) for lid in law_ids]}
        }))
        stats_map = {s['law_id']: s for s in user_stats}
        
        # Convert ObjectId to string and add per-user data
        for law in laws:
            law_id = str(law['_id'])
            law['_id'] = law_id
            # Add per-user starred status
            law['is_starred'] = law_id in starred_law_ids_set
            # Add per-user statistics
            if law_id in stats_map:
                stat = stats_map[law_id]
                law['total_score'] = stat.get('total_score', 0.0)
                law['attempt_count'] = stat.get('attempt_count', 0)
                law['avg_score'] = stat.get('avg_score', 0.0)
            else:
                law['total_score'] = 0.0
                law['attempt_count'] = 0
                law['avg_score'] = 0.0
        
        logger.info(f"Retrieved {len(laws)} laws (page {page}/{total_pages})")
        
        return jsonify({
            "laws": laws,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages
        }), 200
        
    except ValueError as e:
        return jsonify({"error": f"Invalid parameter: {e}"}), 400
    except Exception as e:
        logger.error(f"Error getting laws: {e}")
        return jsonify({"error": "Internal server error"}), 500


@laws_bp.route('/<law_id>', methods=['GET'])
@login_required
def get_law(law_id):
    """
    Get a single law article by ID with per-user data.
    Requires authentication.
    
    Response:
        {
            "_id": str,
            "article_number": str,
            "content": str,
            "chapter": str,
            "is_starred": bool,
            "total_score": float,
            "attempt_count": int,
            "avg_score": float
        }
    """
    try:
        # Get current user
        user_id = get_current_user()
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
        
        # Validate and get law
        try:
            law = laws_collection.find_one({"_id": ObjectId(law_id)})
        except:
            return jsonify({"error": "Invalid law_id format"}), 400

        if not law:
            return jsonify({"error": "Law not found"}), 404

        # Optional language switch: if client requests a different language, try to map
        req_lang = request.args.get('lang')
        if req_lang and req_lang in ['zh-TW', 'en'] and law.get('lang') != req_lang:
            # attempt to find mapping
            try:
                mapping = i18n_mapping_collection.find_one({
                    'zh_tw_law_id': law_id
                }) if law.get('lang') == 'zh-TW' else i18n_mapping_collection.find_one({'en_law_id': law_id})
                if mapping:
                    target_id = mapping['en_law_id'] if req_lang == 'en' else mapping['zh_tw_law_id']
                    try:
                        mapped_law = laws_collection.find_one({"_id": ObjectId(target_id)})
                        if mapped_law:
                            law = mapped_law
                    except:
                        pass
            except Exception:
                pass
        
        # Convert ObjectId to string
        law['_id'] = str(law['_id'])
        
        # Add per-user data
        user_star = user_law_stars_collection.find_one({
            "user_id": user_id,
            "law_id": law_id
        })
        law['is_starred'] = user_star is not None
        
        user_stat = user_law_stats_collection.find_one({
            "user_id": user_id,
            "law_id": law_id
        })
        if user_stat:
            law['total_score'] = user_stat.get('total_score', 0.0)
            law['attempt_count'] = user_stat.get('attempt_count', 0)
            law['avg_score'] = user_stat.get('avg_score', 0.0)
        else:
            law['total_score'] = 0.0
            law['attempt_count'] = 0
            law['avg_score'] = 0.0
        
        logger.info(f"User {user_id}: Retrieved law {law_id}")
        
        return jsonify(law), 200
        
    except Exception as e:
        logger.error(f"Error getting law: {e}")
        return jsonify({"error": "Internal server error"}), 500


@laws_bp.route('/<law_id>/star', methods=['PUT'])
@login_required
def toggle_star(law_id):
    """
    Toggle the starred status of a law article for the current user.
    Requires authentication.
    
    Response:
        {
            "message": str,
            "is_starred": bool
        }
    """
    try:
        # Get current user
        user_id = get_current_user()
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
        
        # Validate law exists
        try:
            law = laws_collection.find_one({"_id": ObjectId(law_id)})
        except:
            return jsonify({"error": "Invalid law_id format"}), 400
        
        if not law:
            return jsonify({"error": "Law not found"}), 404
        
        # Check if user has starred this law
        existing_star = user_law_stars_collection.find_one({
            "user_id": user_id,
            "law_id": law_id
        })
        
        if existing_star:
            # Remove star
            user_law_stars_collection.delete_one({"_id": existing_star["_id"]})
            new_starred = False
            action = "已移除"
        else:
            # Add star
            user_law_stars_collection.insert_one({
                "user_id": user_id,
                "law_id": law_id,
                "created_at": datetime.utcnow()
            })
            new_starred = True
            action = "已加入"
        
        logger.info(f"User {user_id}: Law {law_id} starred status changed to {new_starred}")
        
        return jsonify({
            "message": f"{action}收藏",
            "is_starred": new_starred
        }), 200
        
    except Exception as e:
        logger.error(f"Error toggling star: {e}")
        return jsonify({"error": "Internal server error"}), 500


@laws_bp.route('/chapters', methods=['GET'])
def get_chapters():
    """
    Get all chapters with law counts.
    
    Query Parameters:
        lang: str (optional) - Filter by language: "zh-TW" or "en"
    
    Response:
        {
            "chapters": [
                {
                    "name": str,
                    "count": int
                }
            ],
            "total": int
        }
    """
    try:
        # Get language filter
        req_lang = request.args.get('lang')
        lang = None
        if req_lang:
            nl = req_lang.lower()
            if nl in ['zh-tw', 'zh_tw', 'zh']:
                lang = 'zh-TW'
            elif nl in ['en', 'english']:
                lang = 'en'
        
        # Build filter
        query_filter = {}
        if lang in ['zh-TW', 'en']:
            query_filter['lang'] = lang
        
        # Aggregate chapters with counts
        pipeline = [
            {'$match': query_filter},
            {
                '$group': {
                    '_id': '$chapter',
                    'count': {'$sum': 1}
                }
            },
            {
                '$project': {
                    '_id': 0,
                    'name': '$_id',
                    'count': 1
                }
            },
            {'$sort': {'name': 1}}
        ]
        
        chapters = list(laws_collection.aggregate(pipeline))
        total = sum(chapter['count'] for chapter in chapters)
        
        logger.info(f"Retrieved {len(chapters)} chapters with total {total} laws")
        
        return jsonify({
            "chapters": chapters,
            "total": total
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting chapters: {e}")
        return jsonify({"error": "Internal server error"}), 500


@laws_bp.route('/stats', methods=['GET'])
@login_required
def get_stats():
    """
    Get overall statistics about laws for the current user.
    Requires authentication.
    
    Response:
        {
            "total_laws": int,
            "starred_count": int,
            "total_attempts": int,
            "average_score": float
        }
    """
    try:
        # Get current user
        user_id = get_current_user()
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
        
        # Get total count (global)
        total_laws = laws_collection.count_documents({})
        
        # Get user's starred count
        starred_count = user_law_stars_collection.count_documents({"user_id": user_id})
        
        # Calculate user's aggregate stats
        pipeline = [
            {"$match": {"user_id": user_id}},
            {
                "$group": {
                    "_id": None,
                    "total_attempts": {"$sum": "$attempt_count"},
                    "total_score": {"$sum": "$total_score"}
                }
            }
        ]
        
        agg_result = list(user_law_stats_collection.aggregate(pipeline))
        
        total_attempts = 0
        average_score = 0.0
        
        if agg_result:
            total_attempts = agg_result[0].get('total_attempts', 0)
            total_score = agg_result[0].get('total_score', 0.0)
            average_score = total_score / total_attempts if total_attempts > 0 else 0.0
        
        logger.info(f"User {user_id}: Retrieved stats: {total_laws} laws, {starred_count} starred")
        
        return jsonify({
            "total_laws": total_laws,
            "starred_count": starred_count,
            "total_attempts": total_attempts,
            "average_score": round(average_score, 2)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({"error": "Internal server error"}), 500


@laws_bp.route('/<law_id>/questions', methods=['GET'])
@login_required
def get_law_questions(law_id):
    """
    Get all answered questions for the current user related to a specific law article.
    Only returns questions that have user progress records (已作答過的題目).
    自動判斷答錯狀態：last_score < 0.7 視為答錯題
    Requires authentication.
    
    Response:
        {
            "questions": [...],  # 包含 is_marked_wrong (根據 last_score 自動計算)
            "total": int
        }
    """
    try:
        # Get current user
        user_id = get_current_user()
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
        
        # Validate law exists
        try:
            law = laws_collection.find_one({"_id": ObjectId(law_id)})
        except:
            return jsonify({"error": "Invalid law_id format"}), 400
        
        if not law:
            return jsonify({"error": "Law not found"}), 404
        
        # Get all questions for this law
        all_questions = list(questions_collection.find({"law_id": law_id}))
        
        # OPTIMIZED: Only fetch progress for this user and these specific questions
        question_ids = [str(q['_id']) for q in all_questions]
        progress_records = list(user_progress_collection.find({
            "user_id": user_id,
            "question_id": {"$in": question_ids}
        }))
        
        # Get user's starred questions
        user_question_stars = list(user_question_stars_collection.find({
            "user_id": user_id,
            "question_id": {"$in": question_ids}
        }))
        starred_question_ids = {s['question_id'] for s in user_question_stars}
        
        # Build progress lookup map
        progress_map = {p['question_id']: p for p in progress_records}
        
        # Filter to only include answered questions and add progress info
        questions = []
        for q in all_questions:
            q_id = str(q['_id'])
            if q_id in progress_map:
                q['_id'] = q_id
                # 自動判斷答錯狀態：last_score < 0.7
                last_score = progress_map[q_id].get('last_score', 0.0)
                q['is_marked_wrong'] = last_score < 0.7
                q['last_score'] = last_score
                # Add starred status
                q['is_starred'] = q_id in starred_question_ids
                questions.append(q)
        
        logger.info(f"User {user_id}: Retrieved {len(questions)} answered questions for law {law_id}")
        
        return jsonify({
            "questions": questions,
            "total": len(questions)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting law questions: {e}")
        return jsonify({"error": "Internal server error"}), 500


# Question management endpoints
from flask import Blueprint as _Blueprint
questions_bp = _Blueprint('questions', __name__, url_prefix='/api/questions')


@questions_bp.route('/<question_id>/star', methods=['PUT'])
@login_required
def toggle_question_star(question_id):
    """
    Toggle the starred status of a question for the current user.
    Requires authentication.
    
    Response:
        {
            "message": str,
            "is_starred": bool
        }
    """
    try:
        # Get current user
        user_id = get_current_user()
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
        
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
            action = "已取消收藏"
        else:
            # Add star
            user_question_stars_collection.insert_one({
                "user_id": user_id,
                "question_id": question_id,
                "created_at": datetime.utcnow()
            })
            new_starred = True
            action = "已收藏"
        
        logger.info(f"User {user_id}: Question {question_id} starred status changed to {new_starred}")
        
        return jsonify({
            "message": f"{action}題目",
            "is_starred": new_starred
        }), 200
        
    except Exception as e:
        logger.error(f"Error toggling question star: {e}")
        return jsonify({"error": "Internal server error"}), 500


@questions_bp.route('/my-questions', methods=['GET'])
@login_required
def get_my_questions():
    """
    Get starred or wrong answered questions for the current user with pagination.
    Requires authentication.
    
    Query Parameters:
        tab: str (required) - "starred" or "wrong"
        page: int (optional, default: 1) - Page number
        per_page: int (optional, default: 20, max: 50) - Items per page
        type: str (optional) - Filter by question type: "MCQ" or "ShortAnswer"
        lang: str (optional, default: "zh-TW") - Filter by language: "zh-TW" or "en"
    
    Response:
        {
            "questions": [...],
            "total": int,
            "page": int,
            "per_page": int,
            "total_pages": int
        }
    """
    try:
        # Get current user
        user_id = get_current_user()
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
        
        # Get tab parameter
        tab = request.args.get('tab', 'starred')
        if tab not in ['starred', 'wrong']:
            return jsonify({"error": "Invalid tab. Must be 'starred' or 'wrong'"}), 400
        
        # Get pagination parameters
        page = max(1, int(request.args.get('page', 1)))
        per_page = min(50, max(1, int(request.args.get('per_page', 5))))
        
        # Get type filter (optional)
        question_type = request.args.get('type')
        if question_type and question_type not in ['MCQ', 'ShortAnswer', 'all']:
            return jsonify({"error": "Invalid type. Must be 'MCQ', 'ShortAnswer', or 'all'"}), 400
        
        # Get language filter (default: zh-TW)
        lang = request.args.get('lang', 'zh-TW')
        if lang not in ['zh-TW', 'en']:
            lang = 'zh-TW'
        
        # Build base filter
        base_filter = {"is_deleted": False, "lang": lang}
        if question_type and question_type != 'all':
            base_filter["type"] = question_type
        
        if tab == 'starred':
            # Get user's starred questions
            user_stars = list(user_question_stars_collection.find({"user_id": user_id}))
            starred_question_ids = [ObjectId(s['question_id']) for s in user_stars]
            
            if not starred_question_ids:
                # No starred questions
                return jsonify({
                    "questions": [],
                    "total": 0,
                    "page": page,
                    "per_page": per_page,
                    "total_pages": 0
                }), 200
            
            query_filter = {**base_filter, "_id": {"$in": starred_question_ids}}
            total = questions_collection.count_documents(query_filter)
            
            # Calculate pagination
            total_pages = (total + per_page - 1) // per_page
            skip = (page - 1) * per_page
            
            # Find starred questions with pagination
            questions_list = list(questions_collection.find(query_filter).skip(skip).limit(per_page))
            
        else:  # tab == 'wrong'
            # Get questions with wrong answers for this user (last_score < 0.7)
            wrong_progress = list(user_progress_collection.find({
                "user_id": user_id,
                "last_score": {"$lt": 0.7}
            }))
            
            # Get question IDs
            question_ids = [ObjectId(p['question_id']) for p in wrong_progress]
            
            # Apply type filter
            query_filter = {**base_filter, "_id": {"$in": question_ids}}
            
            # Get total count
            total = questions_collection.count_documents(query_filter)
            
            # Calculate pagination
            total_pages = (total + per_page - 1) // per_page
            skip = (page - 1) * per_page
            
            # Find wrong questions with pagination
            questions_list = list(questions_collection.find(query_filter).skip(skip).limit(per_page))
        
        # Get law info for each question
        result_questions = []
        for q in questions_list:
            q_id = str(q['_id'])
            
            # Get law info
            law = laws_collection.find_one({"_id": ObjectId(q['law_id'])})
            law_info = {
                "article_number": law.get('article_number', 'N/A') if law else 'N/A',
                "chapter": law.get('chapter', '') if law else ''
            }
            
            # Get user's progress info and starred status
            progress = user_progress_collection.find_one({
                "user_id": user_id,
                "question_id": q_id
            })
            
            is_starred = user_question_stars_collection.find_one({
                "user_id": user_id,
                "question_id": q_id
            }) is not None
            
            question_data = {
                "_id": q_id,
                "type": q['type'],
                "content": q['content'],
                "correct_answer": q.get('correct_answer', ''),
                "ai_explanation": q.get('ai_explanation', ''),
                "options": q.get('options', []) if q['type'] == 'MCQ' else None,
                "law_id": q['law_id'],
                "law_info": law_info,
                "is_starred": is_starred,
                "last_score": progress.get('last_score') if progress else None
            }
            
            result_questions.append(question_data)
        
        logger.info(f"User {user_id}: Retrieved {len(result_questions)} {tab} questions (page {page}/{total_pages})")
        
        return jsonify({
            "questions": result_questions,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting my questions: {e}")
        return jsonify({"error": "Internal server error"}), 500
