import os
import json
import requests
from services.question_gen import QuestionGenerator

generator = QuestionGenerator()
def test_short_answer():
    law_content = "本法所稱專利，分為下列三種：一、發明專利。二、新型專利。三、設計專利。"
    law_article = "第2條"
    try:
        generator.generate_questions(
            law_content=law_content,
            law_article_number=law_article,
            question_type="ShortAnswer",
            recent_questions=[],
            count=1
        )
    except Exception as e:
        print("EXCEPTION:", e)
        
test_short_answer()
