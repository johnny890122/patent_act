import os
import logging
from flask import Blueprint, jsonify, request
from db.models import laws_collection, LawModel
from dataclasses import asdict
from pymongo.errors import PyMongoError
from services.law_parser import LawParserService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

@admin_bp.route('/init-laws', methods=['POST'])
def init_laws():
    """
    Initialize laws collection from data source.
    
    Current implementation uses mockup JSON data (knowledge/mock_laws.json).
    Future implementation will parse truth data from markdown using LLM.
    
    Query Parameters:
        source: Optional. Data source type ('mockup' or 'truth'). Default: 'mockup'
        file: Optional. Custom file path for data source
    
    Returns:
        JSON response with inserted/updated counts and data source info
        - 200: Success with statistics
        - 400: Invalid data format
        - 404: Source file not found
        - 500: Database or server error
        - 501: Data source not yet implemented
    
    Example:
        POST /admin/init-laws
        POST /admin/init-laws?source=mockup
        POST /admin/init-laws?source=truth (not yet implemented)
    """
    # Get source type from query parameters (default to 'mockup')
    source_type = request.args.get('source', 'mockup').lower()
    custom_file = request.args.get('file', None)
    
    logger.info(f"Starting law initialization with source type: {source_type}")
    
    # Create appropriate parser service based on source type
    try:
        if source_type == 'mockup':
            parser = LawParserService.create_mockup_source(custom_file)
        elif source_type == 'truth':
            parser = LawParserService.create_truth_source(custom_file)
        else:
            logger.error(f"Invalid source type: {source_type}")
            return jsonify({
                "error": f"Invalid source type: {source_type}",
                "valid_types": ["mockup", "truth"]
            }), 400
        
        logger.info(f"Using data source: {parser.get_source_info()}")
        
    except Exception as e:
        logger.error(f"Failed to initialize parser: {str(e)}")
        return jsonify({"error": f"Parser initialization failed: {str(e)}"}), 500

    # Load laws from data source
    try:
        laws_data = parser.load_laws()
        
    except FileNotFoundError as e:
        logger.error(f"Source file not found: {str(e)}")
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        logger.error(f"Invalid data format: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except NotImplementedError as e:
        logger.warning(f"Data source not yet implemented: {str(e)}")
        return jsonify({
            "error": str(e),
            "suggestion": "Use ?source=mockup for now"
        }), 501
    except IOError as e:
        logger.error(f"File read error: {str(e)}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.error(f"Unexpected error loading laws: {str(e)}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

    # Process and insert/update laws in database
    inserted = 0
    updated = 0
    errors = []
    
    for idx, law_data in enumerate(laws_data):
        try:
            # Validate through Dataclass schema
            law_model = LawModel(**law_data)
            
            # Insert or update in database
            result = laws_collection.replace_one(
                {"article_number": law_model.article_number},
                asdict(law_model),
                upsert=True
            )
            
            if result.upserted_id:
                inserted += 1
                logger.debug(f"Inserted law: {law_model.article_number}")
            else:
                updated += 1
                logger.debug(f"Updated law: {law_model.article_number}")
                
        except TypeError as e:
            error_msg = f"Invalid data format at index {idx}: {str(e)}"
            logger.warning(error_msg)
            errors.append(error_msg)
        except PyMongoError as e:
            error_msg = f"Database error at index {idx}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error at index {idx}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

    # Prepare response
    response = {
        "message": "Law initialization completed",
        "source": parser.get_source_info(),
        "inserted": inserted,
        "updated": updated,
        "total_processed": len(laws_data)
    }
    
    if errors:
        response["errors"] = errors
        response["error_count"] = len(errors)
        response["message"] = "Law initialization completed with errors"
        logger.warning(f"Completed with {len(errors)} errors out of {len(laws_data)} laws")
        return jsonify(response), 207  # 207 Multi-Status
    
    logger.info(f"Successfully initialized laws from {parser.get_source_info()}: {inserted} inserted, {updated} updated")
    return jsonify(response), 200
