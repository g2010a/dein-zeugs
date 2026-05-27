# dein-zeugs — Podcast-Fragenverwaltung

Ein macOS-CLI-Werkzeug für Apple Silicon, das aufgezeichnete Hörerfragen transkribiert, nach Neuheit gegenüber bereits ausgestrahlten Fragen bewertet, Duplikate clustert und einen HTML-Bericht erstellt. Konzipiert für nicht-technische Podcasterinnen und Podcaster: MP3s hineinziehen, Desktop-Starter doppelklicken, Ergebnis im Browser lesen.

Kein Python, kein Ollama, kein Quellcode-Checkout auf dem Zielrechner erforderlich — nur das Release-Archiv.

## Installation (Endnutzer)

1. Das neueste Release-Archiv von der [Releases-Seite](../../releases/latest) herunterladen. Es ist ein kleines Archiv (Binary plus zwei Skripte) — ca. 70 MB.
2. Das Archiv durch Doppelklick entpacken. Es erscheint ein Ordner mit drei Dateien:
   - `dein-zeugs` — das Programm
   - `install.sh` — Installationsskript
   - `Run dein-zeugs.command` — Desktop-Starter
3. Den entpackten Ordner einmal im Terminal öffnen (Rechtsklick auf den Ordner → *Dienste* → *Neues Terminal im Ordner*) und ausführen:
   ```bash
   bash install.sh
   ```
4. Das Installationsskript erledigt folgendes:
   - Kopiert `dein-zeugs` nach `/usr/local/bin/`
   - Entfernt das macOS-Quarantäne-Bit, damit Gatekeeper das Programm zulässt
   - Legt `Run dein-zeugs.command` auf dem Schreibtisch ab
   - Lädt alle drei Modelldateien vorab herunter (~2,3 GB insgesamt: Whisper + Einbettungsmodell + LLM). Dieser Schritt erfolgt einmalig und ist **das einzige Mal**, dass eine Internetverbindung benötigt wird. Fortschrittsbalken erscheinen im Terminal.

Nach der Installation kann der entpackte Ordner gelöscht werden. Das installierte Programm unter `/usr/local/bin/dein-zeugs` ist vollständig in sich geschlossen — es benötigt weder das Release-Archiv noch dieses Repository noch einen Python-Interpreter.

**Voraussetzungen:** macOS 14+, Apple Silicon (arm64).

## Tägliche Nutzung (nicht-technischer Arbeitsablauf)

1. Die MP3-Aufnahmen der Hörerfragen in `~/DeinZeugs/inbox/` ablegen. (Der Ordner `DeinZeugs/` und seine Unterordner werden beim ersten Start automatisch angelegt.)
2. **Run dein-zeugs.command** auf dem Schreibtisch doppelklicken.
3. Ein Terminalfenster öffnet sich. dein-zeugs transkribiert und analysiert jede Datei. Der HTML-Bericht öffnet sich danach automatisch im Standard-Browser. Jeder Start rendert den Bericht neu, sodass er den aktuellen Inhalt von `inbox/` und `aired/` widerspiegelt.
4. Sobald eine Frage in der Sendung ausgestrahlt wurde, die MP3 von `~/DeinZeugs/inbox/` in `~/DeinZeugs/aired/` verschieben. Beim nächsten Start dient `aired/` als Referenzkorpus — neue Fragen werden auf Neuheit gegenüber allem in `aired/` bewertet. Der Bericht selbst enthält file://-Links zu beiden Ordnern, sodass das Verschieben direkt im Finder erfolgen kann.

## Kommandozeilennutzung (optional)

Für die Nutzung im Terminal:

```
dein-zeugs                          # verwendet ~/DeinZeugs/ als Standard
dein-zeugs /pfad/zum/projektordner  # verwendet ein anderes Projektverzeichnis
dein-zeugs --warm-models            # Modell-Cache vorab herunterladen und beenden
dein-zeugs --warm-models --skip-llm # nur Whisper + Einbettungsmodell aufwärmen
dein-zeugs --clean-outputs          # analysis/ und reports/ leeren (inbox/ bleibt erhalten)
dein-zeugs --clean-downloads        # heruntergeladene Modelldateien löschen
dein-zeugs --yes                    # Bestätigungsabfragen überspringen
```

