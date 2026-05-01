"""
Test script for Phase 3 API endpoints.
Tests quiz session, answer submission, appeals, question deletion, and laws endpoints.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
import json
from bson import ObjectId
from db.models import Database, questions_collection, laws_collection, user_progress_collection

# Test configuration
BASE_URL = "http://localhost:5001"
db = Database()

def setup_test_data():
    """Setup test data in database."""
    print("Setting up test data...")
    
    # Ensure we have at least one law
    law = laws_collection.find_one()
    if not law:
        print("❌ No laws found in database. Please run /admin/init first.")
        return None
    
    law_id = str(law['_id'])
    print(f"✓ Found law: {law['article_number']}")
    
    # Ensure we have at least a few questions
    question_count = questions_collection.count_documents({"is_deleted": False})
    print(f"✓ Found {question_count} active questions in database")
    
    if question_count < 3:
        print("⚠ Warning: Less than 3 questions available. Some tests may fail.")
    
    return law_id


def test_laws_endpoints():
    """Test all laws endpoints."""
    print("\n" + "="*60)
    print("TESTING LAWS ENDPOINTS")
    print("="*60)
    
    # Test GET /laws
    print("\n1. GET /laws (paginated list)")
    response = requests.get(f"{BASE_URL}/laws?page=1&per_page=5")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Retrieved {len(data['laws'])} laws (page {data['page']}/{data['total_pages']})")
        print(f"   ✓ Total laws: {data['total']}")
        if data['laws']:
            test_law_id = data['laws'][0]['_id']
        else:
            print("   ❌ No laws returned")
            return None
    else:
        print(f"   ❌ Failed: {response.text}")
        return None
    
    # Test GET /laws with filters
    print("\n2. GET /laws?starred=true")
    response = requests.get(f"{BASE_URL}/laws?starred=true")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Retrieved {len(data['laws'])} starred laws")
    else:
        print(f"   ❌ Failed: {response.text}")
    
    # Test GET /laws/:id
    print(f"\n3. GET /laws/{test_law_id}")
    response = requests.get(f"{BASE_URL}/laws/{test_law_id}")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        law = response.json()
        print(f"   ✓ Retrieved law: {law.get('article_number')}")
        print(f"   ✓ Is starred: {law.get('is_starred')}")
    else:
        print(f"   ❌ Failed: {response.text}")
        return None
    
    # Test PUT /laws/:id/star (toggle star)
    print(f"\n4. PUT /laws/{test_law_id}/star (toggle star)")
    response = requests.put(f"{BASE_URL}/laws/{test_law_id}/star")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ {data['message']}")
        print(f"   ✓ New starred status: {data['is_starred']}")
    else:
        print(f"   ❌ Failed: {response.text}")
    
    # Test GET /laws/chapters
    print("\n5. GET /laws/chapters")
    response = requests.get(f"{BASE_URL}/laws/chapters")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Found {len(data['chapters'])} chapters: {data['chapters'][:3]}...")
    else:
        print(f"   ❌ Failed: {response.text}")
    
    # Test GET /laws/stats
    print("\n6. GET /laws/stats")
    response = requests.get(f"{BASE_URL}/laws/stats")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Total laws: {data['total_laws']}")
        print(f"   ✓ Starred count: {data['starred_count']}")
        print(f"   ✓ Total attempts: {data['total_attempts']}")
        print(f"   ✓ Average score: {data['average_score']}")
    else:
        print(f"   ❌ Failed: {response.text}")
    
    return test_law_id


def test_quiz_session():
    """Test quiz session creation."""
    print("\n" + "="*60)
    print("TESTING QUIZ SESSION CREATION")
    print("="*60)
    
    # Test POST /quiz/session with MCQ
    print("\n1. POST /quiz/session (MCQ, new mode, 2 questions)")
    payload = {
        "type": "MCQ",
        "mode": "new",
        "count": 2
    }
    response = requests.post(f"{BASE_URL}/quiz/session", json=payload)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 201:
        data = response.json()
        session_id = data['session_id']
        questions = data['questions']
        print(f"   ✓ Session created: {session_id}")
        print(f"   ✓ Retrieved {len(questions)} questions")
        print(f"   ✓ Loading state: {data.get('is_loading', False)}")
        
        if questions:
            print(f"   ✓ First question ID: {questions[0]['_id']}")
            print(f"   ✓ Question type: {questions[0]['type']}")
            return session_id, questions[0]
        else:
            print("   ❌ No questions returned")
            return None, None
    else:
        print(f"   ❌ Failed: {response.text}")
        return None, None


def test_answer_submission(session_id, question):
    """Test answer submission."""
    print("\n" + "="*60)
    print("TESTING ANSWER SUBMISSION")
    print("="*60)
    
    question_id = question['_id']
    
    # Get the full question from DB to know correct answer (for testing)
    full_question = questions_collection.find_one({"_id": ObjectId(question_id)})
    
    if question['type'] == 'MCQ':
        # For MCQ, submit the correct answer
        user_answer = full_question['correct_answer']
        print(f"\n1. POST /quiz/session/{session_id}/answer (MCQ - correct answer)")
    else:
        # For ShortAnswer, submit a test answer
        user_answer = "這是一個測試答案"
        print(f"\n1. POST /quiz/session/{session_id}/answer (ShortAnswer)")
    
    payload = {
        "question_id": question_id,
        "user_answer": user_answer
    }
    
    response = requests.post(f"{BASE_URL}/quiz/session/{session_id}/answer", json=payload)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Answer submitted")
        print(f"   ✓ Answer ID: {data['answer_id']}")
        print(f"   ✓ Score: {data['score']}")
        print(f"   ✓ Feedback: {data['feedback'][:50]}...")
        return data['answer_id'], data['score']
    else:
        print(f"   ❌ Failed: {response.text}")
        return None, None


def test_appeal(session_id, answer_id):
    """Test answer appeal."""
    print("\n" + "="*60)
    print("TESTING ANSWER APPEAL")
    print("="*60)
    
    print(f"\n1. POST /quiz/session/{session_id}/answer/{answer_id}/appeal")
    response = requests.post(f"{BASE_URL}/quiz/session/{session_id}/answer/{answer_id}/appeal")
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ {data['message']}")
        print(f"   ✓ New score: {data['new_score']}")
        print(f"   ✓ Is appealed: {data['is_appealed']}")
        return True
    else:
        print(f"   ❌ Failed: {response.text}")
        return False


def test_question_deletion():
    """Test question soft deletion."""
    print("\n" + "="*60)
    print("TESTING QUESTION DELETION")
    print("="*60)
    
    # Find a question to delete
    question = questions_collection.find_one({"is_deleted": False})
    if not question:
        print("   ❌ No questions available for deletion test")
        return False
    
    question_id = str(question['_id'])
    print(f"\n1. DELETE /quiz/questions/{question_id}")
    
    response = requests.delete(f"{BASE_URL}/quiz/questions/{question_id}")
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ {data['message']}")
        
        # Verify it's marked as deleted
        updated_question = questions_collection.find_one({"_id": ObjectId(question_id)})
        if updated_question and updated_question.get('is_deleted'):
            print(f"   ✓ Question marked as deleted in database")
            
            # Restore for future tests
            questions_collection.update_one(
                {"_id": ObjectId(question_id)},
                {"$set": {"is_deleted": False}}
            )
            print(f"   ✓ Restored question for future tests")
            return True
        else:
            print(f"   ❌ Question not marked as deleted in database")
            return False
    else:
        print(f"   ❌ Failed: {response.text}")
        return False


def test_error_handling():
    """Test error handling for invalid requests."""
    print("\n" + "="*60)
    print("TESTING ERROR HANDLING")
    print("="*60)
    
    # Test invalid session creation
    print("\n1. POST /quiz/session with invalid type")
    response = requests.post(f"{BASE_URL}/quiz/session", json={"type": "Invalid", "mode": "new", "count": 1})
    print(f"   Status: {response.status_code}")
    if response.status_code == 400:
        print(f"   ✓ Correctly rejected: {response.json().get('error')}")
    else:
        print(f"   ❌ Should return 400")
    
    # Test invalid law ID
    print("\n2. GET /laws/invalid_id")
    response = requests.get(f"{BASE_URL}/laws/invalid_id")
    print(f"   Status: {response.status_code}")
    if response.status_code == 400:
        print(f"   ✓ Correctly rejected: {response.json().get('error')}")
    else:
        print(f"   ❌ Should return 400")
    
    # Test non-existent session
    print("\n3. POST answer to non-existent session")
    fake_session_id = str(ObjectId())
    response = requests.post(
        f"{BASE_URL}/quiz/session/{fake_session_id}/answer",
        json={"question_id": str(ObjectId()), "user_answer": "test"}
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 404:
        print(f"   ✓ Correctly returned 404: {response.json().get('error')}")
    else:
        print(f"   ❌ Should return 404")


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("PHASE 3 API ENDPOINTS TEST SUITE")
    print("="*60)
    print(f"Testing against: {BASE_URL}")
    
    # Setup
    law_id = setup_test_data()
    if not law_id:
        print("\n❌ Setup failed. Cannot proceed with tests.")
        return
    
    # Test laws endpoints
    test_laws_endpoints()
    
    # Test quiz flow
    session_id, question = test_quiz_session()
    
    if session_id and question:
        answer_id, score = test_answer_submission(session_id, question)
        
        if answer_id is not None:
            test_appeal(session_id, answer_id)
    
    # Test question deletion
    test_question_deletion()
    
    # Test error handling
    test_error_handling()
    
    print("\n" + "="*60)
    print("TEST SUITE COMPLETED")
    print("="*60)


if __name__ == "__main__":
    main()
