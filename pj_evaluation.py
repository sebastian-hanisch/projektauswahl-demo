"""Auswertung: Auswahl per Schnitt gegen einfachere Verfahren, Verteilungen über feste Netze, Preisreihe, Grenze "eine Anlage genügt", Aufwand nach Größe.
Alle Zufallsnetze kommen aus festen Seeds (pj_constants.DIST_SEEDS), unabhängig vom Nutzer-Seed."""

import statistics
import time
from collections import namedtuple

import pj_closure as cl
import pj_constants as C
import pj_scenario as sc

Params = namedtuple("Params", "net p d s fan cost seed algorithm")
DEFAULT_PARAMS = Params(C.DEFAULT_NET, C.DEFAULT_P, C.DEFAULT_D, C.DEFAULT_S, C.DEFAULT_FAN, C.DEFAULT_COST, C.DEFAULT_SEED, C.DEFAULT_ALGORITHM)


def instance(params):
    return sc.build(params.net, params.p, params.d, params.s, params.fan, params.cost, params.seed)


METHODS = ("optimum", "resources", "projects", "all", "nothing")
METHOD_LABELS = {"optimum": "Minimaler Schnitt (optimal)", "resources": "Ressourcen-Greedy", "projects": "Projektweise (Einzelprüfung)", "all": "Alles nehmen", "nothing": "Nichts nehmen"}


def choices(inst, sol):
    """Auswahl je Verfahren."""
    return {"optimum": sol.chosen, "resources": cl.greedy_resources(inst), "projects": cl.greedy_standalone(inst), "all": cl.everything(inst), "nothing": cl.nothing(inst)}


def analyse(params):
    inst = instance(params)
    sol = cl.solve(inst, params.algorithm)
    ch = choices(inst, sol)
    values = {k: cl.value_of(inst, v) for k, v in ch.items()}
    return dict(inst=inst, sol=sol, choices=ch, values=values)


