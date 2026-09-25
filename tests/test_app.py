"""Rauchtests der Streamlit-Oberfläche per AppTest: Standard, jedes Preset, alle Flussverfahren, Randgrößen, Bilder-Regler, ausgeblendete Regler, Permalink, Experimente auf Abruf, Schlüssel und Achsensperre."""

import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import pj_constants as C
from pj_presets import PRESET_KEYS

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app.py"

EXPECTED = {
    "🚚 Zufallsnetz": "Optimal: **5 von 8** Filialen mit Gewinn 30 (Erlös 180, Kosten 150)",
    "🤝 Gemeinsames DC": "Es lohnt sich für **alle 3** Filialen: Gewinn 6",
    "⛓️ Kette": "Es lohnt sich für **alle 1** Filialen: Gewinn 3",
    "🕳️ Nichts lohnt": "Nichts lohnt sich",
    "🎯 Greedy-Falle": "Es lohnt sich für **alle 3** Filialen: Gewinn 6",
    "🔀 Mehrere beste Schnitte": "Optimal: **5 von 8** Filialen mit Gewinn 7",
    "🔂 Eine genügt": "Nichts lohnt sich",
    "🏗️ Große Instanz": "Optimal: **19 von 24** Filialen mit Gewinn 24",
}


def _run(setup=None, timeout=300):
    at = AppTest.from_file(str(APP), default_timeout=timeout)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    if setup is not None:
        setup(at)
        at.run()
        assert not at.exception, [e.value for e in at.exception]
    return at


def _apply(at, p):
    for key, state_key in PRESET_KEYS.items():
        at.session_state[state_key] = p[key]


def _texts(at):
    return [e.value for e in list(at.success) + list(at.warning) + list(at.info) + list(at.error)]


def _has(at, prefix):
    return any(prefix in t for t in _texts(at))


def _metric(at, label):
    return [m.value for m in at.metric if m.label == label]


def _step_slider(at):
    found = [s for s in at.slider if s.key == "pj_step"]
    return found[0] if found else None


def test_default_renders_without_exception():
    at = _run()
    assert any("Hilfsnetz" in m.value for m in at.markdown)
    assert _has(at, EXPECTED["🚚 Zufallsnetz"]) and not at.error
    assert _metric(at, "Gewinn der Auswahl")[0] == "30" and _metric(at, "Gewählte Filialen")[0] == "5 von 8" and _metric(at, "Durchsuchte Kanten")[0] == "224"
    assert _step_slider(at).value == _step_slider(at).max == 13


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_every_preset_renders_with_its_verdict(name):
    at = _run(lambda a: _apply(a, C.PRESETS[name]))
    assert _has(at, EXPECTED[name]), _texts(at)


@pytest.mark.parametrize("algorithm", list(C.ALGORITHMS))
def test_every_flow_method_renders(algorithm):
    at = _run(lambda a: a.session_state.__setitem__("algorithm_radio", algorithm))
    assert _has(at, EXPECTED["🚚 Zufallsnetz"]) and not at.error


def test_extreme_sizes_render():
    for vals in ((("p_slider", C.P_MIN), ("d_slider", C.D_MIN), ("s_slider", C.S_MIN), ("fan_slider", C.FAN_MIN), ("cost_slider", C.COST_MIN)),
                 (("p_slider", C.P_MAX), ("d_slider", C.D_MAX), ("s_slider", C.S_MAX), ("fan_slider", C.FAN_MAX), ("cost_slider", C.COST_MAX))):
        def setup(at, vals=vals):
            for key, value in vals:
                at.session_state[key] = value
        at = _run(setup)
        assert not at.error and (_has(at, "Optimal") or _has(at, "Nichts lohnt sich") or _has(at, "Es lohnt sich"))


def test_step_slider_moves_through_all_frames():
    at = _run(lambda a: _apply(a, C.PRESETS["🤝 Gemeinsames DC"]))
    top = int(_step_slider(at).max)
    assert top == 3
    for value in range(top + 1):
        _step_slider(at).set_value(value)
        at.run()
        assert not at.exception and _step_slider(at).value == value


def test_hidden_controls_keep_their_values_across_a_net_switch():
    at = _run()
    at.sidebar.slider(key="cost_slider").set_value(150)
    at.run()
    at.sidebar.selectbox(key="net_select").set_value("chain")
    at.run()
    assert not at.exception and not [w for w in at.sidebar.slider if w.key == "cost_slider"]
    at.sidebar.selectbox(key="net_select").set_value("random")
    at.run()
    assert at.sidebar.slider(key="cost_slider").value == 150 and not at.exception


def test_permalink_settings_are_loaded_and_clamped():
    at = AppTest.from_file(str(APP), default_timeout=300)
    at.query_params["net"] = "random"
    at.query_params["fan"] = "9"
    at.query_params["cost"] = "137"
    at.query_params["algorithm"] = "bfs"
    at.query_params["s"] = "12"
    at.run()
    assert not at.exception
    assert at.sidebar.slider(key="fan_slider").value == C.FAN_MAX and at.sidebar.slider(key="cost_slider").value == 140
    assert at.sidebar.radio(key="algorithm_radio").value == "bfs" and at.sidebar.slider(key="s_slider").value == 12


def test_experiments_run_on_demand():
    at = _run()
    next(b for b in at.button if b.key == "or_start").click().run()
    assert not at.exception and any("MIP besser als Schnitt" == m.label for m in at.metric)
    next(b for b in at.button if b.key == "check_start").click().run()
    assert not at.exception and _metric(at, "Schnitt = alle Auswahlen") == ["40 von 40"]
    next(b for b in at.button if b.key == "scaling_start").click().run()
    assert not at.exception and any(t.startswith("Mittel über 10 feste Netze je Größe") for t in [c.value for c in at.caption])


def test_either_or_example_shows_the_or_comparison_without_a_button():
    at = _run(lambda a: _apply(a, C.PRESETS["🔂 Eine genügt"]))
    assert any(m.label.startswith("Gewinn: Schnitt (alle nötig)") and m.value == "0 gegen 4" for m in at.metric)


def test_fixed_examples_skip_the_distribution_and_say_so():
    at = _run(lambda a: _apply(a, C.PRESETS["⛓️ Kette"]))
    assert any("Festes Beispiel" in t for t in _texts(at))


def test_source_has_explicit_chart_keys_and_locked_axes():
    app = APP.read_text(encoding="utf-8")
    assert all(re.search(r"plotly_chart\(.*key=", line) for line in app.splitlines() if "st.plotly_chart(" in line)
    viz = (ROOT / "pj_visualization.py").read_text(encoding="utf-8")
    assert viz.count("return _base(fig") + viz.count("return lock_axes(fig)") >= 5 and "def lock_axes" in viz
