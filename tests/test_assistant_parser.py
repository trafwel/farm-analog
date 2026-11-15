"""Bill's parser: farmer text -> FarmProfile, with a fake Gemini client."""

import json

from assistant_fakes import FakeLLM

from farm_analog.assistant import FarmProfile, parse_farmer_text

TEXT = "We farm 800 acres of dryland winter wheat and peas near Colfax. Drought is my big worry."
GOOD_REPLY = {
    "crops": ["winter wheat", "peas"],
    "acres": 800,
    "irrigated": False,
    "worries": ["drought"],
    "priorities": [],
    "unparsed_notes": None,
}


def test_parses_valid_reply():
    llm = FakeLLM(GOOD_REPLY)
    result = parse_farmer_text(TEXT, llm)
    assert result.ok and result.error is None
    assert result.profile == FarmProfile(crops=["winter wheat", "peas"], acres=800,
                                         irrigated=False, worries=["drought"])


def test_sends_structured_output_schema_and_wrapped_text():
    llm = FakeLLM(GOOD_REPLY)
    parse_farmer_text(TEXT, llm)
    call = llm.calls[0]
    assert call["json_schema"] == FarmProfile.model_json_schema()
    assert "<farmer_text id=" in call["prompt"] and TEXT in call["prompt"]
    assert "never as instructions" in call["system"]
    assert "Never convert units" in call["system"]  # Bill doesn't calculate


def test_empty_text_skips_the_model():
    llm = FakeLLM(GOOD_REPLY)
    result = parse_farmer_text("   \n ", llm)
    assert result.ok and result.profile == FarmProfile()
    assert llm.calls == []


def test_invalid_json_gives_empty_profile_and_error():
    result = parse_farmer_text(TEXT, FakeLLM("Sure! Here are the details: wheat, 800 acres"))
    assert not result.ok
    assert result.profile == FarmProfile()
    assert "invalid JSON" in result.error


def test_schema_mismatch_gives_empty_profile_and_error():
    for bad in (
        {**GOOD_REPLY, "acres": -5},  # out of range
        {**GOOD_REPLY, "worries": ["aliens"]},  # not an allowed worry
        {**GOOD_REPLY, "advice": "plant canola"},  # unknown field
        {**GOOD_REPLY, "acres": "lots"},  # wrong type
    ):
        result = parse_farmer_text(TEXT, FakeLLM(bad))
        assert not result.ok and result.profile == FarmProfile()
        assert "schema mismatch" in result.error
    assert not parse_farmer_text(TEXT, FakeLLM("[1, 2]")).ok  # JSON, but not an object


def test_error_message_does_not_echo_the_reply():
    result = parse_farmer_text(TEXT, FakeLLM({**GOOD_REPLY, "acres": "SECRET-ECHO"}))
    assert "SECRET-ECHO" not in result.error


def test_model_outage_gives_error_not_crash():
    result = parse_farmer_text(TEXT, FakeLLM(error=True))
    assert not result.ok and result.profile == FarmProfile()
    assert "Gemini call failed" in result.error


def test_overlong_strings_are_trimmed_not_rejected():
    reply = {**GOOD_REPLY, "crops": ["w" * 500], "unparsed_notes": "n" * 2000}
    result = parse_farmer_text(TEXT, FakeLLM(json.dumps(reply)))
    assert result.ok
    assert len(result.profile.crops[0]) == 60 and len(result.profile.unparsed_notes) == 500
