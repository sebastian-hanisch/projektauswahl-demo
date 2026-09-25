"""Projektauswahl - welche Filialen sich lohnen, wenn Voraussetzungen Kosten teilen - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Anders als die Fall-Demos im Portfolio (ein Anwendungsfall, mehrere Verfahren im Vergleich) zeigt diese Demo EIN Verfahren - den minimalen Schnitt als Entscheidungsmodell - und lässt stattdessen das Beispiel wachsen.
Erste Erweiterung (Stück 13) der Netzwerkfluss-Linie der "Konzepte"-Reihe: hier ist der Schnitt nicht mehr der Beweis des maximalen Flusses, sondern das Modell. Siehe README für die Einordnung.

Lauffähig mit: streamlit run app.py
"""

import time

import streamlit as st

import pj_closure as cl
import pj_constants as C
import pj_evaluation as ev
from pj_presets import (
    KEPT,
    apply_preset,
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    randomize_seed,
    seed_widget,
    sync_query_params,
)
from pj_visualization import build_dist, build_methods, build_network, build_or, build_scaling, build_sweep

st.set_page_config(page_title="Projektauswahl – Sebastian Hanisch", layout="wide")


def _f(x, digits=1):
    return "–" if x is None else f"{x:.{digits}f}".replace(".", ",")


def _int(x):
    return f"{int(round(x)):,}".replace(",", " ")


def _share(x):
    return f"{100 * x:.0f} %"


@st.cache_resource(show_spinner=False, max_entries=32)
def _analysis(params):
    return ev.analyse(ev.Params(*params))


@st.cache_resource(show_spinner=False, max_entries=16)
def _distribution(params):
    return ev.distribution(ev.Params(*params))


@st.cache_resource(show_spinner=False, max_entries=16)
def _sweep(params):
    return ev.sweep(ev.instance(ev.Params(*params)))


@st.cache_resource(show_spinner=False, max_entries=16)
def _sweep_stats(params):
    return ev.sweep_stats(ev.Params(*params))


st.title("✂️ Projektauswahl – welche Filialen lohnen sich?")
st.markdown(
    """
Jede Filiale bringt einen **Erlös**, setzt aber voraus, dass **alle** Verteilzentren ihrer Warengruppen laufen - und jedes Verteilzentrum setzt seine Werke voraus. Jede Anlage kostet Betriebskosten, und mehrere Filialen **teilen** sich dieselbe Anlage.
Einzeln gerechnet lohnt sich fast keine Filiale, gemeinsam fast alle - welche Auswahl bringt den größten Gewinn, ohne eine Voraussetzung zu verletzen? Das ist ein Flussproblem in Verkleidung: aus Erlösen, Kosten und Voraussetzungen wird ein **Hilfsnetz**,
und ein **minimaler Schnitt** trennt die gewählte von der nicht gewählten Menge (Picard 1976). Diese Demo zeigt den Bau des Netzes, den Schnitt, wie einfachere Verfahren an gemeinsamen Kosten scheitern - und wo das Modell endet: sobald **eine** Anlage genügt, ist es kein Schnittproblem mehr.
"""
)
st.caption(
    "Anders als die Fall-Demos im Portfolio, die an einem Anwendungsfall mehrere Verfahren vergleichen, zeigt diese Demo - erste Erweiterung der Netzwerkfluss-Linie der \"Konzepte\"-Reihe, Kind von Edmonds-Karp und Dinic - **ein** Verfahren an einem wachsenden Beispiel. "
    "Bisher war der Schnitt nur der Beweis des maximalen Flusses; hier ist er das **Modell**. Danach kommt **Graph Cuts** (binäre Beschriftung mit Glattheitsstrafe, Boykov-Kolmogorov)."
)

