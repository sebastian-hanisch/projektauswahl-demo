# Projektauswahl – welche Filialen lohnen sich? – Streamlit-Demo

**[→ Demo live ausprobieren](https://sebastianhanisch-projektauswahl-demo.streamlit.app/)**

Erste Erweiterung (Stück 13) der **Netzwerkfluss-Linie** der "Konzepte"-Reihe für die Website "Sebastian Hanisch – Operations Research und Machine Learning", Kind von [edmonds-karp-demo](https://github.com/sebastian-hanisch/edmonds-karp-demo) und [dinic-demo](https://github.com/sebastian-hanisch/dinic-demo):
anders als die Fall-Demos im Portfolio (ein Anwendungsfall, mehrere Verfahren im Vergleich) zeigt diese Demo **ein** Verfahren – den **minimalen Schnitt als Entscheidungsmodell** – an einem wachsenden Beispiel.
In der Hauptlinie war der Schnitt nur der *Beweis* des maximalen Flusses (Max-Flow = Min-Cut); hier ist er das *Modell*. Jede Filiale bringt einen **Erlös**, setzt aber voraus, dass **alle** Verteilzentren ihrer Warengruppen laufen, und jedes Verteilzentrum setzt seine Werke voraus; jede Anlage kostet Betriebskosten, mehrere Filialen teilen sich dieselbe Anlage.
Gesucht ist die Auswahl mit dem größten Gewinn (Erlöse minus Kosten) ohne verletzte Voraussetzung – eine **gewichtsmaximale abgeschlossene Menge** (Picard 1976). Ein **Hilfsnetz** macht daraus einen Fluss: Quelle → Filiale mit dem Erlös als Kapazität, Anlage → Senke mit den Kosten, jede Voraussetzung als Kante mit unendlicher Kapazität; ein minimaler Schnitt trennt die gewählte von der nicht gewählten Menge, und der Gewinn ist *Summe aller Erlöse minus Schnittkapazität*.
Vehikel: das Distributionsnetz der Linie (Werke, Verteilzentren, Filialen) mit Voraussetzungen, dazu fünf feste Lehrbeispiele (gemeinsames DC, Kette, nichts lohnt, Greedy-Falle, „eine Anlage genügt“).

**Einordnung in die Reihe (die Kanten des Graphen):** Der Schnitt ist der Zertifikatsteil von Edmonds-Karp und Dinic, hier zum Modell erhoben; Dinic, Edmonds-Karp und Ford-Fulkerson (Kopien aus den Vorgängern) füllen das Hilfsnetz. Die Grenze des Modells – **eine** Anlage genügt statt aller – führt zur Standortplanung (Erweiterung E3, geplant); endliche statt unendlicher Strafen für unterschiedlich entschiedene Nachbarn führen zum nächsten Stück, **Graph Cuts** (binäre Beschriftung mit Glattheitsstrafe, Boykov-Kolmogorov; geplant). Bisher gebaut: die zwölf Stücke der Hauptlinie und dieses Stück.
```
edmonds-karp-demo (Wurzel: Restgraph, Rückkanten, Max-Flow = Min-Cut)                  [gebaut]
  ├─ dinic-demo (viele kürzeste Wege je Phase: Niveaugraph, blockierender Fluss)        [gebaut]
  ├─ push-relabel-demo (kein Weg: Überschüsse schieben, Höhen anheben)                 [gebaut]
  └─ ssp-demo (Kosten: der billigste Weg im Restgraphen, Potenziale)                    [gebaut]
       ├─ cycle-canceling-demo (negative Kreise löschen) → Netzwerksimplex               [gebaut]
       ├─ cost-scaling-demo (Push-Relabel + ε-Skalierung, das nutzt OR-Tools)           [gebaut]
       └─ multicommodity-demo (mehrere Güter teilen Kapazität: Kanten-LP, Preise)       [gebaut]
            ├─ mcf-column-generation-demo (Pfade als Spalten, Pricing = Dijkstra)       [gebaut]
            ├─ garg-koenemann-demo (Näherung mit Preisen, ohne LP-Löser)                [gebaut]
            └─ fixkosten-netzdesign-demo (Fixkosten: Schranke und Schnitte)             [gebaut]
                 ├─ benders-demo (Entwurf im Master, Fluss im Teilproblem)              [gebaut]
                 └─ slope-scaling-demo (Fixkosten linearisieren, ohne Beweis)           [gebaut]

Erweiterung E1: der Schnitt als Modell (Kind von edmonds-karp-demo und dinic-demo)
  └─ projektauswahl-demo (Auswahl mit Voraussetzungen = Schnitt)                        [dieses Stück]
       └─ graph-cuts-demo (endliche Nachbarstrafen, Boykov-Kolmogorov)                  [geplant]
```

## Ergebnis (Zahlen aus den Tests)

Jede hier genannte Zahl ist in `tests/test_claims.py` belegt: Lehrbeispiele von Hand, Beispielnetze über ihre Seeds, Verteilungen über feste Netze (Seeds ab 100000, dieselben wie in den Vorgänger-Demos, 40 Netze). Standard: 3 Werke, 4 Verteilzentren, 8 Filialen, jede Filiale setzt 1 bis 2 Verteilzentren voraus, Betriebskosten 100 %, Flussverfahren Dinic.
Auswahl und Gewinn sind ganzzahlig und deterministisch (eigener Zufallsstrom); Aufwand wird in durchsuchten Kanten gezählt, nie in Sekunden. Die Kopien aus den Vorgängern sind bewacht (`tests/test_copies.py`).

**Der Schnitt findet die beste Auswahl – und bezahlt den Fluss dafür.** Auf 40 kleinen Netzen (11 Knoten) stimmt der Gewinn des Schnitts in **40 von 40** mit dem Durchprobieren aller 2 048 Auswahlen und mit dem LP überein. Das LP ($x_i\le x_j$, $0\le x\le1$) hat auf **keinem** der 40 Standardnetze eine gebrochene Ecke – die Matrix ist total unimodular; das steht im Kontrast zum Mehrgüterfluss (multicommodity-demo), wo diese Eigenschaft verloren geht. Im Standardnetz (Seed 24): **5 von 8 Filialen**, Gewinn **30** (Erlös 180, Kosten 150), gewählt sind dazu 3 Verteilzentren und 2 Werke; Dinic braucht 12 Wege und 224 durchsuchte Kanten, Edmonds-Karp 441, Ford-Fulkerson 364 (15 Wege).

**Einfachere Verfahren scheitern an geteilten Kosten.** Über die 40 Standardnetze (34 mit positivem Gewinn, im Optimum sind im Mittel 86 % der Filialen gewählt):
die **projektweise Einzelprüfung** (jede Filiale mit ihrer ganzen Kette allein bewerten) verliert im Mittel **98 %** des Gewinns und findet in **30 von 34** Netzen gar nichts, weil kein Erlös allein die Kette trägt; **Ressourcen-Greedy** (schrittweise die Anlage samt Voraussetzungen öffnen, die den größten Gewinn bringt) verliert im Mittel **44 %** und trifft das Optimum in **17 von 34**; **Alles nehmen** verliert 58 %. Im Standardnetz: Einzelprüfung 0, Ressourcen-Greedy 12, Alles nehmen 27 gegen 30.
Lehrbeispiel „Gemeinsames DC“: ein DC (Kosten 10), drei Filialen mit Erlös 6, 7 und 3 – jede allein verliert, zusammen gewinnen sie 16 − 10 = **6**; die Einzelprüfung wählt nichts.
**Ressourcen-Greedy scheitert an *mehreren* Voraussetzungen, nicht an geteilten Kosten:** braucht jede Filiale genau ein Verteilzentrum, ist es fast optimal (Verlust 3 %, Optimum in 36 von 40 Netzen); bei bis zu 2 Voraussetzungen verliert es 44 %, bei bis zu 3 **71 %** (Optimum in 6 von 33 Netzen) – zwei DCs, die eine Filiale nur *zusammen* trägt, findet kein Schritt für Schritt vorgehendes Verfahren.

**Eine kleine Preisänderung kippt ganze Gruppen.** Die Erlöse von 0 % bis 300 % durchgefahren: die Auswahlen sind in **40 von 40** Netzen **geschachtelt** (mehr Erlös nimmt nie etwas weg, parametrische Schnitte nach Gallo/Grigoriadis/Tarjan), aber es gibt nur im Mittel **2,9 verschiedene** Auswahlen, und der größte Sprung nimmt im Mittel **11,3 Knoten** (78 % der größten Auswahl) auf einmal auf, höchstens 15. Im Standardnetz sind es 3 verschiedene Auswahlen (leer, 5 Filialen, alle 8) mit einem Sprung um 10 Knoten. Im Standardnetz kommen bei einer Erlösänderung von nur 5 Prozentpunkten 10 der schließlich 15 gewählten Knoten auf einmal dazu: wer Erlöse oder Kosten schätzt, sollte der Feinheit des Ergebnisses nicht trauen.
Wie stark die Kosten die Auswahl bestimmen: bei 50 % Kosten lohnt sich in 40 von 40 Netzen etwas, bei 100 % in 34, bei 150 % in 18, bei 200 % in 3, bei 250 % in keinem.

**Wo das Modell endet: eine Anlage genügt.** Dieselben 40 Netze, aber jede Filiale braucht nur **eines** ihrer Verteilzentren (Alternativen statt Pflicht): das MIP (HiGHS) findet in **39 von 40** Netzen mehr als der Schnitt, der Schnitt verschenkt im Mittel **50 %** des Gewinns (Standardnetz: 30 gegen 96), und das LP ist in **6 von 40** Netzen gebrochen (bei „alle nötig“ in 0). Lehrbeispiel: eine Filiale (Erlös 10), zwei DCs zu je 6 – als Pflicht kostet die Kette 12 (Auswahl leer), als Alternative genügt ein DC (Gewinn 4). Das ist kein Schnittproblem mehr, sondern Standortplanung.

**Aufwand.** Durchsuchte Kanten im Hilfsnetz (Mittel über 10 Netze je Größe, Kosten 100 %): bei 13 Knoten Dinic 179, Edmonds-Karp 239, Ford-Fulkerson 165 – die Tiefensuche ist hier sogar etwas sparsamer als Dinic; bei 19 Knoten ist Edmonds-Karp das **1,6-Fache** von Dinic, bei 366 Knoten das **19-Fache** (9 146 gegen 172 817). Das LP der Auswahl löst HiGHS auf jeder Größe in wenigen Millisekunden: für die Auswahl allein bringt der Schnitt keinen Zeitvorteil gegenüber dem LP; er liefert den Fluss als Zertifikat und die Preisreihe billig.

## Was nicht funktioniert hat / Vorab-Hypothesen

Vor dem Bau standen fünf Vermutungen im Plan. Gemessen:

- **„Einfaches Greedy verliert spürbar“ – untertrieben.** Die Einzelprüfung verliert 98 % und findet meist nichts; erst Ressourcen-Greedy ist brauchbar (44 %), und selbst das nur, solange jede Filiale ein Verteilzentrum braucht (3 %).
- **„Das LP ist immer ganzzahlig“ – bestätigt** (0 von 40 gebrochen, 40 von 40 kleine Netze gleich dem Durchprobieren) und im Kontrast zum Mehrgüterfluss und zu „eine genügt“ (6 von 40 gebrochen).
- **„Die Auswahlen sind geschachtelt“ – bestätigt (40 von 40), aber es gibt nur wenige verschiedene** (2,9) mit großen Sprüngen; von einer feinen Preiskurve kann keine Rede sein.
- **„Der Schnitt ist oft nicht eindeutig“ – selten:** nur 1 von 40 Standardnetzen hat mehrere beste Auswahlen (Preset „Mehrere beste Schnitte“: Seed 21 mit Gewinn 7, die größte beste Auswahl nimmt zusätzlich W1, D1, F1, F2, F3 ohne Gewinnänderung).
- **„Der Schnitt ist schneller als HiGHS“ – widerlegt:** das LP der Auswahl braucht auf allen Größen wenige Millisekunden; der Schnitt lohnt wegen des Zertifikats und der Preisreihe, nicht wegen der Geschwindigkeit. Dinic gewinnt aber gegen Edmonds-Karp mit wachsendem Abstand (1,3- bis 19-fach).

## Was die Demo zeigt

- **Vom Auswahlproblem zum Schnitt:** ein Regler durch die Bilder – das Hilfsnetz (grün: Erlös-Kanten, rot: Kosten-Kanten, grau gepunktet: Voraussetzungen unendlich), je Verbesserungsweg ein Bild mit dem Fluss (Breite ~ Fluss), am Ende der Schnitt mit der gewählten Menge (grün) und den roten Schnittkanten (verschenkte Erlöse und bezahlte Kosten).
- **Verfahren im Vergleich:** Gewinn von Schnitt, Ressourcen-Greedy, Einzelprüfung, Alles und Nichts; Flussverfahren wählbar (Dinic, Edmonds-Karp, Ford-Fulkerson).
- **Nicht nur dieses Netz:** Verteilung über 40 feste Netze mit Verlust je Verfahren, LP-Ganzzahligkeit und Mehrdeutigkeit.
- **Experimente:** Preisreihe (Erlöse 0 bis 300 %) mit Heatmap der geschachtelten Auswahlen, Grenze „eine genügt“ (auf Abruf), Aufwand nach Größe (auf Abruf), Gegenprobe gegen alle Auswahlen und das LP (auf Abruf).
- **Wo die Annahmen enden:** Pflicht statt Alternative, nur Ja/Nein, feste Kosten, unendliche Strafen für unterschiedliche Nachbarn, ein Zeitpunkt.

## Modell und Verfahren

- **Modell:** $\max\sum_i w_i x_i$ u.d.N. $x_i\le x_j$ für jede Voraussetzung $(i,j)$, $x\in\{0,1\}$; $w_i>0$ Erlös (Filiale), $w_i<0$ Kosten (Verteilzentrum, Werk).
- **Hilfsnetz:** Kanten $(s,i)$ mit Kapazität $w_i$ für $w_i>0$, $(i,t)$ mit $-w_i$ für $w_i<0$, $(i,j)$ mit endlicher, aber größerer Kapazität als jeder Schnitt (Summe aller Erlöse plus 1) für jede Voraussetzung. Der Gewinn einer Auswahl ist $W^+-c(S)$; der minimale Schnitt liefert das Optimum.
- **Kleinste und größte beste Auswahl:** die von $s$ im Restgraphen erreichbare Menge (kleinste Quellseite) und das Komplement der Knoten, von denen $t$ erreichbar ist (größte); beide fallen zusammen, wenn der minimale Schnitt eindeutig ist.
- **Vergleichsverfahren:** Einzelprüfung (Filiale samt Kette allein bewerten), Ressourcen-Greedy (Anlage samt Voraussetzungen mit dem größten Zusatzgewinn öffnen), Alles, Nichts; Gegenproben: alle $2^n$ Auswahlen (bis 18 Knoten), LP und MIP in HiGHS.
- **Preisreihe:** Erlöse mit $\theta\in[0,3]$ skaliert (alle Gewichte mal 100, damit alles ganzzahlig bleibt); die kleinsten minimalen Schnitte sind geschachtelt.

## Ehrliche Grenzen

- **Alle Voraussetzungen sind Pflicht.** Genügt eine von mehreren Anlagen, ist das Problem NP-schwer (Standortplanung); der Schnitt bleibt zulässig, verlangt aber zu viel.
- **Nur Auswahl, keine Mengen.** Eine Filiale ist ganz oder gar nicht beliefert; wie viel wohin fließt, klären Mehrgüterfluss und Netzdesign.
- **Feste Kosten und Erlöse.** Sinkende Stückkosten oder Rabatte machen die Zielfunktion nichtlinear.
- **Nur unendliche Strafen.** Eine Voraussetzung ist eine Kante mit unendlicher Kapazität; endliche Strafen für unterschiedlich entschiedene Nachbarn sind das nächste Stück (Graph Cuts).
- **Synthetische Daten:** Erlöse 10 bis 50, Kosten der Verteilzentren 20 bis 50, der Werke 10 bis 30 (vor dem Kostenniveau); kein Kundenbezug.

## Bewusst nicht umgesetzt

- Mehrklassen-Beschriftung ($\alpha$-Expansion), nicht-submodulare Energien (QPBO) und Bildbeispiele – gehören zum nächsten Stück oder sind bewusst ausgelassen.
- Facility Location / p-Median (Erweiterung E3) – die Grenze „eine genügt“ wird gezeigt, nicht gelöst.
- Gomory-Hu-Baum (optionales drittes Stück der Erweiterung E1).

## Dateien

```
app.py                  Oberfläche (Streamlit)
pj_scenario.py          Instanzen (Voraussetzungen, Lage, Zufallsgenerator), Lehrbeispiele, Net
pj_closure.py           Hilfsnetz, Auswahl per Schnitt, Gegenproben, Vergleichsverfahren, Preisreihe
pj_dinic.py             Dinic (Kopie aus dinic-demo)
pj_edmonds_karp.py      Edmonds-Karp, Ford-Fulkerson (Kopie aus edmonds-karp-demo/dinic-demo)
pj_evaluation.py        Auswertung, Verteilungen, Experimente
pj_visualization.py     Plotly-Abbildungen
pj_presets.py           Permalink, Presets, Zufalls-Seed
pj_constants.py         Konstanten, Regler-Grenzen, feste Seed-Mengen, Preset-Texte
tests/                  Kern, Auswertung, Presets, Behauptungen, Kopien, App, Regler-Zustand
```

## Lokal starten

```bash
python -m venv venv
venv/Scripts/pip install -r requirements.txt
venv/Scripts/streamlit run app.py
```

## Tests ausführen

```bash
venv/Scripts/pip install -r requirements-dev.txt
venv/Scripts/python -m pytest tests/ -v
```

Gebaut mit Streamlit, Plotly, NumPy, SciPy (HiGHS) und einem eigenen Flusskern.
