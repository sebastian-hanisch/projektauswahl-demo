"""Konstanten, Regler-Grenzen, Presets und feste Seed-Mengen der Demo "Projektauswahl: welche Filialen sich lohnen, wenn Voraussetzungen Kosten teilen"."""

# --- Regler ---------------------------------------------------------------------------------------------------------------------
P_MIN, P_MAX, DEFAULT_P = 2, 6, 3            # Werke
D_MIN, D_MAX, DEFAULT_D = 2, 8, 4            # Verteilzentren
S_MIN, S_MAX, DEFAULT_S = 4, 24, 8           # Filialen
FAN_MIN, FAN_MAX, DEFAULT_FAN = 1, 3, 2      # höchste Zahl der Verteilzentren, die eine Filiale voraussetzt
COST_MIN, COST_MAX, DEFAULT_COST = 50, 250, 100   # Betriebskosten in Prozent der Standardkosten, Schritt 10
DEFAULT_SEED = 24
SEED_MAX = 2_000_000_000

NETS = {
    "random": "Zufälliges Distributionsnetz",
    "shared": "Gemeinsames Verteilzentrum (3 Filialen, 1 DC)",
    "chain": "Kette Filiale - DC - Werk",
    "dud": "Nichts lohnt (zwei Filialen)",
    "trap": "Greedy-Falle (3 Filialen, 2 DCs)",
    "either": "Eine Anlage genügt (Negativkontrolle)",
}
DEFAULT_NET = "random"
FIXED_NETS = ("shared", "chain", "dud", "trap", "either")

ALGORITHMS = {"dinic": "Dinic", "bfs": "Edmonds-Karp (kürzester Weg)", "dfs": "Ford-Fulkerson (Tiefensuche)"}
DEFAULT_ALGORITHM = "dinic"

# --- feste Seed-Mengen (dieselben wie in den Flussdemos; unabhängig vom Nutzer-Seed) ---------------------------------------------
DIST_SEEDS = tuple(range(100000, 100100))
SWEEP_SEEDS = DIST_SEEDS[:40]
SMALL_SEEDS = DIST_SEEDS[:40]        # kleine Instanzen (Brute Force möglich)
SCALE_SIZES = ((2, 3, 6, 2), (3, 4, 10, 2), (4, 6, 16, 2), (6, 8, 24, 3), (10, 14, 48, 3), (16, 24, 120, 3), (24, 40, 300, 3))   # (Werke, DCs, Filialen, fan)
SCALE_SEEDS = DIST_SEEDS[:10]
PRICE_PERCENTS = tuple(range(0, 301, 5))     # Erlöse in Prozent des Ausgangswerts (Preisreihe)

COLORS = {
    "profit": "#2ca02c", "cost": "#d62728", "req": "#8a8a8a", "chosen": "#2ca02c", "left": "#8c8c8c", "flow": "#1f77b4", "path": "#ff7f0e",
    "optimal": "#d62728", "store": "#1f77b4", "dc": "#9467bd", "plant": "#7f7f7f", "faint": "rgba(150,150,150,0.45)", "node": "#111111",
}

# --- Presets -----------------------------------------------------------------------------------------------------------------
_BASE = dict(net="random", algorithm=DEFAULT_ALGORITHM, p=DEFAULT_P, d=DEFAULT_D, s=DEFAULT_S, fan=DEFAULT_FAN, cost=DEFAULT_COST, seed=DEFAULT_SEED)
PRESETS = {
    "🚚 Zufallsnetz": {**_BASE},
    "🤝 Gemeinsames DC": {**_BASE, "net": "shared"},
    "⛓️ Kette": {**_BASE, "net": "chain"},
    "🕳️ Nichts lohnt": {**_BASE, "net": "dud"},
    "🎯 Greedy-Falle": {**_BASE, "net": "trap"},
    "🔀 Mehrere beste Schnitte": {**_BASE, "seed": 21},
    "🔂 Eine genügt": {**_BASE, "net": "either"},
    "🏗️ Große Instanz": {**_BASE, "p": 6, "d": 8, "s": 24, "fan": 3, "cost": 200, "seed": 2},
}
# Jede Zahl in diesen Texten ist in tests/test_claims.py belegt (Lehrbeispiele von Hand, Zufallsnetze über die Seeds der Presets)
PRESET_HELP = {
    "🚚 Zufallsnetz": "3 Werke, 4 Verteilzentren, 8 Filialen: optimal sind 5 von 8 Filialen mit Gewinn 30 (Erlös 180, Kosten 150). Projektweise Einzelprüfung findet 0, Ressourcen-Greedy 12, Alles nehmen 27. Dinic braucht 12 Wege und durchsucht 224 Kanten.",
    "🤝 Gemeinsames DC": "Ein Verteilzentrum (Kosten 10), drei Filialen mit Erlös 6, 7 und 3: jede allein verliert, zusammen gewinnen sie 16 - 10 = 6. Projektweise Einzelprüfung wählt nichts und findet 0.",
    "⛓️ Kette": "Eine Filiale (Erlös 20) setzt ein Verteilzentrum (Kosten 8) voraus, das ein Werk (Kosten 9) voraussetzt: Gewinn 3, aber nur mit der ganzen Kette. Alle Verfahren finden ihn.",
    "🕳️ Nichts lohnt": "Zwei Filialen (Erlös 5 und 4) mit je einem eigenen Verteilzentrum (Kosten 6 und 5): die beste Auswahl ist die leere, Gewinn 0. Alles nehmen verliert 2.",
    "🎯 Greedy-Falle": "Zwei Verteilzentren (je 10), drei Filialen mit Erlös 11, 6 und 9 (die zweite braucht beide DCs): der Schnitt wählt alle drei und gewinnt 6, projektweise Einzelprüfung nur die erste (Gewinn 1).",
    "🔀 Mehrere beste Schnitte": "5 von 8 Filialen mit Gewinn 7. Es gibt eine zweite beste Auswahl, die zusätzlich W1, D1, F1, F2 und F3 nimmt und denselben Gewinn 7 hat: kleinste und größte Quellseite des Schnitts fallen nicht zusammen. Ressourcen-Greedy und Einzelprüfung finden 0.",
    "🔂 Eine genügt": "Eine Filiale (Erlös 10) mit zwei Verteilzentren zu je 6 als Alternativen. Der Schnitt verlangt beide (Kette 12) und wählt nichts; mit „eine genügt“ (MIP) ist der Gewinn 4. Hier hört das Schnittmodell auf.",
    "🏗️ Große Instanz": "6 Werke, 8 Verteilzentren, 24 Filialen, Kosten 200 %: 19 von 24 Filialen mit Gewinn 24 (Erlös 648, Kosten 624); Ressourcen-Greedy findet 0, Alles nehmen verliert 11. Mehrere beste Auswahlen; Dinic braucht 37 Wege und durchsucht 1328 Kanten.",
}
