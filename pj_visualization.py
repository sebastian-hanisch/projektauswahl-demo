"""Plotly-Abbildungen: Hilfsnetz mit Fluss und Schnitt, Verfahren im Vergleich, Preisreihe, Verteilungen, Grenze "eine genügt", Aufwand.
Achsen sind gesperrt (fixedrange), damit Touch-Geräte beim Scrollen nicht zoomen. Kanten haben über unsichtbare Marker einen Hover-Text
(Plotly-Linien reagieren nur an ihren Stützpunkten). Kantenbeschriftungen sind Annotationen mit heller Hinterlegung."""

from math import atan2, degrees, hypot

import plotly.graph_objects as go
from plotly.subplots import make_subplots

import pj_constants as C
import pj_scenario as sc


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _base(fig, height):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.12), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def _curve(p0, p1, steps=8):
    """Gerade Kante als Punktfolge, dazu Pfeilposition und -winkel bei 65 % und die Kantenmitte."""
    (x0, y0), (x1, y1) = p0, p1
    xs = [x0 + (x1 - x0) * k / steps for k in range(steps + 1)]
    ys = [y0 + (y1 - y0) * k / steps for k in range(steps + 1)]
    t = 0.65
    ax, ay = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
    return xs, ys, (ax, ay, degrees(atan2(x1 - x0, y1 - y0))), (xs[steps // 2], ys[steps // 2])


def _segments(curves):
    x, y = [], []
    for xs, ys, _, _ in curves:
        x += xs + [None]
        y += ys + [None]
    return x, y


def _lines(fig, curves, color, width, name, dash=None, showlegend=True):
    if not curves:
        return
    x, y = _segments(curves)
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=color, width=width, dash=dash), hoverinfo="skip", name=name, showlegend=showlegend))


def _arrows(fig, curves, color, size=9):
    if not curves:
        return
    fig.add_trace(go.Scatter(x=[c[2][0] for c in curves], y=[c[2][1] for c in curves], mode="markers", hoverinfo="skip", showlegend=False,
                             marker=dict(symbol="arrow", size=size, color=color, angle=[c[2][2] for c in curves])))


def _hover_points(fig, entries):
    x, y, text = [], [], []
    for curve, label in entries:
        xs, ys = curve[0], curve[1]
        for k in range(1, len(xs) - 1):
            x.append(xs[k]); y.append(ys[k]); text.append(label)
    if x:
        fig.add_trace(go.Scatter(x=x, y=y, mode="markers", marker=dict(size=9, opacity=0), hovertext=text, hoverinfo="text", showlegend=False))


def _labels(fig, points, color="#111"):
    for x, y, text in points:
        fig.add_annotation(x=x, y=y, text=text, showarrow=False, xanchor="left", font=dict(size=11, color=color), bgcolor="rgba(255,255,255,0.88)", borderpad=1)


def _layout(fig, net, height):
    """Gleicher Maßstab in x und y mit automatischem Bereich; der Rand kommt über zwei unsichtbare Punkte an den Ecken (ein fest vorgegebener Bereich wird beim ersten
    Zeichnen in schmaler Breite eingefroren und bleibt zu klein)."""
    xs = [p[0] for p in net.pos]
    ys = [p[1] for p in net.pos]
    pad = 10
    fig.update_xaxes(visible=False, scaleanchor="y", scaleratio=1)
    fig.update_yaxes(visible=False)
    fig.add_trace(go.Scatter(x=[min(xs) - pad, max(xs) + pad], y=[min(ys) - pad, max(ys) + pad], mode="markers", marker=dict(opacity=0), hoverinfo="skip", showlegend=False))
    return _base(fig, height)


def _weight_text(inst, i):
    w = inst.weights[i]
    return f"{inst.labels[i]}<br>{'+' if w > 0 else ''}{w}" if w else inst.labels[i]