## Konfiguration

Eine `config.toml` wird beim ersten Start automatisch im Stammverzeichnis angelegt:

```toml
[analysis]
similarity_threshold = 0.80          # Kosinus-Ähnlichkeit, ab der eine Frage als Wiederholung gilt
whisper_model = "medium"             # tiny / base / small / medium / large
embedding_model = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
llm_model_path = "~/.dein_zeugs/models/Llama-3.2-3B-Instruct-Q4_K_M.gguf"

[paths]
analysis_dir = "analysis"            # optionale Überschreibung
reports_dir  = "reports"             # optionale Überschreibung

[report]
standouts_count = 10                 # Anzahl der Fragen mit höchster Neuheit im Highlights-Abschnitt
```

## Verzeichnisstruktur

```
~/DeinZeugs/                         # Standardwurzel (wird automatisch angelegt)
  inbox/                             # MP3-Fragenaufnahmen hier ablegen
  aired/                             # MP3s hierher verschieben, sobald die Frage ausgestrahlt wurde
  analysis/{stem}.yaml               # eine YAML-Datei pro Frage: Transkript, Zusammenfassung, Schlüsselwörter, Einbettung, Neuheitswerte
  reports/report.html                # der gerenderte Bericht (öffnet sich nach jedem Start automatisch)
  config.toml                        # wird automatisch mit Standardwerten angelegt
```

Modelldateien liegen außerhalb des Projektstammordners:

```
~/.cache/huggingface/hub/    # Whisper- und Einbettungsmodell-Cache (~200 MB)
~/.cache/fastembed/          # fastembed-Cache
~/.dein_zeugs/models/        # LLM GGUF (~2 GB)
```

## Was der Bericht zeigt

Der Bericht beginnt mit dem Abschnitt **Highlights**: die N Fragen mit dem höchsten `standout_score = min(novelty_vs_aired, intra_batch_uniqueness)`. Jede Karte enthält einen farbigen Neuheitsbalken (grün ≥ 0,7, gelb 0,4–0,7, rot < 0,4) sowie file://-Links zu `inbox/` und `aired/` für den direkten Zugriff im Finder.

Darunter folgen aufklappbare Abschnitte: mögliche Wiederholungen, die vollständige Fragenübersicht, Ähnlichkeitscluster (aufgeteilt in „nur neu" — Duplikate innerhalb dieser Runde — und „gemischt" — Überschneidungen mit bereits ausgestrahlten Fragen), die ausgestrahlten Fragen und noch nicht verarbeitete Dateien.

## Optional: Automator-Ordneraktion

Wer dein-zeugs automatisch starten möchte, sobald eine Datei in `inbox/` abgelegt wird (anstatt den Desktop-Starter doppelzuklicken), kann eine macOS-Automator-Ordneraktion einrichten. Die Schritt-für-Schritt-Anleitung findet sich unter [`installer/com.dein_zeugs.folderaction.workflow.md`](installer/com.dein_zeugs.folderaction.workflow.md). Dies ist für erfahrene Nutzer gedacht; die meisten können diesen Abschnitt ignorieren.

## Aus dem Quellcode bauen (nur für Maintainer)

Dieser Abschnitt richtet sich an diejenigen, die Releases erstellen. Endnutzer benötigen ihn nicht.

Python 3.12 ist erforderlich; 3.14+ wird nicht unterstützt.

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"
uv pip install pyinstaller
make build            # erstellt dist/dein-zeugs (~70 MB)
make package          # signiert das Binary
```

Für das Release-Archiv diese drei Dateien in einem flachen Verzeichnis zusammenstellen und als tar/zip packen:

```
dist/dein-zeugs
installer/install.sh
installer/Run dein-zeugs.command
```

Das fertige Archiv als GitHub-Release hochladen. Endnutzer laden nur dieses herunter.

## Entwicklung

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"
.venv/bin/pytest tests/ -q
```
