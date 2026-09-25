"""Presets: vollständig, in den Grenzen, und jedes Beispiel zeigt, was sein Hilfetext behauptet."""

import pytest

import pj_constants as C
import pj_evaluation as ev
import pj_presets as P

KEYS = set(P.PRESET_KEYS)


def _params(p):
    return ev.Params(p["net"], p["p"], p["d"], p["s"], p["fan"], p["cost"], p["seed"], p["algorithm"])


def test_every_preset_has_help_and_all_keys():
    assert set(C.PRESETS) == set(C.PRESET_HELP) and len(C.PRESETS) == 8
    assert all(C.PRESET_HELP[name].strip() for name in C.PRESETS)
    for name, p in C.PRESETS.items():
        assert set(p) == KEYS, name


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_preset_values_are_inside_the_bounds_and_on_the_step_grid(name):
    p = C.PRESETS[name]
    assert p["net"] in C.NETS and p["algorithm"] in C.ALGORITHMS
    for key, state_key in P.PRESET_KEYS.items():
        spec = P.SETTING_SPECS[state_key]
        if spec.lo is not None:
            assert spec.lo <= p[key] <= spec.hi, (name, key)
    assert (p["cost"] - C.COST_MIN) % 10 == 0


def test_setting_specs_have_room_to_move():
    """Ein Regler mit lo == hi würde Streamlit abstürzen lassen."""
    assert all(spec.lo < spec.hi for spec in P.SETTING_SPECS.values() if spec.lo is not None)


def test_presets_use_seeds_outside_the_distribution_set():
    for name, p in C.PRESETS.items():
        assert p["seed"] not in C.DIST_SEEDS, name


def test_defaults_equal_the_random_net_preset():
    p = C.PRESETS["🚚 Zufallsnetz"]
    assert (p["net"], p["algorithm"], p["p"], p["d"], p["s"], p["fan"], p["cost"], p["seed"]) == (
        C.DEFAULT_NET, C.DEFAULT_ALGORITHM, C.DEFAULT_P, C.DEFAULT_D, C.DEFAULT_S, C.DEFAULT_FAN, C.DEFAULT_COST, C.DEFAULT_SEED)


def test_fixed_presets_hide_the_random_controls():
    assert {n for n, p in C.PRESETS.items() if p["net"] in C.FIXED_NETS} == {"🤝 Gemeinsames DC", "⛓️ Kette", "🕳️ Nichts lohnt", "🎯 Greedy-Falle", "🔂 Eine genügt"}


def test_the_presets_show_both_good_and_bad_news():
    """Der Schnitt ist nie schlechter als ein einfaches Verfahren; die Presets zeigen Fälle, in denen die einfachen Verfahren scheitern (Gemeinsames DC, Zufallsnetz),
    und Fälle, in denen sie gleich gut sind (Kette) oder in denen es nichts zu holen gibt (Nichts lohnt)."""
    res = {name: ev.analyse(_params(p)) for name, p in C.PRESETS.items()}
    assert all(r["values"]["optimum"] >= max(r["values"].values()) for r in res.values())
    assert res["🤝 Gemeinsames DC"]["values"]["projects"] == 0 < res["🤝 Gemeinsames DC"]["values"]["optimum"]
    assert res["⛓️ Kette"]["values"]["projects"] == res["⛓️ Kette"]["values"]["optimum"]
    assert res["🕳️ Nichts lohnt"]["values"]["optimum"] == 0
    assert res["🚚 Zufallsnetz"]["values"]["resources"] < res["🚚 Zufallsnetz"]["values"]["optimum"]


def test_the_ties_preset_has_several_best_selections():
    assert not ev.analyse(_params(C.PRESETS["🔀 Mehrere beste Schnitte"]))["sol"].unique
    assert ev.analyse(_params(C.PRESETS["🚚 Zufallsnetz"]))["sol"].unique