def build_network(inst, sol, flow=None, path=None, final=False, height=560):
    """Hilfsnetz: Quelle S (oben) -> Projekte mit dem Erlös als Kapazität, Voraussetzungen als gestrichelte Kanten (unendlich), Knoten mit Kosten -> Senke T (unten).
    `flow`: Fluss je Kante (Blau, Breite ~ Fluss), `path`: Kanten des letzten Weges (orange); `final`: Schnitt - gewählte Knoten (Quellseite) grün, Schnittkanten rot."""
    net = sol.net
    fig = go.Figure()
    flow = flow if flow is not None else (0,) * net.m
    chosen = {i + 2 for i in range(inst.n) if sol.chosen[i]} | {net.s}
    path_set = set(path or ())
    top = max((c for _, _, c, _, k in net.arcs if k != sc.K_REQ), default=1)
    kinds = {"profit": [], "cost": [], "req": [], "flow": {}, "path": [], "cut": []}
    hover, labels = [], []
    for i, (u, v, cap, _, kind) in enumerate(net.arcs):
        curve = _curve(net.pos[u], net.pos[v])
        inf = kind == sc.K_REQ
        capt = "∞" if inf else f"{cap / 100:g}"
        name = f"{net.names[u]} → {net.names[v]}"
        hover.append((curve, f"{name}: Fluss {flow[i] / 100:g} von {capt}" + (" (Voraussetzung)" if inf else " (Erlös)" if kind == sc.K_PROFIT else " (Kosten)")))
        t = 0.72 if u == net.s else 0.28 if v == net.t else 0.5          # Beschriftung nahe am Knoten der Kante, damit sich die Zahlen nicht drängen
        lx, ly = net.pos[u][0] + (net.pos[v][0] - net.pos[u][0]) * t + 1.2, net.pos[u][1] + (net.pos[v][1] - net.pos[u][1]) * t
        if final and u in chosen and v not in chosen:
            kinds["cut"].append(curve)
            labels.append((lx, ly, capt))
        elif i in path_set:
            kinds["path"].append(curve)
            labels.append((lx, ly, f"{flow[i] / 100:g}" + ("" if inf else f"/{capt}")))
        elif flow[i] > 0:
            kinds["flow"].setdefault(max(1, round(1 + 5 * flow[i] / top)), []).append(curve)
        else:
            kinds["req" if inf else ("profit" if kind == sc.K_PROFIT else "cost")].append(curve)
    _lines(fig, kinds["req"], "rgba(120,120,120,0.55)", 1.3, "Voraussetzung (unendlich)", dash="dot")
    _lines(fig, kinds["profit"], "rgba(44,160,44,0.55)", 1.6, "Erlös-Kante (Kapazität = Erlös)")
    _lines(fig, kinds["cost"], "rgba(214,39,40,0.5)", 1.6, "Kosten-Kante (Kapazität = Kosten)")
    first = True
    for w, curves in sorted(kinds["flow"].items()):
        _lines(fig, curves, C.COLORS["flow"], w, "Fluss", showlegend=first)
        first = False
    _lines(fig, kinds["path"], C.COLORS["path"], 5, "Kante des letzten Weges")
    _lines(fig, kinds["cut"], C.COLORS["optimal"], 5, "Schnittkante (Kapazität beschriftet)")
    if net.m <= 90:
        plain = kinds["req"] + kinds["profit"] + kinds["cost"] + [c for cs in kinds["flow"].values() for c in cs]
        _arrows(fig, plain, "rgba(60,60,60,0.7)", 8)
    _arrows(fig, kinds["path"] + kinds["cut"], "rgba(30,30,30,0.9)", 11)
    _hover_points(fig, hover)
    _labels(fig, labels)
    idx = list(range(net.n))
    colors = [C.COLORS["node"] if not final else (C.COLORS["chosen"] if v in chosen else C.COLORS["left"]) for v in idx]
    texts = ["S", "T"] + [_weight_text(inst, i) for i in range(inst.n)]
    hovers = [net.names[v] for v in idx]
    pos = ["top center" if v == net.s else "bottom center" if v == net.t else ("top center" if v >= 2 and inst.kinds[v - 2] in ("store", "project") else "middle right") for v in idx]
    fig.add_trace(go.Scatter(x=[net.pos[v][0] for v in idx], y=[net.pos[v][1] for v in idx], mode="markers+text", showlegend=False, text=texts, textposition=pos,
                             hovertext=hovers, hoverinfo="text", textfont=dict(size=10),
                             marker=dict(symbol=["square" if v in (net.s, net.t) else "circle" for v in idx], size=[13 if v in (net.s, net.t) else 11 for v in idx], color=colors,
                                         line=dict(width=1.5, color="#333"))))
    return _layout(fig, net, height)


def build_methods(inst, values, height=280):
    """Gewinn je Verfahren (Balken); das Optimum in Rot."""
    import pj_evaluation as ev
    keys = list(ev.METHODS)
    fig = go.Figure(go.Bar(y=[ev.METHOD_LABELS[k] for k in keys][::-1], x=[values[k] for k in keys][::-1], orientation="h",
                           marker_color=[C.COLORS["optimal"] if k == "optimum" else "#1f77b4" for k in keys][::-1], text=[f"{values[k]}" for k in keys][::-1], textposition="outside"))
    fig.update_xaxes(title="Gewinn (Erlöse minus Kosten)", zeroline=True, zerolinecolor="#555")
    fig = _base(fig, height)
    fig.update_layout(margin=dict(l=10, r=30, t=10, b=10))
    return fig


