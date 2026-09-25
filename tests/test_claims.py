"""Jede Zahl, die README, Hilfetexte und Beispieltexte nennen, ist hier belegt (Standardeinstellungen, feste Netze, Seeds ab 100000).
Auswahl, Gewinn und durchsuchte Kanten sind ganzzahlig und deterministisch (eigener Zufallsstrom); Verteilungen werden mit Bändern geprüft, Sekunden nur als grobe Größenordnung."""

import pytest

import pj_closure as cl
import pj_constants as C
import pj_evaluation as ev
import pj_scenario as sc

P = ev.DEFAULT_PARAMS


def _analyse(name):
    p = C.PRESETS[name]
    return ev.analyse(ev.Params(p["net"], p["p"], p["d"], p["s"], p["fan"], p["cost"], p["seed"], p["algorithm"]))


def _chosen(a):
    return [a["inst"].labels[i] for i in range(a["inst"].n) if a["sol"].chosen[i]]


def test_teaching_examples_by_hand():
    """Gemeinsames DC: 6 (jede Filiale allein verliert); Kette: 3; Nichts lohnt: 0, Alles nehmen -2; Greedy-Falle: 6 gegen 1 der Einzelprüfung; Eine genügt: Schnitt 0, MIP 4."""
    shared = _analyse("🤝 Gemeinsames DC")
    assert shared["values"] == {"optimum": 6, "resources": 6, "projects": 0, "all": 6, "nothing": 0}
    assert shared["inst"].weights == (6, 7, 3, -10) and all(w + -10 < 0 for w in (6, 7, 3))
    chain = _analyse("⛓️ Kette")
    assert chain["values"]["optimum"] == 3 and chain["values"]["projects"] == 3 and chain["values"]["resources"] == 3
    dud = _analyse("🕳️ Nichts lohnt")
    assert dud["values"]["optimum"] == 0 and dud["values"]["all"] == -2 and dud["values"]["projects"] == 0 and not any(dud["sol"].chosen)
    trap = _analyse("🎯 Greedy-Falle")
    assert trap["values"]["optimum"] == 6 and trap["values"]["projects"] == 1 and sum(trap["sol"].chosen) == 5
    either = _analyse("🔂 Eine genügt")
    assert either["values"]["optimum"] == 0 and cl.solve_or(either["inst"])[0] == 4


def test_default_preset_numbers():
    """Zufallsnetz Seed 24: 5 von 8 Filialen, Gewinn 30 (Erlös 180, Kosten 150), Einzelprüfung 0, Ressourcen-Greedy 12, Alles nehmen 27; Dinic 12 Wege und 224 durchsuchte Kanten,
    Edmonds-Karp 441, Ford-Fulkerson 364 (15 Wege); bei „eine genügt“ wären es 96."""
    a = _analyse("🚚 Zufallsnetz")
    s = a["sol"]
    assert a["values"] == {"optimum": 30, "resources": 12, "projects": 0, "all": 27, "nothing": 0}
    assert (s.revenue, s.cost, s.n_paths, s.scanned) == (180, 150, 12, 224) and _chosen(a) == ["W1", "W2", "D1", "D2", "D3", "F1", "F2", "F3", "F4", "F5"]
    assert ev.verdict(a["inst"], s, a["values"]) == ("mixed", 5, 8)
    e = ev.analyse(ev.DEFAULT_PARAMS._replace(algorithm="bfs"))["sol"]
    f = ev.analyse(ev.DEFAULT_PARAMS._replace(algorithm="dfs"))["sol"]
    assert (e.scanned, e.n_paths, f.scanned, f.n_paths) == (441, 12, 364, 15)
    assert cl.solve_or(a["inst"])[0] == 96


