"""
Translator Service - Handles translation of questions between Traditional Chinese (zh-TW) and English (en).
Provides both single-question translation and bilingual question generation.
"""
import logging
import uuid
from typing import Dict, List, Optional, Tuple, Literal
from pydantic import BaseModel, Field, ValidationError
from services.llm_client import LLMClient, DEFAULT_MODEL

logger = logging.getLogger(__name__)


class TranslatedQuestion(BaseModel):
    """Pydantic model for validating translated question content."""
    content: str = Field(..., min_length=1, description="The translated question text")
    options: Optional[List[str]] = Field(None, description="Translated options for MCQ, null for ShortAnswer")
    correct_answer: str = Field(..., min_length=1, description="The translated correct answer")
    ai_explanation: str = Field(..., min_length=1, description="The translated explanation")


class BilingualQuestion(BaseModel):
    """Pydantic model for validating bilingual question generation."""
    zh_tw: TranslatedQuestion = Field(..., description="Traditional Chinese version")
    en: TranslatedQuestion = Field(..., description="English version")


class Translator:
    """Translates questions between zh-TW and EN, and generates bilingual questions."""
    
    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize Translator with LLM client.
        
        Args:
            api_key: OpenRouter API key (defaults to environment variable)
            model: Model name (defaults to thinking model for quality)
        """
        self.llm_client = LLMClient(api_key=api_key, model=model or DEFAULT_MODEL)
        
        if not self.llm_client.api_key:
            logger.warning("OPENROUTER_API_KEY is not set. Translation will fail.")
    
    def translate_question_to_en(
        self,
        question_dict: Dict
    ) -> Dict:
        """
        Translate a zh-TW question to English.
        
        Args:
            question_dict: Dictionary with zh-TW question content, options, correct_answer, ai_explanation
            
        Returns:
            Dictionary with English translated content
            
        Raises:
            ValueError: If translation fails after retries or validation fails
        """
        question_content = question_dict.get('content', '')
        options = question_dict.get('options', [])
        correct_answer = question_dict.get('correct_answer', '')
        ai_explanation = question_dict.get('ai_explanation', '')
        question_type = question_dict.get('type', 'MCQ')
        
        # Build options text for translation context
        options_text = ""
        if options:
            options_text = "Multiple choice options:\n"
            for opt in options:
                options_text += f"  {opt}\n"
        
        # Build options JSON format for the schema (outside f-string to avoid backslash issues)
        options_json_format = '["A. ...", "B. ...", "C. ...", "D. ..."]' if options else "null"
        
        user_prompt = f"""Translate the following Traditional Chinese patent law question to fluent English.
Maintain the technical accuracy and all important details.
Ensure the translated question is clear and appropriate for exam context.

Original zh-TW question:
{question_content}

{options_text}

Correct answer (zh-TW): {correct_answer}

Explanation (zh-TW):
{ai_explanation}

Provide the translation in the following JSON format (do NOT include markdown code blocks, just raw JSON):
{{
  "content": "English question text",
  "options": {options_json_format},
  "correct_answer": "English correct answer",
  "ai_explanation": "English explanation"
}}
"""
        
        system_prompt = """You are an expert translator specializing in legal and patent terminology.
You have deep knowledge of both Traditional Chinese (Taiwan Patent Law) and English legal terminology.

Translate the question maintaining:
1. Technical accuracy and legal precision
2. All important distinctions between similar concepts
3. Proper patent law terminology in English
4. Clarity and naturalness in English phrasing
5. Consistency with the provided correct answer and explanation

