"""
Question Generator Service - Generates MCQ and Short Answer questions using LLM.
Uses diversity checks to avoid duplicate questions.
Supports both monolingual (zh-TW only) and bilingual (zh-TW + EN) generation.
"""
import logging
import uuid
from typing import List, Dict, Optional, Literal, Tuple
from pydantic import BaseModel, Field, ValidationError
from services.llm_client import LLMClient, DEFAULT_MODEL
from services.translator import Translator

logger = logging.getLogger(__name__)


class GeneratedQuestion(BaseModel):
    """Pydantic model for validating LLM-generated questions."""
    content: str = Field(..., min_length=1, description="The question text")
    options: Optional[List[str]] = Field(None, description="Options for MCQ, null for ShortAnswer")
    correct_answer: str = Field(..., min_length=1, description="The correct answer")
    ai_explanation: str = Field(..., min_length=1, description="Explanation of the answer")
    type: Optional[Literal["MCQ", "ShortAnswer"]] = Field(None, description="Question type, added by system")


class QuestionGenerator:
    """Generates exam questions for law articles using LLM."""
    
    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize Question Generator with LLM client.
        
        Args:
            api_key: OpenRouter API key (defaults to environment variable)
            model: Model name (defaults to thinking model for quality)
        """
        self.llm_client = LLMClient(api_key=api_key, model=model or DEFAULT_MODEL)
        self.translator = Translator(api_key=api_key, model=model or DEFAULT_MODEL)
        
        if not self.llm_client.api_key:
            logger.warning("OPENROUTER_API_KEY is not set. Question generation will fail.")

    def generate_questions(
        self,
        law_content: str,
        law_article_number: str,
        question_type: Literal["MCQ", "ShortAnswer"],
        recent_questions: List[Dict] = None,
        count: int = 1,
        law_type: str = "patent-act",
        law_name: str = None
    ) -> List[Dict]:
        """
        Generate questions for a specific law article using OpenRouter.
        
        Args:
            law_content: The content of the law article
            law_article_number: Article number for reference
            question_type: Type of questions to generate ("MCQ" or "ShortAnswer")
            recent_questions: List of recent questions to avoid duplicates
            count: Number of questions to generate
            law_type: Law type identifier (e.g., "patent-act", "administrative-appeal")
            law_name: Law name in Chinese (e.g., "專利法", "訴願法"). If None, inferred from law_type
            
        Returns:
            List of validated question dicts
            
        Raises:
            ValueError: If generation fails or validation fails after retries
        """
        if not recent_questions:
            recent_questions = []

        # Infer law name from law_type if not provided
        if law_name is None:
            from db.models import LAW_TYPES
            law_name = LAW_TYPES.get(law_type, {}).get('name_zh', '專利法')

        # Format recent questions to avoid duplicates
        recent_qs_text = ""
        if recent_questions:
            recent_qs_text = "Here are the most recent questions generated for this article. Please generate something DIFFERENT:\n"
            for q in recent_questions:
                recent_qs_text += f"- {q.get('content', '')}\n"

        user_prompt = f"""
你是台灣{law_name}的專家。請根據以下法條生成 {count} 道 {question_type} 題目：
{law_name} {law_article_number}：{law_content}

{recent_qs_text}

重要：
1. 所有題目、選項、答案和解釋都必須使用繁體中文
2. 題目中提到法條時，必須使用「{law_name}」，不要使用其他法律名稱
3. 題目應該聚焦在這條法條的內容和應用
"""
        
        system_prompt = """你是法律考試題目生成專家。
請以嚴格的 JSON 格式輸出，必須是物件列表。
每個物件必須符合以下格式（全部使用繁體中文）：
{
  "content": "題目文字（繁體中文）",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."], // 僅當題型為 MCQ 時需要，否則為 null 或空列表
  "correct_answer": "正確答案（繁體中文）",
  "ai_explanation": "詳細解釋為什麼這個答案正確，需引用法條（繁體中文）"
}
不要在 JSON 外包含任何其他文字。不要使用 markdown 代碼塊，直接輸出原始 JSON 列表。
"""

        max_retries = 3
        for attempt in range(max_retries):
            try:
                parsed_json = self.llm_client.call_llm_json(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    timeout=60,
                    max_retries=1  # Let outer loop handle retries
                )
                
                # Ensure it's a list
                if isinstance(parsed_json, dict):
                    # Sometimes models output an object wrapping the list, like {"questions": [...]}
                    if "questions" in parsed_json:
                        parsed_json = parsed_json["questions"]
                    else:
                        parsed_json = [parsed_json]
                
                # Validate using Pydantic
                validated_questions = []
                validation_failed = False
                for item in parsed_json:
                    try:
                        # Add type before validation
                        item['type'] = question_type
                        if question_type == 'ShortAnswer' and 'options' not in item:
                            item['options'] = None
                        
                        question = GeneratedQuestion(**item)
                        validated_questions.append(question.model_dump())
                    except ValidationError as e:
                        logger.error(f"Question validation failed: {e}\nItem: {item}")
                        validation_failed = True
                        break

                if validation_failed:
                    if attempt == max_retries - 1:
                        raise ValueError("Generated question does not match schema after multiple retries.")
                    continue
                
                # If we reach here, validation succeeded - return the questions
                logger.info(f"Successfully generated {len(validated_questions)} questions")
                return validated_questions
                
            except Exception as e:
                logger.error(f"Error generating questions (attempt {attempt+1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise
        
        raise ValueError("Failed to generate questions after multiple retries.")
    
    def generate_bilingual_questions(
        self,
        law_content_zh: str,
        law_content_en: str,
        law_article_number: str,
        question_type: Literal["MCQ", "ShortAnswer"],
        recent_questions_zh: List[Dict] = None,
        recent_questions_en: List[Dict] = None,
        count: int = 1
    ) -> List[Tuple[Dict, Dict]]:
        """
        Generate bilingual questions (zh-TW and EN) for a law article.
        Both versions are generated simultaneously with identical meaning.
        
        Args:
            law_content_zh: Content of law article in Traditional Chinese
            law_content_en: Content of law article in English
            law_article_number: Article number for reference
            question_type: Type of questions ("MCQ" or "ShortAnswer")
            recent_questions_zh: Recent zh-TW questions to avoid duplicates
            recent_questions_en: Recent en questions to avoid duplicates
            count: Number of question pairs to generate
            
        Returns:
            List of tuples: [(zh_tw_question_dict, en_question_dict), ...]
            
        Raises:
            ValueError: If generation fails after retries
        """
        try:
            result_pairs = self.translator.generate_bilingual_question(
                law_content_zh=law_content_zh,
                law_content_en=law_content_en,
                law_article_number=law_article_number,
                question_type=question_type,
                recent_questions_zh=recent_questions_zh,
                recent_questions_en=recent_questions_en,
                count=count
            )
            
            logger.info(f"Successfully generated {len(result_pairs)} bilingual question pair(s)")
            return result_pairs
            
        except Exception as e:
            logger.error(f"Error generating bilingual questions: {e}")
            raise

