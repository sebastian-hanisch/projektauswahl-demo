"""Orakel-Regressionstest: Projektauswahl (Closure als Minimalschnitt) gegen Aufzählung aller Teilmengen und networkx.

Beliebige kleine Voraussetzungs-Graphen (auch mit Kreisen, Voraussetzungen zwischen Projekten, Gewicht 0, viele Gleichstände): Optimum, kleinste und größte beste Auswahl
(Schnitt und Vereinigung aller besten Mengen), Eindeutigkeit, Preisreihe und die Variante "eine Anlage genügt" gegen Aufzählung."""

import random
from itertools import product

import pytest

nx = pytest.importorskip("networkx")

import pj_closure as cl  # noqa: E402
import pj_evaluation as ev  # noqa: E402
import pj_scenario as sc  # noqa: E402


def _inst(weights, requires, or_nodes=()):
    n = len(weights)
    return sc.Instance(tuple(f"N{i}" for i in range(n)), tuple(str(i) for i in range(n)), tuple((5 * i % 100, 9 * i % 100) for i in range(n)), ("project",) * n,
                       tuple(weights), tuple(sorted(requires)), tuple(or_nodes), False)


def _random(rng, n):
    w = [rng.choice([0, 1, 2, 3, 5, 8, 10, -1, -2, -3, -5, -8, -10, rng.randint(-12, 12)]) for _ in range(n)]
    p = rng.choice([0.05, 0.15, 0.3])
    return _inst(w, [(i, j) for i in range(n) for j in range(n) if i != j and rng.random() < p])


def _optimal_sets(weights, requires):
    best, sets = None, []
    for bits in product((0, 1), repeat=len(weights)):
        s = {i for i, b in enumerate(bits) if b}
        if all(j in s for i, j in requires if i in s):
            v = sum(weights[i] for i in s)
            if best is None or v > best:
                best, sets = v, [s]
            elif v == best:
                sets.append(s)
    return best, sets


def _picard_nx(inst):
    G = nx.DiGraph()
    G.add_nodes_from(["s", "t"])
    big = inst.positive_total() + 1
    for i, w in enumerate(inst.weights):
        G.add_node(i)
        if w > 0:
            G.add_edge("s", i, capacity=w)
        elif w < 0:
            G.add_edge(i, "t", capacity=-w)
    G.add_edges_from((i, j, {"capacity": big}) for i, j in inst.requires)
    return inst.positive_total() - nx.minimum_cut(G, "s", "t")[0]


def test_closure_value_smallest_and_largest_optimum_equal_enumeration():
    rng = random.Random(21)
    for _ in range(60):
        inst = _random(rng, rng.randint(1, 10))
        best, sets = _optimal_sets(inst.weights, inst.requires)
        assert _picard_nx(inst) == best and cl.lp_closure(inst)[0] == pytest.approx(best)
        for algo in ("dinic", "bfs", "dfs"):
            s = cl.solve(inst, algo)
            assert s.value == best == cl.revenue_of(inst, s.chosen) - cl.cost_of(inst, s.chosen) and cl.is_closed(inst, s.chosen)
            assert {i for i in range(inst.n) if s.chosen[i]} == set.intersection(*sets)
            assert {i for i in range(inst.n) if s.largest[i]} == set.union(*sets)
            assert s.unique == (len(sets) == 1)


def test_price_sweep_sets_equal_enumeration_and_are_nested():
    rng = random.Random(22)
    pcts = (0, 50, 100, 200, 300)
    for _ in range(25):
        inst = _random(rng, rng.randint(1, 9))
        sw = ev.sweep(inst, pcts)
        assert sw["nested"]
        for p, chosen in zip(pcts, sw["sets"]):
            w = [x * p if x > 0 else x * 100 for x in inst.weights]
            assert {i for i in range(inst.n) if chosen[i]} == set.intersection(*_optimal_sets(w, inst.requires)[1])


def test_either_or_variant_equals_enumeration_and_greedy_stays_below_the_optimum():
    for seed in range(100000, 100010):
        inst = sc.generate(2, 3, 6, 2, 100, seed)
        n, orset = inst.n, set(inst.or_nodes)
        best = None
        for bits in product((0, 1), repeat=n):
            s = {i for i, b in enumerate(bits) if b}
            ok = all((any(j in s for j in inst.needs(i)) if i in orset else all(j in s for j in inst.needs(i))) for i in s if inst.needs(i))
            if ok:
                v = sum(inst.weights[i] for i in s)
                best = v if best is None or v > best else best
        assert cl.solve_or(inst)[0] == best
        opt = cl.solve(inst).value
        for pick in (cl.greedy_resources(inst), cl.greedy_standalone(inst)):
            assert cl.is_closed(inst, pick) and cl.value_of(inst, pick) <= opt
