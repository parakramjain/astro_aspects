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

# ------------------------------
# Cost Calculation Configuration
# ------------------------------
INPUT_PRICE_PER_1M = 3.00      # USD
OUTPUT_PRICE_PER_1M = 12.00    # USD

# ------------------------------
# Cost Calculation Functions
# ------------------------------
def calculate_token_cost(tokens: int, price_per_1m: float) -> float:
    """
    Calculate cost for given token count.
    Args:
        tokens (int): Number of tokens.
        price_per_1m (float): Price per 1 million tokens.
    Returns:
        float: Cost in USD.
    """
    return (tokens / 1_000_000) * price_per_1m

def calculate_total_cost(prompt_tokens: int, completion_tokens: int) -> dict:
    """
    Calculate input, output and total cost.
    Returns:
        dict: {
            "input_cost": float,
            "output_cost": float,
            "total_cost": float
        }
    """
    input_cost = calculate_token_cost(prompt_tokens, INPUT_PRICE_PER_1M)
    output_cost = calculate_token_cost(completion_tokens, OUTPUT_PRICE_PER_1M)

    return {
        "input_cost": f"${input_cost:.4f}",
        "output_cost": f"${output_cost:.4f}",
        "total_cost": f"${input_cost + output_cost:.4f}"
    }

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
            usage_info = {
                "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                "completion_tokens": getattr(response.usage, "completion_tokens", 0),
                "total_tokens": getattr(response.usage, "total_tokens", 0)
            }
            cost_info = calculate_total_cost(usage_info["prompt_tokens"], usage_info["completion_tokens"])
            print(f"Token Usage: {usage_info}, Cost: {cost_info}")
        print("===============================================================")
        return response_text
    except Exception as e:
        return f"❌ Error occurred: {e}"

    