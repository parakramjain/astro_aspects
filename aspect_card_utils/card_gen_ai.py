from datetime import date
from openai import OpenAI

client = OpenAI()


ASPECT_CARD_JSON_SCHEMA = {
  "name": "aspect_card",
  "schema": {
    "type": "object",
    "additionalProperties": False,
    "required": ["id","pair","applies_to","core_meaning","facets","risk_notes",
                 "actionables","keywords","quality_tags","weights_hint",
                 "modifiers","theme_overlays","refs","provenance","locales","retrieval"],
    "properties": {
      "id": {"type":"string"},
      "pair": {"type":"array","items":{"type":"string"}, "minItems":3, "maxItems":3},
      "applies_to": {"type":"array","items":{"type":"string"}},
      "core_meaning": {"type":"string"},
      "facets": {
        "type":"object",
        "required": ["career","relationships","money","health_adj"],
        "properties": {
          "career":{"type":"string"},
          "relationships":{"type":"string"},
          "money":{"type":"string"},
          "health_adj":{"type":"string"}
        }
      },
      "risk_notes": {"type":"array","items":{"type":"string"}},
      "actionables": {
        "type":"object",
        "required": ["applying","exact","separating"],
        "properties": {
          "applying":{"type":"array","items":{"type":"string"}},
          "exact":{"type":"array","items":{"type":"string"}},
          "separating":{"type":"array","items":{"type":"string"}}
        }
      },
      "keywords": {"type":"array","items":{"type":"string"}},
      "quality_tags": {"type":"array","items":{"type":"string"}},
      "weights_hint": {"type":"object"},
      "modifiers": {"type":"object"},
      "theme_overlays": {"type":"array","items":{"type":"string"}},
      "refs": {"type":"array","items":{"type":"string"}},
      "provenance": {"type":"object"},
      "locales": {
        "type":"object",
        "required":["en","hi"],
        "properties":{
          "en":{"type":"object","required":["title","core","tone"],
                "properties":{"title":{"type":"string"},"core":{"type":"string"},"tone":{"type":"string"}}},
          "hi":{"type":"object","required":["title","core","tone"],
                "properties":{"title":{"type":"string"},"core":{"type":"string"},"tone":{"type":"string"}}}
        }
      },
      "retrieval": {"type":"object"}
    }
  }
}


SYSTEM_PROMPT = """You are a senior Vedic astrologer.
Write precise, practitioner-grade Aspect Cards that are:
- concise, specific, and free of fluff
- culturally sensitive (Vedic-aware) yet accessible to global users
- include pragmatic guidance for applying/exact/separating phases
- include risks/pitfalls and boundaries
Rules:
- No medical or financial guarantees; use probabilistic language.
- EN copy in neutral/warm tone; HI copy in simple, clear Hindi.
- Keep actionables verb-first and time-bound when possible.
"""

def generate_aspect_card(p1, asp_code, p2, asp_name, applies_to, weights_hint, quality_tags_seed):
    today = str(date.today())
    user_prompt = f"""
            Input:
            - p1: {p1}
            - aspect_code: {asp_code}
            - aspect_name: {asp_name}
            - p2: {p2}
            - applies_to: {applies_to}
            - today: {today}

            Goals:
            1) Compose a canon 'core_meaning' (2–3 sentences) blending {p1} and {p2} archetypes with {asp_name.lower()} tone.
            2) Fill facets: career, relationships, money, health_adj (1–2 sentences each).
            3) Add actionables for applying/exact/separating (2–3 bullet sentences each; imperative, time-aware).
            4) Add 4–8 'risk_notes' tied to planets/aspect (no fearmongering).
            5) Provide 8–16 'keywords' useful for search/retrieval.
            6) Provide 'quality_tags' starting from seed {quality_tags_seed} and expand (e.g., benefic/challenging/mixed, fusion, external-opportunity, discipline-required).
            7) Provide bilingual 'locales': en + hi (title/core/tone).
            8) Provide 'retrieval' with short summaries for core/career/relationships/money/health_adj and 2–4 aliases.
            9) Keep content verifiable, non-deterministic claims avoided.

            Output MUST obey the provided JSON schema.
            """
    # Call responses.create with supported parameters (omit unsupported 'seed' and complex 'response_format')
    resp = client.responses.create(
        model="gpt-4.1-mini",  # or your preferred current model
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        
        temperature=0.4
    )

    # SDKs differ in shape of the response object; try common patterns to extract the returned text
    card_text = None
    # try attribute-style access (object with output list) — robustly handle multiple SDK shapes
    try:
        card_text = None
        if getattr(resp, "output", None):
            out0 = resp.output[0]

            # try different shapes for content: attribute or dict key
            content = None
            # prefer attribute-style content when available but avoid direct attribute access
            content = None
            content_attr = getattr(out0, "content", None)
            if content_attr is not None:
                content = content_attr
            elif isinstance(out0, dict) and "content" in out0:
                content = out0["content"]

            # if content is present and iterable, try to find text inside its elements
            if content:
                for c in content:
                    # prefer attribute access if available
                    txt = getattr(c, "text", None)
                    if not txt and isinstance(c, dict):
                        # common dict keys that may hold the text
                        txt = c.get("text") or c.get("content") or c.get("message")
                        # if nested dict, drill once for common nested shapes
                        if isinstance(txt, dict):
                            txt = txt.get("text") or txt.get("content")
                    if txt:
                        card_text = txt
                        break

            # fallbacks if no content/text found above
            if card_text is None:
                card_text = (
                    getattr(out0, "text", None)
                    or getattr(out0, "message", None)
                    or (out0.get("text") if isinstance(out0, dict) else None)
                    or (out0.get("message") if isinstance(out0, dict) else None)
                )
    except Exception:
        card_text = None

    # try dict-style access
    if card_text is None:
        try:
            if isinstance(resp, dict) and "output" in resp and resp["output"]:
                card_text = resp["output"][0]["content"][0].get("text")
        except Exception:
            card_text = None

    # fallback: if SDK returned a plain string or list with text
    if card_text is None:
        if isinstance(resp, str):
            card_text = resp
        elif isinstance(resp, (list, tuple)) and resp:
            first = resp[0]
            if isinstance(first, dict):
                card_text = first.get("text") or first.get("content")
            elif isinstance(first, str):
                card_text = first

    # parse JSON string to dict if needed
    import json
    if isinstance(card_text, str):
        return json.loads(card_text)
    return card_text
