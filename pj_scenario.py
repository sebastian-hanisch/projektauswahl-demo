"""Szenario: Projektauswahl mit Voraussetzungen im Distributionsnetz und feste Lehrbeispiele.

Eine Filiale zu beliefern bringt einen Erlös, setzt aber voraus, dass alle Verteilzentren ihrer Warengruppen laufen (jedes kostet Betriebskosten), und jedes
Verteilzentrum setzt seine Werke voraus. Gesucht: die Auswahl mit dem größten Gewinn (Erlöse minus Kosten), die keine Voraussetzung verletzt - eine
**gewichtsmaximale abgeschlossene Menge** (Picard 1976). Jeder Knoten hat ein Gewicht (Erlös > 0, Kosten < 0), jede Voraussetzung ist ein Paar (i, j): wer i
wählt, muss auch j wählen.

Das Hilfsnetz macht daraus einen Flussschnitt: Quelle -> Knoten mit Erlös als Kapazität, Knoten mit Kosten -> Senke mit den Kosten als Kapazität, jede Voraussetzung
als Kante mit unendlicher Kapazität. Ein minimaler Schnitt trennt die gewählte (Quellseite) von der nicht gewählten Menge.

Alles ist ganzzahlig und läuft über einen eigenen Zufallsgenerator (SplitMix64 auf Python-Ints) statt über `numpy.random`: numpy garantiert keine über Versionen
stabilen Zufallsströme, die CI installiert aber wöchentlich die neueste Version. So sind Voreinstellungen, Seeds und jede im Text genannte Zahl auf Windows und Linux dieselben.
"""

from dataclasses import dataclass

_MASK = (1 << 64) - 1
MAP_W = 160
# Erlöse und Kosten (vor Anwendung des Kostenniveaus): Grundwert + gleichverteilte Streuung
REV_BASE, REV_SPAN = 10, 41
DC_BASE, DC_SPAN = 20, 31
PLANT_BASE, PLANT_SPAN = 10, 21
LAYER_Y = {"S": 100, "store": 78, "dc": 50, "plant": 22, "T": 2, "project": 76, "resource": 30}

# Art einer Kante des Hilfsnetzes
K_PROFIT, K_COST, K_REQ, K_OTHER = range(4)
KIND_LABELS = {K_PROFIT: "Erlös (Quelle → Projekt)", K_COST: "Kosten (Knoten → Senke)", K_REQ: "Voraussetzung (unendlich)", K_OTHER: "Kante"}


class SplitMix64:
    """Kleiner, gut gemischter 64-Bit-Zufallsgenerator (Vigna); reine Ganzzahl-Arithmetik."""

    def __init__(self, seed):
        self.state = seed & _MASK

    def next(self):
        self.state = (self.state + 0x9E3779B97F4A7C15) & _MASK
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _MASK
        return z ^ (z >> 31)

    def below(self, n):
        """Ganzzahl in 0..n-1 (die Modulo-Verzerrung bei n <= 101 liegt um 1e-17)."""
        return self.next() % n


@dataclass(frozen=True)
class Net:
    names: tuple      # Anzeigename je Knoten (Hover)
    labels: tuple     # Kurzbeschriftung je Knoten (Karte)
    pos: tuple        # ((x, y), ...) je Knoten
    arcs: tuple       # ((u, v, Kapazität, Kosten je Einheit, Art), ...)
    s: int
    t: int
    logistic: bool    # True: Werke/DCs/Filialen; False: Lehrnetz mit frei benannten Knoten

    @property
    def n(self):
        return len(self.names)

    @property
    def m(self):
        return len(self.arcs)

    def total_capacity_out_of_s(self):
        return sum(c for u, _, c, _, _ in self.arcs if u == self.s)


@dataclass(frozen=True)
class Instance:
    names: tuple
    labels: tuple
    pos: tuple
    kinds: tuple         # "store" | "dc" | "plant" (Distributionsnetz) bzw. "project" | "resource" (Lehrbeispiele)
    weights: tuple       # > 0 Erlös, < 0 Kosten, 0 neutral
    requires: tuple      # ((i, j), ...): wer i wählt, muss auch j wählen
    or_nodes: tuple      # Knoten, deren Voraussetzungen in der Negativkontrolle "eine genügt" Alternativen sind (die Filialen)
    logistic: bool

    @property
    def n(self):
        return len(self.names)

    def positive_total(self):
        return sum(w for w in self.weights if w > 0)

    def needs(self, i):
        return tuple(j for a, j in self.requires if a == i)


