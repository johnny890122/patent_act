"""
Test suite for services/grader.py
"""
import json
import os
from services.grader import Grader, GradingResult
from pydantic import ValidationError

def test_grade_correct_answer():
    """Test grading a correct answer."""
    grader = Grader()
    
    question = "專利權人對於侵害其專利權者，得請求損害賠償，請說明損害賠償的計算方式。"
    user_answer = "依專利法第97條，損害賠償可依以下方式計算：1.依民法第216條規定請求。2.依侵害人因侵害行為所得之利益。3.依授權實施該發明專利所得收取之合理權利金為基礎計算。"
    correct_answer = "依專利法第97條規定，損害賠償額可依以下三種方式計算：1.依民法第216條之規定；2.依侵害人因侵害行為所得之利益；3.以專利權人行使專利權通常所能獲取之利益，減除受害後行使同一專利權所得利益之差額；或以相當於授權實施該發明專利所得收取之合理權利金數額為所受損害。"
    law_content = "專利權人對於侵害其專利權者，得請求損害賠償。前項損害賠償額，得依下列各款規定計算之：一、依民法第二百十六條之規定。二、依侵害人因侵害行為所得之利益。"
    
    result = grader.grade_answer(question, user_answer, correct_answer, law_content)
    
    print("\n=== Test: Correct Answer ===")
    print(f"Score: {result['score']}")
    print(f"Feedback: {result['feedback']}")
    
    assert result['score'] in [0, 0.5, 1], f"Score must be 0, 0.5, or 1, got {result['score']}"
    assert isinstance(result['feedback'], str), "Feedback must be a string"
    assert len(result['feedback']) > 0, "Feedback must not be empty"
    
    print("✓ Test passed: Correct answer graded successfully")
    return result

def test_grade_partial_answer():
    """Test grading a partially correct answer."""
    grader = Grader()
    
    question = "何謂專利權？專利權的效力為何？"
    user_answer = "專利權是國家授予發明人的獨占權利。"
    correct_answer = "專利權是國家依法授予發明人或其受讓人，在一定期間內對其發明享有的排他獨占實施權。專利權人可以排除他人未經同意而實施其專利。"
    
    result = grader.grade_answer(question, user_answer, correct_answer)
    
    print("\n=== Test: Partial Answer ===")
    print(f"Score: {result['score']}")
    print(f"Feedback: {result['feedback']}")
    
    assert result['score'] in [0, 0.5, 1], f"Score must be 0, 0.5, or 1, got {result['score']}"
    assert isinstance(result['feedback'], str), "Feedback must be a string"
    
    print("✓ Test passed: Partial answer graded successfully")
    return result

def test_grade_incorrect_answer():
    """Test grading an incorrect answer."""
    grader = Grader()
    
    question = "專利申請權可否轉讓？"
    user_answer = "專利申請權不可以轉讓給其他人。"
    correct_answer = "依專利法第12條規定，專利申請權得讓與或繼承。"
    
    result = grader.grade_answer(question, user_answer, correct_answer)
    
    print("\n=== Test: Incorrect Answer ===")
    print(f"Score: {result['score']}")
    print(f"Feedback: {result['feedback']}")
    
    assert result['score'] in [0, 0.5, 1], f"Score must be 0, 0.5, or 1, got {result['score']}"
    assert isinstance(result['feedback'], str), "Feedback must be a string"
    
    print("✓ Test passed: Incorrect answer graded successfully")
    return result

def test_grading_result_validation():
    """Test GradingResult Pydantic model validation."""
    print("\n=== Test: Pydantic Model Validation ===")
    
    # Valid result
    valid_result = GradingResult(score=1, feedback="答案完全正確")
    assert valid_result.score == 1
    print("✓ Valid result accepted")
    
    # Test all valid scores
    for score in [0, 0.5, 1]:
        result = GradingResult(score=score, feedback=f"Score {score}")
        assert result.score == score
    print("✓ All valid scores (0, 0.5, 1) accepted")
    
    # Invalid score should raise error
    try:
        invalid_result = GradingResult(score=0.7, feedback="Invalid score")
        assert False, "Should have raised ValidationError for invalid score"
    except ValidationError:
        print("✓ Invalid score rejected as expected")
    
    # Empty feedback should raise error
    try:
        invalid_result = GradingResult(score=1, feedback="")
        assert False, "Should have raised ValidationError for empty feedback"
    except ValidationError:
        print("✓ Empty feedback rejected as expected")
    
    print("✓ Test passed: Pydantic validation working correctly")

def test_save_grading_samples():
    """Run grading tests and save samples to file."""
    import datetime
    
    print("\n" + "="*60)
    print("Starting Grader Tests")
    print("="*60)
    
    # Run validation test first
    test_grading_result_validation()
    
    # Run grading tests
    results = {
        'timestamp': datetime.datetime.now().isoformat(),
        'tests': []
    }
    
    try:
        result1 = test_grade_correct_answer()
        results['tests'].append({
            'test_name': 'correct_answer',
            'result': result1
        })
    except Exception as e:
        print(f"✗ Correct answer test failed: {e}")
        results['tests'].append({
            'test_name': 'correct_answer',
            'error': str(e)
        })
    
    try:
        result2 = test_grade_partial_answer()
        results['tests'].append({
            'test_name': 'partial_answer',
            'result': result2
        })
    except Exception as e:
        print(f"✗ Partial answer test failed: {e}")
        results['tests'].append({
            'test_name': 'partial_answer',
            'error': str(e)
        })
    
    try:
        result3 = test_grade_incorrect_answer()
        results['tests'].append({
            'test_name': 'incorrect_answer',
            'result': result3
        })
    except Exception as e:
        print(f"✗ Incorrect answer test failed: {e}")
        results['tests'].append({
            'test_name': 'incorrect_answer',
            'error': str(e)
        })
    
    # Save results
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"test_outputs/grading_test_{timestamp}.json"
    
    os.makedirs("test_outputs", exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ Test results saved to {output_file}")
    print("="*60)
    print("All Grader Tests Completed")
    print("="*60)

if __name__ == "__main__":
    test_save_grading_samples()
