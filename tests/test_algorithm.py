"""Kern gegen Handrechnung und Gegenproben: Lehrbeispiele, alle 2^n Auswahlen, LP, drei Flussverfahren, Zulässigkeit, Schachtelung der Preisreihe."""

import pytest

import pj_closure as cl
import pj_constants as C
import pj_evaluation as ev
import pj_scenario as sc

SMALL = (2, 3, 6, 2, 100)


def _chosen_names(inst, sol):
    return [inst.names[i] for i in range(inst.n) if sol.chosen[i]]


def test_shared_dc_by_hand():
    """DC kostet 10, Filialen mit Erlös 6, 7, 3: jede allein verliert, alle drei gewinnen 16 - 10 = 6. Hilfsnetz: Quellkanten 6, 7, 3, eine Senkenkante 10, drei unendliche Kanten; maximaler Fluss 10 = 16 - 6."""
    inst = sc.shared_dc()
    sol = cl.solve(inst)
    assert sol.value == 6 and sol.revenue == 16 and sol.cost == 10 and _chosen_names(inst, sol) == ["Filiale A", "Filiale B", "Filiale C", "DC"]
    assert sol.flow.value == 1000 and sol.n_paths == 2
    caps = sorted(c for _, _, c, _, _ in sol.net.arcs)
    assert caps[:4] == [300, 600, 700, 1000] and len(caps) == 7 and all(c > 1000 for c in caps[4:])
    assert cl.value_of(inst, cl.greedy_standalone(inst)) == 0 and cl.value_of(inst, cl.greedy_resources(inst)) == 6


def test_chain_by_hand():
    inst = sc.chain()
    sol = cl.solve(inst)
    assert sol.value == 3 and sol.size == 3 and (sol.revenue, sol.cost) == (20, 17)


def test_dud_has_an_empty_best_selection():
    inst = sc.dud()
    sol = cl.solve(inst)
    assert sol.value == 0 and sol.size == 0 and cl.value_of(inst, cl.everything(inst)) == -2


def test_greedy_trap_by_hand():
    """Zwei DCs (je 10), Erlöse 11, 6, 9: Optimum 26 - 20 = 6 mit allen; nur A gibt 1, A + C gibt 0; Einzelprüfung wählt nur A."""
    inst = sc.greedy_trap()
    sol = cl.solve(inst)
    assert sol.value == 6 and sol.size == 5
    assert cl.value_of(inst, cl.greedy_standalone(inst)) == 1
    assert cl.brute_force(inst)[0] == 6


def test_either_or_by_hand():
    """Filiale (Erlös 10), zwei DCs zu 6: Pflicht kostet 12 -> Auswahl leer; Alternative genügt ein DC -> Gewinn 4."""
    inst = sc.either_or()
    assert cl.solve(inst).value == 0
    value, chosen, lp, frac = cl.solve_or(inst)
    assert value == 4 and sum(chosen) == 2 and lp == pytest.approx(4.0) and frac == 0


@pytest.mark.parametrize("seed", C.SMALL_SEEDS)
def test_cut_equals_all_selections_and_lp_on_small_instances(seed):
    inst = sc.generate(*SMALL, seed)
    sol = cl.solve(inst, keep_flows=False)
    assert sol.value == cl.brute_force(inst)[0]
    lp, x = cl.lp_closure(inst)
    assert lp == pytest.approx(sol.value, abs=1e-6) and all(abs(v - round(v)) < 1e-6 for v in x)


@pytest.mark.parametrize("seed", C.DIST_SEEDS[:20])
def test_selection_is_closed_and_value_is_positive_revenue_minus_flow(seed):
    inst = sc.generate(3, 4, 8, 2, 100, seed)
    sol = cl.solve(inst)
    assert cl.is_closed(inst, sol.chosen) and cl.is_closed(inst, sol.largest)
    assert sol.value == inst.positive_total() - sol.flow.value // 100 and sol.value >= 0
    assert cl.value_of(inst, sol.largest) == sol.value and all(b or not a for a, b in zip(sol.chosen, sol.largest))
    assert sol.unique == (sol.chosen == sol.largest)


@pytest.mark.parametrize("seed", C.DIST_SEEDS[:20])
def test_all_three_flow_methods_find_the_same_value_and_selection(seed):
    inst = sc.generate(3, 4, 8, 2, 100, seed)
    sols = [cl.solve(inst, algo) for algo in C.ALGORITHMS]
    assert len({s.value for s in sols}) == 1 and len({s.chosen for s in sols}) == 1


def test_no_method_beats_the_optimum_and_all_are_feasible_or_trivial():
    for seed in C.DIST_SEEDS[:40]:
        inst = sc.generate(3, 4, 8, 2, 100, seed)
        opt = cl.solve(inst, keep_flows=False).value
        for choose in (cl.greedy_standalone, cl.greedy_resources, cl.nothing):
            ch = choose(inst)
            assert cl.is_closed(inst, ch) and cl.value_of(inst, ch) <= opt


def test_price_sweep_is_nested_and_monotone_in_the_extremes():
    inst = sc.generate(3, 4, 8, 2, 100, 24)
    sw = ev.sweep(inst)
    assert sw["nested"] and sw["sets"][0] == (False,) * inst.n and all(sw["sets"][-1][i] for i in range(inst.n) if inst.weights[i] > 0)
    assert sw["values"] == sorted(sw["values"])
    assert sw["values"][0] == 0 and sw["percents"][0] == 0 and sw["percents"][-1] == 300
    assert sw["values"][sw["percents"].index(100)] == 30


def test_or_model_never_pays_less_than_all_required():
    for seed in C.DIST_SEEDS[:10]:
        inst = sc.generate(3, 4, 8, 2, 100, seed)
        assert cl.solve_or(inst)[0] >= cl.solve(inst, keep_flows=False).value


def test_aux_net_scales_only_the_revenue():
    inst = sc.shared_dc()
    net = cl.aux_net(inst, scale_revenue=50)
    profit = sorted(c for _, _, c, _, k in net.arcs if k == sc.K_PROFIT)
    cost = [c for _, _, c, _, k in net.arcs if k == sc.K_COST]
    assert profit == [150, 300, 350] and cost == [1000]
