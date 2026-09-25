"""Szenario (Voraussetzungen, Lage, Zufallsstrom) und Auswertung (Kennzahlen, Frames, Verteilungen)."""

import pytest

import pj_closure as cl
import pj_constants as C
import pj_evaluation as ev
import pj_scenario as sc

P = ev.DEFAULT_PARAMS


def _parts(a):
    return a["inst"], a["sol"], a["values"]


def test_generation_is_deterministic_and_seed_dependent():
    a, b, c = sc.generate(3, 4, 8, 2, 100, 24), sc.generate(3, 4, 8, 2, 100, 24), sc.generate(3, 4, 8, 2, 100, 25)
    assert a == b and a != c


def test_node_counts_kinds_and_prerequisite_structure():
    inst = sc.generate(4, 6, 12, 3, 100, 7)
    assert inst.n == 22 and [inst.kinds.count(k) for k in ("plant", "dc", "store")] == [4, 6, 12]
    for i, k in enumerate(inst.kinds):
        needs = inst.needs(i)
        if k == "store":
            assert 1 <= len(needs) <= 3 and all(inst.kinds[j] == "dc" for j in needs) and inst.weights[i] > 0
        elif k == "dc":
            assert 1 <= len(needs) <= 2 and all(inst.kinds[j] == "plant" for j in needs) and inst.weights[i] < 0
        else:
            assert needs == () and inst.weights[i] < 0
    assert set(inst.or_nodes) == {i for i, k in enumerate(inst.kinds) if k == "store"}


def test_cost_level_changes_only_the_costs():
    a, b = sc.generate(3, 4, 8, 2, 100, 24), sc.generate(3, 4, 8, 2, 200, 24)
    assert a.requires == b.requires and a.kinds == b.kinds and a.pos == b.pos
    for i in range(a.n):
        if a.weights[i] > 0:
            assert a.weights[i] == b.weights[i]
        else:
            assert b.weights[i] <= a.weights[i] and abs(b.weights[i] - 2 * a.weights[i]) <= 1


def test_single_fan_gives_each_store_exactly_one_dc():
    inst = sc.generate(3, 4, 8, 1, 100, 24)
    assert all(len(inst.needs(i)) == 1 for i, k in enumerate(inst.kinds) if k == "store")


def test_positions_are_inside_the_map_and_layers_do_not_overlap():
    inst = sc.generate(6, 8, 24, 3, 100, 2)
    assert all(0 <= x <= sc.MAP_W for x, _ in inst.pos)
    layers = {}
    for x, y in inst.pos:
        layers.setdefault(y, []).append(x)
    assert all(len(xs) == len(set(xs)) for xs in layers.values())


def test_lessons_and_build_dispatch():
    assert set(sc.LESSONS) == set(C.FIXED_NETS) and sc.build("shared", 9, 9, 9, 3, 300, 1).n == 4
    assert sc.build("random", 3, 4, 8, 2, 100, 24) == sc.generate(3, 4, 8, 2, 100, 24)


def test_aux_net_is_a_valid_flow_net():
    inst = sc.generate(3, 4, 8, 2, 100, 24)
    net = cl.aux_net(inst)
    assert net.s == 0 and net.t == 1 and net.n == inst.n + 2
    assert net.m == sum(1 for w in inst.weights if w != 0) + len(inst.requires)
    assert all(0 <= u < net.n and 0 <= v < net.n and c > 0 for u, v, c, _, _ in net.arcs)


def test_frames_and_verdict():
    a = ev.analyse(P)
    fr = ev.frames(a["sol"])
    assert len(fr) == a["sol"].n_paths + 1 and fr[0][0] == (0,) * a["sol"].net.m and fr[0][1] == ()
    assert ev.verdict(*_parts(a)) == ("mixed", 5, 8)
    assert ev.verdict(*_parts(ev.analyse(P._replace(net="dud"))))[0] == "empty"
    assert ev.verdict(*_parts(ev.analyse(P._replace(net="chain"))))[0] == "all"


@pytest.mark.parametrize("algo", list(C.ALGORITHMS))
def test_frames_end_at_the_maximum_flow_for_every_algorithm(algo):
    sol = ev.analyse(P._replace(algorithm=algo))["sol"]
    last = ev.frames(sol)[-1][0]
    assert sum(last[i] for i, (u, _, _, _, _) in enumerate(sol.net.arcs) if u == sol.net.s) == sol.flow.value


def test_analyse_values_cover_all_methods():
    a = ev.analyse(P)
    assert set(a["values"]) == set(ev.METHODS) and a["values"]["optimum"] == max(a["values"].values())


def test_distribution_shapes():
    d = ev.distribution(P)
    assert d["n"] == 40 and len(d["rows"]) == 40 and d["positive"] <= 40 and 0 <= d["share_mean"] <= 1
    assert all(r["opt"] >= 0 and r["projects"] <= r["opt"] and r["resources"] <= r["opt"] for r in d["rows"])


def test_or_control_rows():
    o = ev.or_control(P, seeds=C.SWEEP_SEEDS[:8])
    assert o["n"] == 8 and all(r["or_value"] >= r["and_value"] for r in o["rows"])


def test_scaling_rows_are_ordered_by_size():
    rows = ev.scaling(sizes=C.SCALE_SIZES[:3], seeds=C.SCALE_SEEDS[:3])
    assert [r["m"] for r in rows] == sorted(r["m"] for r in rows) and all(r["dinic"] > 0 and r["bfs"] > 0 and r["dfs"] > 0 for r in rows)
