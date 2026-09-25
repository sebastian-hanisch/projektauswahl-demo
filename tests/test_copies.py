"""Die aus den Vorgängern kopierten Bausteine (Zufallsgenerator, Edmonds-Karp, Dinic) sind bewacht: dieselben Zahlen wie in edmonds-karp-demo und dinic-demo."""

import pj_dinic as dn
import pj_edmonds_karp as ek
import pj_scenario as sc


def test_splitmix64_stream_is_the_portfolio_standard():
    rng = sc.SplitMix64(1)
    assert [rng.next() for _ in range(2)] == [10451216379200822465, 13757245211066428519]


def _assignment(k=4):
    """Zuordnung als Fluss wie in dinic-demo: S -> Fahrzeug -> Auftrag -> T, Kette F1-A1-F2-A2-..., alle Kapazitäten 1."""
    n = k + 1
    names = ["S", "T"] + [f"F{i + 1}" for i in range(n)] + [f"A{i + 1}" for i in range(n)]
    arcs = [(0, 2 + i, 1, 0, 0) for i in range(n)]
    for i in range(n):
        arcs.append((2 + i, 2 + n + i, 1, 0, 0))
        if i + 1 < n:
            arcs.append((2 + i + 1, 2 + n + i, 1, 0, 0))
    arcs += [(2 + n + i, 1, 1, 0, 0) for i in range(n)]
    return sc.Net(tuple(names), tuple(names), tuple((0, 0) for _ in names), tuple(arcs), 0, 1, False)


def test_dinic_and_edmonds_karp_copies_reproduce_the_predecessor_numbers():
    """dinic-demo, Preset "Zuordnung als Fluss": eine Phase (Niveau 3) mit 5 Wegen, 69 durchsuchte Kanten gegen 100 bei Edmonds-Karp."""
    net = _assignment()
    d = dn.dinic(net)
    assert (d.value, len(d.phases), d.phases[0].level, d.n_paths, d.scanned_total) == (5, 1, 3, 5, 69)
    e = ek.max_flow(net)
    assert (e.value, len(e.rounds), e.scanned_total) == (5, 5, 100)
