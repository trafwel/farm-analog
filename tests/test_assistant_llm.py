"""GeminiLLM wrapper, driven by a fake genai client (no network)."""

import pytest
from assistant_fakes import FakeGenaiClient

from farm_analog import config
from farm_analog.assistant import FarmProfile, GeminiLLM, LLMError
from farm_analog.assistant.llm import _SUPPORTED_SCHEMA_KEYS, gemini_schema


def _keys(schema, found=None):
    found = set() if found is None else found
    if isinstance(schema, dict):
        for key, value in schema.items():
            if key in ("properties", "$defs"):
                for sub in value.values():
                    _keys(sub, found)
            else:
                found.add(key)
                _keys(value, found)
    elif isinstance(schema, list):
        for item in schema:
            _keys(item, found)
    return found


def test_schema_keeps_only_supported_keywords():
    schema = gemini_schema(FarmProfile.model_json_schema())
    assert _keys(schema) <= _SUPPORTED_SCHEMA_KEYS
    assert set(schema["properties"]) == set(FarmProfile.model_fields)


def test_json_request_sets_structured_output():
    client = FakeGenaiClient('{"crops": []}')
    llm = GeminiLLM(client=client)
    assert llm.generate(system="s", prompt="p", json_schema=FarmProfile.model_json_schema())
    assert client.kwargs["model"] == config.GEMINI_MODEL
    cfg = client.kwargs["config"]
    assert cfg.response_mime_type == "application/json"
    assert cfg.response_json_schema["title"] == "FarmProfile"
    assert cfg.system_instruction == "s"


def test_text_request_has_no_schema():
    client = FakeGenaiClient("hello")
    assert GeminiLLM(client=client).generate(system="s", prompt="p") == "hello"
    assert client.kwargs["config"].response_json_schema is None


def test_sdk_error_becomes_llm_error_without_prompt_text():
    client = FakeGenaiClient(exc=RuntimeError("400 bad request: <farmer_text>secret</farmer_text>"))
    with pytest.raises(LLMError) as info:
        GeminiLLM(client=client).generate(system="s", prompt="p")
    assert "secret" not in str(info.value)
    assert info.value.__cause__ is None and info.value.__suppress_context__


def test_empty_reply_is_an_error():
    with pytest.raises(LLMError):
        GeminiLLM(client=FakeGenaiClient(text=None)).generate(system="s", prompt="p")


def test_missing_key_is_a_clear_error(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)  # no .env here, so load_dotenv finds nothing
    with pytest.raises(LLMError, match="GEMINI_API_KEY"):
        GeminiLLM()
