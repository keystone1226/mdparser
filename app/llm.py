from __future__ import annotations

from typing import Optional

from openai import OpenAI

from .config import settings


def build_fabrix_client() -> Optional[OpenAI]:
    """Return an OpenAI SDK client wired to the Fabrix Open API.

    Fabrix follows the OpenAI chat/completions schema but authenticates through
    three custom headers (x-fabrix-client, x-openapi-token, x-llm-model-id) and
    expects the SDK `api_key` field to be the literal string "EMPTY".
    """
    if not settings.llm_enabled:
        return None

    default_headers = {
        "X-FABRIX-CLIENT": settings.fabrix_client_key,
        "X-OPENAPI-TOKEN": settings.fabrix_openapi_token,
        "X-LLM-MODEL-ID": settings.fabrix_model_id,
    }
    if settings.fabrix_user_email:
        default_headers["X-GENERATIVE-AI-USER-EMAIL"] = settings.fabrix_user_email

    return OpenAI(
        base_url=settings.fabrix_endpoint_url,
        api_key="EMPTY",
        default_headers=default_headers,
    )