def test_ties_and_large_presets():
    """Seed 21: Gewinn 7 mit 5 von 8 Filialen; die größte beste Auswahl nimmt zusätzlich W1, D1, F1, F2, F3; Einzelprüfung und Ressourcen-Greedy 0.
    Große Instanz: 19 von 24 Filialen mit Gewinn 24 (Erlös 648, Kosten 624), Ressourcen-Greedy 0, Alles nehmen -11, 37 Wege, 1328 durchsuchte Kanten, mehrere beste Auswahlen."""
    t = _analyse("🔀 Mehrere beste Schnitte")
    assert t["values"] == {"optimum": 7, "resources": 0, "projects": 0, "all": 7, "nothing": 0} and not t["sol"].unique
    assert [t["inst"].labels[i] for i in range(t["inst"].n) if t["sol"].largest[i] and not t["sol"].chosen[i]] == ["W1", "D1", "F1", "F2", "F3"]
    assert ev.verdict(t["inst"], t["sol"], t["values"]) == ("mixed", 5, 8)
    g = _analyse("🏗️ Große Instanz")
    assert g["values"] == {"optimum": 24, "resources": 0, "projects": 0, "all": -11, "nothing": 0} and not g["sol"].unique
    assert (g["sol"].revenue, g["sol"].cost, g["sol"].n_paths, g["sol"].scanned) == (648, 624, 37, 1328) and ev.verdict(g["inst"], g["sol"], g["values"]) == ("mixed", 19, 24)


@pytest.fixture(scope="module")
def dist():
    return ev.distribution(P)


def test_distribution_at_default_settings(dist):
    """40 feste Netze (3 Werke, 4 DCs, 8 Filialen, Kosten 100 %): in 34 lohnt sich eine Auswahl, im Mittel sind 86 % der Filialen gewählt; Einzelprüfung verliert im Mittel 98 % und findet in 30 von 34
    Netzen nichts, Ressourcen-Greedy verliert 44 % und trifft das Optimum in 17 von 34, Alles nehmen verliert 58 %; das LP ist in keinem Netz gebrochen, in 1 Netz gibt es mehrere beste Auswahlen."""
    assert dist["n"] == 40 and dist["positive"] == 34 and dist["share_mean"] == pytest.approx(0.86, abs=0.02)
    assert dist["loss_projects"] == pytest.approx(0.98, abs=0.02) and dist["zero_projects"] == 30 and dist["hit_projects"] == 0
    assert dist["loss_resources"] == pytest.approx(0.44, abs=0.03) and dist["hit_resources"] == 17 and dist["zero_resources"] == 11
    assert dist["loss_all"] == pytest.approx(0.58, abs=0.03)
    assert dist["lp_fractional"] == 0 and dist["lp_gap_max"] < 1e-6 and dist["nonunique"] == 1


def test_cost_slider_help_numbers():
    """Kostenniveau 100 %: in 34 von 40 Netzen lohnt sich eine Auswahl; 150 %: 18; 200 %: 3; 250 %: keines."""
    counts = {c: ev.distribution(P._replace(cost=c))["positive"] for c in (50, 100, 150, 200, 250)}
    assert counts == {50: 40, 100: 34, 150: 18, 200: 3, 250: 0}


def test_the_resource_greedy_fails_when_stores_need_several_dcs():
    """Braucht jede Filiale genau ein DC, ist Ressourcen-Greedy fast optimal (Verlust 3 %, Optimum in 36 von 40); mit bis zu 2 DCs verliert es 44 %, mit bis zu 3 DCs 71 % (Optimum in 6 von 33)."""
    one, two, three = (ev.distribution(P._replace(fan=f)) for f in (1, 2, 3))
    assert one["loss_resources"] == pytest.approx(0.03, abs=0.02) and one["hit_resources"] == 36 and one["positive"] == 40
    assert two["loss_resources"] == pytest.approx(0.44, abs=0.03)
    assert three["loss_resources"] == pytest.approx(0.71, abs=0.03) and three["hit_resources"] == 6 and three["positive"] == 33
    assert one["loss_projects"] > 0.85