with st.expander("So funktioniert die Auswahl per Schnitt", expanded=True):
    st.markdown(
        r"""
1. **Gewichte:** jeder Knoten hat ein Gewicht $w_i$: Erlös $>0$ (Filiale), Kosten $<0$ (Verteilzentrum, Werk). Eine **Voraussetzung** $(i, j)$ heißt: wer $i$ wählt, muss auch $j$ wählen. Gesucht ist die Menge $C$ ohne verletzte Voraussetzung mit dem größten $\sum_{i\in C} w_i$ - eine **gewichtsmaximale abgeschlossene Menge**.
2. **Hilfsnetz:** Quelle $s$ → jede Filiale mit dem Erlös als Kapazität; jeder Kostenknoten → Senke $t$ mit den Kosten als Kapazität; jede Voraussetzung als Kante $i \to j$ mit **unendlicher** Kapazität.
3. **Schnitt:** ein Schnitt mit endlicher Kapazität schneidet keine Voraussetzungskante durch: alles, was eine gewählte Filiale voraussetzt, liegt mit ihr auf der Quellseite. Er kostet die Erlöse der nicht gewählten Filialen (Quellkanten) plus die Kosten der gewählten Anlagen (Senkenkanten). Der Gewinn der Auswahl ist deshalb **Summe aller Erlöse minus Schnittkapazität**.
4. **Fluss:** ein minimaler Schnitt hat die Kapazität des maximalen Flusses. Dinic, Edmonds-Karp oder Ford-Fulkerson füllen das Hilfsnetz Weg für Weg; die von $s$ erreichbaren Knoten im Restgraphen sind die beste Auswahl. Wer den Fluss in der Abbildung verfolgt, sieht, wie Erlöse gegen Kosten aufgerechnet werden: ein Weg $s \to$ Filiale $\to$ DC $\to$ Werk $\to t$ verrechnet Erlös mit Kosten.
5. **Zwei Grenzfälle:** ein DC, das kein Erlös trägt, wird nur gewählt, wenn die Erlöse seiner Filialen es tragen; und eine Filiale, deren Kette zu teuer ist, bleibt draußen - selbst wenn ihr eigener Erlös hoch ist.
        """
    )

st.caption("🎯 Schnellstart – ein Beispiel laden:")
names = list(C.PRESETS.keys())
for row in range(0, len(names), 4):
    preset_cols = st.columns(4)
    for col, name in zip(preset_cols, names[row:row + 4]):
        with col:
            st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP[name])

st.caption(
    "🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, "
    "um ein Szenario zu teilen."
)

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    net_key = st.selectbox(
        "Beispiel", list(C.NETS), key="net_select", format_func=lambda k: C.NETS[k],
        help="Ein zufälliges Distributionsnetz oder eines der festen Beispiele: gemeinsames DC (jede Filiale allein verliert, zusammen gewinnen sie), Kette, Nichts lohnt, Greedy-Falle und die Negativkontrolle „eine Anlage genügt“.",
    )
    algorithm = st.radio(
        "Flussverfahren", list(C.ALGORITHMS), key="algorithm_radio", format_func=lambda k: C.ALGORITHMS[k],
        help="Alle drei finden denselben Gewinn (der Schnitt ist ein Zertifikat); sie unterscheiden sich in den Wegen und in den durchsuchten Kanten. Dinic durchsucht bei 13 Knoten etwa 1,3-mal weniger Kanten als Edmonds-Karp, bei 366 Knoten etwa 19-mal weniger.",
    )
    if net_key == "random":
        seed_widget("p_slider")
        p = st.slider("Werke", *bounds("p_slider"), key="p_slider", help="Anzahl der Werke (unten im Netz).")
        st.session_state[KEPT["p_slider"]] = p
        seed_widget("d_slider")
        d = st.slider("Verteilzentren", *bounds("d_slider"), key="d_slider", help="Anzahl der Verteilzentren; jedes setzt ein bis zwei Werke voraus.")
        st.session_state[KEPT["d_slider"]] = d
        seed_widget("s_slider")
        s = st.slider("Filialen", *bounds("s_slider"), key="s_slider", help="Anzahl der Filialen (oben im Netz); jede bringt 10 bis 50 Erlös.")
        st.session_state[KEPT["s_slider"]] = s
        seed_widget("fan_slider")
        fan = st.slider("Voraussetzungen je Filiale (höchstens)", *bounds("fan_slider"), key="fan_slider", help="Eine Filiale setzt 1 bis zu diesem Wert Verteilzentren voraus (mehrere Warengruppen). Bei 1 hängt jede Filiale an genau einem DC.")
        st.session_state[KEPT["fan_slider"]] = fan
        seed_widget("cost_slider")
        cost = st.slider("Betriebskosten [% der Standardkosten]", *bounds("cost_slider"), key="cost_slider", step=10, help="Skaliert die Kosten aller Werke und Verteilzentren. Bei 100 % lohnt sich in 34 von 40 festen Netzen eine Auswahl, bei 150 % in 18, bei 200 % in 3.")
        st.session_state[KEPT["cost_slider"]] = cost
        seed_widget("seed_input")
        seed = st.number_input("Zufalls-Seed", *bounds("seed_input"), key="seed_input", step=1)
        st.session_state[KEPT["seed_input"]] = seed
        st.button("🎲 Neues Netz generieren", width="stretch", on_click=randomize_seed, help="Würfelt einen neuen Zufalls-Seed. Die Verteilungen über 40 feste Netze weiter unten ändern sich dabei nicht.")
    else:
        p = int(st.session_state.get(KEPT["p_slider"], C.DEFAULT_P))
        d = int(st.session_state.get(KEPT["d_slider"], C.DEFAULT_D))
        s = int(st.session_state.get(KEPT["s_slider"], C.DEFAULT_S))
        fan = int(st.session_state.get(KEPT["fan_slider"], C.DEFAULT_FAN))
        cost = int(st.session_state.get(KEPT["cost_slider"], C.DEFAULT_COST))
        seed = int(st.session_state.get(KEPT["seed_input"], C.DEFAULT_SEED))
        st.caption("Dieses Beispiel ist fest - es gibt nichts zu erzeugen. Werke, Verteilzentren, Filialen, Voraussetzungen, Kosten und Seed gehören zum zufälligen Netz.")

