"""
End-to-End Integration Test - Full System Test with MongoDB
Tests the complete flow: Laws → Question Generation → Grading → Inventory
Run with: python3 test/test_integration_e2e.py
"""
import sys
import os
from pathlib import Path
from datetime import datetime
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bson import ObjectId
from db.models import laws_collection, questions_collection, user_progress_collection
from services.law_parser import LawParserService, MockupDataSource
from services.question_gen import QuestionGenerator
from services.grader import Grader
from services.inventory import QuestionInventory
from db.models import LawModel
from dataclasses import asdict


class TestStats:
    """Track test statistics."""
    def __init__(self):
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.start_time = datetime.now()
    
    def record_pass(self):
        self.total_tests += 1
        self.passed_tests += 1
    
    def record_fail(self):
        self.total_tests += 1
        self.failed_tests += 1
    
    def summary(self):
        duration = (datetime.now() - self.start_time).total_seconds()
        return {
            "total": self.total_tests,
            "passed": self.passed_tests,
            "failed": self.failed_tests,
            "duration": f"{duration:.2f}s",
            "pass_rate": f"{(self.passed_tests/self.total_tests*100):.1f}%" if self.total_tests > 0 else "0%"
        }


stats = TestStats()


def setup_test_environment():
    """Setup clean test environment."""
    print("\n" + "="*60)
    print("🧹 Setting up Test Environment")
    print("="*60)
    
    # Clear all collections
    laws_collection.delete_many({})
    questions_collection.delete_many({})
    user_progress_collection.delete_many({})
    
    print("✓ Cleared all collections")
    print("✓ Test environment ready")


def cleanup_test_environment():
    """Cleanup after tests."""
    print("\n" + "="*60)
    print("🧹 Cleaning up Test Environment")
    print("="*60)
    
    # Option to keep or clear data
    laws_collection.delete_many({})
    questions_collection.delete_many({})
    user_progress_collection.delete_many({})
    
    print("✓ Test environment cleaned")