def build_sweep(sw, inst, current_percent=None, height=460):
    """Preisreihe: oben je Knoten (Zeile) und Erlösniveau (Spalte), ob er gewählt ist - die Flächen wachsen nur nach rechts (geschachtelt); unten der Gewinn."""
    percents = sw["percents"]
    order = sorted(range(inst.n), key=lambda i: (next((k for k, s in enumerate(sw["sets"]) if s[i]), len(percents)), i))
    order = [i for i in order if any(s[i] for s in sw["sets"])] or order[:1]
    z = [[1 if s[i] else 0 for s in sw["sets"]] for i in order]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.68, 0.32], vertical_spacing=0.06)
    fig.add_trace(go.Heatmap(z=z, x=list(percents), y=[inst.labels[i] for i in order], colorscale=[[0, "#eeeeee"], [1, C.COLORS["chosen"]]], showscale=False,
                             hovertemplate="%{y} bei %{x} % Erlös: %{z}<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=list(percents), y=sw["values"], mode="lines", line=dict(color=C.COLORS["flow"], width=2), name="Gewinn", showlegend=False), row=2, col=1)
    if current_percent is not None:
        fig.add_vline(x=current_percent, line=dict(color=C.COLORS["optimal"], dash="dash"))
    fig.update_yaxes(type="category", autorange="reversed", row=1, col=1)
    fig.update_yaxes(title="Gewinn", row=2, col=1)
    fig.update_xaxes(title="Erlöse in Prozent des Ausgangswerts (Kosten fest)", row=2, col=1)
    return _base(fig, height)


def build_dist(dist, height=320):
    """Anteil des Optimums (im Mittel über die Netze mit positivem Optimum) je Verfahren."""
    rows = [r for r in dist["rows"] if r["opt"] > 0]
    names = ["Ressourcen-Greedy", "Projektweise", "Alles nehmen"]
    keys = ["resources", "projects", "all"]
    share = [sum(max(0, r[k]) / r["opt"] for r in rows) / len(rows) if rows else 0 for k in keys]
    hit = [sum(1 for r in rows if r[k] == r["opt"]) for k in keys]
    fig = go.Figure(go.Bar(x=names, y=share, marker_color="#1f77b4", text=[f"{s:.0%}<br>Optimum in {h} von {len(rows)}" for s, h in zip(share, hit)], textposition="outside"))
    fig.add_hline(y=1, line=dict(color=C.COLORS["optimal"], dash="dash"), annotation_text="Optimum (Schnitt)", annotation_position="top left")
    fig.update_yaxes(title="Anteil des optimalen Gewinns", range=[0, 1.25], tickformat=".0%")
    return _base(fig, height)


def build_or(oc, height=340):
    """Gewinn bei "alle nötig" (Schnitt) gegen "eine genügt" (MIP) je Netz."""
    rows = oc["rows"]
    top = max([r["or_value"] for r in rows] + [1]) * 1.05
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0, top], y=[0, top], mode="lines", line=dict(color="#555", dash="dash"), name="gleich", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=[r["and_value"] for r in rows], y=[r["or_value"] for r in rows], mode="markers", name="Netz", marker=dict(size=8, color=C.COLORS["flow"], opacity=0.75),
                             hovertext=[f"Seed {r['seed']}: alle nötig {r['and_value']}, eine genügt {r['or_value']}" for r in rows], hoverinfo="text"))
    fig.update_xaxes(title="Gewinn des Schnitts (alle Voraussetzungen nötig)", range=[-2, top])
    fig.update_yaxes(title="Gewinn bei „eine genügt“ (MIP)", range=[-2, top])
    return _base(fig, height)


def build_scaling(rows, height=340):
    """Durchsuchte Kanten gegen die Kantenzahl des Hilfsnetzes (doppelt logarithmisch): Dinic, Edmonds-Karp, Ford-Fulkerson."""
    fig = go.Figure()
    m = [r["m"] for r in rows]
    for key, label, color, dash in (("dinic", "Dinic", "#2ca02c", "solid"), ("bfs", "Edmonds-Karp", "#1f77b4", "solid"), ("dfs", "Ford-Fulkerson (Tiefensuche)", "#ff7f0e", "dot")):
        fig.add_trace(go.Scatter(x=m, y=[r[key] for r in rows], mode="lines+markers", name=label, line=dict(color=color, dash=dash)))
    fig.add_trace(go.Scatter(x=m, y=m, mode="lines", name="Kanten des Hilfsnetzes", line=dict(color="#555", dash="dashdot")))
    fig.update_xaxes(title="Kanten des Hilfsnetzes", type="log")
    fig.update_yaxes(title="durchsuchte Kanten", type="log")
    return _base(fig, height)