def _spread(count):
    """Gleichmäßige x-Positionen für `count` Knoten einer Schicht."""
    return [(2 * i + 1) * MAP_W // (2 * count) for i in range(count)]


def _order(keys):
    """Indizes nach (Schwerpunkt, Index) sortiert."""
    return sorted(range(len(keys)), key=lambda i: (keys[i], i))


def generate(n_plants, n_dcs, n_stores, fan, cost_level, seed):
    """Zufälliges Distributionsnetz mit Voraussetzungen. `fan`: höchste Zahl der Verteilzentren, die eine Filiale voraussetzt (1..fan gleichverteilt);
    jedes Verteilzentrum setzt 1 bis min(fan, 2) Werke voraus. `cost_level`: Betriebskosten in Prozent der Standardkosten. Die Zufallszahlen werden in fester
    Reihenfolge gezogen, so ändert `cost_level` nur die Kosten, nicht die Voraussetzungen. Knoten sind nach ihrer Lage sortiert (Kreuzungen der Voraussetzungen bleiben wenige)."""
    rng = SplitMix64(seed)
    P, D, S = n_plants, n_dcs, n_stores
    plant_cost = [PLANT_BASE + rng.below(PLANT_SPAN) for _ in range(P)]
    dc_cost = [DC_BASE + rng.below(DC_SPAN) for _ in range(D)]
    revenue = [REV_BASE + rng.below(REV_SPAN) for _ in range(S)]

    def pick(count, upto):
        k = 1 + rng.below(min(upto, count))
        chosen = []
        while len(chosen) < k:
            j = rng.below(count)
            if j not in chosen:
                chosen.append(j)
        return sorted(chosen)

    dc_plants = [pick(P, min(fan, 2)) for _ in range(D)]
    store_dcs = [pick(D, fan) for _ in range(S)]
    # Lage: Werke gleichmäßig, DCs nach dem Schwerpunkt ihrer Werke, Filialen nach dem Schwerpunkt ihrer DCs
    plant_x = _spread(P)
    dc_order = _order([sum(plant_x[p] for p in dc_plants[d]) / len(dc_plants[d]) for d in range(D)])
    dc_x = {d: x for d, x in zip(dc_order, _spread(D))}
    store_order = _order([sum(dc_x[d] for d in store_dcs[s]) / len(store_dcs[s]) for s in range(S)])
    store_x = {s: x for s, x in zip(store_order, _spread(S))}

    # Knotennummern in Lagereihenfolge: Werke, dann DCs, dann Filialen (jeweils von links nach rechts)
    plant_id = {p: p for p in range(P)}
    dc_id = {d: P + k for k, d in enumerate(dc_order)}
    store_id = {s: P + D + k for k, s in enumerate(store_order)}
    n = P + D + S
    names, labels, pos, kinds, weights = [None] * n, [None] * n, [None] * n, [None] * n, [0] * n
    for p in range(P):
        i = plant_id[p]
        names[i], labels[i], pos[i], kinds[i], weights[i] = f"Werk {p + 1}", f"W{p + 1}", (plant_x[p], LAYER_Y["plant"]), "plant", -(plant_cost[p] * cost_level // 100)
    for k, d in enumerate(dc_order):
        i = dc_id[d]
        names[i], labels[i], pos[i], kinds[i], weights[i] = f"DC {k + 1}", f"D{k + 1}", (dc_x[d], LAYER_Y["dc"]), "dc", -(dc_cost[d] * cost_level // 100)
    for k, s in enumerate(store_order):
        i = store_id[s]
        names[i], labels[i], pos[i], kinds[i], weights[i] = f"Filiale {k + 1}", f"F{k + 1}", (store_x[s], LAYER_Y["store"]), "store", revenue[s]
    requires = []
    for s in range(S):
        requires += [(store_id[s], dc_id[d]) for d in store_dcs[s]]
    for d in range(D):
        requires += [(dc_id[d], plant_id[p]) for p in dc_plants[d]]
    requires = tuple(sorted(requires))
    or_nodes = tuple(store_id[s] for s in range(S))
    return Instance(tuple(names), tuple(labels), tuple(pos), tuple(kinds), tuple(weights), requires, tuple(sorted(or_nodes)), True)


# --- feste Lehrbeispiele ---------------------------------------------------------------------------------------------------

def _wide(pos):
    """Handgesetzte Lagen (x in 0..100) auf die Kartenbreite strecken."""
    return tuple((x * MAP_W // 100, y) for x, y in pos)


def _teaching(names, kinds, weights, requires, pos):
    return Instance(tuple(names), tuple(names), _wide(pos), tuple(kinds), tuple(weights), tuple(requires), (), False)


def shared_dc():
    """Gemeinsames Verteilzentrum: DC kostet 10, drei Filialen mit Erlös 6, 7 und 3 setzen es alle voraus. Jede allein verliert (6, 7, 3 gegen 10), zusammen gewinnen sie 16 - 10 = 6."""
    names = ["Filiale A", "Filiale B", "Filiale C", "DC"]
    return _teaching(names, ["project"] * 3 + ["resource"], [6, 7, 3, -10], [(0, 3), (1, 3), (2, 3)], [(15, 76), (50, 76), (85, 76), (50, 30)])


def chain():
    """Kette: Filiale (Erlös 20) setzt ein DC (Kosten 8) voraus, das ein Werk (Kosten 9) voraussetzt: 20 - 17 = 3 Gewinn, aber nur, wenn die ganze Kette gewählt wird."""
    names = ["Filiale", "DC", "Werk"]
    return _teaching(names, ["project", "resource", "resource"], [20, -8, -9], [(0, 1), (1, 2)], [(50, 82), (50, 52), (50, 22)])


def dud():
    """Nichts lohnt: zwei Filialen (Erlös 5 und 4) setzen je ein eigenes DC mit Kosten 6 und 5 voraus. Die beste Auswahl ist die leere mit Gewinn 0."""
    names = ["Filiale A", "Filiale B", "DC A", "DC B"]
    return _teaching(names, ["project"] * 2 + ["resource"] * 2, [5, 4, -6, -5], [(0, 2), (1, 3)], [(25, 76), (75, 76), (25, 30), (75, 30)])


def greedy_trap():
    """Schrittweises Greedy scheitert an der Reihenfolge: zwei DCs (Kosten 10 und 10); Filiale A (Erlös 11) braucht nur DC 1, Filiale B (Erlös 6) braucht DC 1 und DC 2, Filiale C (Erlös 9)
    braucht DC 2. Einzeln lohnt nur A (+1) und C (-1, nein), B (-14); zusammen A + B + C: 26 - 20 = 6, A + C: 20 - 20 = 0, nur A: 1. Optimum 6."""
    names = ["Filiale A", "Filiale B", "Filiale C", "DC 1", "DC 2"]
    return _teaching(names, ["project"] * 3 + ["resource"] * 2, [11, 6, 9, -10, -10],
                     [(0, 3), (1, 3), (1, 4), (2, 4)], [(15, 76), (50, 76), (85, 76), (30, 30), (70, 30)])


def either_or():
    """Negativkontrolle "eine genügt": eine Filiale (Erlös 10) kann von DC 1 oder DC 2 (Kosten je 6) beliefert werden. Als Alternative genügt ein DC (Gewinn 4); als
    Pflicht (alle nötig) braucht sie beide (Gewinn 10 - 12 < 0, Auswahl leer)."""
    names = ["Filiale", "DC 1", "DC 2"]
    return Instance(tuple(names), tuple(names), _wide(((50, 76), (30, 30), (70, 30))), ("project", "resource", "resource"), (10, -6, -6), ((0, 1), (0, 2)), (0,), False)


LESSONS = {
    "shared": shared_dc,
    "chain": chain,
    "dud": dud,
    "trap": greedy_trap,
    "either": either_or,
}


def build(net, n_plants, n_dcs, n_stores, fan, cost_level, seed):
    """Instanz zu den Einstellungen; feste Beispiele ignorieren die Zufallsparameter."""
    if net != "random":
        return LESSONS[net]()
    return generate(n_plants, n_dcs, n_stores, fan, cost_level, seed)
