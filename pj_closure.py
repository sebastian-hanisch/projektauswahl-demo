"""Projektauswahl als Flussschnitt (Picard 1976), dazu Gegenproben und einfachere Verfahren zum Vergleich.

Gewichtsmaximale abgeschlossene Menge: wähle Knoten so, dass mit jedem Knoten i auch alle Knoten j gewählt sind, die er voraussetzt, und die Summe der Gewichte
maximal ist. Hilfsnetz: Quelle -> i mit Kapazität w_i für w_i > 0, i -> Senke mit Kapazität -w_i für w_i < 0, i -> j mit unendlicher Kapazität für jede Voraussetzung.
Jeder endliche Schnitt trennt eine abgeschlossene Menge C (Quellseite) ab und kostet (Erlöse der nicht gewählten Knoten) + (Kosten der gewählten Knoten); der Gewinn von C
ist deshalb (Summe aller Erlöse) - (Kapazität des Schnitts), und der minimale Schnitt liefert die beste Auswahl.

Aufwand wird wie in den Flussdemos in durchsuchten Kanten gezählt, nie in Sekunden.
"""

from dataclasses import dataclass
from itertools import product

import numpy as np
from scipy.optimize import linprog, milp, LinearConstraint, Bounds

import pj_dinic
import pj_edmonds_karp as ek
import pj_scenario as sc


def infinity(inst):
    """Kapazität der Voraussetzungskanten: größer als jeder endliche Schnitt (mindestens die Summe aller Erlöse + 1)."""
    return inst.positive_total() + 1


