from farm_analog import rotations as rot
from farm_analog.match import palouse_demo
from farm_analog.schema import AnalogResult

WW, P, SW, F = "Winter wheat", "Pulses", "Spring wheat", "Fallow"


def test_crop_groups():
    assert rot.crop_group(24) == WW and rot.crop_group(53) == P and rot.crop_group(52) == P
    assert rot.crop_group(61) == F and rot.crop_group(23) == SW
    assert rot.crop_group(141) is None  # forest is not cropland
    assert rot.crop_group(None) is None and rot.crop_group(float("nan")) is None
    assert rot.crop_group(44) == "Other crops"


def test_rotation_of_finds_cycles_in_any_starting_year():
    two_year = [WW, F, WW, F, WW, F, WW, F]
    assert rot.rotation_of(two_year) == rot.Rotation("cycle", (WW, F))
    assert rot.rotation_of(two_year[1:] + [WW]) == rot.Rotation("cycle", (WW, F))
    three_year = [P, WW, SW, P, WW, SW, P, WW]
    assert rot.rotation_of(three_year) == rot.Rotation("cycle", (WW, SW, P))
    assert rot.rotation_of([WW] * 8).name == "Continuous winter wheat"
    wwf = rot.rotation_of([F, WW, WW, F, WW, WW, F, WW])
    assert wwf.name == "Winter wheat → Winter wheat → Fallow"
    assert rot.rotation_of([WW, F, WW, F, WW, None, WW, F]) == rot.Rotation("cycle", (WW, F))
    # A gap year must not shift the cycle, and a repeated crop is one crop.
    assert rot.rotation_of([WW, F, WW, F, WW, F, None, WW]) == rot.Rotation("cycle", (WW, F))
    assert rot.rotation_of([WW, WW, WW, None, WW, WW, WW, WW]).name == "Continuous winter wheat"


def test_rotation_of_handles_messy_and_sparse_pixels():
    assert rot.rotation_of([WW, None, None, None, None, None, None, P]) is None
    messy = [WW, P, SW, WW, F, P, WW, SW]
    r = rot.rotation_of(messy)
    assert r.kind == "flexible" and WW in r.crops
    assert r.name.startswith("Flexible mix of")


def test_rotation_shares_drop_rare_rotations():
    seqs = [[WW, F] * 4] * 18 + [[WW] * 8] * 1 + [[WW, P] * 4] * 1
    shares = rot.rotation_shares(seqs)
    assert shares[rot.Rotation("cycle", (WW, F))] == 0.9
    assert rot.Rotation("cycle", (WW,)) in shares  # 5% is kept
    assert rot.rotation_shares([[None] * 8]) == {}


def test_strategies_put_current_first_and_give_at_least_three():
    a_wf, a_wsp = rot.Rotation("cycle", (WW, F)), rot.Rotation("cycle", (WW, SW, P))
    a_wp = rot.Rotation("cycle", (WW, P))
    field = {a_wsp: 0.7, a_wp: 0.3}
    analogs = {1: {a_wf: 0.6, a_wp: 0.4}, 2: {a_wf: 0.5, a_wsp: 0.2, a_wp: 0.3},
               3: {a_wp: 1.0}}
    agree = {1: (8, 8), 2: (7, 8), 3: (5, 8)}
    out = rot.strategies(field, analogs, agree)
    assert len(out) >= 3
    assert out[0].current and out[0].name == "Winter wheat → Spring wheat → Pulses"
    names = [s.name for s in out[1:]]
    assert names[0] == "Winter wheat → Pulses"  # most used across analogs (57%)
    assert "Winter wheat → Fallow" in names
    wp = out[1]
    assert wp.analogs_using == 3 and wp.analogs_checked == 3
    assert any("nitrogen" in b.lower() for b in wp.benefits)
    assert any("8 of 8" in e for e in wp.evidence)
    wf = next(s for s in out if s.name == "Winter wheat → Fallow")
    assert any("erosion" in r for r in wf.risks)
    assert all(s.gaps[-1] == rot.CHECK_LOCALLY for s in out)


def test_current_rotation_without_analog_support_says_so():
    mono = rot.Rotation("cycle", (WW,))
    out = rot.strategies({mono: 1.0}, {1: {rot.Rotation("cycle", (WW, P)): 1.0}}, {1: (8, 8)})
    assert out[0].current and out[0].analogs_using == 0
    assert "evidence that it suits" in out[0].gaps[0]
    assert any("no break" in r for r in out[0].risks)


def test_no_field_rotation_still_lists_analog_rotations():
    out = rot.strategies({}, {1: {rot.Rotation("cycle", (WW, F)): 1.0}}, {1: (6, 8)})
    assert len(out) == 1 and not out[0].current


def test_rare_rotations_fill_up_to_three_and_say_so():
    wf, wp, wsf = (rot.Rotation("cycle", c) for c in [(WW, F), (WW, P), (WW, SW, F)])
    analogs = {1: {wf: 0.92, wp: 0.05, wsf: 0.03}, 2: {wf: 0.95, wp: 0.05}}
    out = rot.strategies({wf: 1.0}, analogs, {1: (8, 8), 2: (8, 8)})
    assert [s.name for s in out] == ["Winter wheat → Fallow", "Winter wheat → Pulses",
                                     "Winter wheat → Spring wheat → Fallow"]
    assert out[1].analogs_using == 0 and "evidence that it suits" in out[1].gaps[0]


def test_attach_keeps_the_contract_valid():
    result, _ = palouse_demo(top_n=3)
    s = rot.strategies({}, {1: {rot.Rotation("cycle", (WW, P)): 1.0}}, {1: (1, 1)})
    enriched = rot.attach(result, s)
    AnalogResult.model_validate(enriched.model_dump())
    assert enriched.rotations[0].crops == [WW, P]