sync_query_params({"net_select": net_key, "algorithm_radio": algorithm, "p_slider": int(p), "d_slider": int(d), "s_slider": int(s), "fan_slider": int(fan),
                   "cost_slider": int(cost), "seed_input": int(seed)})

# feste Beispiele ignorieren die Zufallsregler: sonst würden gleiche Beispiele unter verschiedenen Schlüsseln mehrfach berechnet
params = (net_key, int(p), int(d), int(s), int(fan), int(cost), int(seed), algorithm)
if net_key in C.FIXED_NETS:
    params = (net_key, C.DEFAULT_P, C.DEFAULT_D, C.DEFAULT_S, C.DEFAULT_FAN, C.DEFAULT_COST, C.DEFAULT_SEED, algorithm)
with st.spinner("Rechne..."):
    a = _analysis(params)
inst, sol, values = a["inst"], a["sol"], a["values"]
net = sol.net
code, n_stores_chosen, n_stores = ev.verdict(inst, sol, values)
fr = ev.frames(sol)
n_frames = len(fr) + 1                   # Bilder des Flusses und zuletzt der Schnitt
kind_of = {i: k for i, k in enumerate(inst.kinds)}
store_kinds = ("store", "project")


def _names(nodes):
    return ", ".join(inst.names[i] for i in nodes) or "keine"


def _count(kinds):
    return sum(1 for i in range(inst.n) if kind_of[i] in kinds and sol.chosen[i]), sum(1 for i in range(inst.n) if kind_of[i] in kinds)


# --- Hilfsnetz und Schnitt ---------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Vom Auswahlproblem zum Schnitt")
if st.session_state.get("pj_step_owner") != params:
    st.session_state["pj_step"] = n_frames - 1
    st.session_state["pj_step_owner"] = params
step_col, play_col = st.columns([5, 2])
with step_col:
    step = st.slider("Bild", 0, n_frames - 1, key="pj_step", help="Bild 0: das Hilfsnetz ohne Fluss; dann je ein Bild pro aufgefülltem Weg; ganz rechts der fertige Schnitt mit der Auswahl.")
with play_col:
    auto_play = st.button("▶️ Abspielen", width="stretch")
view_slot = st.empty()


