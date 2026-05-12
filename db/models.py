import os
from typing import Optional, List, Literal
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# Supported law types
LAW_TYPES = {
    "patent-act": {
        "name_zh": "專利法",
        "name_en": "Patent Law",
        "code": "patent-act"
    },
    "trademark-act": {
        "name_zh": "商標法",
        "name_en": "Trademark Law",
        "code": "trademark-act"
    },
    "copyright-act": {
        "name_zh": "著作權法",
        "name_en": "Copyright Law",
        "code": "copyright-act"
    },
    "patent-examination": {
        "name_zh": "專利審查基準",
        "name_en": "Patent Examination Guidelines",
        "code": "patent-examination"
    }
}

@dataclass
class UserModel:
    """User account for multi-user support"""
    username: str          # Unique login identifier (e.g., "alice")
    display_name: str      # Display name (e.g., "Alice Chen")
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None

@dataclass
class LawModel:
    article_number: str
    content: str
    chapter: str
    type: str = "patent-act"  # Law type identifier (patent-act, trademark-act, etc.)
    article_number_int: int = 0  # 用於排序的整數條號
    lang: str = "zh-TW"  # Language tag (zh-TW or en)

@dataclass
class QuestionModel:
    law_id: str
    type: Literal["MCQ", "ShortAnswer"]
    content: str
    correct_answer: str
    ai_explanation: str
    lang: str = "zh-TW"  # Language tag (zh-TW or en)
    options: Optional[List[str]] = None
    is_deleted: bool = False
    base_question_id: Optional[str] = None  # Links zh-TW ↔ en translations
    # REMOVED: is_starred (now per-user)
    # 答錯狀態改為從 user_progress.last_score 自動判斷

@dataclass
class UserProgressModel:
    """Per-user progress tracking for questions"""
    user_id: str           # Links to users collection
    question_id: str
    correct_streak: int = 0
    needs_review: bool = True
    last_score: float = 0.0
    is_appealed: bool = False
    # Composite unique index: (user_id, question_id)

@dataclass
class UserLawStarModel:
    """Per-user law article stars"""
    user_id: str           # Links to users collection
    law_id: str            # Links to laws collection
    created_at: datetime = field(default_factory=datetime.utcnow)
    # Composite unique index: (user_id, law_id)

@dataclass
class UserLawStatsModel:
    """Per-user law article statistics"""
    user_id: str           # Links to users collection
    law_id: str            # Links to laws collection
    total_score: float = 0.0
    attempt_count: int = 0
    avg_score: float = 0.0
    # Composite unique index: (user_id, law_id)

@dataclass
class UserQuestionStarModel:
    """Per-user question stars"""
    user_id: str           # Links to users collection
    question_id: str       # Links to questions collection
    created_at: datetime = field(default_factory=datetime.utcnow)
    # Composite unique index: (user_id, question_id)

@dataclass
class I18nMappingModel:
    """Bidirectional mapping between zh-TW and en law articles"""
    zh_tw_law_id: str      # ObjectId of zh-TW law
    en_law_id: str         # ObjectId of en law
    article_number: str    # Common article number (e.g., "Article 1")
    type: str = "patent-act"  # Law type (patent-act, trademark-act, etc.)

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
        
        # Shared collections
        self.laws_collection = self.db['laws']
        self.questions_collection = self.db['questions']
        self.i18n_mapping_collection = self.db['i18n_mapping']
        
        # User-specific collections (NEW for multi-user support)
        self.users_collection = self.db['users']
        self.user_progress_collection = self.db['user_progress']
        self.user_law_stars_collection = self.db['user_law_stars']
        self.user_law_stats_collection = self.db['user_law_stats']
        self.user_question_stars_collection = self.db['user_question_stars']

    def init_db(self):
        """Ensure indexes are created for performance."""
        # Laws indexes (shared content)
        self.laws_collection.create_index('article_number_int')  # For sorting
        self.laws_collection.create_index('chapter')  # For filtering by chapter
        self.laws_collection.create_index([('article_number', 1), ('lang', 1)], unique=True)  # i18n lookup
        self.laws_collection.create_index('lang')  # For language filtering
        # Multi-law support indexes (NEW)
        self.laws_collection.create_index('type')  # For filtering by law type
        self.laws_collection.create_index([('type', 1), ('lang', 1)])  # Combined filter
        self.laws_collection.create_index([('type', 1), ('article_number_int', 1)])  # For sorted queries by type
        
        # Questions indexes (shared content)
        self.questions_collection.create_index('law_id')
        self.questions_collection.create_index([('is_deleted', 1), ('type', 1)])  # For filtered queries
        self.questions_collection.create_index([('law_id', 1), ('lang', 1)])  # i18n lookup
        self.questions_collection.create_index([('base_question_id', 1), ('lang', 1)])  # Link translations
        self.questions_collection.create_index('lang')  # For language filtering
        
        # Users indexes (NEW)
        self.users_collection.create_index('username', unique=True)
        
        # User progress indexes (UPDATED for multi-user)
        # Drop old single-user index if exists
        try:
            self.user_progress_collection.drop_index('question_id_1')
        except:
            pass  # Index doesn't exist, which is fine
        self.user_progress_collection.create_index([('user_id', 1), ('question_id', 1)], unique=True)
        self.user_progress_collection.create_index([('user_id', 1), ('needs_review', 1)])  # For review mode queries
        self.user_progress_collection.create_index('user_id')  # For user-specific queries
        
        # User law stars indexes (NEW)
        self.user_law_stars_collection.create_index([('user_id', 1), ('law_id', 1)], unique=True)
        self.user_law_stars_collection.create_index('user_id')  # For user-specific queries
        
        # User law stats indexes (NEW)
        self.user_law_stats_collection.create_index([('user_id', 1), ('law_id', 1)], unique=True)
        self.user_law_stats_collection.create_index('user_id')  # For user-specific queries
        
        # User question stars indexes (NEW)
        self.user_question_stars_collection.create_index([('user_id', 1), ('question_id', 1)], unique=True)
        self.user_question_stars_collection.create_index('user_id')  # For user-specific queries
        
        # i18n mapping indexes
        try:
            # Get existing indexes first
            existing_indexes = self.i18n_mapping_collection.index_information()
            # Drop old unique index if exists
            if 'article_number_1' in existing_indexes:
                self.i18n_mapping_collection.drop_index('article_number_1')
        except Exception as e:
            # Index doesn't exist or can't be dropped, which is fine
            pass
        
        # Create indexes (use unique names to avoid conflicts)
        try:
            self.i18n_mapping_collection.create_index([('article_number', 1)], name='article_number_idx')
        except:
            pass  # Index might already exist
        try:
            self.i18n_mapping_collection.create_index('zh_tw_law_id', name='zh_tw_law_id_idx')
        except:
            pass
        try:
            self.i18n_mapping_collection.create_index('en_law_id', name='en_law_id_idx')
        except:
            pass
        
        # i18n mapping indexes - Multi-law support (NEW)
        try:
            self.i18n_mapping_collection.create_index([('type', 1), ('article_number', 1)], name='type_article_idx')
        except:
            pass  # Index might already exist
        
        print("Database indexes initialized for multi-user and multi-law support.")

db = Database()

# Shared collections
laws_collection = db.laws_collection
questions_collection = db.questions_collection
i18n_mapping_collection = db.i18n_mapping_collection

# User-specific collections (NEW for multi-user support)
users_collection = db.users_collection
user_progress_collection = db.user_progress_collection
user_law_stars_collection = db.user_law_stars_collection
user_law_stats_collection = db.user_law_stats_collection
user_question_stars_collection = db.user_question_stars_collection
