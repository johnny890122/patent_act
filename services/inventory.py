"""
Question Inventory Service - Manages question pool and triggers generation.
Implements the n, 4n inventory logic with sync/async generation.
"""
import logging
import threading
import random
from typing import List, Dict, Literal, Optional
from bson import ObjectId
from db.models import questions_collection, user_progress_collection, laws_collection
from services.question_gen import QuestionGenerator

logger = logging.getLogger(__name__)

class QuestionInventory:
    """Manages question inventory and generation triggers."""
    
    def __init__(self, api_key: str = None):
        """
        Initialize Question Inventory Manager.
        
        Args:
            api_key: OpenRouter API key for question generation
        """
        self.question_gen = QuestionGenerator(api_key=api_key)
    
    def count_available_questions(
        self,
        question_type: Literal["MCQ", "ShortAnswer", "Mixed"],
        session_mode: Literal["new", "review", "mixed"],
        lang: str = 'zh-TW',
        user_id: str = None,
        law_type: str = None
    ) -> int:
        """
        Count available questions based on type and session mode for a specific user.
        OPTIMIZED: Batch fetch all progress records to avoid N+1 queries.
        
        Args:
            question_type: Type of questions to count
            session_mode: Session mode (new/review/mixed)
            lang: Language filter
            user_id: User ID for filtering progress (required for multi-user)
            law_type: Law type filter (e.g., "patent-act") - NEW for multi-law support
            
        Returns:
            Count of available questions
        """
        # Get law_type from session if not provided
        if law_type is None:
            from services.auth import get_current_law_type
            law_type = get_current_law_type()
        # Build question type filter
        type_filter = {}
        if question_type == "MCQ":
            type_filter["type"] = "MCQ"
        elif question_type == "ShortAnswer":
            type_filter["type"] = "ShortAnswer"
        # Mixed means both types, no filter needed
        
        # Build language filter
        lang_filter = {}
        if lang and lang != 'both':
            lang_filter['lang'] = lang
        
        # Build law type filter (NEW for multi-law support)
        # Get law IDs for this law type first
        law_ids = [
            str(law["_id"])
            for law in laws_collection.find({"type": law_type}, {"_id": 1})
        ]
        
        if not law_ids:
            logger.warning(f"No laws found for type: {law_type}")
            return 0

        # Get all non-deleted question IDs for this law type
        all_questions = list(questions_collection.find({
            **type_filter,
            "is_deleted": False,
            **lang_filter,
            "law_id": {"$in": law_ids}  # Filter by law type
        }, {"_id": 1}))
        
        question_ids = [str(q["_id"]) for q in all_questions]
        
        # Batch fetch all progress records for these questions (OPTIMIZED!)
        # Filter by user_id for multi-user support
        progress_filter = {"question_id": {"$in": question_ids}}
        if user_id:
            # Convert string user_id to ObjectId for DB query
            from bson import ObjectId as OID
            progress_filter["user_id"] = OID(user_id) if isinstance(user_id, str) else user_id
        
        progress_records = list(user_progress_collection.find(progress_filter))
        
        # Build a lookup dictionary for fast access
        progress_map = {p["question_id"]: p for p in progress_records}
        
        if session_mode == "new":
            # New questions: not in user_progress OR (correct_streak == 0 AND needs_review == False)
            count = 0
            for qid in question_ids:
                progress = progress_map.get(qid)
                if not progress or (progress.get("correct_streak", 0) == 0 and not progress.get("needs_review", True)):
                    count += 1
            return count
            
        elif session_mode == "review":
            # Review questions: needs_review == True
            count = 0
            for qid in question_ids:
                progress = progress_map.get(qid)
                if progress and progress.get("needs_review", False):
                    count += 1
            return count
            
        else:  # mixed
            # For mixed, calculate both counts in one pass
            new_count = 0
            review_count = 0
            for qid in question_ids:
                progress = progress_map.get(qid)
                # Check for new
                if not progress or (progress.get("correct_streak", 0) == 0 and not progress.get("needs_review", True)):
                    new_count += 1
                # Check for review
                if progress and progress.get("needs_review", False):
                    review_count += 1
            # Mixed needs at least n/2 of each, so total available is min * 2
            return min(new_count, review_count) * 2
    
    def fetch_questions(
        self,
        question_type: Literal["MCQ", "ShortAnswer", "Mixed"],
        session_mode: Literal["new", "review", "mixed"],
        count: int,
        lang: str = 'zh-TW',
        user_id: str = None,
        law_type: str = None
    ) -> List[Dict]:
        """
        Fetch questions from database based on type and mode for a specific user.
        
        Args:
            question_type: Type of questions to fetch
            session_mode: Session mode (new/review/mixed)
            count: Number of questions to fetch
            lang: Language filter
            user_id: User ID for filtering progress (required for multi-user)
            law_type: Law type filter (e.g., "patent-act") - NEW for multi-law support
            
        Returns:
            List of question documents with full details
        """
        # Get law_type from session if not provided
        if law_type is None:
            from services.auth import get_current_law_type
            law_type = get_current_law_type()
        
        if session_mode == "mixed":
            # Split 50/50
            new_count = count // 2
            review_count = count - new_count
            new_qs = self._fetch_by_mode(question_type, "new", new_count, lang, user_id, law_type)
            review_qs = self._fetch_by_mode(question_type, "review", review_count, lang, user_id, law_type)
            return new_qs + review_qs
        else:
            return self._fetch_by_mode(question_type, session_mode, count, lang, user_id, law_type)
    
    def _fetch_by_mode(
        self,
        question_type: Literal["MCQ", "ShortAnswer", "Mixed"],
        session_mode: Literal["new", "review"],
        count: int,
        lang: str = 'zh-TW',
        user_id: str = None,
        law_type: str = None
    ) -> List[Dict]:
        """
        Internal helper to fetch questions by specific mode for a specific user.
        OPTIMIZED: Batch fetch all progress records to avoid N+1 queries.
        
        Args:
            question_type: Type of questions
            session_mode: Either "new" or "review"
            count: Number to fetch
            lang: Language filter
            user_id: User ID for filtering progress (required for multi-user)
            law_type: Law type filter (e.g., "patent-act") - NEW for multi-law support
            
        Returns:
            List of question documents
        """
        # Get law_type from session if not provided
        if law_type is None:
            from services.auth import get_current_law_type
            law_type = get_current_law_type()
        # Build type filter
        type_filter = {}
        if question_type == "MCQ":
            type_filter["type"] = "MCQ"
        elif question_type == "ShortAnswer":
            type_filter["type"] = "ShortAnswer"
        
        # Build language filter
        lang_filter = {}
        if lang and lang != 'both':
            lang_filter['lang'] = lang
        
        # Build law type filter (NEW for multi-law support)
        # Get law IDs for this law type first
        law_ids = [
            str(law["_id"])
            for law in laws_collection.find({"type": law_type}, {"_id": 1})
        ]
        
        if not law_ids:
            logger.warning(f"No laws found for type: {law_type}")
            return []

        # Get all non-deleted questions for this law type
        all_questions = list(questions_collection.find({
            **type_filter,
            "is_deleted": False,
            **lang_filter,
            "law_id": {"$in": law_ids}  # Filter by law type
        }))
        
        # Batch fetch all progress records (OPTIMIZED!)
        # Filter by user_id for multi-user support
        question_ids = [str(q["_id"]) for q in all_questions]
        progress_filter = {"question_id": {"$in": question_ids}}
        if user_id:
            # Convert string user_id to ObjectId for DB query
            from bson import ObjectId as OID
            progress_filter["user_id"] = OID(user_id) if isinstance(user_id, str) else user_id
        
        progress_records = list(user_progress_collection.find(progress_filter))
        
        # Build a lookup dictionary for fast access
        progress_map = {p["question_id"]: p for p in progress_records}
        
        # Filter based on mode
        filtered_questions = []
        for q in all_questions:
            qid = str(q["_id"])
            progress = progress_map.get(qid)
            
            if session_mode == "new":
                # New: not in progress OR (streak == 0 AND not needs_review)
                if not progress or (progress.get("correct_streak", 0) == 0 and not progress.get("needs_review", True)):
                    filtered_questions.append(q)
            elif session_mode == "review":
                # Review: needs_review == True
                if progress and progress.get("needs_review", False):
                    filtered_questions.append(q)
        
        # Randomize question selection to ensure variety
        if len(filtered_questions) > count:
            result = random.sample(filtered_questions, count)
        else:
            result = filtered_questions
        
        # Convert ObjectId to string for JSON serialization
        for q in result:
            q["_id"] = str(q["_id"])
        
        return result
    
    def generate_questions_sync(
        self,
        question_type: Literal["MCQ", "ShortAnswer", "Mixed"],
        count: int,
        law_ids: Optional[List[str]] = None,
        lang: str = 'zh-TW',
        law_type: str = None
    ) -> List[Dict]:
        """
        Synchronously generate and save questions. Blocks until complete.
        
        Args:
            question_type: Type of questions to generate
            count: Number of questions to generate
            law_ids: Optional list of law IDs to use. If None, uses all laws of the specified type.
            lang: Language filter
            law_type: Law type filter (e.g., "patent-act") - NEW for multi-law support
            
        Returns:
            List of newly generated question documents
        """
        # Get law_type from session if not provided
        if law_type is None:
            from services.auth import get_current_law_type
            law_type = get_current_law_type()
        
        logger.info(f"Starting sync generation of {count} {question_type} questions for law type: {law_type}")
        
        # Get law articles to generate questions for (respect language and law type)
        law_filter = {"type": law_type}  # Filter by law type
        if lang and lang != 'both':
            law_filter['lang'] = lang

        if not law_ids:
            laws = list(laws_collection.find(law_filter, {"_id": 1, "content": 1, "article_number": 1}))
        else:
            laws = list(laws_collection.find(
                {"_id": {"$in": [ObjectId(lid) for lid in law_ids]}, **law_filter},
                {"_id": 1, "content": 1, "article_number": 1}
            ))
        
        if not laws:
            logger.warning("No laws found for question generation")
            return []
        
        generated_questions = []
        questions_per_law = max(1, count // len(laws))
        remaining = count
        
        for law in laws:
            if remaining <= 0:
                break
            
            law_id = str(law["_id"])
            to_generate = min(questions_per_law, remaining)
            
            # Get recent questions for diversity
            recent = list(questions_collection.find(
                {"law_id": law_id},
                {"content": 1}
            ).sort("_id", -1).limit(3))
            
            # Determine actual type to generate (if Mixed, alternate)
            if question_type == "Mixed":
                actual_type = "MCQ" if len(generated_questions) % 2 == 0 else "ShortAnswer"
            else:
                actual_type = question_type
            
            try:
                # Generate questions using QuestionGenerator
                new_qs = self.question_gen.generate_questions(
                    law_content=law["content"],
                    law_article_number=law["article_number"],
                    question_type=actual_type,
                    recent_questions=recent,
                    count=to_generate
                )
                
                # Save to database
                for q in new_qs:
                    q["law_id"] = law_id
                    q["is_deleted"] = False
                    # attach language metadata
                    if lang and lang != 'both':
                        q['lang'] = lang
                    result = questions_collection.insert_one(q)
                    q["_id"] = str(result.inserted_id)
                    generated_questions.append(q)
                    remaining -= 1
                    
            except Exception as e:
                logger.error(f"Failed to generate questions for law {law_id}: {e}")
                continue
        
        logger.info(f"Successfully generated {len(generated_questions)} questions")
        return generated_questions
    
    def generate_questions_async(
        self,
        question_type: Literal["MCQ", "ShortAnswer", "Mixed"],
        count: int,
        law_ids: Optional[List[str]] = None,
        lang: str = 'zh-TW',
        law_type: str = None
    ):
        """
        Asynchronously generate questions in background thread.
        
        Args:
            question_type: Type of questions to generate
            count: Number of questions to generate
            law_ids: Optional list of law IDs to use
            lang: Language filter
            law_type: Law type filter (e.g., "patent-act") - NEW for multi-law support
        """
        # Get law_type from session if not provided
        if law_type is None:
            from services.auth import get_current_law_type
            law_type = get_current_law_type()
        
        def background_task():
            try:
                self.generate_questions_sync(question_type, count, law_ids, lang, law_type)
                logger.info(f"Background generation of {count} questions for {law_type} completed")
            except Exception as e:
                logger.error(f"Background generation failed: {e}")
        
        thread = threading.Thread(target=background_task, daemon=True)
        thread.start()
        logger.info(f"Started background generation of {count} {question_type} questions for law type: {law_type}")
    
    def get_session_questions(
        self,
        question_type: Literal["MCQ", "ShortAnswer", "Mixed"],
        session_mode: Literal["new", "review", "mixed"],
        count: int,
        law_ids: Optional[List[str]] = None,
        lang: str = 'zh-TW',
        user_id: str = None,
        law_type: str = None
    ) -> tuple[List[Dict], bool]:
        """
        Main entry point for getting session questions for a specific user.
        Implements n, 4n inventory logic with sync/async generation.
        
        Rules:
        - available >= 4n: Return n questions directly
        - n <= available < 4n: Return n questions + trigger async generation of 40 more
        - available < n: Block and generate synchronously
        
        Args:
            question_type: Type of questions
            session_mode: Session mode (new/review/mixed)
            count: Number of questions requested (n)
            law_ids: Optional list of law IDs to focus on
            lang: Language filter
            user_id: User ID for filtering progress (required for multi-user)
            law_type: Law type filter (e.g., "patent-act") - NEW for multi-law support
            
        Returns:
            Tuple of (questions list, is_loading_state)
            - questions: List of question documents
            - is_loading_state: True if had to generate synchronously
        """
        # Get law_type from session if not provided
        if law_type is None:
            from services.auth import get_current_law_type
            law_type = get_current_law_type()
        
        available = self.count_available_questions(question_type, session_mode, lang, user_id, law_type)
        logger.info(f"User {user_id}: Available questions: {available}, Requested: {count}, Type: {question_type}, Mode: {session_mode}, Law: {law_type}")
        
        if available >= 4 * count:
            # Plenty available, just return n questions
            logger.info("Sufficient inventory (>= 4n), fetching directly")
            questions = self.fetch_questions(question_type, session_mode, count, lang, user_id, law_type)
            return questions, False
            
        elif available >= count:
            # Have enough for this session, but trigger background generation
            logger.info(f"Adequate inventory ({count} <= {available} < {4*count}), fetching + async generation")
            questions = self.fetch_questions(question_type, session_mode, count, lang, user_id, law_type)

            # Trigger async generation of 40 more
            self.generate_questions_async(question_type, 40, law_ids, lang, law_type)
            
            return questions, False
            
        else:
            # Not enough, must generate synchronously
            logger.info(f"Insufficient inventory ({available} < {count}), sync generation required")
            
            # Generate exactly what we need
            needed = count - available
            new_questions = self.generate_questions_sync(question_type, needed, law_ids, lang, law_type)
            
            # Fetch any existing ones if available
            existing = self.fetch_questions(question_type, session_mode, available, lang, user_id, law_type) if available > 0 else []
            
            all_questions = existing + new_questions
            return all_questions[:count], True  # True indicates loading state was needed
