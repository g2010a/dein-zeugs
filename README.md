# podq — Podcast Question Manager

A macOS M1 CLI tool that transcribes podcast episodes, extracts questions, clusters them semantically, and produces an HTML report of recurring listener questions.

## Prerequisites

- Python 3.12 (required; 3.14+ not supported)
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- [Ollama](https://ollama.ai) running locally with `llama3.2:3b` pulled (`ollama pull llama3.2:3b`)

## Building the binary (macOS Apple Silicon only)

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"
uv pip install pyinstaller
make package          # produces dist/podq (~500 MB–1.5 GB)
bash installer/install.sh
```

## Development install

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"
```

## Usage

```bash
podq {root}
```

Where `{root}` is your project directory containing an `inbox/` folder with MP3 files.

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
