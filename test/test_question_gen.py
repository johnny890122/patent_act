"""
Test script for QuestionGenerator to verify actual question generation.
Run with: python3 test/test_question_gen.py
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables BEFORE importing other modules
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.question_gen import QuestionGenerator

# Ensure output directory exists
OUTPUT_DIR = Path(__file__).parent.parent / "test_outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

def test_mcq_generation():
    """Test MCQ question generation"""
    print("\n" + "="*80)
    print("測試 1: MCQ 選擇題生成")
    print("="*80)
    
    generator = QuestionGenerator()
    
    law_content = "為鼓勵、保護、利用發明、新型及設計之創作，以促進產業發展，特制定本法。"
    law_article = "第1條"
    
    try:
        questions = generator.generate_questions(
            law_content=law_content,
            law_article_number=law_article,
            question_type="MCQ",
            recent_questions=[],
            count=1
        )
        
        print(f"\n✅ 成功生成 {len(questions)} 道選擇題")
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = OUTPUT_DIR / f"mcq_questions_{timestamp}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)
        print(f"\n💾 題目已儲存至: {output_file}")
        
        print("\n生成的題目：")
        print(json.dumps(questions, ensure_ascii=False, indent=2))
        
        # Validate structure
        for q in questions:
            assert 'content' in q, "缺少 content 欄位"
            assert 'options' in q, "缺少 options 欄位"
            assert 'correct_answer' in q, "缺少 correct_answer 欄位"
            assert 'ai_explanation' in q, "缺少 ai_explanation 欄位"
            assert 'type' in q, "缺少 type 欄位"
            assert q['type'] == 'MCQ', f"題型應為 MCQ，實際為 {q['type']}"
            assert isinstance(q['options'], list) and len(q['options']) > 0, "options 應為非空列表"
            
        print("\n✅ Schema 驗證通過")
        return True
        
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_short_answer_generation():
    """Test ShortAnswer question generation"""
    print("\n" + "="*80)
    print("測試 2: ShortAnswer 簡答題生成")
    print("="*80)
    
    generator = QuestionGenerator()
    
    law_content = "本法所稱專利，分為下列三種：一、發明專利。二、新型專利。三、設計專利。"
    law_article = "第2條"
    
    try:
        questions = generator.generate_questions(
            law_content=law_content,
            law_article_number=law_article,
            question_type="ShortAnswer",
            recent_questions=[],
            count=1
        )
        
        print(f"\n✅ 成功生成 {len(questions)} 道簡答題")
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = OUTPUT_DIR / f"short_answer_questions_{timestamp}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)
        print(f"\n💾 題目已儲存至: {output_file}")
        
        print("\n生成的題目：")
        print(json.dumps(questions, ensure_ascii=False, indent=2))
        
        # Validate structure
        for q in questions:
            assert 'content' in q, "缺少 content 欄位"
            assert 'correct_answer' in q, "缺少 correct_answer 欄位"
            assert 'ai_explanation' in q, "缺少 ai_explanation 欄位"
            assert 'type' in q, "缺少 type 欄位"
            assert q['type'] == 'ShortAnswer', f"題型應為 ShortAnswer，實際為 {q['type']}"
            # options should be None or empty for ShortAnswer
            assert q.get('options') is None or q.get('options') == [], "ShortAnswer 的 options 應為 None 或空列表"
            
        print("\n✅ Schema 驗證通過")
        return True
        
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_with_recent_questions():
    """Test question generation with recent questions to avoid duplicates"""
    print("\n" + "="*80)
    print("測試 3: 帶有近期題目的防重複機制")
    print("="*80)
    
    generator = QuestionGenerator()
    
    law_content = "本法所稱專利，分為下列三種：一、發明專利。二、新型專利。三、設計專利。"
    law_article = "第2條"
    
    recent_questions = [
        {"content": "專利法將專利分為哪三種類型？"}
    ]
    
    try:
        questions = generator.generate_questions(
            law_content=law_content,
            law_article_number=law_article,
            question_type="MCQ",
            recent_questions=recent_questions,
            count=1
        )
        
        print(f"\n✅ 成功生成 {len(questions)} 道題目")
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = OUTPUT_DIR / f"duplicate_prevention_{timestamp}.json"
        output_data = {
            "recent_questions": recent_questions,
            "new_questions": questions
        }
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"\n💾 題目已儲存至: {output_file}")
        
        print("\n近期題目（避免重複）：")
        for rq in recent_questions:
            print(f"  - {rq['content']}")
        print("\n新生成的題目：")
        print(json.dumps(questions, ensure_ascii=False, indent=2))
        
        print("\n✅ 防重複機制測試完成")
        return True
        
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "🧪 "*20)
    print("QuestionGenerator 實際功能測試")
    print("🧪 "*20)
    
    # Check API key
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("\n❌ 錯誤：未設定 OPENROUTER_API_KEY 環境變數")
        print("請在 .env 檔案中設定：OPENROUTER_API_KEY=your_key_here")
        sys.exit(1)
    
    print(f"\n✅ API Key 已設定（前8碼：{api_key[:8]}...）")
    
    # Run tests
    results = []
    results.append(("MCQ 生成測試", test_mcq_generation()))
    results.append(("簡答題生成測試", test_short_answer_generation()))
    results.append(("防重複機制測試", test_with_recent_questions()))
    
    # Summary
    print("\n" + "="*80)
    print("測試結果總結")
    print("="*80)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    all_passed = all(r[1] for r in results)
    
    print("\n" + "="*80)
    if all_passed:
        print("🎉 所有測試通過！QuestionGenerator 運作正常。")
    else:
        print("⚠️ 部分測試失敗，請檢查錯誤訊息。")
    print("="*80 + "\n")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