Output ONLY valid JSON, no markdown, no additional text.
"""
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                parsed_json = self.llm_client.call_llm_json(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    timeout=60,
                    max_retries=1
                )
                
                # Validate using Pydantic
                translated = TranslatedQuestion(**parsed_json)
                result = translated.model_dump()
                result['type'] = question_type
                result['lang'] = 'en'
                
                logger.info(f"Successfully translated question to English")
                return result
                
            except ValidationError as e:
                logger.error(f"Translation validation failed (attempt {attempt+1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise ValueError(f"Translation validation failed: {e}")
            except Exception as e:
                logger.error(f"Error translating question (attempt {attempt+1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise
        
        raise ValueError("Failed to translate question after multiple retries.")
    
    def generate_bilingual_question(
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
        Generate bilingual questions (zh-TW and EN) for a law article in a single LLM call.
        Ensures semantic consistency between language versions.
        
        Args:
            law_content_zh: Content of the law article in Traditional Chinese
            law_content_en: Content of the law article in English
            law_article_number: Article number for reference
            question_type: Type of questions to generate ("MCQ" or "ShortAnswer")
            recent_questions_zh: List of recent zh-TW questions to avoid duplicates
            recent_questions_en: List of recent en questions to avoid duplicates
            count: Number of question pairs to generate
            
        Returns:
            List of tuples: [(zh_tw_question_dict, en_question_dict), ...]
            
        Raises:
            ValueError: If generation fails or validation fails after retries
        """
        if not recent_questions_zh:
            recent_questions_zh = []
        if not recent_questions_en:
            recent_questions_en = []
        
        # Format recent questions to avoid duplicates
        recent_qs_zh_text = ""
        if recent_questions_zh:
            recent_qs_zh_text = "Recent zh-TW questions (generate something DIFFERENT):\n"
            for q in recent_questions_zh[:3]:
                recent_qs_zh_text += f"- {q.get('content', '')}\n"
        
        recent_qs_en_text = ""
        if recent_questions_en:
            recent_qs_en_text = "Recent EN questions (generate something DIFFERENT):\n"
            for q in recent_questions_en[:3]:
                recent_qs_en_text += f"- {q.get('content', '')}\n"
        
        # Build options JSON format strings
        if question_type == "MCQ":
            zh_options_format = '["A. ...", "B. ...", "C. ...", "D. ..."]'
            en_options_format = '["A. ...", "B. ...", "C. ...", "D. ..."]'
        else:
            zh_options_format = 'null'
            en_options_format = 'null'
        
        # Build the JSON schema template outside f-string
        json_schema_template = f'''{{
  "zh_tw": {{
    "content": "Traditional Chinese question",
    "options": {zh_options_format},
    "correct_answer": "Traditional Chinese answer",
    "ai_explanation": "Traditional Chinese explanation"
  }},
  "en": {{
    "content": "English question",
    "options": {en_options_format},
    "correct_answer": "English answer",
    "ai_explanation": "English explanation"
  }}
}}'''
        
        user_prompt = f"""Generate {count} {question_type} question pair(s) for the Patent Act Article {law_article_number}.
Generate questions in BOTH Traditional Chinese (zh-TW) AND English (en) SIMULTANEOUSLY.
The English question must be a precise translation/equivalent of the Chinese question.

Article {law_article_number} (Traditional Chinese):
{law_content_zh}

Article {law_article_number} (English):
{law_content_en}

{recent_qs_zh_text}

{recent_qs_en_text}

CRITICAL: The zh-TW and English versions MUST have identical meaning and answer.
Both versions must reference the same legal concept with appropriate terminology in their respective languages.

For each question pair, provide ONE JSON object with both language versions:
{json_schema_template}

Output a JSON array of such objects. No markdown, no additional text, just raw JSON array.
"""
        
        system_prompt = f"""You are an expert in Taiwan Patent Law with fluent bilingual skills in Traditional Chinese and English.
Your task is to generate exam questions in BOTH languages simultaneously, ensuring perfect semantic alignment.

Guidelines:
1. Each question pair (zh-TW, EN) must have IDENTICAL meaning and correct answer
2. Use appropriate legal terminology in each language
3. Ensure both versions are clear and exam-appropriate
4. For MCQ: Use A, B, C, D options consistently in both languages (same logical position)
5. Question type: {question_type}
6. All output must be valid JSON only - no markdown, no text outside JSON

Output Format:
- If generating {count} question pair(s), output a JSON array with {count} element(s)
- Each element has "zh_tw" and "en" keys with question details
"""
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                parsed_json = self.llm_client.call_llm_json(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    timeout=90,
                    max_retries=1
                )
                
                # Ensure it's a list
                if isinstance(parsed_json, dict):
                    if "questions" in parsed_json:
                        parsed_json = parsed_json["questions"]
                    else:
                        parsed_json = [parsed_json]
                
                # Validate and process each question pair
                result_pairs = []
                validation_failed = False
                
                for item in parsed_json:
                    try:
                        bilingual = BilingualQuestion(**item)
                        
                        # Generate shared base_question_id for linking zh-TW and EN versions
                        base_question_id = str(uuid.uuid4())
                        
                        zh_tw_dict = bilingual.zh_tw.model_dump()
                        zh_tw_dict['type'] = question_type
                        zh_tw_dict['lang'] = 'zh-TW'
                        zh_tw_dict['base_question_id'] = base_question_id
                        
                        en_dict = bilingual.en.model_dump()
                        en_dict['type'] = question_type
                        en_dict['lang'] = 'en'
                        en_dict['base_question_id'] = base_question_id
                        
                        result_pairs.append((zh_tw_dict, en_dict))
                        
                    except ValidationError as e:
                        logger.error(f"Question pair validation failed: {e}\nItem: {item}")
                        validation_failed = True
                        break
                
                if validation_failed:
                    if attempt == max_retries - 1:
                        raise ValueError("Generated question pairs do not match schema after multiple retries.")
                    continue
                
                logger.info(f"Successfully generated {len(result_pairs)} bilingual question pair(s)")
                return result_pairs
                
            except Exception as e:
                logger.error(f"Error generating bilingual questions (attempt {attempt+1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise
        
        raise ValueError("Failed to generate bilingual questions after multiple retries.")
