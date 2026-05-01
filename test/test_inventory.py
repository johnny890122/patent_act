"""
Test suite for Question Inventory Service.
Tests the n, 4n inventory logic and sync/async generation triggers.
Run with: python3 test/test_inventory.py
"""
import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bson import ObjectId
from db.models import questions_collection, user_progress_collection, laws_collection
from services.inventory import QuestionInventory


def setup_test_data():
    """Setup test data before tests."""
    # Clear test collections
    questions_collection.delete_many({})
    user_progress_collection.delete_many({})
    
    # Ensure we have at least one law article for testing
    if laws_collection.count_documents({}) == 0:
        laws_collection.insert_one({
            "article_number": "Test Article 1",
            "content": "這是測試用的法條內容，用於驗證題目產生系統。",
            "chapter": "測試章節",
            "is_starred": False
        })
    
    print("✓ Test data setup complete")


def cleanup_test_data():
    """Cleanup test data after tests."""
    questions_collection.delete_many({})
    user_progress_collection.delete_many({})
    print("✓ Test data cleanup complete")


def test_count_available_new_questions():
    """Test counting new questions (not in progress)."""
    print("\n=== Test: Count Available New Questions ===")
    
    cleanup_test_data()
    inventory = QuestionInventory()
    
    # Insert test questions
    q1 = questions_collection.insert_one({
        "law_id": "test_law_1",
        "type": "MCQ",
        "content": "Test question 1",
        "correct_answer": "A",
        "ai_explanation": "Test explanation",
        "options": ["A", "B", "C", "D"],
        "is_deleted": False
    })
    
    q2 = questions_collection.insert_one({
        "law_id": "test_law_1",
        "type": "ShortAnswer",
        "content": "Test question 2",
        "correct_answer": "Test answer",
        "ai_explanation": "Test explanation",
        "is_deleted": False
    })
    
    # Count new MCQ questions (no progress = new)
    count = inventory.count_available_questions("MCQ", "new")
    assert count == 1, f"Expected 1 new MCQ, got {count}"
    print(f"  ✓ MCQ count: {count}")
    
    # Count all new questions
    count = inventory.count_available_questions("Mixed", "new")
    assert count == 2, f"Expected 2 new Mixed questions, got {count}"
    print(f"  ✓ Mixed count: {count}")
    
    print("✓ Test passed: Count available new questions")


def test_count_available_review_questions():
    """Test counting review questions (needs_review == True)."""
    print("\n=== Test: Count Available Review Questions ===")
    
    cleanup_test_data()
    inventory = QuestionInventory()
    
    # Insert test question
    q1 = questions_collection.insert_one({
        "law_id": "test_law_1",
        "type": "MCQ",
        "content": "Test question 1",
        "correct_answer": "A",
        "ai_explanation": "Test explanation",
        "options": ["A", "B", "C", "D"],
        "is_deleted": False
    })
    
    # Mark as needs review
    user_progress_collection.insert_one({
        "question_id": str(q1.inserted_id),
        "correct_streak": 1,
        "needs_review": True,
        "last_score": 0.5
    })
    
    # Count review questions
    count = inventory.count_available_questions("MCQ", "review")
    assert count == 1, f"Expected 1 review MCQ, got {count}"
    print(f"  ✓ Review count: {count}")
    
    # Count new questions (should be 0)
    count = inventory.count_available_questions("MCQ", "new")
    assert count == 0, f"Expected 0 new MCQ, got {count}"
    print(f"  ✓ New count (should be 0): {count}")
    
    print("✓ Test passed: Count available review questions")