def frames(sol):
    """Bilder des Flusses im Hilfsnetz: [(Fluss je Kante, Kanten des letzten Weges (Netzkanten-Indizes) oder ())]. Bild 0 = leerer Fluss."""
    net = sol.net
    res = sol.flow
    out = [((0,) * net.m, ())]
    if hasattr(res, "phases"):
        for ph in res.phases:
            for p in ph.paths:
                out.append((p.flow_after, tuple(e // 2 for e in p.arcs)))
    else:
        for k, rd in enumerate(res.rounds):
            out.append((res.flows[k + 1], tuple(e // 2 for e in rd.path)))
    return out


def verdict(inst, sol, values):
    """Kurzurteil: 'empty' (nichts lohnt), 'all' (alles lohnt), 'mixed' (Teilauswahl); dazu Anteil gewählter Filialen."""
    stores = [i for i, k in enumerate(inst.kinds) if k in ("store", "project")]
    chosen_stores = [i for i in stores if sol.chosen[i]]
    if sol.value == 0 and not any(sol.chosen):
        code = "empty"
    elif len(chosen_stores) == len(stores):
        code = "all"
    else:
        code = "mixed"
    return code, len(chosen_stores), len(stores)


# --- Verteilung über feste Netze ------------------------------------------------------------------------------------------------

def _one(cfg, seed):
    inst = sc.generate(*cfg, seed)
    sol = cl.solve(inst, keep_flows=False)
    ch = choices(inst, sol)
    values = {k: cl.value_of(inst, v) for k, v in ch.items()}
    stores = [i for i, k in enumerate(inst.kinds) if k == "store"]
    return inst, sol, values, sum(1 for i in stores if sol.chosen[i]) / len(stores)


def distribution(params, seeds=C.SWEEP_SEEDS):
    """Optimum und einfache Verfahren über die festen Netze der Einstellung (Werke, DCs, Filialen, Voraussetzungen, Kostenniveau)."""
    cfg = (params.p, params.d, params.s, params.fan, params.cost)
    rows = []
    for seed in seeds:
        inst, sol, values, share = _one(cfg, seed)
        lp, x = cl.lp_closure(inst)
        frac = sum(1 for v in x if 1e-6 < v < 1 - 1e-6)
        rows.append(dict(seed=seed, opt=values["optimum"], resources=values["resources"], projects=values["projects"], all=values["all"], nothing=0, share=share,
                         unique=sol.unique, lp_gap=abs(lp - sol.value), lp_frac=frac, scanned=sol.scanned, size=sol.size))
    positive = [r for r in rows if r["opt"] > 0]

    def loss(key):
        return [(r["opt"] - r[key]) / r["opt"] for r in positive]

    def mean(v):
        return statistics.fmean(v) if v else 0.0

    return dict(
        n=len(rows), positive=len(positive), share_mean=mean([r["share"] for r in positive]),
        loss_resources=mean(loss("resources")), loss_projects=mean(loss("projects")), loss_all=mean([(r["opt"] - r["all"]) / r["opt"] for r in positive]),
        hit_resources=sum(1 for r in positive if r["resources"] == r["opt"]), hit_projects=sum(1 for r in positive if r["projects"] == r["opt"]),
        zero_projects=sum(1 for r in positive if r["projects"] == 0), zero_resources=sum(1 for r in positive if r["resources"] == 0),
        lp_fractional=sum(1 for r in rows if r["lp_frac"] > 0), lp_gap_max=max(r["lp_gap"] for r in rows), nonunique=sum(1 for r in rows if not r["unique"]),
        value_mean=mean([r["opt"] for r in rows]), rows=rows,
    )


def small_check(seeds=C.SMALL_SEEDS, cfg=(2, 3, 6, 2, 100)):
    """Kleine Instanzen (11 Knoten): Schnitt gegen alle 2^11 Auswahlen und gegen das LP."""
    ok_bf = ok_lp = 0
    for seed in seeds:
        inst = sc.generate(*cfg, seed)
        sol = cl.solve(inst, keep_flows=False)
        ok_bf += cl.brute_force(inst)[0] == sol.value
        ok_lp += abs(cl.lp_closure(inst)[0] - sol.value) < 1e-6
    return dict(n=len(seeds), brute=ok_bf, lp=ok_lp)


# --- Preisreihe (geschachtelte Auswahlen) ---------------------------------------------------------------------------------------

def sweep(inst, percents=C.PRICE_PERCENTS):
    """Optimale Auswahl je Erlös-Skalierung. Rückgabe: Prozente, Auswahlen (kleinste Quellseite), Gewinne (Kosten- und Erlöseinheiten der Instanz, als Bruch aus 100 geteilt), Zahl der
    verschiedenen Auswahlen, größter Sprung in der Auswahlgröße zwischen zwei Nachbarwerten, und ob die Auswahlen geschachtelt sind."""
    sols = cl.price_sweep(inst, percents)
    sets = [s.chosen for s in sols]
    nested = all(all(b or not a for a, b in zip(sets[k], sets[k + 1])) for k in range(len(sets) - 1))
    sizes = [sum(s) for s in sets]
    jumps = [sizes[k + 1] - sizes[k] for k in range(len(sizes) - 1)]
    return dict(percents=tuple(percents), sets=sets, values=[sum((w * pc / 100 if w > 0 else w) for w, c in zip(inst.weights, st) if c) for st, pc in zip(sets, percents)], sizes=sizes, distinct=len({s for s in sets}), max_jump=max(jumps) if jumps else 0, nested=nested)


def sweep_stats(params, seeds=C.SWEEP_SEEDS):
    """Über die festen Netze: Anteil geschachtelter Preisreihen, mittlere Zahl verschiedener Auswahlen, mittlerer und größter Sprung."""
    cfg = (params.p, params.d, params.s, params.fan, params.cost)
    nested = 0
    distinct, jumps, jump_share = [], [], []
    for seed in seeds:
        inst = sc.generate(*cfg, seed)
        sw = sweep(inst)
        nested += sw["nested"]
        distinct.append(sw["distinct"])
        jumps.append(sw["max_jump"])
        jump_share.append(sw["max_jump"] / max(1, max(sw["sizes"])))
    return dict(n=len(seeds), nested=nested, distinct_mean=statistics.fmean(distinct), jump_mean=statistics.fmean(jumps), jump_max=max(jumps), jump_share_mean=statistics.fmean(jump_share))


# --- Grenze: eine Anlage genügt --------------------------------------------------------------------------------------------------

def or_control(params, seeds=C.SWEEP_SEEDS):
    """Negativkontrolle: dieselben Netze, aber jede Filiale braucht nur EINES ihrer Verteilzentren. Der Schnitt (alle nötig) bleibt zulässig, ist aber zu vorsichtig; das MIP
    ("eine genügt") findet mehr; das LP ist dort gebrochen (die Matrix ist nicht mehr total unimodular)."""
    cfg = (params.p, params.d, params.s, params.fan, params.cost)
    rows = []
    for seed in seeds:
        inst = sc.generate(*cfg, seed)
        and_value = cl.solve(inst, keep_flows=False).value
        or_value, _, lp_value, frac = cl.solve_or(inst)
        rows.append(dict(seed=seed, and_value=and_value, or_value=or_value, lp_or=lp_value, frac=frac))
    better = [r for r in rows if r["or_value"] > r["and_value"]]
    positive = [r for r in rows if r["or_value"] > 0]
    return dict(
        n=len(rows), better=len(better), gain_mean=statistics.fmean([(r["or_value"] - r["and_value"]) / r["or_value"] for r in positive]) if positive else 0.0,
        lp_fractional=sum(1 for r in rows if r["frac"] > 0), lp_gap_share=sum(1 for r in rows if r["lp_or"] > r["or_value"] + 1e-6), rows=rows,
    )


# --- Aufwand nach Größe -----------------------------------------------------------------------------------------------------------

def scaling(params=None, sizes=C.SCALE_SIZES, seeds=C.SCALE_SEEDS, cost=C.DEFAULT_COST):
    """Durchsuchte Kanten von Dinic, Edmonds-Karp und Ford-Fulkerson (Tiefensuche) im Hilfsnetz je Größe, dazu die Laufzeit der LP-Relaxation in HiGHS (nur als grobes Verhältnis)."""
    rows = []
    for (P, D, S, fan) in sizes:
        acc = {"dinic": [], "bfs": [], "dfs": [], "lp": [], "n": [], "m": []}
        for seed in seeds:
            inst = sc.generate(P, D, S, fan, cost, seed)
            net = cl.aux_net(inst)
            acc["n"].append(net.n)
            acc["m"].append(net.m)
            for algo in ("dinic", "bfs", "dfs"):
                acc[algo].append(cl.solve(inst, algo, keep_flows=False).scanned)
            t0 = time.perf_counter()
            cl.lp_closure(inst)
            acc["lp"].append(time.perf_counter() - t0)
        rows.append(dict(P=P, D=D, S=S, fan=fan, n=statistics.fmean(acc["n"]), m=statistics.fmean(acc["m"]), dinic=statistics.fmean(acc["dinic"]), bfs=statistics.fmean(acc["bfs"]),
                         dfs=statistics.fmean(acc["dfs"]), lp_seconds=statistics.fmean(acc["lp"])))
    return rows
