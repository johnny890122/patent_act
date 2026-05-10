"""
Law Types API Routes - Manages law type selection and information.
New feature for multi-law support.
"""
import logging
from flask import Blueprint, request, jsonify, session
from services.auth import (
    login_required,
    get_current_law_type,
    set_current_law_type,
    get_available_law_types
)
from db.models import LAW_TYPES

logger = logging.getLogger(__name__)

law_types_bp = Blueprint('law_types', __name__, url_prefix='/api/law-types')


@law_types_bp.route('', methods=['GET'])
@login_required
def get_law_types():
    """
    Get list of all available law types with article counts.
    Requires login.
    
    Returns:
        JSON: {
            "law_types": [
                {
                    "type": "patent-act",
                    "name_zh": "專利法",
                    "name_en": "Patent Law",
                    "count_zh_tw": 168,
                    "count_en": 168,
                    "total": 336
                },
                ...
            ],
            "current": "patent-act"
        }
    """
    try:
        law_types = get_available_law_types()
        current = get_current_law_type()
        
        return jsonify({
            "law_types": law_types,
            "current": current
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting law types: {e}")
        return jsonify({"error": "無法獲取法律類型列表"}), 500


@law_types_bp.route('/current', methods=['GET'])
@login_required
def get_current():
    """
    Get current selected law type from session.
    Requires login.
    
    Returns:
        JSON: {
            "type": "patent-act",
            "name_zh": "專利法",
            "name_en": "Patent Law"
        }
    """
    try:
        law_type = get_current_law_type()
        
        if law_type not in LAW_TYPES:
            # Fallback to patent-act if invalid
            law_type = "patent-act"
            set_current_law_type(law_type)
        
        law_info = LAW_TYPES[law_type]
        
        return jsonify({
            "type": law_type,
            "name_zh": law_info["name_zh"],
            "name_en": law_info["name_en"]
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting current law type: {e}")
        return jsonify({"error": "無法獲取當前法律類型"}), 500


@law_types_bp.route('/select', methods=['POST'])
@login_required
def select_law_type():
    """
    Set current law type in session.
    Requires login.
    
    Request Body:
        {
            "law_type": "patent-act"
        }
    
    Returns:
        JSON: {
            "success": true,
            "law_type": "patent-act",
            "name_zh": "專利法",
            "name_en": "Patent Law"
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'law_type' not in data:
            return jsonify({"error": "缺少 law_type 參數"}), 400
        
        law_type = data['law_type']
        
        # Validate law type
        if law_type not in LAW_TYPES:
            return jsonify({
                "error": f"無效的法律類型: {law_type}",
                "valid_types": list(LAW_TYPES.keys())
            }), 400
        
        # Set in session
        success = set_current_law_type(law_type)
        
        if not success:
            return jsonify({"error": "設定法律類型失敗"}), 500
        
        law_info = LAW_TYPES[law_type]
        
        logger.info(f"User switched to law type: {law_type}")
        
        return jsonify({
            "success": True,
            "law_type": law_type,
            "name_zh": law_info["name_zh"],
            "name_en": law_info["name_en"]
        }), 200
        
    except Exception as e:
        logger.error(f"Error selecting law type: {e}")
        return jsonify({"error": "設定法律類型時發生錯誤"}), 500


@law_types_bp.route('/info/<law_type>', methods=['GET'])
@login_required  
def get_law_type_info(law_type):
    """
    Get detailed information about a specific law type.
    Requires login.
    
    Args:
        law_type: Law type code (e.g., "patent-act")
    
    Returns:
        JSON: {
            "type": "patent-act",
            "name_zh": "專利法",
            "name_en": "Patent Law",
            "code": "patent-act",
            "count_zh_tw": 168,
            "count_en": 168,
            "total": 336
        }
    """
    try:
        if law_type not in LAW_TYPES:
            return jsonify({"error": f"找不到法律類型: {law_type}"}), 404
        
        # Get law type info with counts
        law_types = get_available_law_types()
        law_info = next((lt for lt in law_types if lt["type"] == law_type), None)
        
        if not law_info:
            # Fallback to basic info without counts
            basic_info = LAW_TYPES[law_type]
            return jsonify({
                "type": law_type,
                **basic_info,
                "count_zh_tw": 0,
                "count_en": 0,
                "total": 0
            }), 200
        
        return jsonify(law_info), 200
        
    except Exception as e:
        logger.error(f"Error getting law type info: {e}")
        return jsonify({"error": "無法獲取法律類型資訊"}), 500