def aux_net(inst, scale_revenue=100):
    """Hilfsnetz zur Instanz. Knoten 0 = Quelle, 1 = Senke, Knoten i der Instanz ist Knoten i + 2. `scale_revenue`: Erlöse in Prozent (für die Preisreihe); die Kosten bleiben,
    alle Gewichte werden dafür mit 100 multipliziert, damit alles ganzzahlig bleibt."""
    names = ("Quelle S", "Senke T") + inst.names
    labels = ("S", "T") + inst.labels
    top = max(y for _, y in inst.pos) if inst.pos else 0
    bottom = min(y for _, y in inst.pos) if inst.pos else 0
    pos = ((sc.MAP_W // 2, top + 22), (sc.MAP_W // 2, bottom - 22)) + tuple(inst.pos)
    w = [x * scale_revenue if x > 0 else x * 100 for x in inst.weights]
    inf = sum(x for x in w if x > 0) + 1
    arcs = []
    for i, x in enumerate(w):
        if x > 0:
            arcs.append((0, i + 2, x, 0, sc.K_PROFIT))
    for i, x in enumerate(w):
        if x < 0:
            arcs.append((i + 2, 1, -x, 0, sc.K_COST))
    for i, j in inst.requires:
        arcs.append((i + 2, j + 2, inf, 0, sc.K_REQ))
    return sc.Net(names, labels, pos, tuple(arcs), 0, 1, inst.logistic)


def value_of(inst, chosen):
    return sum(w for w, c in zip(inst.weights, chosen) if c)


def revenue_of(inst, chosen):
    return sum(w for w, c in zip(inst.weights, chosen) if c and w > 0)


def cost_of(inst, chosen):
    return -sum(w for w, c in zip(inst.weights, chosen) if c and w < 0)


def is_closed(inst, chosen):
    return all(chosen[j] for i, j in inst.requires if chosen[i])


@dataclass(frozen=True)
class Solution:
    chosen: tuple            # bool je Knoten der Instanz (kleinste Quellseite des minimalen Schnitts)
    largest: tuple           # bool je Knoten: größte Quellseite (Komplement der Knoten, von denen T erreichbar ist)
    value: int               # Gewinn der Auswahl
    revenue: int
    cost: int
    flow: object             # Ergebnis des Flussverfahrens (Phasen, Wege, Schnitt) im Hilfsnetz
    net: object              # das Hilfsnetz
    scanned: int             # durchsuchte Kanten
    n_paths: int
    unique: bool             # kleinste und größte Quellseite fallen zusammen

    @property
    def size(self):
        return sum(self.chosen)


def solve(inst, algorithm="dinic", scale_revenue=100, keep_flows=True):
    """Beste Auswahl per minimalem Schnitt. `algorithm`: 'dinic' (Standard), 'bfs' (Edmonds-Karp), 'dfs' (Ford-Fulkerson).
    Bei skalierten Erlösen (scale_revenue != 100) sind alle Gewichte um den Faktor 100 größer; `value` ist dann durch 100 geteilt gerundet nicht zulässig - Aufrufer nutzen `value_scaled`."""
    net = aux_net(inst, scale_revenue)
    if algorithm == "dinic":
        res = pj_dinic.dinic(net, keep_flows=keep_flows)
        reach, co_reach, scanned, n_paths, unique = res.reach, res.co_reach, res.scanned_total, res.n_paths, res.unique_cut
    else:
        res = ek.max_flow(net, rule=algorithm, keep_flows=keep_flows)
        reach, co_reach, scanned, n_paths, unique = res.reach, res.co_reach, res.scanned_total, len(res.rounds), res.unique_cut
    chosen = tuple(bool(reach[i + 2]) for i in range(inst.n))
    largest = tuple(not co_reach[i + 2] for i in range(inst.n))
    w = tuple(x * scale_revenue if x > 0 else x * 100 for x in inst.weights)
    scaled = sum(x for x, c in zip(w, chosen) if c)
    rev = sum(x for x, c in zip(w, chosen) if c and x > 0)
    cost = -sum(x for x, c in zip(w, chosen) if c and x < 0)
    return Solution(chosen, largest, scaled if scale_revenue != 100 else value_of(inst, chosen), rev if scale_revenue != 100 else revenue_of(inst, chosen),
                    cost if scale_revenue != 100 else cost_of(inst, chosen), res, net, scanned, n_paths, unique)


# --- Gegenproben --------------------------------------------------------------------------------------------------------

def brute_force(inst):
    """Alle 2^n Auswahlen: beste abgeschlossene. Nur für kleine Instanzen (n <= 18)."""
    n = inst.n
    assert n <= 18
    best, best_set = 0, (False,) * n
    for bits in product((False, True), repeat=n):
        if is_closed(inst, bits):
            v = value_of(inst, bits)
            if v > best:
                best, best_set = v, bits
    return best, best_set


def _constraint_rows(inst):
    rows = []
    for i, j in inst.requires:
        row = np.zeros(inst.n)
        row[i], row[j] = 1.0, -1.0           # x_i - x_j <= 0
        rows.append(row)
    return np.array(rows).reshape(len(rows), inst.n)


def lp_closure(inst):
    """LP-Relaxation (0 <= x <= 1, x_i <= x_j) mit HiGHS: Zielwert und die Lösung. Die Matrix ist total unimodular, das LP liefert deshalb ganzzahlige Ecken."""
    c = -np.array(inst.weights, dtype=float)
    res = linprog(c, A_ub=_constraint_rows(inst) if inst.requires else None, b_ub=np.zeros(len(inst.requires)) if inst.requires else None, bounds=[(0, 1)] * inst.n, method="highs")
    return -res.fun, res.x


def solve_or(inst):
    """Negativkontrolle "eine genügt": die Voraussetzungen der Knoten in `or_nodes` sind Alternativen (mindestens ein Verteilzentrum), alle übrigen bleiben Pflicht.
    Das ist kein Schnittproblem mehr (Standortplanung, NP-schwer); HiGHS löst das MIP. Rückgabe (Optimum, Auswahl, LP-Optimum der Relaxation, Anteil gebrochener Variablen im LP)."""
    n = inst.n
    or_set = set(inst.or_nodes)
    rows, lo, hi = [], [], []
    for i in range(n):
        needs = inst.needs(i)
        if not needs:
            continue
        if i in or_set:
            row = np.zeros(n)
            row[i] = 1.0
            for j in needs:
                row[j] -= 1.0
            rows.append(row); lo.append(-np.inf); hi.append(0.0)         # x_i <= Summe x_j
        else:
            for j in needs:
                row = np.zeros(n)
                row[i], row[j] = 1.0, -1.0
                rows.append(row); lo.append(-np.inf); hi.append(0.0)
    c = -np.array(inst.weights, dtype=float)
    a = np.array(rows).reshape(len(rows), n)
    lp = linprog(c, A_ub=a, b_ub=np.array(hi), bounds=[(0, 1)] * n, method="highs")
    mip = milp(c, constraints=LinearConstraint(a, np.array(lo), np.array(hi)), integrality=np.ones(n), bounds=Bounds(0, 1))
    chosen = tuple(bool(round(v)) for v in mip.x)
    frac = int(np.sum((lp.x > 1e-6) & (lp.x < 1 - 1e-6)))
    return round(-mip.fun), chosen, -lp.fun, frac


# --- einfachere Verfahren zum Vergleich ------------------------------------------------------------------------------------

def _closure_of(inst, seed_nodes):
    """Kleinste abgeschlossene Menge, die `seed_nodes` enthält (transitive Voraussetzungen)."""
    chosen = set(seed_nodes)
    stack = list(seed_nodes)
    while stack:
        i = stack.pop()
        for j in inst.needs(i):
            if j not in chosen:
                chosen.add(j)
                stack.append(j)
    return chosen


def greedy_standalone(inst):
    """Einzelprüfung: jede Filiale (positives Gewicht) für sich mit ihrer ganzen Voraussetzungskette bewerten; wer allein Gewinn bringt, wird gewählt, dazu die Vereinigung
    aller Voraussetzungen (gemeinsame Kosten fallen nur einmal an). Übersieht Gruppen, die sich erst gemeinsam lohnen."""
    take = [i for i, w in enumerate(inst.weights) if w > 0 and w + sum(inst.weights[j] for j in _closure_of(inst, [i]) if j != i) > 0]
    chosen = _closure_of(inst, take)
    return tuple(i in chosen for i in range(inst.n))


def greedy_resources(inst):
    """Ressourcen-Greedy: wiederhole - öffne die Ressource (Knoten mit negativem Gewicht) samt ihren noch fehlenden Voraussetzungen, die den größten Gewinn bringt (Erlöse der Projekte,
    deren Voraussetzungen dadurch alle erfüllt sind, minus die neuen Kosten), solange er positiv ist. Findet ein einzelnes teures Verteilzentrum, das sich lohnt; übersieht Paare, die
    sich nur gemeinsam lohnen (zwei Verteilzentren, die eine Filiale beide braucht)."""
    resources = [i for i, w in enumerate(inst.weights) if w < 0]
    projects = [i for i, w in enumerate(inst.weights) if w > 0]
    opened = set()
    taken = set()

    def gain(add):
        new_open = opened | add
        enabled = [p for p in projects if p not in taken and all(j in new_open for j in _closure_of(inst, [p]) if inst.weights[j] < 0)]
        return sum(inst.weights[p] for p in enabled) + sum(inst.weights[j] for j in add), enabled

    while True:
        best, best_gain, best_add, best_enabled = None, 0, None, None
        for r in resources:
            if r in opened:
                continue
            add = {j for j in _closure_of(inst, [r]) if inst.weights[j] < 0} - opened
            g, enabled = gain(add)
            if g > best_gain:
                best, best_gain, best_add, best_enabled = r, g, add, enabled
        if best is None:
            break
        opened |= best_add
        taken |= set(best_enabled)
    chosen = _closure_of(inst, taken) | opened if taken else set()
    chosen = _closure_of(inst, taken)
    return tuple(i in chosen for i in range(inst.n))


def everything(inst):
    return (True,) * inst.n


def nothing(inst):
    return (False,) * inst.n


# --- Preisreihe (parametrische Schnitte) ----------------------------------------------------------------------------------------

def price_sweep(inst, percents):
    """Optimale kleinste Quellseite für jede Erlös-Skalierung in Prozent (Kosten bleiben). Die Auswahlen sind geschachtelt: mehr Erlös nimmt nie etwas weg (Gallo-Grigoriadis-Tarjan)."""
    return [solve(inst, scale_revenue=p, keep_flows=False) for p in percents]
