"""
Grader Service - Evaluates short answer questions using LLM.
Returns scores of 0, 0.5, or 1 with detailed feedback.
"""
import logging
from typing import Dict
from pydantic import BaseModel, Field, field_validator, ValidationError
from services.llm_client import LLMClient, GRADING_MODEL

logger = logging.getLogger(__name__)


class GradingResult(BaseModel):
    """Pydantic model for validating LLM grading output."""
    score: float = Field(..., description="The score: 0 (incorrect), 0.5 (partial), or 1 (correct)")
    feedback: str = Field(..., min_length=1, description="Detailed feedback in Traditional Chinese")
    
    @field_validator('score')
    @classmethod
    def validate_score(cls, v: float) -> float:
        """Ensure score is exactly 0, 0.5, or 1."""
        if v not in [0, 0.5, 1]:
            raise ValueError(f"Score must be 0, 0.5, or 1, got {v}")
        return v


class Grader:
    """Evaluates short answer questions using LLM."""
    
    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize Grader with LLM client.
        
        Args:
            api_key: OpenRouter API key (defaults to environment variable)
            model: Model name (defaults to fast grading model)
        """
        self.llm_client = LLMClient(api_key=api_key, model=model or GRADING_MODEL)
        
        if not self.llm_client.api_key:
            logger.warning("OPENROUTER_API_KEY is not set. Grading will fail.")
    
    def grade_answer(
        self, 
        question: str,
        user_answer: str,
        correct_answer: str,
        law_content: str = None
    ) -> Dict[str, any]:
        """
        Grade a short answer question using OpenRouter LLM.
        
        Args:
            question: The question text
            user_answer: The user's submitted answer
            correct_answer: The correct/reference answer
            law_content: Optional law article content for context
            
        Returns:
            dict: {"score": 0|0.5|1, "feedback": "..."}
            
        Raises:
            ValueError: If grading fails after retries or validation fails
        """
        # Build context
        law_context = ""
        if law_content:
            law_context = f"\n相關法條內容：{law_content}\n"
        
        user_prompt = f"""
請評分以下簡答題作答：

題目：{question}

標準答案：{correct_answer}

學生答案：{user_answer}
{law_context}

請給予評分與反饋。評分標準：
- 1 分：答案完全正確，涵蓋所有關鍵要點
- 0.5 分：答案部分正確，涵蓋部分關鍵要點但有缺漏或小錯誤
- 0 分：答案錯誤或完全偏離主題

請以繁體中文提供詳細的反饋，說明評分理由，並指出答案的優缺點。
"""
        
        system_prompt = """你是台灣專利法考試的評分專家。
請以嚴格的 JSON 格式輸出，必須符合以下格式：
{
  "score": 0 或 0.5 或 1（數字，不是字串），
  "feedback": "詳細的評分反饋（繁體中文）"
}

評分必須嚴格公正：
- score 必須是數字 0、0.5 或 1
- feedback 必須詳細說明評分理由，包括答案的正確與不足之處

不要在 JSON 外包含任何其他文字。不要使用 markdown 代碼塊，直接輸出原始 JSON 物件。
"""
        
        try:
            # Call LLM with lower temperature for consistent grading
            parsed_json = self.llm_client.call_llm_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                timeout=30,
                max_retries=3
            )
            
            # Validate using Pydantic
            grading_result = GradingResult(**parsed_json)
            
            logger.info(f"Successfully graded answer. Score: {grading_result.score}")
            return grading_result.model_dump()
            
        except ValidationError as e:
            logger.error(f"Grading result validation failed: {e}")
            raise ValueError(f"Invalid grading result: {e}")
        except Exception as e:
            logger.error(f"Failed to grade answer: {e}")
            raise
