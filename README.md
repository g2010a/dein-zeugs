# podq — Podcast Question Manager

A macOS Apple Silicon CLI tool that transcribes podcast episodes, extracts listener questions, clusters them semantically, and produces an HTML report of recurring themes.

No Python, no Ollama, no dependencies required on the target machine — just the binary.

## Installation (end users)

Download `podq` from the [latest release](../../releases/latest) and run the installer:

```bash
bash installer/install.sh
```

The installer:
1. Copies `podq` to `/usr/local/bin/`
2. Pre-warms the Whisper and embedding model caches (~200 MB, one-time download)

The LLM model (~2 GB GGUF) downloads automatically to `~/.podq/models/` on first use.

**Requirements:** macOS 14+, Apple Silicon (arm64)

## Usage

```bash
podq {root}
```

Where `{root}` is your project directory. Drop MP3 files into `{root}/inbox/` and run podq — it transcribes, analyzes, and writes a report to `{root}/reports/report.html`.

### Options

```
podq {root}          Run a full drain pass and render report
podq --warm-models   Pre-download Whisper and embedding models, then exit
```

### Configuration

A `config.toml` is created automatically on first run:

```toml
[analysis]
similarity_threshold = 0.80          # cosine similarity above which a question is "repeat"
whisper_model = "medium"             # tiny / base / small / medium / large
embedding_model = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
llm_model_path = "~/.podq/models/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
```

## Directory Layout

```
{root}/
  inbox/        # Drop MP3 episodes here (not created by podq)
  transcripts/  # Auto-generated .txt transcripts
  analysis/     # Auto-generated .json question extractions
  reports/      # Auto-generated HTML reports
  aired/        # Move processed episodes here manually
  config.toml   # Auto-created with defaults on first run
```

## Building from source (macOS Apple Silicon only)

Python 3.12 is required; 3.14+ is not supported.

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"
uv pip install pyinstaller
make package          # produces dist/podq (~70 MB)
```

Then upload `dist/podq` to a GitHub release and distribute `installer/install.sh` alongside it.

## Development

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"
.venv/bin/pytest tests/ -v
```