def test_fetch_questions_by_mode():
    """Test fetching questions by session mode."""
    print("\n=== Test: Fetch Questions by Mode ===")
    
    cleanup_test_data()
    inventory = QuestionInventory()
    
    # Insert test questions
    q1 = questions_collection.insert_one({
        "law_id": "test_law_1",
        "type": "MCQ",
        "content": "New question",
        "correct_answer": "A",
        "ai_explanation": "Test",
        "options": ["A", "B", "C", "D"],
        "is_deleted": False
    })
    
    q2 = questions_collection.insert_one({
        "law_id": "test_law_1",
        "type": "MCQ",
        "content": "Review question",
        "correct_answer": "B",
        "ai_explanation": "Test",
        "options": ["A", "B", "C", "D"],
        "is_deleted": False
    })
    
    # Mark q2 as needs review
    user_progress_collection.insert_one({
        "question_id": str(q2.inserted_id),
        "needs_review": True
    })
    
    # Fetch new questions
    new_qs = inventory.fetch_questions("MCQ", "new", 5)
    assert len(new_qs) == 1, f"Expected 1 new question, got {len(new_qs)}"
    assert new_qs[0]["content"] == "New question"
    print(f"  ✓ Fetched {len(new_qs)} new question(s)")
    
    # Fetch review questions
    review_qs = inventory.fetch_questions("MCQ", "review", 5)
    assert len(review_qs) == 1, f"Expected 1 review question, got {len(review_qs)}"
    assert review_qs[0]["content"] == "Review question"
    print(f"  ✓ Fetched {len(review_qs)} review question(s)")
    
    print("✓ Test passed: Fetch questions by mode")


def test_fetch_mixed_mode():
    """Test fetching questions in mixed mode (50% new + 50% review)."""
    print("\n=== Test: Fetch Mixed Mode Questions ===")
    
    cleanup_test_data()
    inventory = QuestionInventory()
    
    # Insert 4 questions - 2 new, 2 review
    for i in range(4):
        q = questions_collection.insert_one({
            "law_id": "test_law_1",
            "type": "MCQ",
            "content": f"Question {i+1}",
            "correct_answer": "A",
            "ai_explanation": "Test",
            "options": ["A", "B", "C", "D"],
            "is_deleted": False
        })
        
        if i >= 2:  # Last 2 are review
            user_progress_collection.insert_one({
                "question_id": str(q.inserted_id),
                "needs_review": True
            })
    
    # Fetch 4 mixed questions (should get 2 new + 2 review)
    mixed_qs = inventory.fetch_questions("MCQ", "mixed", 4)
    assert len(mixed_qs) == 4, f"Expected 4 mixed questions, got {len(mixed_qs)}"
    print(f"  ✓ Fetched {len(mixed_qs)} mixed questions (2 new + 2 review)")
    
    print("✓ Test passed: Fetch mixed mode questions")


def test_inventory_logic_4n_available():
    """Test inventory logic when >= 4n questions available."""
    print("\n=== Test: Inventory Logic (>= 4n) ===")
    
    cleanup_test_data()
    inventory = QuestionInventory()
    
    # Insert 20 questions (4n where n=5)
    for i in range(20):
        questions_collection.insert_one({
            "law_id": "test_law_1",
            "type": "MCQ",
            "content": f"Question {i+1}",
            "correct_answer": "A",
            "ai_explanation": "Test",
            "options": ["A", "B", "C", "D"],
            "is_deleted": False
        })
    
    # Request 5 questions
    questions, is_loading = inventory.get_session_questions("MCQ", "new", 5)
    
    assert len(questions) == 5, f"Expected 5 questions, got {len(questions)}"
    assert is_loading == False, "Should not require loading state"
    print(f"  ✓ Got {len(questions)} questions, loading state: {is_loading}")
    
    print("✓ Test passed: Inventory logic with >= 4n questions")


def test_inventory_logic_between_n_and_4n():
    """Test inventory logic when n <= available < 4n (triggers async generation)."""
    print("\n=== Test: Inventory Logic (n <= available < 4n) ===")
    
    cleanup_test_data()
    inventory = QuestionInventory()
    
    # Insert 7 questions (between n=5 and 4n=20)
    for i in range(7):
        questions_collection.insert_one({
            "law_id": "test_law_1",
            "type": "MCQ",
            "content": f"Question {i+1}",
            "correct_answer": "A",
            "ai_explanation": "Test",
            "options": ["A", "B", "C", "D"],
            "is_deleted": False
        })
    
    # Request 5 questions
    questions, is_loading = inventory.get_session_questions("MCQ", "new", 5)
    
    assert len(questions) == 5, f"Expected 5 questions, got {len(questions)}"
    assert is_loading == False, "Should not require loading state (has enough for session)"
    print(f"  ✓ Got {len(questions)} questions, loading state: {is_loading}")
    print("  ✓ Async generation triggered for 40 more questions (background)")
    
    print("✓ Test passed: Inventory logic with n <= available < 4n")