def _render(k):
    with view_slot.container():
        if k >= len(fr):
            st.markdown(f"**Schnitt** - Kapazität {sol.flow.value / 100:g} = Fluss; Gewinn = Erlöse {inst.positive_total()} − {sol.flow.value / 100:g}")
            st.plotly_chart(build_network(inst, sol, flow=fr[-1][0], final=True), width="stretch", key=f"net_final_{k}")
            st.caption(
                f"Die grünen Knoten liegen auf der Quellseite: die gewählte Menge ({_names([i for i in range(inst.n) if sol.chosen[i]])}). "
                f"Die roten Schnittkanten sind entweder **verschenkte Erlöse** (Quelle → nicht gewählte Filiale) oder **bezahlte Kosten** (gewählte Anlage → Senke); Voraussetzungskanten werden nie durchschnitten. "
                f"Ihre Kapazitäten summieren sich auf {sol.flow.value / 100:g}, den Wert des maximalen Flusses."
            )
            return
        flow, path = fr[k]
        value = sum(flow[i] for i, (u, v, _, _, _) in enumerate(net.arcs) if u == net.s) / 100
        st.markdown(f"**Hilfsnetz** - " + ("noch kein Fluss" if k == 0 else f"Weg {k} von {len(fr) - 1}, Flusswert {value:g}"))
        st.plotly_chart(build_network(inst, sol, flow=flow, path=path), width="stretch", key=f"net_{k}")
        if k == 0:
            st.caption("Grün: Erlös-Kanten (Kapazität = Erlös der Filiale), rot: Kosten-Kanten (Kapazität = Kosten der Anlage), gepunktet grau: Voraussetzungen mit unendlicher Kapazität. Die Zahl unter einem Knoten ist sein Gewicht (+ Erlös, − Kosten).")
        else:
            nodes = [net.names[net.arcs[e][0]] for e in path] + [net.names[net.arcs[path[-1]][1]]]
            st.caption(f"Weg {k}: {' → '.join(nodes)}, um {min(net.arcs[e][2] - fr[k - 1][0][e] for e in path) / 100:g} aufgefüllt. Der Weg verrechnet den Erlös einer Filiale (Erlös-Kante, grün) mit den Kosten einer Anlage, die sie voraussetzt (Kosten-Kante, rot): beide Kanten werden um diese Menge voller. Ist eine Erlös-Kante voll, ist der Erlös dieser Filiale aufgebraucht; ist eine Kosten-Kante voll, sind die Kosten der Anlage durch Erlöse gedeckt.")


if auto_play:
    for k in range(n_frames):
        _render(k)
        time.sleep(min(0.7, 7.0 / max(n_frames, 1)))
    step = n_frames - 1
else:
    _render(step)

st.markdown("---")

# --- Ergebnis ---------------------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Was lohnt sich - und was findet ein einfacheres Verfahren?")
sf, st_total = _count(store_kinds)
df, dt = _count(("dc",))
wf, wt = _count(("plant",))
rf, rt = _count(("resource",))
m1, m2, m3, m4 = st.columns(4)
m1.metric("Gewinn der Auswahl", f"{sol.value}", delta=f"Erlös {sol.revenue} − Kosten {sol.cost}", delta_color="off", help="Erlöse der gewählten Filialen minus Kosten der gewählten Anlagen: das Maximum aller Auswahlen ohne verletzte Voraussetzung.")
m2.metric("Gewählte Filialen", f"{sf} von {st_total}", help="Filialen (bzw. Projekte) auf der Quellseite des Schnitts.")
m3.metric("Gewählte Anlagen", f"{df + wf + rf}", delta=(f"{df} von {dt} DCs, {wf} von {wt} Werken" if net.logistic else f"von {rt} Anlagen"), delta_color="off", help="Verteilzentren und Werke, die für die gewählten Filialen laufen müssen.")
m4.metric("Durchsuchte Kanten", _int(sol.scanned), delta=f"{sol.n_paths} Wege ({C.ALGORITHMS[algorithm]})", delta_color="off", help="Aufwand des Flussverfahrens im Hilfsnetz, maschinenunabhängig gezählt; Wege = aufgefüllte Verbesserungswege.")

base = values["optimum"]
if code == "empty":
    st.info("ℹ️ Nichts lohnt sich: keine Filiale trägt die Kosten ihrer Voraussetzungen, auch nicht gemeinsam. Die beste Auswahl ist die leere mit Gewinn 0; der minimale Schnitt kappt alle Erlös-Kanten.")
elif code == "all":
    st.success(f"✅ Es lohnt sich für **alle {n_stores_chosen}** Filialen: Gewinn {base} (Erlös {sol.revenue}, Kosten {sol.cost}). Projektweise Einzelprüfung findet {values['projects']}, Ressourcen-Greedy {values['resources']}.")
else:
    st.success(f"✅ Optimal: **{n_stores_chosen} von {n_stores}** Filialen mit Gewinn {base} (Erlös {sol.revenue}, Kosten {sol.cost}). Projektweise Einzelprüfung findet {values['projects']}, Ressourcen-Greedy {values['resources']}, Alles nehmen {values['all']}.")
