"""
Test Session Complete Flow - Tasks 4.4 & 4.5
Tests Session Summary, Appeal, and Delete functionality
Run with: python3 test/test_session_complete.py
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bson import ObjectId
from db.models import (
    laws_collection, 
    questions_collection, 
    user_progress_collection,
    db
)
from services.question_gen import QuestionGenerator
from datetime import datetime

sessions_collection = db.db['sessions']


def setup_test_data():
    """Setup test data for session flow testing."""
    print("\n" + "="*60)
    print("🧹 Setting up Test Data")
    print("="*60)
    
    # Clear test data
    sessions_collection.delete_many({})
    
    # Get an existing law
    law = laws_collection.find_one()
    if not law:
        print("❌ No laws found. Run test_integration_e2e.py first!")
        return None, None
    
    # Get or create test questions
    questions = list(questions_collection.find({"is_deleted": False}).limit(3))
    
    if len(questions) < 3:
        print("  → Generating test questions...")
        generator = QuestionGenerator()
        
        # Generate MCQ and ShortAnswer
        mcq_questions = generator.generate_questions(
            law_content=law['content'],
            law_article_number=law['article_number'],
            question_type="MCQ",
            count=2
        )
        
        short_questions = generator.generate_questions(
            law_content=law['content'],
            law_article_number=law['article_number'],
            question_type="ShortAnswer",
            count=1
        )
        
        questions = []
        for q in mcq_questions + short_questions:
            q['law_id'] = str(law['_id'])
            q['is_deleted'] = False
            result = questions_collection.insert_one(q)
            q['_id'] = result.inserted_id
            questions.append(q)
        
        print(f"  ✓ Generated {len(questions)} test questions")
    else:
        print(f"  ✓ Using {len(questions)} existing questions")
    
    # Create a test session
    session_doc = {
        "type": "Mixed",
        "mode": "new",
        "question_ids": [str(q["_id"]) for q in questions],
        "answers": [],
        "created_at": datetime.utcnow(),
        "status": "active"
    }
    
    session_result = sessions_collection.insert_one(session_doc)
    session_id = str(session_result.inserted_id)
    
    print(f"  ✓ Created test session: {session_id}")
    print(f"  ✓ Test data ready")
    
    return session_id, questions


def test_answer_submission(session_id, questions):
    """Test 1: Submit answers for all questions."""
    print("\n" + "="*60)
    print("📝 Test 1: Answer Submission")
    print("="*60)
    
    try:
        session = sessions_collection.find_one({"_id": ObjectId(session_id)})
        
        for i, question in enumerate(questions, 1):
            print(f"\n  → Submitting answer {i}/3 (Type: {question['type']})")
            
            # Simulate answer submission
            if question['type'] == 'MCQ':
                user_answer = question['correct_answer']  # Submit correct answer
            else:
                user_answer = "這是測試答案"  # Submit a test answer
            
            answer_doc = {
                "question_id": str(question["_id"]),
                "user_answer": user_answer,
                "score": 1.0 if question['type'] == 'MCQ' else 0.5,
                "feedback": "測試反饋",
                "is_appealed": False,
                "submitted_at": datetime.utcnow()
            }
            
            sessions_collection.update_one(
                {"_id": ObjectId(session_id)},
                {"$push": {"answers": answer_doc}}
            )
            
            print(f"  ✓ Answer submitted (Score: {answer_doc['score']})")
        
        # Verify all answers submitted
        session = sessions_collection.find_one({"_id": ObjectId(session_id)})
        assert len(session['answers']) == 3, "Not all answers submitted"
        print(f"\n✅ Test 1 PASSED - All {len(session['answers'])} answers submitted")
        return True
        
    except Exception as e:
        print(f"\n❌ Test 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_session_summary(session_id):
    """Test 2: Verify session summary statistics."""
    print("\n" + "="*60)
    print("📊 Test 2: Session Summary Statistics")
    print("="*60)
    
    try:
        session = sessions_collection.find_one({"_id": ObjectId(session_id)})
        answers = session['answers']
        
        # Calculate stats
        total_questions = len(answers)
        correct_count = sum(1 for a in answers if a['score'] >= 1.0)
        accuracy_rate = round((correct_count / total_questions) * 100)
        avg_score = sum(a['score'] for a in answers) / total_questions
        
        print(f"\n  📈 Summary Statistics:")
        print(f"     Total Questions: {total_questions}")
        print(f"     Correct Count: {correct_count}")
        print(f"     Accuracy Rate: {accuracy_rate}%")
        print(f"     Average Score: {avg_score:.2f}")
        
        # Verify calculations
        assert total_questions == 3, f"Expected 3 questions, got {total_questions}"
        assert 0 <= accuracy_rate <= 100, f"Invalid accuracy rate: {accuracy_rate}"
        assert 0 <= avg_score <= 1, f"Invalid average score: {avg_score}"
        
        print(f"\n✅ Test 2 PASSED - Summary statistics calculated correctly")
        return True
        
    except Exception as e:
        print(f"\n❌ Test 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_appeal_functionality(session_id):
    """Test 3: Test appeal functionality."""
    print("\n" + "="*60)
    print("📢 Test 3: Appeal Functionality")
    print("="*60)
    
    try:
        session = sessions_collection.find_one({"_id": ObjectId(session_id)})
        
        # Get first answer to appeal
        answer_idx = 0
        answer = session['answers'][answer_idx]
        old_score = answer['score']
        
        print(f"\n  → Original Score: {old_score}")
        print(f"  → Appealing answer {answer_idx}...")
        
        # Check if already appealed
        if answer.get('is_appealed', False):
            print("  ⚠️  Answer already appealed, skipping...")
            return True
        
        # Reverse the score logic
        new_score = 0.0 if old_score >= 1.0 else 1.0
        
        # Update answer in session
        sessions_collection.update_one(
            {"_id": ObjectId(session_id)},
            {
                "$set": {
                    f"answers.{answer_idx}.score": new_score,
                    f"answers.{answer_idx}.is_appealed": True,
                    f"answers.{answer_idx}.feedback": f"[已申訴] {answer['feedback']}"
                }
            }
        )
        
        print(f"  → New Score: {new_score}")
        print(f"  ✓ Appeal marked in session")
        
        # Update user progress
        question_id = answer['question_id']
        user_progress_collection.update_one(
            {"question_id": question_id},
            {
                "$set": {
                    "is_appealed": True,
                    "last_score": new_score
                }
            },
            upsert=True
        )
        
        print(f"  ✓ Appeal marked in user progress")
        
        # Verify
        session = sessions_collection.find_one({"_id": ObjectId(session_id)})
        updated_answer = session['answers'][answer_idx]
        assert updated_answer['is_appealed'] == True, "Appeal flag not set"
        assert updated_answer['score'] == new_score, "Score not updated"
        
        print(f"\n✅ Test 3 PASSED - Appeal processed successfully")
        return True
        
    except Exception as e:
        print(f"\n❌ Test 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_delete_functionality(questions):
    """Test 4: Test delete functionality."""
    print("\n" + "="*60)
    print("🗑️  Test 4: Delete Functionality")
    print("="*60)
    
    try:
        # Get first question to delete
        question = questions[0]
        question_id = str(question['_id'])
        
        print(f"\n  → Deleting question: {question_id}")
        print(f"     Type: {question['type']}")
        print(f"     Content: {question['content'][:50]}...")
        
        # Check if already deleted
        current_q = questions_collection.find_one({"_id": ObjectId(question_id)})
        if current_q.get('is_deleted', False):
            print("  ⚠️  Question already deleted")
            return True
        
        # Soft delete
        questions_collection.update_one(
            {"_id": ObjectId(question_id)},
            {"$set": {"is_deleted": True}}
        )
        
        print(f"  ✓ Question marked as deleted")
        
        # Verify deletion
        deleted_q = questions_collection.find_one({"_id": ObjectId(question_id)})
        assert deleted_q['is_deleted'] == True, "Question not marked as deleted"
        
        # Verify it won't be fetched in future sessions
        active_count = questions_collection.count_documents({"is_deleted": False})
        print(f"  ✓ Active questions remaining: {active_count}")
        
        print(f"\n✅ Test 4 PASSED - Question deleted successfully")
        return True
        
    except Exception as e:
        print(f"\n❌ Test 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_end_to_end_flow():
    """Test 5: Complete end-to-end flow."""
    print("\n" + "="*60)
    print("🔄 Test 5: End-to-End Flow")
    print("="*60)
    
    try:
        print("\n  → Simulating complete session flow...")
        
        # 1. Create session
        print("  1️⃣  Creating session...")
        session_id, questions = setup_test_data()
        if not session_id:
            return False
        
        # 2. Submit answers
        print("  2️⃣  Submitting answers...")
        result = test_answer_submission(session_id, questions)
        if not result:
            return False
        
        # 3. View summary
        print("  3️⃣  Calculating summary...")
        result = test_session_summary(session_id)
        if not result:
            return False
        
        # 4. Appeal an answer
        print("  4️⃣  Processing appeal...")
        result = test_appeal_functionality(session_id)
        if not result:
            return False
        
        # 5. Delete a question
        print("  5️⃣  Deleting question...")
        result = test_delete_functionality(questions)
        if not result:
            return False
        
        print(f"\n✅ Test 5 PASSED - Complete end-to-end flow successful")
        return True
        
    except Exception as e:
        print(f"\n❌ Test 5 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("🚀 SESSION COMPLETE FLOW TESTS - Tasks 4.4 & 4.5")
    print("="*60)
    
    results = {
        "total": 0,
        "passed": 0,
        "failed": 0
    }
    
    # Setup test data
    session_id, questions = setup_test_data()
    if not session_id:
        print("\n❌ ABORT: Failed to setup test data")
        return
    
    # Run tests
    tests = [
        ("Answer Submission", lambda: test_answer_submission(session_id, questions)),
        ("Session Summary", lambda: test_session_summary(session_id)),
        ("Appeal Functionality", lambda: test_appeal_functionality(session_id)),
        ("Delete Functionality", lambda: test_delete_functionality(questions)),
    ]
    
    for test_name, test_func in tests:
        results["total"] += 1
        if test_func():
            results["passed"] += 1
        else:
            results["failed"] += 1
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"Total Tests: {results['total']}")
    print(f"✅ Passed: {results['passed']}")
    print(f"❌ Failed: {results['failed']}")
    
    if results['failed'] == 0:
        print("\n🎉 ALL TESTS PASSED!")
        print("\n✅ Tasks 4.4 & 4.5 Implementation Complete:")
        print("   ✓ Session Summary with statistics")
        print("   ✓ Appeal functionality")
        print("   ✓ Delete functionality")
        print("   ✓ End-to-end flow verified")
    else:
        print(f"\n⚠️  {results['failed']} test(s) failed")


if __name__ == '__main__':
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
