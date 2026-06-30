"""Bounded report assistant (T-04 / T-11 Layer 7).

Grounded narration + bounded analyst chat over the FarmTrust evidence packet.
Deterministic-first: a no-LLM brief is the always-on narration and the fallback;
the Azure ``gpt-4o`` model is layered on top and gated off when unconfigured.
LangChain is isolated to ``llm.py`` so the provider stays swappable.
"""