if not sol.unique:
    extra = [i for i in range(inst.n) if sol.largest[i] and not sol.chosen[i]]
    st.info(f"ℹ️ Es gibt **mehrere beste Auswahlen** mit demselben Gewinn: gezeigt ist die kleinste (kleinste Quellseite). Die größte nimmt zusätzlich {_names(extra)}, ohne den Gewinn zu ändern - deren Erlöse und Kosten heben sich gerade auf.")

c1, c2 = st.columns([3, 2])
with c1:
    st.plotly_chart(build_methods(inst, values), width="stretch", key="methods_chart")
with c2:
    st.table({"Verfahren": [ev.METHOD_LABELS[k] for k in ev.METHODS], "Gewinn": [values[k] for k in ev.METHODS],
              "Anteil des Optimums": [_share(values[k] / base) if base > 0 else "–" for k in ev.METHODS]})
st.caption("**Projektweise (Einzelprüfung):** jede Filiale mit ihrer ganzen Kette allein bewerten, nur Gewinnbringer wählen - übersieht, was sich erst gemeinsam lohnt. **Ressourcen-Greedy:** schrittweise die Anlage samt Voraussetzungen öffnen, die den größten Gewinn bringt - findet einzelne DCs, aber keine Paare, die eine Filiale nur zusammen trägt. **Alles nehmen:** trägt Verlustbringer mit.")

if net_key in C.FIXED_NETS:
    st.info("Festes Beispiel: es gibt nur diese eine Ziehung. Für die Verteilungen über viele Netze ein zufälliges Distributionsnetz wählen.")
else:
    st.markdown(f"**Nicht nur dieses eine Netz:** {len(C.SWEEP_SEEDS)} feste Netze mit denselben Einstellungen (Werke {p}, Verteilzentren {d}, Filialen {s}, Voraussetzungen höchstens {fan}, Kosten {cost} %), getrennt vom Seed oben.")
    dist = _distribution(params)
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Netze mit Gewinn", f"{dist['positive']} von {dist['n']}", help="In den übrigen Netzen ist die leere Auswahl die beste.")
    p2.metric("Ressourcen-Greedy", _share(dist["loss_resources"]) + " verloren" if dist["positive"] else "–", delta=f"Optimum in {dist['hit_resources']} von {dist['positive']}", delta_color="off", help="Mittlerer Verlust gegen das Optimum über die Netze mit Gewinn.")
    p3.metric("Projektweise", _share(dist["loss_projects"]) + " verloren" if dist["positive"] else "–", delta=f"nichts gefunden in {dist['zero_projects']} von {dist['positive']}", delta_color="off", help="Mittlerer Verlust der Einzelprüfung; in den meisten Netzen wählt sie gar nichts.")
    p4.metric("LP gebrochen", f"{dist['lp_fractional']} von {dist['n']}", delta=f"mehrdeutige Schnitte: {dist['nonunique']}", delta_color="off", help="Das LP (0 ≤ x ≤ 1, x_i ≤ x_j) hat auf allen Netzen ganzzahlige Ecken: die Matrix ist total unimodular. Mehrdeutig: Netze, in denen kleinste und größte beste Auswahl verschieden sind.")
    st.plotly_chart(build_dist(dist), width="stretch", key="dist_chart")
    st.caption(f"Mittel über die {dist['positive']} Netze mit Gewinn. Im Optimum sind im Mittel {_share(dist['share_mean'])} der Filialen gewählt. Der Gewinn des Optimums liegt im Mittel bei {_f(dist['value_mean'], 1)}.")

st.markdown("---")

