"""
Laws Routes - Handles law article browsing and starring functionality.
"""
import logging
from flask import Blueprint, request, jsonify
from bson import ObjectId
from db.models import laws_collection

logger = logging.getLogger(__name__)

laws_bp = Blueprint('laws', __name__, url_prefix='/laws')


@laws_bp.route('', methods=['GET'])
def get_laws():
    """
    Get paginated list of law articles.
    
    Query Parameters:
        page: int (default: 1)
        per_page: int (default: 20, max: 100)
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
        # Get query parameters
        page = max(1, int(request.args.get('page', 1)))
        per_page = min(100, max(1, int(request.args.get('per_page', 20))))
        chapter = request.args.get('chapter')
        starred_param = request.args.get('starred')
        sort_field = request.args.get('sort', 'article_number')
        order = request.args.get('order', 'asc')
        
        # Build filter
        query_filter = {}
        if chapter:
            query_filter['chapter'] = chapter
        if starred_param is not None:
            # Parse boolean
            starred = starred_param.lower() in ['true', '1', 'yes']
            query_filter['is_starred'] = starred
        
        # Validate sort field
        valid_sort_fields = ['article_number', 'avg_score', 'attempt_count']
        if sort_field not in valid_sort_fields:
            sort_field = 'article_number'
        
        # Sort direction
        sort_direction = 1 if order == 'asc' else -1
        
        # Get total count
        total = laws_collection.count_documents(query_filter)
        total_pages = (total + per_page - 1) // per_page
        
        # Get paginated results
        skip = (page - 1) * per_page
        laws = list(laws_collection.find(query_filter)
                   .sort(sort_field, sort_direction)
                   .skip(skip)
                   .limit(per_page))
        
        # Convert ObjectId to string
        for law in laws:
            law['_id'] = str(law['_id'])
        
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
def get_law(law_id):
    """
    Get a single law article by ID.
    
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
        # Validate and get law
        try:
            law = laws_collection.find_one({"_id": ObjectId(law_id)})
        except:
            return jsonify({"error": "Invalid law_id format"}), 400
        
        if not law:
            return jsonify({"error": "Law not found"}), 404
        
        # Convert ObjectId to string
        law['_id'] = str(law['_id'])
        
        logger.info(f"Retrieved law {law_id}")
        
        return jsonify(law), 200
        
    except Exception as e:
        logger.error(f"Error getting law: {e}")
        return jsonify({"error": "Internal server error"}), 500


@laws_bp.route('/<law_id>/star', methods=['PUT'])
def toggle_star(law_id):
    """
    Toggle the starred status of a law article.
    
    Response:
        {
            "message": str,
            "is_starred": bool
        }
    """
    try:
        # Validate and get law
        try:
            law = laws_collection.find_one({"_id": ObjectId(law_id)})
        except:
            return jsonify({"error": "Invalid law_id format"}), 400
        
        if not law:
            return jsonify({"error": "Law not found"}), 404
        
        # Toggle starred status
        current_starred = law.get('is_starred', False)
        new_starred = not current_starred
        
        laws_collection.update_one(
            {"_id": ObjectId(law_id)},
            {"$set": {"is_starred": new_starred}}
        )
        
        action = "已加入" if new_starred else "已移除"
        logger.info(f"Law {law_id} starred status changed to {new_starred}")
        
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
    Get list of all unique chapters.
    
    Response:
        {
            "chapters": [str, ...]
        }
    """
    try:
        # Get distinct chapters
        chapters = laws_collection.distinct('chapter')
        
        # Sort chapters
        chapters.sort()
        
        logger.info(f"Retrieved {len(chapters)} chapters")
        
        return jsonify({
            "chapters": chapters
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting chapters: {e}")
        return jsonify({"error": "Internal server error"}), 500


@laws_bp.route('/stats', methods=['GET'])
def get_stats():
    """
    Get overall statistics about laws.
    
    Response:
        {
            "total_laws": int,
            "starred_count": int,
            "total_attempts": int,
            "average_score": float
        }
    """
    try:
        # Get total count
        total_laws = laws_collection.count_documents({})
        
        # Get starred count
        starred_count = laws_collection.count_documents({"is_starred": True})
        
        # Calculate aggregate stats
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "total_attempts": {"$sum": "$attempt_count"},
                    "total_score": {"$sum": "$total_score"}
                }
            }
        ]
        
        agg_result = list(laws_collection.aggregate(pipeline))
        
        total_attempts = 0
        average_score = 0.0
        
        if agg_result:
            total_attempts = agg_result[0].get('total_attempts', 0)
            total_score = agg_result[0].get('total_score', 0.0)
            average_score = total_score / total_attempts if total_attempts > 0 else 0.0
        
        logger.info(f"Retrieved stats: {total_laws} laws, {starred_count} starred")
        
        return jsonify({
            "total_laws": total_laws,
            "starred_count": starred_count,
            "total_attempts": total_attempts,
            "average_score": round(average_score, 2)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({"error": "Internal server error"}), 500