def test_small_instances_agree_with_all_selections_and_lp():
    """40 kleine Netze (2 Werke, 3 DCs, 6 Filialen = 11 Knoten): der Schnitt liefert in 40 von 40 denselben Gewinn wie das Durchprobieren aller 2048 Auswahlen und wie das LP."""
    assert ev.small_check() == {"n": 40, "brute": 40, "lp": 40}


def test_price_sweep_is_nested_but_jumps(dist):
    """Preisreihe 0 bis 300 % über 40 Netze: in 40 von 40 geschachtelt; im Mittel 2,9 verschiedene Auswahlen, der größte Sprung nimmt im Mittel 11,3 Knoten (78 % der größten Auswahl) auf einmal auf, höchstens 15."""
    ss = ev.sweep_stats(P)
    assert ss["nested"] == 40 and ss["distinct_mean"] == pytest.approx(2.9, abs=0.3) and ss["jump_mean"] == pytest.approx(11.3, abs=1.0)
    assert ss["jump_share_mean"] == pytest.approx(0.78, abs=0.05) and ss["jump_max"] == 15
    sw = ev.sweep(sc.generate(3, 4, 8, 2, 100, 24))
    assert sw["distinct"] == 3 and sw["max_jump"] == 10 and sw["values"][sw["percents"].index(100)] == 30
    assert sorted(set(sw["sizes"])) == [0, 10, 15] and max(sw["sizes"]) == 15


def test_one_of_several_prerequisites_is_no_longer_a_cut():
    """Genügt EINE Anlage (Alternativen): das MIP findet in 39 von 40 Netzen mehr als der Schnitt, der Schnitt verschenkt im Mittel 50 % des Gewinns, und das LP ist in 6 von 40 Netzen gebrochen (bei „alle nötig“ in 0)."""
    oc = ev.or_control(P)
    assert oc["n"] == 40 and oc["better"] == 39 and oc["gain_mean"] == pytest.approx(0.50, abs=0.05) and oc["lp_fractional"] == 6


def test_scaling_dinic_pulls_away_from_edmonds_karp():
    """Durchsuchte Kanten (Mittel über 10 Netze je Größe): 13 Knoten Dinic 179, Edmonds-Karp 239, Ford-Fulkerson 165 (die Tiefensuche ist hier sogar etwas sparsamer als Dinic); 19 Knoten Faktor Edmonds-Karp / Dinic 1,6;
    366 Knoten Faktor 19 (Dinic 9146 gegen 172 817); das LP der Auswahl braucht auf jeder Größe wenige Millisekunden."""
    rows = ev.scaling()
    small, mid, big = rows[0], rows[1], rows[-1]
    assert round(small["n"]) == 13 and small["dinic"] == pytest.approx(179, abs=8) and small["bfs"] == pytest.approx(239, abs=8) and small["dfs"] == pytest.approx(165, abs=8) and small["dfs"] < small["dinic"]
    assert round(mid["n"]) == 19 and mid["bfs"] / mid["dinic"] == pytest.approx(1.6, abs=0.15)
    assert round(big["n"]) == 366 and big["bfs"] / big["dinic"] == pytest.approx(19, abs=1.5) and big["dinic"] == pytest.approx(9146, rel=0.05)
    factors = [r["bfs"] / r["dinic"] for r in rows]
    assert factors == sorted(factors) and factors[0] == pytest.approx(1.3, abs=0.15)
    assert all(r["lp_seconds"] < 0.1 for r in rows)


def test_weight_ranges_of_the_generator():
    """Erlöse der Filialen 10 bis 50, Kosten der Verteilzentren 20 bis 50, der Werke 10 bis 30 (bei Kostenniveau 100 %)."""
    revenue, dc, plant = [], [], []
    for seed in C.DIST_SEEDS:
        inst = sc.generate(3, 4, 8, 2, 100, seed)
        for k, w in zip(inst.kinds, inst.weights):
            {"store": revenue, "dc": dc, "plant": plant}[k].append(abs(w))
    assert (min(revenue), max(revenue)) == (10, 50) and (min(dc), max(dc)) == (20, 50) and (min(plant), max(plant)) == (10, 30)