# --- Experimente -------------------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Kippt eine kleine Preisänderung alles?")
st.caption("Die Erlöse werden von 0 % bis 300 % des Ausgangswerts durchgefahren, die Kosten bleiben. Die Auswahlen sind **geschachtelt**: mehr Erlös nimmt nie eine Filiale oder Anlage weg (parametrische Schnitte). Nicht selten kommen aber ganze Gruppen auf einmal dazu.")
sw = _sweep(params)
sm1, sm2, sm3 = st.columns(3)
sm1.metric("Verschiedene Auswahlen", f"{sw['distinct']}", help="Wie viele verschiedene beste Auswahlen die 61 Erlösniveaus ergeben.")
sm2.metric("Größter Sprung", f"{sw['max_jump']} Knoten", help="Größte Zahl an Knoten, die zwischen zwei benachbarten Erlösniveaus (5 Prozentpunkte) auf einmal dazukommen.")
sm3.metric("Geschachtelt", "ja" if sw["nested"] else "nein", help="Jede Auswahl ist in der nächsten enthalten (Satz von Gallo, Grigoriadis und Tarjan).")
st.plotly_chart(build_sweep(sw, inst, current_percent=100), width="stretch", key="sweep_chart")
st.caption("Oben: eine Zeile je Knoten, grün = in der besten Auswahl bei diesem Erlösniveau; die grünen Flächen wachsen nur nach rechts. Unten der Gewinn. Die rote Linie markiert 100 %, den Ausgangswert.")
if net_key not in C.FIXED_NETS:
    ss = _sweep_stats(params)
    st.caption(f"Über die {ss['n']} festen Netze der Einstellung: in {ss['nested']} von {ss['n']} sind die Auswahlen geschachtelt; im Mittel gibt es {_f(ss['distinct_mean'], 1)} verschiedene Auswahlen, der größte Sprung nimmt im Mittel {_f(ss['jump_mean'], 1)} Knoten auf einmal auf ({_share(ss['jump_share_mean'])} der größten Auswahl), höchstens {ss['jump_max']}.")

st.subheader("🔬 Wo der Schnitt aufhört: eine Anlage genügt")
st.caption("Wenn eine Filiale nur **eines** ihrer Verteilzentren braucht (Alternativen statt Pflicht), ist das Problem eine Standortplanung, kein Schnitt mehr: die Voraussetzung ist ein „oder“. Der Schnitt bleibt zulässig, verlangt aber zu viel; das MIP (HiGHS) findet die wirklich beste Auswahl.")
if net_key == "either":
    o = cl.solve_or(inst)
    st.metric("Gewinn: Schnitt (alle nötig) gegen MIP (eine genügt)", f"{sol.value} gegen {o[0]}", help="Lehrbeispiel: eine Filiale mit Erlös 10 und zwei DCs zu je 6. Als Pflicht kostet die Kette 12 und lohnt nicht; als Alternative genügt ein DC (Gewinn 4).")
    st.caption("Die Filiale bleibt im Schnitt draußen, weil er beide DCs verlangt; mit „eine genügt“ reicht ein DC, und der Gewinn ist 4.")
elif net_key != "random":
    st.info("Für dieses Experiment ein zufälliges Distributionsnetz oder das Beispiel „Eine Anlage genügt“ wählen.")
else:
    if st.button("Über 40 Netze durchrechnen (dauert wenige Sekunden)", key="or_start"):
        st.session_state["or_on"] = True
    if st.session_state.get("or_on"):
        with st.spinner("Rechne Schnitt und MIP..."):
            oc = ev.or_control(ev.Params(*params))
        oo1, oo2, oo3 = st.columns(3)
        oo1.metric("MIP besser als Schnitt", f"{oc['better']} von {oc['n']}", help="Netze, in denen „eine genügt“ einen größeren Gewinn erlaubt als „alle nötig“.")
        oo2.metric("Fehlender Gewinn", _share(oc["gain_mean"]), help="Mittlerer Anteil des MIP-Optimums, den der Schnitt (alle nötig) verschenkt, über die Netze mit Gewinn.")
        oo3.metric("LP gebrochen", f"{oc['lp_fractional']} von {oc['n']}", help="Bei „eine genügt“ ist die Matrix nicht mehr total unimodular: das LP kann gebrochene Ecken haben (bei „alle nötig“ nie).")
        st.plotly_chart(build_or(oc), width="stretch", key="or_chart")
        st.caption("Jeder Punkt ein Netz: waagerecht der Gewinn des Schnitts, senkrecht der Gewinn bei „eine genügt“. Alle Punkte liegen auf oder über der Diagonalen: die Alternativen erlauben mehr. Der Schnitt ist dann eine zulässige, aber zu vorsichtige Antwort.")

