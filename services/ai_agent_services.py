from openai import OpenAI
from typing import cast, List, Dict, Any
import os
from dotenv import load_dotenv
from services.ai_prompt_service import get_system_prompt_natal, get_user_prompt_natal

load_dotenv()
# Set your OpenAI API key securely
api_key = os.getenv("OPENAI_API_KEY")


# Automatically uses OPENAI_API_KEY from environment variable
client = OpenAI(api_key=api_key)

# Function to generate astrology AI summary and return JSON response
def generate_astrology_AI_summary(system_prompt: str, user_prompt: str, model: str = "gpt-4.1"):
    messages_for_llm = cast(List[Dict[str, Any]], [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ])
    try:
        response = client.chat.completions.create(
            model=model,
            messages=cast(Any, messages_for_llm),
            temperature=0.8,
            max_tokens=10000,
        )

        # Safely extract content from the choice message, handling both object and dict shapes.
        choice = response.choices[0]
        content = None
        # If choice is a dict-like structure
        try:
            if isinstance(choice, dict):
                msg = choice.get("message") or {}
                if isinstance(msg, dict):
                    content = msg.get("content") or choice.get("text")
                else:
                    content = choice.get("text")
            else:
                # object-like access
                msg = getattr(choice, "message", None)
                if msg is not None:
                    content = getattr(msg, "content", None)
                else:
                    content = getattr(choice, "text", None)
        except Exception:
            content = None

        response_text = content.strip() if isinstance(content, str) else ""
        response_text = content.strip() if isinstance(content, str) else ""
        if not response_text:
            print("Warning: response content is empty or None; using empty string as response_text.")

        # Token usage information from the API response
        if hasattr(response, 'usage') and response.usage is not None:
            print("Prompt tokens:", response.usage.prompt_tokens)
            print("Completion tokens:", response.usage.completion_tokens)
            print("Total tokens:", response.usage.total_tokens)
        # print("========== Response from generate_astrology_AI_summary ===========")
        # print(response_text)
        print("===============================================================")
        return response_text
    except Exception as e:
        return f"❌ Error occurred: {e}"

    