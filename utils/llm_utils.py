import tiktoken
from typing import List, Dict

def get_token_encoder(model: str):
    """Return the encoder for the given model."""
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding("cl100k_base")

def count_tokens(messages: List[Dict[str, str]], model: str = "gpt-4.1") -> int:
    """
    Count the tokens used in the messages for GPT-4.1 model.

    Args:
        messages: List of message dictionaries with 'role' and 'content'.
        model: GPT model identifier.

    Returns:
        Total token count.
    """
    encoding = get_token_encoder(model)
    token_count = 0
    for message in messages:
        # GPT models add tokens per message structure (role and content)
        token_count += len(encoding.encode(message["role"]))
        token_count += len(encoding.encode(message["content"]))
    # Adding 3 tokens per message as per OpenAI guidance for message separators.
    token_count += 3 * len(messages)
    # Add 3 tokens for priming of reply
    token_count += 3
    return token_count

def count_response_tokens(response_content: str, model: str = "gpt-4.1") -> int:
    """
    Count tokens in response from GPT-4.1.

    Args:
        response_content: Response text from LLM.
        model: GPT model identifier.

    Returns:
        Token count of response.
    """
    encoding = get_token_encoder(model)
    return len(encoding.encode(response_content.strip()))