st.subheader("🔬 Wächst der Aufwand langsam?")
st.caption("Durchsuchte Kanten von Dinic, Edmonds-Karp und Ford-Fulkerson im Hilfsnetz, von 13 bis 366 Knoten; das LP-Verfahren (HiGHS) zum Vergleich als Laufzeit.")
if st.button("Netze durchrechnen (dauert einige Sekunden)", key="scaling_start"):
    st.session_state["scaling_on"] = True
if st.session_state.get("scaling_on"):
    with st.spinner("Rechne 7 Größen × 10 Netze × 3 Verfahren..."):
        sc_rows = ev.scaling()
    st.plotly_chart(build_scaling(sc_rows), width="stretch", key="scaling_chart")
    st.table({"Werke / DCs / Filialen": [f"{r['P']} / {r['D']} / {r['S']}" for r in sc_rows], "Knoten": [_f(r["n"], 0) for r in sc_rows], "Kanten": [_f(r["m"], 0) for r in sc_rows],
              "Dinic": [_int(r["dinic"]) for r in sc_rows], "Edmonds-Karp": [_int(r["bfs"]) for r in sc_rows], "Ford-Fulkerson": [_int(r["dfs"]) for r in sc_rows],
              "Edmonds-Karp ÷ Dinic": [_f(r["bfs"] / r["dinic"], 1) for r in sc_rows], "LP (Millisekunden)": [_f(1000 * r["lp_seconds"], 1) for r in sc_rows]})
    st.caption("Mittel über 10 feste Netze je Größe (Kosten 100 %). Dinic wächst am langsamsten; der Abstand zu Edmonds-Karp wächst von etwa dem 1,3-Fachen auf das 19-Fache. Bei den kleinsten Netzen ist die Tiefensuche (Ford-Fulkerson) sogar etwas sparsamer als Dinic (165 gegen 179 Kanten). Das LP der Auswahl ist auf allen Größen in wenigen Millisekunden gelöst: für die Auswahl allein bringt der Schnitt keinen Zeitvorteil, er liefert aber den Fluss als Zertifikat und die Preisreihe billig.")

st.subheader("🔬 Stimmt die Auswahl wirklich?")
st.caption("Gegenprobe auf kleinen Netzen (11 Knoten): alle 2048 Auswahlen durchprobieren und mit dem Schnitt und dem LP vergleichen.")
if st.button("40 kleine Netze prüfen", key="check_start"):
    st.session_state["check_on"] = True
if st.session_state.get("check_on"):
    chk = ev.small_check()
    ck1, ck2 = st.columns(2)
    ck1.metric("Schnitt = alle Auswahlen", f"{chk['brute']} von {chk['n']}", help="Der beste Gewinn aller 2^11 Auswahlen ohne verletzte Voraussetzung stimmt mit dem Schnitt überein.")
    ck2.metric("Schnitt = LP", f"{chk['lp']} von {chk['n']}", help="Das LP mit x_i ≤ x_j hat denselben Zielwert.")

st.markdown("---")

# --- Grenzen -----------------------------------------------------------------------------------------------------------------------------

st.subheader("🚧 Wo die Annahmen enden")
st.markdown(
    """
| Annahme | Was passiert, wenn sie verletzt ist - und wer ansetzt |
|---|---|
| **Alle Voraussetzungen sind Pflicht** | Genügt eine von mehreren Anlagen, ist das ein „oder“: der Schnitt verlangt zu viel (im Mittel fehlt die Hälfte des Gewinns), das LP wird gebrochen, das Problem ist NP-schwer. Ansatzpunkt: **Standortplanung** (geplant: Facility Location, p-Median). |
| **Nur die Auswahl zählt** | Es gibt keine Mengen: eine Filiale ist ganz oder gar nicht beliefert. Wie viel wohin fließt, ist eine andere Frage. Ansatzpunkt: **Mehrgüterfluss** und **Fixkosten-Netzdesign** (gebaut). |
| **Die Kosten sind fest** | Kosten und Erlöse ändern sich nicht mit der Auswahl. Sinkende Stückkosten oder Rabatte machen die Zielfunktion nicht mehr linear. Die Preisreihe zeigt nur, wie die Auswahl auf feste Skalierungen reagiert. |
| **Jede Kante ein Ja/Nein** | Die Strafe für zwei unterschiedlich entschiedene Nachbarn ist hier unendlich (Voraussetzung). Endliche Strafen für unterschiedliche Nachbarn sind der nächste Schritt: **Graph Cuts** (nächstes Stück, geplant), binäre Beschriftung mit Glattheitsstrafe. |
| **Ein Zeitpunkt** | Die Auswahl gilt für eine Periode. Ansatzpunkt: Fall-Demo „Distributionsnetzwerk-Optimierung“. |
"""
)
st.caption("Die Netzwerkfluss-Linie ist als Ganzes geplant: die zwölf Stücke der Hauptlinie (gebaut), dazu die Erweiterung E1 (Graph Cuts): **Projektauswahl** (dieses Stück) und **Graph Cuts** (nächstes Stück, geplant).")

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Modell.** Gerichteter Graph $G=(V,A)$ mit Gewichten $w_i\in\mathbb{Z}$ und Voraussetzungen $(i,j)\in A$. Gesucht ist $C\subseteq V$ mit $(i,j)\in A,\ i\in C \Rightarrow j\in C$ (abgeschlossen), die $\sum_{i\in C} w_i$ maximiert:
$$\max \sum_i w_i x_i \quad \text{u.d.N.}\quad x_i \le x_j\ \ \forall (i,j)\in A,\quad x\in\{0,1\}^V.$$

