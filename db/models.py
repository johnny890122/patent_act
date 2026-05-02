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
    options: Optional[List[str]] = None
    is_deleted: bool = False
    is_starred: bool = False
    # 答錯狀態改為從 user_progress.last_score 自動判斷

@dataclass
class UserProgressModel:
    question_id: str
    correct_streak: int = 0
    needs_review: bool = True
    last_score: float = 0.0
    is_appealed: bool = False

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

    def init_db(self):
        """Ensure indexes are created for performance."""
        # Laws indexes
        self.laws_collection.create_index('article_number', unique=True)
        self.laws_collection.create_index('article_number_int')  # For sorting
        self.laws_collection.create_index('is_starred')  # For filtering starred laws
        self.laws_collection.create_index('chapter')  # For filtering by chapter
        
        # Questions indexes
        self.questions_collection.create_index('law_id')
        self.questions_collection.create_index([('is_deleted', 1), ('type', 1)])  # For filtered queries
        self.questions_collection.create_index('is_starred')  # For starred questions
        
        # User progress indexes
        self.user_progress_collection.create_index('question_id', unique=True)
        self.user_progress_collection.create_index('needs_review')  # For review mode queries
        
        print("Database indexes initialized.")

db = Database()
laws_collection = db.laws_collection
questions_collection = db.questions_collection
user_progress_collection = db.user_progress_collection
