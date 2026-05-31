"""
Local model backend — serves acharya responses from the locally fine-tuned
gita-lm model instead of the Claude API.

Only `prabhupada` has a trained LoRA adapter (see https://github.com/Aryag1507/gita-lm).
For other acharyas, callers should fall back to the Claude backend.

Enable by setting environment variables:
    USE_LOCAL_MODEL=1
    GITA_LM_PATH=/absolute/path/to/gita-lm   (defaults to ../gita-lm)

The model is loaded lazily and cached, so the first call pays the load cost
(~a few seconds on Apple Silicon) and subsequent calls are fast.
"""
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Optional

# Acharyas that have a trained local adapter. Others must fall back to Claude.
LOCAL_SUPPORTED = {"prabhupada"}


def is_enabled() -> bool:
    return os.environ.get("USE_LOCAL_MODEL", "").strip() in {"1", "true", "True", "yes"}


def supports(acharya: str) -> bool:
    """Whether the local model can serve this acharya."""
    return is_enabled() and acharya.lower() in LOCAL_SUPPORTED


def _gita_lm_path() -> Path:
    raw = os.environ.get("GITA_LM_PATH", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    # Default: sibling directory next to gita-insight-engine
    return (Path(__file__).parent.parent.parent / "gita-lm").resolve()


@lru_cache(maxsize=1)
def _load_backend():
    """
    Import gita-lm and load the fine-tuned model + tokenizer once.
    Returns a tuple (config, model, tokenizer, generate_fn) or raises
    a RuntimeError with an actionable message if gita-lm isn't available.
    """
    lm_path = _gita_lm_path()
    if not lm_path.exists():
        raise RuntimeError(
            f"gita-lm not found at {lm_path}. Clone https://github.com/Aryag1507/gita-lm "
            f"and/or set GITA_LM_PATH to its location."
        )

    # Make gita-lm importable without packaging it
    if str(lm_path) not in sys.path:
        sys.path.insert(0, str(lm_path))

    try:
        from config import get_config                       # gita-lm/config.py
        from generate import load_model                     # gita-lm/generate.py
        from src.evaluation.evaluate import generate_commentary
    except ImportError as e:
        raise RuntimeError(f"Failed to import gita-lm modules from {lm_path}: {e}")

    cfg = get_config()
    model, tokenizer = load_model(cfg)
    model.eval()
    return cfg, model, tokenizer, generate_commentary


def chat_as_acharya_local(
    message: str,
    acharya: str,
    excerpts: list[dict],
    history: list[dict],
    max_new_tokens: int = 200,
) -> str:
    """
    Drop-in local replacement for analysis.qa.chat_as_acharya for supported acharyas.

    Builds a prompt in the same format the model was fine-tuned on, optionally
    grounded in retrieved excerpts, and generates a single response.

    Raises RuntimeError if called for an unsupported acharya — callers should
    check supports(acharya) first and fall back to Claude otherwise.
    """
    if acharya.lower() not in LOCAL_SUPPORTED:
        raise RuntimeError(
            f"Local model has no adapter for '{acharya}'. Fall back to the Claude backend."
        )

    cfg, model, tokenizer, generate_commentary = _load_backend()

    # Compose a prompt consistent with the fine-tuning format. The excerpts give
    # the model grounding (RAG-style); the message frames the question.
    excerpt_text = (
        "\n\n".join(f"[{e['verse']}]\n{e['text']}" for e in excerpts)
        if excerpts else ""
    )

    prompt_parts = []
    if excerpt_text:
        prompt_parts.append(f"Context from commentaries:\n{excerpt_text}\n")
    prompt_parts.append(f"Question: {message}")
    prompt_parts.append("### Commentary:\n")
    prompt = "\n".join(prompt_parts)

    candidates = generate_commentary(
        model,
        tokenizer,
        prompt,
        cfg.device,
        max_new_tokens=max_new_tokens,
        num_return_sequences=1,
    )
    return candidates[0].strip()
