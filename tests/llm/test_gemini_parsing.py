"""Gemini response parsing is exercised with stand-in objects; no network."""
from types import SimpleNamespace

from app.llm.gemini import GeminiProvider


def _fake_response(text: str, prompt_tokens=100, out_tokens=50, uris=("https://a.example/x",)):
    chunks = [SimpleNamespace(web=SimpleNamespace(uri=u, title="A")) for u in uris]
    cand = SimpleNamespace(grounding_metadata=SimpleNamespace(grounding_chunks=chunks, web_search_queries=["q1"]))
    usage = SimpleNamespace(prompt_token_count=prompt_tokens, candidates_token_count=out_tokens, thoughts_token_count=0)
    return SimpleNamespace(text=text, candidates=[cand], usage_metadata=usage)


def test_response_to_llm_response_extracts_usage_cost_and_grounding():
    p = GeminiProvider(api_key="x", fast_model="gemini-3.8-flash", smart_model="gemini-3.1-pro-preview", vision_model="gemini-3.8-flash")
    res = p._to_llm_response(_fake_response('{"a": 1}'), model="gemini-3.8-flash")
    assert res.text == '{"a": 1}'
    assert res.input_tokens == 100 and res.output_tokens == 50
    assert res.cost_usd > 0
    assert res.grounding[0]["uri"] == "https://a.example/x"
    assert res.model == "gemini-3.8-flash"
