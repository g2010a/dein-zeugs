# podq — Podcast Question Manager

A macOS Apple Silicon CLI tool that transcribes recorded listener questions, ranks them by novelty against questions you've already aired, clusters near-duplicates, and produces an HTML report. Designed so a non-technical podcaster can drag MP3s in, double-click a Desktop launcher, and read the result in their browser.

No Python, no Ollama, no source checkout required on the target machine — just the release archive.

## Installation (end users)

1. Download the latest release archive from the [releases page](../../releases/latest). It is a small archive (binary plus two scripts) — about 70 MB.
2. Double-click the archive to unpack it. You'll get a folder containing three files:
   - `podq` — the binary
   - `install.sh` — installer script
   - `Run podq.command` — Desktop launcher
3. Open the unpacked folder in Terminal once (right-click the folder → *Services* → *New Terminal at Folder*) and run:
   ```bash
   bash install.sh
   ```
4. The installer will:
   - Copy `podq` to `/usr/local/bin/`
   - Strip the macOS quarantine bit so Gatekeeper allows it to run
   - Place `Run podq.command` on your Desktop
   - Pre-download all three model files (~2.3 GB total: Whisper + embedding + LLM). This step runs once and is **the only time** you need internet for podq. Progress bars stream in the Terminal during the download.

After install you may delete the unpacked folder. The installed binary in `/usr/local/bin/podq` is fully self-contained — it does not need the release archive, this repository, or any Python interpreter to run.

**Requirements:** macOS 14+, Apple Silicon (arm64).

## Daily use (non-technical workflow)

1. Drop the MP3s of recorded listener questions into `~/Podq/inbox/`. (The `Podq/` folder and its subdirectories are created automatically on first run if they don't exist.)
2. Double-click **Run podq.command** on your Desktop.
3. A Terminal window pops up, podq transcribes and analyses each file, and the HTML report opens in your default browser when done. Each run also re-renders the report so it reflects whatever is currently in `inbox/` and `aired/`.
4. After a question has aired on your show, drag its MP3 from `~/Podq/inbox/` into `~/Podq/aired/`. The next run will treat it as the reference corpus — new questions are scored for novelty against everything in `aired/`. The report itself links to both folders so you can do this drag in Finder without typing paths.

## Command-line use (optional)

If you prefer Terminal:

```
podq                       # uses ~/Podq/ by default
podq /path/to/some/root    # uses a different project directory
podq --warm-models         # pre-download model caches and exit
podq --warm-models --skip-llm    # warm only Whisper + embedding
podq --clean-outputs       # wipe analysis/ and reports/ (preserves inbox/)
podq --clean-downloads     # delete cached model files
podq --yes                 # skip confirmation prompts
```

## Configuration

A `config.toml` is created automatically in the root directory on first run:

```toml
[analysis]
similarity_threshold = 0.80          # cosine similarity above which a question is treated as a repeat
whisper_model = "medium"             # tiny / base / small / medium / large
embedding_model = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
llm_model_path = "~/.podq/models/Llama-3.2-3B-Instruct-Q4_K_M.gguf"

[paths]
analysis_dir = "analysis"            # optional override
reports_dir  = "reports"             # optional override

[report]
standouts_count = 10                 # number of top-novelty questions in the report's Highlights section
```

## Directory layout

```
~/Podq/                     # default root (auto-created)
  inbox/                    # drop MP3 question recordings here
  aired/                    # move MP3s here once their question has aired
  analysis/{stem}.yaml      # one merged YAML per question: transcript, summary, keywords, embedding, novelty scores
  reports/report.html       # the rendered report (opens automatically after each run)
  config.toml               # auto-created with defaults
```

Model files live outside the project root:

```
~/.cache/huggingface/hub/    # Whisper + embedding caches (~200 MB)
~/.cache/fastembed/          # fastembed cache
~/.podq/models/              # LLM GGUF (~2 GB)
```

## What the report shows

The report opens with a **Highlights** section: the top-N processed questions ranked by `standout_score = min(novelty_vs_aired, intra_batch_uniqueness)`. Each card has a coloured novelty bar (green ≥ 0.7, amber 0.4–0.7, red < 0.4) plus a small footer with file:// links to your `inbox/` and `aired/` folders so the "mark as aired" workflow is one drag in Finder.

Below that, collapsed sections cover possible repeats, the full processed table, similarity clusters (split into "new-only" — duplicates within this batch — and "mixed" — overlaps with already-aired questions), the aired list, and any unprocessed files.

## Optional: Automator folder action

If you want podq to run automatically the moment you drop a file into `inbox/` (instead of double-clicking the Desktop launcher), set up a macOS Automator folder action. See [`installer/com.podq.folderaction.workflow.md`](installer/com.podq.folderaction.workflow.md) for the step-by-step. This is power-user setup; most users can ignore it.

## Building from source (maintainers only)

This section is for whoever cuts releases — end users do not need it.

Python 3.12 is required; 3.14+ is not supported.

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"
uv pip install pyinstaller
make build            # produces dist/podq (~70 MB)
make package          # codesigns the binary
```

To assemble the release archive, place these three files in a flat directory and tar/zip it:

```
dist/podq
installer/install.sh
installer/Run podq.command
```

Upload the resulting archive to a GitHub release. End users will download only that.

## Development

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"
.venv/bin/pytest tests/ -q
```