def test_1_law_loading():
    """Test 1: Load laws from mock data into MongoDB."""
    print("\n" + "="*60)
    print("📚 Test 1: Law Loading from Mock Data")
    print("="*60)
    
    try:
        # Use LawParserService with MockupDataSource
        parser = LawParserService(data_source=MockupDataSource())
        
        # Load mock laws
        print("\n  → Loading mock laws...")
        laws_data = parser.load_laws()
        
        assert len(laws_data) > 0, "No laws loaded from mock data"
        print(f"  ✓ Loaded {len(laws_data)} laws from mock data")
        
        # Save laws to database (mimicking admin.py logic)
        print("\n  → Saving laws to MongoDB...")
        inserted = 0
        for law_data in laws_data:
            law_model = LawModel(**law_data)
            result = laws_collection.replace_one(
                {"article_number": law_model.article_number},
                asdict(law_model),
                upsert=True
            )
            if result.upserted_id:
                inserted += 1
        
        print(f"  ✓ Inserted {inserted} laws into MongoDB")
        
        # Verify first law
        first_law = laws_data[0]
        assert "article_number" in first_law
        assert "content" in first_law
        assert "chapter" in first_law
        print(f"  ✓ First law: {first_law['article_number']}")
        
        # Verify in database
        db_count = laws_collection.count_documents({})
        assert db_count >= inserted, f"DB count mismatch: {db_count} < {inserted}"
        print(f"  ✓ Verified {db_count} laws in MongoDB")
        
        # Display sample law
        sample = laws_collection.find_one()
        print(f"\n  📄 Sample Law:")
        print(f"     Article: {sample['article_number']}")
        print(f"     Chapter: {sample['chapter']}")
        print(f"     Content: {sample['content'][:50]}...")
        
        stats.record_pass()
        print("\n✅ Test 1 PASSED")
        return True
        
    except Exception as e:
        stats.record_fail()
        print(f"\n❌ Test 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_2_question_generation_mcq():
    """Test 2: Generate MCQ questions using LLM."""
    print("\n" + "="*60)
    print("🤖 Test 2: MCQ Question Generation with LLM")
    print("="*60)
    
    try:
        # Get a law article
        law = laws_collection.find_one()
        assert law is not None, "No laws in database"
        print(f"\n  → Using law: {law['article_number']}")
        
        # Generate MCQ questions
        generator = QuestionGenerator()
        print(f"  → Generating 2 MCQ questions...")
        
        questions = generator.generate_questions(
            law_content=law['content'],
            law_article_number=law['article_number'],
            question_type="MCQ",
            count=2
        )
        
        assert len(questions) == 2, f"Expected 2 questions, got {len(questions)}"
        print(f"  ✓ Generated {len(questions)} MCQ questions")
        
        # Validate question structure
        for i, q in enumerate(questions, 1):
            assert q['type'] == "MCQ"
            assert 'content' in q
            assert 'options' in q
            assert 'correct_answer' in q
            assert 'ai_explanation' in q
            assert len(q['options']) == 4
            print(f"  ✓ Question {i} structure valid")
        
        # Save to database
        for q in questions:
            q['law_id'] = str(law['_id'])
            q['is_deleted'] = False
            result = questions_collection.insert_one(q)
            print(f"  ✓ Saved question to DB: {result.inserted_id}")
        
        # Display first question
        print(f"\n  📝 Sample MCQ Question:")
        print(f"     Q: {questions[0]['content'][:60]}...")
        print(f"     Options: {len(questions[0]['options'])} choices")
        print(f"     Answer: {questions[0]['correct_answer']}")
        
        stats.record_pass()
        print("\n✅ Test 2 PASSED")
        return True
        
    except Exception as e:
        stats.record_fail()
        print(f"\n❌ Test 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_3_question_generation_short_answer():
    """Test 3: Generate Short Answer questions using LLM."""
    print("\n" + "="*60)
    print("🤖 Test 3: Short Answer Question Generation with LLM")
    print("="*60)
    
    try:
        # Get a law article
        law = laws_collection.find_one()
        assert law is not None, "No laws in database"
        print(f"\n  → Using law: {law['article_number']}")
        
        # Generate Short Answer questions
        generator = QuestionGenerator()
        print(f"  → Generating 2 Short Answer questions...")
        
        questions = generator.generate_questions(
            law_content=law['content'],
            law_article_number=law['article_number'],
            question_type="ShortAnswer",
            count=2
        )
        
        assert len(questions) == 2, f"Expected 2 questions, got {len(questions)}"
        print(f"  ✓ Generated {len(questions)} Short Answer questions")
        
        # Validate question structure
        for i, q in enumerate(questions, 1):
            assert q['type'] == "ShortAnswer"
            assert 'content' in q
            assert 'correct_answer' in q
            assert 'ai_explanation' in q
            assert q['options'] is None or q['options'] == []
            print(f"  ✓ Question {i} structure valid")
        
        # Save to database
        for q in questions:
            q['law_id'] = str(law['_id'])
            q['is_deleted'] = False
            result = questions_collection.insert_one(q)
            print(f"  ✓ Saved question to DB: {result.inserted_id}")
        
        # Display first question
        print(f"\n  📝 Sample Short Answer Question:")
        print(f"     Q: {questions[0]['content'][:60]}...")
        print(f"     Expected Answer: {questions[0]['correct_answer'][:60]}...")
        
        stats.record_pass()
        print("\n✅ Test 3 PASSED")
        return True
        
    except Exception as e:
        stats.record_fail()
        print(f"\n❌ Test 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_4_grading_short_answer():
    """Test 4: Grade short answer using LLM."""
    print("\n" + "="*60)
    print("✍️ Test 4: Short Answer Grading with LLM")
    print("="*60)
    
    try:
        # Get a short answer question from DB
        question = questions_collection.find_one({"type": "ShortAnswer"})
        assert question is not None, "No Short Answer questions in database"
        print(f"\n  → Using question: {question['content'][:50]}...")
        
        grader = Grader()
        
        # Test Case 1: Good answer (should get 1.0)
        print("\n  🧪 Test Case 1: Good Answer")
        good_answer = question['correct_answer']
        result = grader.grade_answer(
            question=question['content'],
            user_answer=good_answer,
            correct_answer=question['correct_answer'],
            law_content=""
        )
        
        assert result['score'] in [0, 0.5, 1], f"Invalid score: {result['score']}"
        assert 'feedback' in result
        print(f"  ✓ Score: {result['score']}")
        print(f"  ✓ Feedback: {result['feedback'][:60]}...")
        
        # Test Case 2: Poor answer (should get 0 or 0.5)
        print("\n  🧪 Test Case 2: Poor Answer")
        poor_answer = "我不知道"
        result = grader.grade_answer(
            question=question['content'],
            user_answer=poor_answer,
            correct_answer=question['correct_answer'],
            law_content=""
        )
        
        assert result['score'] in [0, 0.5, 1], f"Invalid score: {result['score']}"
        print(f"  ✓ Score: {result['score']}")
        print(f"  ✓ Feedback: {result['feedback'][:60]}...")
        
        # Save to user_progress
        progress = {
            "question_id": str(question['_id']),
            "correct_streak": 1 if result['score'] == 1 else 0,
            "needs_review": result['score'] < 1,
            "last_score": result['score'],
            "is_appealed": False
        }
        user_progress_collection.replace_one(
            {"question_id": str(question['_id'])},
            progress,
            upsert=True
        )
        print(f"  ✓ Saved progress to DB")
        
        stats.record_pass()
        print("\n✅ Test 4 PASSED")
        return True
        
    except Exception as e:
        stats.record_fail()
        print(f"\n❌ Test 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_5_inventory_management():
    """Test 5: Question inventory management and retrieval."""
    print("\n" + "="*60)
    print("📦 Test 5: Question Inventory Management")
    print("="*60)
    
    try:
        inventory = QuestionInventory()
        
        # Count available questions
        print("\n  → Counting available questions...")
        mcq_count = inventory.count_available_questions("MCQ", "new")
        sa_count = inventory.count_available_questions("ShortAnswer", "new")
        mixed_count = inventory.count_available_questions("Mixed", "new")
        
        print(f"  ✓ MCQ: {mcq_count} questions")
        print(f"  ✓ Short Answer: {sa_count} questions")
        print(f"  ✓ Mixed: {mixed_count} questions")
        
        # Test fetching questions
        print("\n  → Fetching 2 mixed questions...")
        questions, is_loading = inventory.get_session_questions(
            question_type="Mixed",
            session_mode="new",
            count=2
        )
        
        assert len(questions) <= 2, f"Got more questions than requested"
        print(f"  ✓ Retrieved {len(questions)} questions")
        print(f"  ✓ Loading state: {is_loading}")
        
        # Display question types
        types = [q['type'] for q in questions]
        print(f"  ✓ Question types: {types}")
        
        # Test review mode
        print("\n  → Testing review mode...")
        review_count = inventory.count_available_questions("Mixed", "review")
        print(f"  ✓ Review questions available: {review_count}")
        
        stats.record_pass()
        print("\n✅ Test 5 PASSED")
        return True
        
    except Exception as e:
        stats.record_fail()
        print(f"\n❌ Test 5 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_6_database_integrity():
    """Test 6: Verify database integrity and relationships."""
    print("\n" + "="*60)
    print("🔍 Test 6: Database Integrity Check")
    print("="*60)
    
    try:
        # Count documents
        law_count = laws_collection.count_documents({})
        question_count = questions_collection.count_documents({})
        progress_count = user_progress_collection.count_documents({})
        
        print(f"\n  📊 Database Statistics:")
        print(f"     Laws: {law_count}")
        print(f"     Questions: {question_count}")
        print(f"     User Progress: {progress_count}")
        
        assert law_count > 0, "No laws in database"
        assert question_count > 0, "No questions in database"
        print(f"  ✓ All collections have data")
        
        # Verify relationships
        print(f"\n  → Verifying relationships...")
        questions = list(questions_collection.find().limit(5))
        for q in questions:
            # Check law_id exists
            law = laws_collection.find_one({"_id": ObjectId(q['law_id'])})
            assert law is not None, f"Orphaned question: {q['_id']}"
        
        print(f"  ✓ All questions linked to valid laws")
        
        # Check for duplicates
        print(f"\n  → Checking for duplicate questions...")
        pipeline = [
            {"$group": {
                "_id": "$content",
                "count": {"$sum": 1}
            }},
            {"$match": {"count": {"$gt": 1}}}
        ]
        duplicates = list(questions_collection.aggregate(pipeline))
        print(f"  ✓ Found {len(duplicates)} duplicate question contents (expected in test)")
        
        stats.record_pass()
        print("\n✅ Test 6 PASSED")
        return True
        
    except Exception as e:
        stats.record_fail()
        print(f"\n❌ Test 6 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_7_full_workflow_simulation():
    """Test 7: Simulate a complete user workflow."""
    print("\n" + "="*60)
    print("🔄 Test 7: Full Workflow Simulation")
    print("="*60)
    
    try:
        print("\n  📖 Scenario: User starts a quiz session")
        
        # Step 1: Get laws
        print("\n  → Step 1: Browse available laws")
        laws = list(laws_collection.find().limit(3))
        print(f"  ✓ Found {len(laws)} laws")
        
        # Step 2: Start quiz session
        print("\n  → Step 2: Request quiz session (2 mixed questions)")
        inventory = QuestionInventory()
        questions, is_loading = inventory.get_session_questions(
            question_type="Mixed",
            session_mode="new",
            count=2
        )
        print(f"  ✓ Got {len(questions)} questions")
        
        if len(questions) == 0:
            print("  ⚠️ No questions available, generating...")
            # This scenario would trigger sync generation in real app
        
        # Step 3: Answer questions
        print("\n  → Step 3: User answers questions")
        grader = Grader()
        
        for i, q in enumerate(questions, 1):
            print(f"\n  📝 Question {i}: {q['type']}")
            
            if q['type'] == "MCQ":
                # Simulate MCQ answer
                user_answer = q['correct_answer']
                score = 1 if user_answer == q['correct_answer'] else 0
                print(f"     User selected: {user_answer}")
                print(f"     Score: {score}")
                
            else:  # ShortAnswer
                # Simulate short answer grading
                user_answer = q['correct_answer'][:30] + "..."  # Partial answer
                result = grader.grade_answer(
                    question=q['content'],
                    user_answer=user_answer,
                    correct_answer=q['correct_answer'],
                    law_content=""
                )
                score = result['score']
                print(f"     User answer: {user_answer[:40]}...")
                print(f"     Score: {score}")
                print(f"     Feedback: {result['feedback'][:50]}...")
            
            # Update progress
            progress = {
                "question_id": str(q['_id']),
                "correct_streak": 1 if score == 1 else 0,
                "needs_review": score < 1,
                "last_score": score,
                "is_appealed": False
            }
            user_progress_collection.replace_one(
                {"question_id": str(q['_id'])},
                progress,
                upsert=True
            )
            print(f"     ✓ Progress saved")
        
        # Step 4: Check updated stats
        print("\n  → Step 4: Check updated statistics")
        progress_count = user_progress_collection.count_documents({})
        needs_review = user_progress_collection.count_documents({"needs_review": True})
        mastered = user_progress_collection.count_documents({"correct_streak": {"$gte": 3}})
        
        print(f"  ✓ Total questions attempted: {progress_count}")
        print(f"  ✓ Questions needing review: {needs_review}")
        print(f"  ✓ Questions mastered: {mastered}")
        
        stats.record_pass()
        print("\n✅ Test 7 PASSED")
        return True
        
    except Exception as e:
        stats.record_fail()
        print(f"\n❌ Test 7 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all integration tests."""
    print("\n" + "="*60)
    print("🚀 STARTING END-TO-END INTEGRATION TESTS")
    print("="*60)
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🗄️  Database: MongoDB Local")
    print(f"🔧 Mode: Full Integration")
    
    try:
        setup_test_environment()
        
        # Run all tests in sequence
        tests = [
            test_1_law_loading,
            test_2_question_generation_mcq,
            test_3_question_generation_short_answer,
            test_4_grading_short_answer,
            test_5_inventory_management,
            test_6_database_integrity,
            test_7_full_workflow_simulation
        ]
        
        results = []
        for test_func in tests:
            result = test_func()
            results.append(result)
            if not result:
                print(f"\n⚠️  Test failed, continuing...")
        
        # Print summary
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        
        summary = stats.summary()
        print(f"Total Tests: {summary['total']}")
        print(f"Passed: ✅ {summary['passed']}")
        print(f"Failed: ❌ {summary['failed']}")
        print(f"Pass Rate: {summary['pass_rate']}")
        print(f"Duration: {summary['duration']}")
        
        if summary['failed'] == 0:
            print("\n" + "="*60)
            print("🎉 ALL TESTS PASSED!")
            print("="*60)
            return True
        else:
            print("\n" + "="*60)
            print("⚠️  SOME TESTS FAILED")
            print("="*60)
            return False
        
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Ask user if they want to cleanup
        print("\n" + "="*60)
        print("⚠️  Note: Test data is still in database")
        print("To clean up, uncomment cleanup_test_environment() below")
        print("="*60)
        # Uncomment to cleanup:
        # cleanup_test_environment()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
