import httpx
from tenacity import retry,  stop_after_attempt, wait_exponential, retry_if_exception_type
import logging
from typing import List, Dict

from app.core.config import settings
from app.core.llm import BaseLLMProvider, LLMProviderError, LLMQuotaError

logger = logging.getLogger(__name__)

class LLMClient(BaseLLMProvider):
    def __init__(self):
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = settings.GROQ_MODEL
        self.api_key = settings.GROQ_API_KEY
        
        if not self.api_key:
             raise ValueError("GROQ_API_KEY is not configured.")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException, LLMProviderError, LLMQuotaError)),
        reraise=True
    )
    async def chat(self, messages: List[Dict], **kwargs) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1024)
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.base_url, json=payload, headers=headers)
                
                if response.status_code == 429:
                    raise LLMQuotaError("Rate limit exceeded (429).")
                
                if response.status_code >= 500:
                    raise LLMProviderError(f"Server error: {response.status_code}")

                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]

        except Exception as e:
            logger.error(f"LLM Call failed: {e}")
            raise

    # For compatibility if needed, but we'll use chat
    async def generate(self, system_prompt: str, user_message: str, **kwargs) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        return await self.chat(messages, **kwargs)