**Hilfsnetz.** Quelle $s$, Senke $t$, $V^+=\{i: w_i>0\}$, $V^-=\{i: w_i<0\}$. Kanten $(s,i)$ mit Kapazität $w_i$ für $i\in V^+$, $(i,t)$ mit $-w_i$ für $i\in V^-$, $(i,j)$ mit Kapazität $\infty$ für jede Voraussetzung.

**Satz (Picard 1976).** Ist $(S\cup\{s\},\ \bar S\cup\{t\})$ ein Schnitt endlicher Kapazität, so ist $S$ abgeschlossen (sonst schnitte er eine $\infty$-Kante), und seine Kapazität ist
$$c(S)=\sum_{i\in V^+\setminus S} w_i+\sum_{i\in V^-\cap S}(-w_i)=W^+-\sum_{i\in S}w_i,\qquad W^+=\sum_{i\in V^+}w_i.$$
Also ist $S$ genau dann ein minimaler Schnitt, wenn $S$ eine gewichtsmaximale abgeschlossene Menge ist, und der Gewinn ist $W^+-\text{maxflow}$. Die von $s$ im Restgraphen erreichbare Menge ist die **kleinste** beste Auswahl, das Komplement der Knoten, von denen $t$ erreichbar ist, die **größte**; beide sind gleich, wenn der minimale Schnitt eindeutig ist.

**Ganzzahligkeit.** Die Matrix $x_i-x_j\le 0$ ist eine Netzwerkmatrix (total unimodular): das LP hat ganzzahlige Ecken, und der Schnitt löst es in Polynomialzeit. Mit „eine genügt“ ($x_i\le\sum_{j\in N(i)}x_j$) geht das verloren.

**Preisreihe.** Skaliert man alle Erlöse mit $\theta$, wachsen die Quellkapazitäten monoton in $\theta$; die kleinsten minimalen Schnitte sind dann geschachtelt (Gallo, Grigoriadis, Tarjan 1989), und alle Auswahlen zu allen $\theta$ berechnet man mit einem Fluss.

**Vergleichsverfahren.** Einzelprüfung: wähle $i\in V^+$ mit $w_i+\sum_{j\in \mathrm{Kette}(i)\setminus i}w_j>0$ samt Ketten. Ressourcen-Greedy: öffne wiederholt die Anlage $r\in V^-$ samt Voraussetzungen mit dem größten Gewinn (Erlöse aller damit vollständig freigeschalteten Filialen minus neue Kosten), solange er positiv ist.

Implementiert in `pj_scenario.py` (Instanzen, eigener Zufallsgenerator, Lehrbeispiele), `pj_closure.py` (Hilfsnetz, Auswahl per Schnitt, Gegenproben, Verfahren im Vergleich), `pj_dinic.py` und `pj_edmonds_karp.py` (Kopien der Vorgänger-Demos), `pj_evaluation.py` (Kennzahlen, Verteilungen, Experimente).
        """
    )

st.markdown("---")

st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning. Interesse an einer maßgeschneiderten Lösung für "
    "Ihr Unternehmen? [Kontakt aufnehmen](https://sebastianhanisch.net/kontakt.html)"
)
