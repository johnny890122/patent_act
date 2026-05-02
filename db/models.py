import os
from typing import Optional, List, Literal
from dataclasses import dataclass, asdict
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

@dataclass
class LawModel:
    article_number: str
    content: str
    chapter: str
    article_number_int: int = 0  # 用於排序的整數條號
    lang: str = "zh-TW"  # NEW: Language tag (zh-TW or en)
    is_starred: bool = False
    total_score: float = 0.0
    attempt_count: int = 0
    avg_score: float = 0.0

@dataclass
class QuestionModel:
    law_id: str
    type: Literal["MCQ", "ShortAnswer"]
    content: str
    correct_answer: str
    ai_explanation: str
    lang: str = "zh-TW"  # NEW: Language tag (zh-TW or en)
    options: Optional[List[str]] = None
    is_deleted: bool = False
    is_starred: bool = False
    base_question_id: Optional[str] = None  # NEW: Links zh-TW ↔ en translations
    # 答錯狀態改為從 user_progress.last_score 自動判斷

@dataclass
class UserProgressModel:
    question_id: str
    correct_streak: int = 0
    needs_review: bool = True
    last_score: float = 0.0
    is_appealed: bool = False

@dataclass
class I18nMappingModel:
    """Bidirectional mapping between zh-TW and en law articles"""
    zh_tw_law_id: str      # ObjectId of zh-TW law
    en_law_id: str         # ObjectId of en law
    article_number: str    # Common article number (e.g., "Article 1")

class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        mongo_uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/patent_act')
        self.client = MongoClient(mongo_uri)
        db_name = self.client.get_database().name if self.client.get_database().name else 'patent_act'
        self.db = self.client[db_name]
        
        self.laws_collection = self.db['laws']
        self.questions_collection = self.db['questions']
        self.user_progress_collection = self.db['user_progress']
        self.i18n_mapping_collection = self.db['i18n_mapping']  # NEW: i18n mapping collection

    def init_db(self):
        """Ensure indexes are created for performance."""
        # Laws indexes
        self.laws_collection.create_index('article_number', unique=True)
        self.laws_collection.create_index('article_number_int')  # For sorting
        self.laws_collection.create_index('is_starred')  # For filtering starred laws
        self.laws_collection.create_index('chapter')  # For filtering by chapter
        self.laws_collection.create_index([('article_number', 1), ('lang', 1)], unique=True)  # NEW: i18n lookup
        self.laws_collection.create_index('lang')  # NEW: For language filtering
        
        # Questions indexes
        self.questions_collection.create_index('law_id')
        self.questions_collection.create_index([('is_deleted', 1), ('type', 1)])  # For filtered queries
        self.questions_collection.create_index('is_starred')  # For starred questions
        self.questions_collection.create_index([('law_id', 1), ('lang', 1)])  # NEW: i18n lookup
        self.questions_collection.create_index([('base_question_id', 1), ('lang', 1)])  # NEW: Link translations
        self.questions_collection.create_index('lang')  # NEW: For language filtering
        
        # User progress indexes
        self.user_progress_collection.create_index('question_id', unique=True)
        self.user_progress_collection.create_index('needs_review')  # For review mode queries
        
        # i18n mapping indexes
        self.i18n_mapping_collection.create_index([('article_number', 1)], unique=True)  # NEW: For quick lookup
        self.i18n_mapping_collection.create_index('zh_tw_law_id')  # NEW
        self.i18n_mapping_collection.create_index('en_law_id')  # NEW
        
        print("Database indexes initialized.")

db = Database()
laws_collection = db.laws_collection
questions_collection = db.questions_collection
user_progress_collection = db.user_progress_collection
i18n_mapping_collection = db.i18n_mapping_collection  # NEW: i18n mapping collection
