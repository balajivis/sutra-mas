"""Lightweight LLM client for the research pipeline.

Two providers:
  - Claude Opus 4.6 (via Azure Anthropic Foundry) — default for analysis
  - GPT 5.1 (via Azure OpenAI) — for coding, fast tasks

Reads credentials from .env (project root) or experiments/.env.
"""

import json
import os
import time

import anthropic
from openai import AzureOpenAI

# Load .env — check project root first, then experiments/
for _env_path in [".env", "experiments/.env"]:
    if os.path.exists(_env_path):
        with open(_env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    if key.strip() not in os.environ:
                        os.environ[key.strip()] = value.strip()


def _get_anthropic_client() -> anthropic.Anthropic:
    """Create an Anthropic client using Azure endpoint."""
    endpoint = os.environ.get("AZURE_ANTHROPIC_ENDPOINT", "")
    api_key = os.environ.get("AZURE_API_KEY", "")

    if endpoint and api_key:
        return anthropic.Anthropic(api_key=api_key, base_url=endpoint)

    # Fallback to direct Anthropic
    return anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


def _get_openai_client() -> AzureOpenAI:
    """Create an Azure OpenAI client."""
    return AzureOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ.get("AZURE_OPENAI_API_KEY", os.environ.get("AZURE_API_KEY", "")),
        api_version="2025-01-01-preview",
    )


# --- Claude (default) ---

def chat(
    system: str,
    user_message: str,
    model: str = "claude-opus-4-6",
    max_tokens: int = 2048,
    temperature: float = 0.3,
) -> str:
    """Chat completion via Claude. Returns the response text."""
    client = _get_anthropic_client()
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text if response.content else ""


def chat_json(
    system: str,
    user_message: str,
    model: str = "claude-opus-4-6",
    max_tokens: int = 2048,
    temperature: float = 0.3,
) -> dict:
    """Chat completion via Claude that parses JSON from the response."""
    text = chat(system, user_message, model, max_tokens, temperature)

    # Extract JSON from markdown code blocks if present
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        text = text[start:end].strip()

    return json.loads(text)


# --- GPT (for coding, fast tasks) ---

def gpt_chat(
    system: str,
    user_message: str,
    model: str = None,
    max_tokens: int = 4096,
    **kwargs,
) -> str:
    """Chat completion via Azure OpenAI (GPT 5.1). Returns the response text."""
    model = model or os.environ.get("AZURE_OPENAI_MODEL", "gpt-5.1")
    client = _get_openai_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ],
        max_completion_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""


def gpt_chat_json(
    system: str,
    user_message: str,
    model: str = None,
    max_tokens: int = 4096,
    **kwargs,
) -> dict:
    """Chat completion via GPT that parses JSON from the response."""
    text = gpt_chat(system, user_message, model, max_tokens)

    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        text = text[start:end].strip()

    return json.loads(text)


# --- Embeddings ---

def embed(
    texts: list[str],
    model: str = None,
) -> list[list[float]]:
    """Generate embeddings via Azure OpenAI (text-embedding-3-small).

    Accepts a batch of texts (up to 16 recommended per call).
    Returns a list of embedding vectors (1536 dimensions each).
    """
    model = model or os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")
    client = _get_openai_client()
    response = client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in response.data]
