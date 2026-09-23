"""AI integration adapters.

This package is the designated location for provider-specific AI adapters.
Add one module per provider or capability:

    src/ai/openai.py       — OpenAI / OpenAI-compatible chat + embeddings
    src/ai/anthropic.py    — Anthropic / Claude
    src/ai/speech.py       — Speech-to-text (Whisper, Deepgram, etc.)
    src/ai/vision.py       — Vision / OCR
    src/ai/embeddings.py   — Embedding generation (provider-neutral)

Design principles:
- Each adapter wraps the provider SDK or makes direct httpx calls.
- No LangChain, LlamaIndex, or similar frameworks unless actually required.
- Adapters call src.core.http_client.get_client() for raw HTTP.
- Adapters are called from controllers, never from models or endpoints.
- Keep adapter interfaces narrow — one function per capability.
"""