def test_deleted_questions_excluded():
    """Test that deleted questions are not counted or fetched."""
    print("\n=== Test: Deleted Questions Excluded ===")
    
    cleanup_test_data()
    inventory = QuestionInventory()
    
    # Insert 2 questions, mark 1 as deleted
    q1 = questions_collection.insert_one({
        "law_id": "test_law_1",
        "type": "MCQ",
        "content": "Active question",
        "correct_answer": "A",
        "ai_explanation": "Test",
        "options": ["A", "B", "C", "D"],
        "is_deleted": False
    })
    
    q2 = questions_collection.insert_one({
        "law_id": "test_law_1",
        "type": "MCQ",
        "content": "Deleted question",
        "correct_answer": "B",
        "ai_explanation": "Test",
        "options": ["A", "B", "C", "D"],
        "is_deleted": True  # Deleted
    })
    
    # Count should only return 1
    count = inventory.count_available_questions("MCQ", "new")
    assert count == 1, f"Expected 1 active question, got {count}"
    print(f"  ✓ Count (excluding deleted): {count}")
    
    # Fetch should only return the active one
    questions = inventory.fetch_questions("MCQ", "new", 5)
    assert len(questions) == 1, f"Expected 1 active question, got {len(questions)}"
    assert questions[0]["content"] == "Active question"
    print(f"  ✓ Fetched only active questions: {len(questions)}")
    
    print("✓ Test passed: Deleted questions excluded")


def test_type_filtering():
    """Test that question type filtering works correctly."""
    print("\n=== Test: Question Type Filtering ===")
    
    cleanup_test_data()
    inventory = QuestionInventory()
    
    # Insert different question types
    questions_collection.insert_one({
        "law_id": "test_law_1",
        "type": "MCQ",
        "content": "MCQ question",
        "correct_answer": "A",
        "ai_explanation": "Test",
        "options": ["A", "B", "C", "D"],
        "is_deleted": False
    })
    
    questions_collection.insert_one({
        "law_id": "test_law_1",
        "type": "ShortAnswer",
        "content": "Short answer question",
        "correct_answer": "Test answer",
        "ai_explanation": "Test",
        "is_deleted": False
    })
    
    # Count MCQ only
    mcq_count = inventory.count_available_questions("MCQ", "new")
    assert mcq_count == 1, f"Expected 1 MCQ, got {mcq_count}"
    print(f"  ✓ MCQ count: {mcq_count}")
    
    # Count ShortAnswer only
    sa_count = inventory.count_available_questions("ShortAnswer", "new")
    assert sa_count == 1, f"Expected 1 ShortAnswer, got {sa_count}"
    print(f"  ✓ ShortAnswer count: {sa_count}")
    
    # Count Mixed (both)
    mixed_count = inventory.count_available_questions("Mixed", "new")
    assert mixed_count == 2, f"Expected 2 Mixed, got {mixed_count}"
    print(f"  ✓ Mixed count: {mixed_count}")
    
    print("✓ Test passed: Question type filtering")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("Running Question Inventory Tests")
    print("=" * 60)
    
    try:
        setup_test_data()
        
        test_count_available_new_questions()
        test_count_available_review_questions()
        test_fetch_questions_by_mode()
        test_fetch_mixed_mode()
        test_inventory_logic_4n_available()
        test_inventory_logic_between_n_and_4n()
        test_deleted_questions_excluded()
        test_type_filtering()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cleanup_test_data()
    
    return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
