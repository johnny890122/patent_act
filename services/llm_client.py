"""
OpenRouter LLM Client - Base module for all LLM interactions.
Provides a unified interface for calling OpenRouter API with standard error handling.
"""
import os
import json
import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# OpenRouter API Configuration
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.5")
GRADING_MODEL = os.environ.get("OPENROUTER_GRADING_MODEL", "anthropic/claude-3.5-haiku")


class LLMClient:
    """Base client for OpenRouter API interactions."""
    
    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize LLM client.
        
        Args:
            api_key: OpenRouter API key (defaults to environment variable)
            model: Model name (defaults to environment variable or claude-sonnet-4.5)
        """
        self.api_key = api_key or OPENROUTER_API_KEY
        self.model = model or DEFAULT_MODEL
        
        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY is not set. LLM calls will fail.")
    
    def _build_headers(self) -> Dict[str, str]:
        """Build standard headers for OpenRouter API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/johnny890122/patent_act",
            "X-Title": "Patent Act Assistant",
            "Content-Type": "application/json"
        }
    
    def _clean_json_output(self, content: str) -> str:
        """
        Clean LLM output by removing markdown code blocks.
        
        Args:
            content: Raw LLM output string
            
        Returns:
            Cleaned JSON string
        """
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return content.strip()
    
    def call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        timeout: int = 60,
        max_retries: int = 3
    ) -> str:
        """
        Call OpenRouter API with retry logic and error handling.
        
        Args:
            system_prompt: System message for the LLM
            user_prompt: User message for the LLM
            temperature: Optional temperature parameter (0.0-1.0)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            
        Returns:
            Raw content string from LLM response
            
        Raises:
            ValueError: If LLM returns empty content or fails after retries
            requests.exceptions.RequestException: If API call fails
        """
        headers = self._build_headers()
        
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }
        
        # Add optional parameters
        if temperature is not None:
            payload["temperature"] = temperature
        
        # Add response_format for GPT models
        if "gpt-4" in self.model or "gpt-3.5" in self.model:
            payload["response_format"] = {"type": "json_object"}
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    OPENROUTER_API_URL,
                    headers=headers,
                    json=payload,
                    timeout=timeout
                )
                response.raise_for_status()
                data = response.json()
                
                content = data['choices'][0]['message'].get('content')
                
                if content is None:
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"LLM returned empty content. Retrying... ({attempt+1}/{max_retries})"
                        )
                        continue
                    raise ValueError("LLM returned empty or None content after multiple retries.")
                
                return content
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error calling OpenRouter API: {e}")
                if attempt == max_retries - 1:
                    raise
            except KeyError as e:
                logger.error(f"Unexpected response format from OpenRouter: {e}")
                if attempt == max_retries - 1:
                    raise ValueError(f"Unexpected response format from OpenRouter: {e}")
        
        raise ValueError("Failed to call LLM after multiple retries.")
    
    def call_llm_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        timeout: int = 60,
        max_retries: int = 3
    ) -> Any:
        """
        Call OpenRouter API and parse response as JSON.
        
        Args:
            system_prompt: System message for the LLM
            user_prompt: User message for the LLM
            temperature: Optional temperature parameter (0.0-1.0)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            
        Returns:
            Parsed JSON object (dict or list)
            
        Raises:
            ValueError: If LLM returns invalid JSON or fails after retries
        """
        for attempt in range(max_retries):
            try:
                content = self.call_llm(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    timeout=timeout,
                    max_retries=1  # call_llm will handle one attempt
                )
                
                # Clean and parse JSON
                cleaned_content = self._clean_json_output(content)
                parsed_json = json.loads(cleaned_content, strict=False)
                
                return parsed_json
                
            except json.JSONDecodeError as e:
                logger.error(
                    f"Failed to parse LLM output as JSON: {e}\nOutput was: {content}"
                )
                if attempt == max_retries - 1:
                    raise ValueError(f"Failed to parse LLM response: {e}")
        
        raise ValueError("Failed to get valid JSON from LLM after multiple retries.")
