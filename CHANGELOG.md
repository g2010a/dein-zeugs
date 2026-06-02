# CHANGELOG


## v0.3.2 (2026-06-02)

### Bug Fixes

- **release**: Distribute bare binary instead of zip archive
  ([`e7f2597`](https://github.com/g2010a/dein-zeugs/commit/e7f259765335309f209b6e1148f76f5b7ef62e80))

Now that the .command wrapper is gone the zip served no purpose — it wrapped a single file and added
  an unnecessary extraction step. Upload dist/dein-zeugs directly to GitHub Releases. Update all
  docs (README, Automator guide) to remove zip and .command references.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **release**: Drop .command wrapper, add Gatekeeper approval instructions
  ([`1b5aa70`](https://github.com/g2010a/dein-zeugs/commit/1b5aa70774849a82877cc63a57b7de2f4545cd73))

The .command file itself gets quarantined on download, so Gatekeeper blocks it before it can strip
  quarantine from the binary — making the wrapper approach self-defeating. Revert to distributing a
  single binary with clear right-click-Open and Privacy & Security fallback instructions.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>


## v0.3.1 (2026-06-02)

### Bug Fixes

- **release**: Upload zip archive instead of bare binary
  ([#3](https://github.com/g2010a/dein-zeugs/pull/3),
  [`2f4673c`](https://github.com/g2010a/dein-zeugs/commit/2f4673c8e6d53435a491e14153d1716a6befcd8e))


## v0.3.0 (2026-06-02)

### Bug Fixes

- Address code-review findings from Phase 4 validation
  ([`9f8c7a0`](https://github.com/g2010a/dein-zeugs/commit/9f8c7a06abd188f37a035c7c3a2fca900cd75bea))

ensure_llm_model(force=True): removed premature path.unlink() that deleted the existing model before
  the download completed. The post-download replacement block (lines 76-82) already handles the
  atomic swap safely; the early unlink was redundant and left the user with no model on download
  failure.

analyze_all: two fixes — (1) data["stem"] -> data.get("stem") or normalize_stem(yaml_path.stem) to
  avoid KeyError on a hand-edited or partially-written YAML; (2) aired items are now processed in a
  first pass and each embedding is appended to aired_embeddings before inbox items are scored,
  matching the progressive ordering of process_all_unprocessed.

cli.py: - Extracted _bootstrap() helper (root resolve + mkdir + Config + Paths) shared by the five
  handlers that previously repeated the same four lines verbatim. - Added try/except around the
  subcommand dispatch so any unhandled exception prints to stderr and returns 1 instead of
  propagating a raw traceback to the caller. - _load_config_optional now prints a warning to stderr
  when a supplied root exists but config loading fails.

tests: added coverage for partial-YAML resumption, transcribe skip, analyze skip, ensure_llm_model
  force safety, and subcommand error wrapping.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **analysis**: Clarify prompt wording for summary extraction
  ([`404c40c`](https://github.com/g2010a/dein-zeugs/commit/404c40c512f3488f5baf4cd61d32e70d3106c8e0))

The SUMMARY_PROMPT previously said "falls angegeben" (if provided), which could be read as always
  listing all three fields. Adding "nur" (only) makes it unambiguous that fields should be omitted
  when absent.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **report**: Search full transcript without button-text leakage
  ([`89f31f6`](https://github.com/g2010a/dein-zeugs/commit/89f31f6659ee058ed8eafd65a7daf07019d4b02d))

Replace single textContent-on-transcript-body with two targeted reads: -
  getElementsByClassName('transcript-rest')[0]?.textContent — hidden span (chars 301+) -
  getElementsByClassName('transcript-body')[0]?.firstChild?.textContent — leading text node (chars
  1-300)

This covers the full transcript while excluding the "Mehr anzeigen" button text that previously
  caused spurious matches on the word "mehr".

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Build System

- Add make release target and update README build instructions
  ([`cebc0c5`](https://github.com/g2010a/dein-zeugs/commit/cebc0c5e79c191b9dd1f0ab8b8a13b0569d0700f))

- make release: signs binary, copies dein-zeugs + dein-zeugs.command into dist/release/, zips as
  dist/dein-zeugs-release.zip for GitHub upload - README: replace 'make package' with 'make release'
  in build instructions

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Chores

- Rename PODQ_NO_OPEN env var and remaining podq references to dein_zeugs
  ([`4470fba`](https://github.com/g2010a/dein-zeugs/commit/4470fbaa5a154c977c1d602e61bbde3a6883b884))

The package was renamed from podq to dein-zeugs in 0.1.0 but several test fixtures, logger names,
  and the PODQ_NO_OPEN environment variable still used the old name. The env var is the only
  user-visible surface (used to suppress macOS 'open' during tests), so it must match the current
  project identity.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Documentation

- Add dein-zeugs.command launcher and fix Gatekeeper instructions
  ([`f82293c`](https://github.com/g2010a/dein-zeugs/commit/f82293c81a7cabb040523564bec7bf9a501e5eb6))

macOS opens .command files in Terminal on double-click; plain binaries have no app association and
  open in TextEdit. Reintroduce a minimal launcher that removes the binary's quarantine flag on
  first run so users only need to approve one simple dialog.

- installer/dein-zeugs.command: cd to own dir, xattr-strip binary, run it - README: installation now
  references two-file archive and .command launcher - README: daily usage points to
  dein-zeugs.command double-click - README: build/release section updated to list both release
  artifacts

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Add screenshot
  ([`0905bbd`](https://github.com/g2010a/dein-zeugs/commit/0905bbda9ac43db1f50bc578cab14eec6b844783))

For marketing purposes :P

- Rewrite README with Divio structure, remove installer
  ([`4c66189`](https://github.com/g2010a/dein-zeugs/commit/4c6618916cce7939640fed2da4045a614fd20467))

- Restructure README usage-first (Divio): install → daily use → CLI reference → config → directory
  layout → report → advanced → maintainer - Update CLI reference from old flags (--warm-models,
  --clean-outputs, --clean-downloads) to current subcommands (fetch-models, delete-outputs,
  delete-downloads, transcribe, analyze, cluster, report, initialize) - Simplify installation to:
  download binary, right-click Open once - Remove installer/install.sh and installer/Run
  podq.command — the PyInstaller binary is double-clickable directly; no installer needed - Update
  Makefile package message to reference GitHub Release upload

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Features

- Search transcripts
  ([`b125137`](https://github.com/g2010a/dein-zeugs/commit/b125137fef7ee561db32c7b9c939a6f926ad961a))

User expects search to include all text

- **analysis**: Add transcribe_all and analyze_all for independent pipeline steps
  ([`5b5a83c`](https://github.com/g2010a/dein-zeugs/commit/5b5a83c189f08ecfe6943cd69bc52ab105ec550d))

The default process_all_unprocessed fused transcription and LLM analysis into a single pass with no
  way to run either step alone. This prevented users from, e.g., batch-transcribing overnight and
  running the heavier LLM analysis separately.

Changes: - transcribe_all: writes partial YAMLs (transcript + metadata only); skips
  already-transcribed files unless --force clears analysis fields - analyze_all: fills in
  embedding/summary/keywords on partial YAMLs; skips files that already have an embedding unless
  --force - _analyze_one: reuses an existing transcript from a partial YAML so the default
  orchestration can resume from a prior transcribe step - process_all_unprocessed: now uses
  _needs_full_analysis (no YAML OR YAML missing embedding) instead of the stricter "no YAML" check,
  so it cleanly completes files left half-done by transcribe_all

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **cli**: Add cluster subcommand and wire into default workflow
  ([`ba0f2e8`](https://github.com/g2010a/dein-zeugs/commit/ba0f2e87df5f94db748a23876edf24ff4a5700c0))

Adds cluster_all() which computes cluster assignments from transcript embeddings (chosen over
  summary/keyword embeddings as they are LLM-free and carry the full semantic signal without
  abstraction errors) and writes cluster_id back to each YAML atomically.

render_report now reads stored cluster_id when available; falls back to recomputing from embeddings
  on first run. The default orchestration workflow calls cluster_all between the analysis drain loop
  and report rendering.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **cli**: Expose pipeline steps as independent subcommands
  ([`a5f5e93`](https://github.com/g2010a/dein-zeugs/commit/a5f5e9324ac1c7ce0c73527221de58f20562f2ab))

Following Unix philosophy, each stage of the workflow is now a discrete subcommand so it can be
  invoked, scripted, or debugged in isolation:

dein-zeugs initialize – create directory tree + config dein-zeugs fetch-models – download/warm all
  model caches dein-zeugs transcribe [--force] – run Whisper, write partial YAMLs dein-zeugs analyze
  [--force] – LLM analysis on transcribed YAMLs dein-zeugs report – render HTML report from YAMLs
  dein-zeugs delete-downloads – remove downloaded model files dein-zeugs delete-outputs – empty
  analysis/ and reports/

The bare `dein-zeugs [root]` invocation is unchanged: it orchestrates whatever steps are still
  needed, exactly as before. The legacy --warm-models / --clean-downloads / --clean-outputs flags
  are kept for backwards compatibility.

ensure_llm_model gains a force= parameter so fetch-models --force can delete and re-download an
  existing LLM file.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Refactoring

- Remove slop from analysis.py and cli.py
  ([`e170550`](https://github.com/g2010a/dein-zeugs/commit/e17055082126c11325e5bff9da905f6d2c7f6e4c))

analysis.py: - Removed multi-paragraph docstrings from transcribe_all, analyze_all, and
  process_all_unprocessed (project style: one short line max) - Eliminated _needs_analysis and
  _load_candidates inner closures in analyze_all; they were each used exactly once and added nesting
  for trivially simple operations - Pre-compute stem when building candidates to remove the
  three-way duplication across _run_one and the two loop passes - Removed a comment in _analyze_one
  that explained what the code does rather than why

cli.py: - Removed three cosmetic # ---...--- section-divider banners

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **cli**: Remove flags that duplicate subcommands
  ([`adf5328`](https://github.com/g2010a/dein-zeugs/commit/adf5328e42a56c2086c5c01907607727751adc2b))

--warm-models, --clean-downloads, --clean-outputs, --yes, and --skip-llm in _run_orchestrate
  duplicated fetch-models, delete-downloads, and delete-outputs. Removed the flags and their tests;
  subcommand tests already provide equivalent coverage.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Testing

- **cli**: Add coverage for all seven new subcommands
  ([`d3f1dfe`](https://github.com/g2010a/dein-zeugs/commit/d3f1dfeec0ca27db3b7fd0a61f672cf9fd6a1fb2))

Each subcommand (initialize, fetch-models, transcribe, analyze, report, delete-downloads,
  delete-outputs) now has dedicated tests verifying: - it returns 0 on success - it calls the
  expected underlying function - flag variants (--force, --yes, --skip-llm) are forwarded correctly
  - the default root (~/DeinZeugs) is used when no root is supplied

Also moved transcribe_all and analyze_all to the module-level import in cli.py so they can be
  patched at dein_zeugs.cli.* in tests, consistent with how process_all_unprocessed is already
  handled.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>


## v0.2.0 (2026-05-29)

### Features

- **report**: Dos-style UI overhaul with ASCII banner and merged stem column
  ([`91e2540`](https://github.com/g2010a/dein-zeugs/commit/91e2540b93a379f8270df0f42da114eb0694c1bc))

- Replace sticky nav bar with ASCII art "DEIN ZEUGS" banner (10px monospace, bright yellow on dark
  navy, full-width centered) - Retheme entire CSS to 90s DOS palette: #000080 body, #0000AA headers,
  #00AAAA cyan borders, #FFFF55 yellow headings, #FF55FF magenta actives, #55FFFF cyan links,
  monospace font throughout; sharp square corners - Remove dedicated Stem column from table header;
  render filename/stem as .cell-stem block element inside Zusammenfassung cell (11px, de-emphasized
  #7777AA), chip-aired badge stays inline before stem for aired rows

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>


## v0.1.0 (2026-05-29)

### Bug Fixes

- Force tqdm progress bars in PyInstaller binary context
  ([`a2d877b`](https://github.com/g2010a/dein-zeugs/commit/a2d877b176962cc89377712926d09ee95e4ba582))

- models.py: add _make_forced_tqdm() (lazy import, forces disable=False and dynamic_ncols regardless
  of TTY detection) and patch_tqdm() which monkey-patches tqdm.tqdm, tqdm.auto.tqdm, and fastembed
  internals - models.py: add ensure_whisper_model() which uses snapshot_download with the forced
  tqdm class for guaranteed progress display - cli.py: call patch_tqdm() and ensure_whisper_model()
  in --warm-models so both Whisper and fastembed downloads show byte-level progress bars

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Freeze_support for PyInstaller multiprocessing and tqdm rendering
  ([`90dac8e`](https://github.com/g2010a/dein-zeugs/commit/90dac8e57e107416db2fdd9d481befddee44e656))

- __main__.py: add multiprocessing.freeze_support() so huggingface_hub worker subprocesses don't
  re-enter the CLI argparser when the frozen binary is used as sys.executable - logging.py: direct
  StreamHandler to stdout instead of stderr so tqdm progress bars (stderr) and log messages (stdout)
  render on separate streams without overwriting each other

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **analysis**: Improve LLM prompt quality and context limits
  ([`85675f2`](https://github.com/g2010a/dein-zeugs/commit/85675f2142c3c77149b99b0672d77ca496106db9))

- Expand SUMMARY_PROMPT from 2 to 4 examples covering repetitive input, short/single-word
  transcripts, and multi-sentence source text; add explicit instruction to collapse repetitions to
  core meaning - Expand KEYWORDS_PROMPT from 1 to 3 examples; add lemmatization instruction
  (base/infinitive forms) and allowance for 1-2 keywords on very short inputs; fix `gelenke` →
  `gelenk` in existing example - Add `\n` stop token for keyword inference to prevent multi-line
  prompt leakage on minimal inputs - Bump `n_ctx` from 2048 to 8192 so long transcripts are not
  truncated (model supports 131 072; 2048 was causing silent truncation) - Suppress fastembed
  mean-pooling UserWarning in EmbeddingModel._load; mean pooling is correct for this model, warning
  was noise

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **analysis**: Reduce verbose LLM output with few-shot prompt examples
  ([`b43b333`](https://github.com/g2010a/dein-zeugs/commit/b43b333f2899d53ad05e610a4bea97869eaf1cfb))

Remove "Hörerfrage" framing that caused hallucinated radio context, add two few-shot examples to
  each prompt to anchor concise single-sentence summaries and single-word keywords.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **analysis**: Substitute transcript into LLM prompts
  ([`5550470`](https://github.com/g2010a/dein-zeugs/commit/55504700be1995eab4d870df8a76c7d0bb6cf110))

{{TRANSKRIPT}} used escaped braces, so Python's .format() emitted the literal string {TRANSKRIPT}
  instead of the transcript text. The keyword mismatch (TRANSKRIPT vs transcript) would have broken
  it even with single braces. LLM was hallucinating completions against an unfilled placeholder.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **analysis**: Tighten LLM prompts to prevent hallucination and keyphrases
  ([`da9e867`](https://github.com/g2010a/dein-zeugs/commit/da9e867ca68e52546bbfee7d5e7fb88139478b2f))

- Summary: add grounding instruction ("nur aus dem Text"), output anchor ("Zusammenfassung:"),
  reduce max_tokens 256→100 - Keywords: require single words not phrases, output anchor
  ("Schlüsselwörter:"), reduce cap 8→5

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **analysis**: Update aired corpus in-place during backfill pass
  ([`6970717`](https://github.com/g2010a/dein-zeugs/commit/6970717392f31af3cf39962b1740738a7ca5206d))

Aired items processed in the same drain pass now see each other as neighbors: _analyze_one returns
  the embedding, which the aired loop appends to aired_embeddings/aired_stems before the next
  iteration. Also deduplicates unprocessed_audio/unprocessed_aired_audio into a shared
  _unprocessed_in helper, and adds regression tests confirming within-pass scoring and that
  intra_batch fields are absent from aired YAMLs.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **ci**: Restore full dep install in CI and prefer wheels on macOS build
  ([`2e8e3c5`](https://github.com/g2010a/dein-zeugs/commit/2e8e3c523eb15dda328a430ffacbfce9f70c821d))

ci.yml: was using --no-deps which caused ModuleNotFoundError at pytest collection for dein_zeugs
  modules that import faster-whisper/llama-cpp/ fastembed; restore pip install -e "[dev]" ruff (all
  deps have pre-built linux x86_64 wheels, no compilation needed on ubuntu-latest)

release.yml: add --prefer-binary so pip uses arm64 macOS wheels for llama-cpp-python and
  faster-whisper before falling back to source build

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **cli**: Show KB for sub-MB sizes in clean-outputs/clean-downloads
  ([`51256ce`](https://github.com/g2010a/dein-zeugs/commit/51256cee267e03215cfc5240f2cb21939d479f20))

Integer bit-shift >> 20 truncated directories smaller than 1 MB to "0 MB". Add _fmt_size() helper
  that renders KB below 1 MB and MB above, applied to all six display sites in both clean functions.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **llm**: Cache load failure, bundle libllama, surface errors in report
  ([`202748a`](https://github.com/g2010a/dein-zeugs/commit/202748a9ccef687c5e8de9ee161064183f1b8264))

- Cache the first LLM load exception in _llm_error so _infer logs once per session instead of twice
  per file (summarize + keywords both fail silently after the first log) - Add
  build/hooks/hook-llama_cpp.py so PyInstaller bundles the libllama shared library that was missing
  from the distributed binary - Write llm_error field into YAML when inference fails; report.py
  reads it and passes llm_error_count to the template - Show orange warning banner and ⚠ KI-Fehler
  chip on affected items in the HTML report so users know summaries/keywords are unavailable

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **models**: Remove nonexistent huggingface_hub.enable_progress_bars() calls
  ([`fa5417d`](https://github.com/g2010a/dein-zeugs/commit/fa5417d69c7b3b6f3b5b3d1498773d50eb1b22b2))

The function does not exist in huggingface_hub 1.16.4. Progress display is handled by the tqdm_class
  argument passed to snapshot_download/ hf_hub_download, so the calls were both wrong and redundant.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **models**: Use huggingface_hub.hf_hub_download for LLM to stream progress
  ([`bf42293`](https://github.com/g2010a/dein-zeugs/commit/bf4229319e7e74db181a9e9a6403b45b8dbaa5ab))

Replaces the urllib + \r-print downloader with huggingface_hub.hf_hub_download, which provides a
  real tqdm bar with bytes/sec, ETA, partial-file resume, and proper Content-Length handling. The
  downloaded file is symlinked (or copied as a fallback) into the configured llm_model_path to
  preserve the existing config contract. Fixes the bug where the 2 GB LLM download showed no
  progress on Automator-piped stderr until completion.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **report**: Address validator findings
  ([`cee5537`](https://github.com/g2010a/dein-zeugs/commit/cee55377a617ee99d91ed64f30dc739d7a55b8a0))

report.py: - _derive_cluster_name: return cluster_stems[0] when summary is empty/missing - Drop
  unused clusters/new_only_clusters/mixed_clusters from template.render()

report.js: - Declare groupByCluster before sortTable (fixes var-hoisting confusion) - itemVisible:
  include data-first-seen and data-analyzed-at in free-text search - applyFilters: rebuild cluster
  headers after filtering (fixes stale counts) - applyGroupByCluster: use DOM methods not innerHTML
  (prevents LLM-content injection) - applyGroupByCluster: derive colspan dynamically from thead th
  count - applyGroupByCluster: skip clusters where all rows are hidden by filter - sortTable: treat
  empty date strings as always-last regardless of sort direction

report.css: - Remove dead .cluster-type-group-new/.cluster-type-group-mixed rules - Remove dead
  .chip-repeat rule

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **report**: Bypass Jinja2 autoescape for inlined CSS and JS
  ([`ea93f2c`](https://github.com/g2010a/dein-zeugs/commit/ea93f2c562e93a30f3576595471e89dfc69c9ddf))

Single quotes in CSS and JS were being escaped as &#39;, breaking JavaScript. The | safe filter
  marks both inlined assets as trusted HTML-safe strings before rendering.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **report**: Label clusters by representative stem
  ([`075ee19`](https://github.com/g2010a/dein-zeugs/commit/075ee198c0d556f5944cdc3304e7a6835df6e38a))

Anonymous "Cluster (N Fragen):" headings were indistinguishable from each other. Each cluster now
  shows its first stem as a name so users can tell clusters apart at a glance.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **report**: Remove double browser open; add collapsible transcripts
  ([`3b3b451`](https://github.com/g2010a/dein-zeugs/commit/3b3b4518887dac51a2530f36c834552b7e0fc1ad))

Browser opened twice on every run because render_report() called subprocess.run(["open", ...])
  internally while cli.py also called _open_report() after it returned. Removed the duplicate from
  report.py along with the now-unused os and subprocess imports.

Transcript display: report.py now reads the transcript field from each YAML into processed_items and
  aired_items. The Jinja2 template exposes a transcript_block macro that renders a <details> showing
  the first 300 characters; a "Mehr anzeigen" button reveals the rest. Cards in the Highlights and
  Wiederholungen sections show transcripts inline; the Alle Fragen and Ausgestrahlt tables gain a
  Transkript column. A global toolbar (Alle aufklappen / Alle zuklappen) sits below the banner and
  controls all transcript details at once via report.js event listeners.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **report**: Remove Unverarbeitete Dateien section
  ([`ec35e4b`](https://github.com/g2010a/dein-zeugs/commit/ec35e4ba096b6243c8aaff36a55e1dd5817538ba))

The section was always empty because inbox files without a YAML are processed before the report is
  opened. Remove the nav link, the template section, the Python computation, and update the test.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **report**: Rename score labels to Neuheitswert and drop stale column
  ([`e75bc14`](https://github.com/g2010a/dein-zeugs/commit/e75bc14d6c3e8956d3e2a33167192c650c74700d))

Generic "Score:" label is replaced with "Neuheitswert:" in standout cards and repeat cards. Table
  header "Neuheit" updated to "Neuheitswert". "Nächste ausgestrahlte Frage" column removed — it was
  always empty.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **report**: Replace expand/collapse transcript buttons with single toggle
  ([`ba87c53`](https://github.com/g2010a/dein-zeugs/commit/ba87c531c3f191c640487bbc49f9bf8074876f94))

Two separate buttons were redundant. A single button now toggles all transcripts open or closed and
  updates its own label to match the resulting state.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Build System

- Add PyInstaller spec, hooks, installer script, and Makefile
  ([`ac8eb88`](https://github.com/g2010a/dein-zeugs/commit/ac8eb88e51bf32931eb12e946237715c3b8e52e5))

podq.spec targets arm64 --onefile with hidden imports for whisper, sentence_transformers, torch,
  tiktoken. install.sh verifies arm64/macOS14, installs Ollama, pulls llama3.2:3b, copies binary,
  and prints Automator setup instructions.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Fix openai-whisper install on Python 3.12+ and update build docs
  ([`b8640c5`](https://github.com/g2010a/dein-zeugs/commit/b8640c5d2196e2065800686adef34b5af9e038a9))

Pin requires-python to <3.14, add uv extra-build-dependencies for openai-whisper's missing
  pkg_resources declaration, and update README with correct Python version and binary build
  instructions.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Fix setuptools build backend to setuptools.build_meta
  ([`5a07dda`](https://github.com/g2010a/dein-zeugs/commit/5a07ddad2782f850ffd5c9d5bcd048936f55c141))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Chores

- Add .gitignore for venv, pycache, dist, and build artifacts
  ([`0e27647`](https://github.com/g2010a/dein-zeugs/commit/0e27647a9f6e8b610f1b1327ed818972e4850925))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Increase defaut displayed items
  ([`1cdffa9`](https://github.com/g2010a/dein-zeugs/commit/1cdffa9627e67396e9661052ac422f602b5f03ac))

We want to show a lot by default

- Lower similarity threshold
  ([`c3deba8`](https://github.com/g2010a/dein-zeugs/commit/c3deba8eb1284403185ad491b14afc74697f253a))

It was not grouping files adequately

- **installer**: Drop deferred-LLM note now that --warm-models pre-loads it
  ([`1831b76`](https://github.com/g2010a/dein-zeugs/commit/1831b767c5789e8d10b164189bb41a844d2ef7f0))

The LLM model is now pre-warmed in the third stage of --warm-models, so the note telling users it
  will download lazily on first use is no longer accurate.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **installer**: Support flat release-archive layout, slim post-install hint
  ([`4dcfed7`](https://github.com/g2010a/dein-zeugs/commit/4dcfed7288cd33d9331724505da255942cb7cac4))

End-user release archive is flat (./install.sh + ./podq + ./Run podq.command). The previous
  installer hard-coded the source-tree layout ('../dist/podq') and pointed users at 'make package'
  on failure — neither makes sense for someone who just unpacked a tarball.

- Probe both layouts (flat release first, source tree as fallback) - Probe for the launcher too;
  fail early with a clearer message - Replace the inline 30-line Automator tutorial with a 3-line
  German quick-start ("MP3s ablegen → doppelklicken → Bericht öffnet sich") plus a one-line pointer
  to the workflow doc. Cuts noise in the common path; the doc itself is what users follow for the
  rare Automator setup.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **lint**: Fix pre-existing ruff warnings and consolidate imports
  ([`fd83e7f`](https://github.com/g2010a/dein-zeugs/commit/fd83e7fe4659ec3e0b1fcb801cf4308c01be90c4))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Continuous Integration

- Add GitHub Actions for CI and semantic-release publishing
  ([`8841fb8`](https://github.com/g2010a/dein-zeugs/commit/8841fb842b7b12c86257fc8bb036a67bf4782a9d))

- ci.yml: lint (ruff) + test (pytest) on every push/PR to main; installs package without heavy
  native ML deps so tests run on ubuntu - release.yml: triggered by workflow_run after CI passes on
  main; guards against PR-triggered privilege escalation via four-condition check; uses
  python-semantic-release@v9 to auto-bump version from conventional commits and create GitHub
  Release; builds macOS arm64 binary with PyInstaller (make package for ad-hoc codesign) and uploads
  to release - pyproject.toml: add [tool.semantic_release] config pointing at project.version in
  TOML and enabling CHANGELOG.md generation

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Documentation

- Rewrite README with end-user install and usage instructions
  ([`4723f59`](https://github.com/g2010a/dein-zeugs/commit/4723f599916198bb79a9883fd3c11b8e10fcada7))

Replace developer-centric setup notes with a proper user-facing README: install steps, usage, config
  reference, directory layout, and updated build-from-source instructions with correct binary size
  (~70 MB).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **installer**: Mark Automator folder action as optional power-user setup
  ([`61b4b06`](https://github.com/g2010a/dein-zeugs/commit/61b4b065a1d8e9ecb663f4f7ef0ec99bfd4bc2a8))

Most users only need the Desktop launcher (Run podq.command) installed by install.sh. The Automator
  setup is now strictly opt-in for users who want auto-trigger on file drop. Adds an example zsh
  body for the default ~/Podq root and clarifies that launcher and Automator action can coexist (the
  .podq.lock flock serialises concurrent runs).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **readme**: Rewrite for binary-only end-user distribution
  ([`771268f`](https://github.com/g2010a/dein-zeugs/commit/771268f97c79e31abe4a9aad0096dcc052948589))

End users download a release archive (binary + install.sh + Run podq.command), not the repo. Old
  wording implied a source checkout was needed. Also fixes stale claims:

- transcripts/ no longer exists; analysis/ is YAML, not JSON - default root is ~/Podq/ and is
  auto-created - --skip-llm, --clean-downloads, --clean-outputs were undocumented - the report's
  Highlights/standout_score surfacing was undocumented

Adds a maintainer-only "Building from source" note that the release archive should bundle three
  files (binary + install.sh + launcher), since the launcher is required for the no-Terminal
  workflow.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Features

- Replace openai-whisper/torch/ollama with faster-whisper/llama-cpp-python/fastembed
  ([`0dd7ddd`](https://github.com/g2010a/dein-zeugs/commit/0dd7dddf5a13bf275e7ff0b6dab10cdcff0cd641))

Eliminates the Ollama daemon requirement and the torch/openai-whisper dependency stack. The LLM
  model (GGUF) now downloads automatically on first use via a bundled downloader; Whisper and
  embedding models use CTranslate2 and ONNX Runtime respectively, keeping the binary ~200 MB instead
  of ~1.5 GB.

- transcription: openai-whisper → faster-whisper (CTranslate2, int8) - analysis: ollama HTTP →
  llama-cpp-python (in-process GGUF inference) - embedding: sentence-transformers/torch → fastembed
  (ONNX Runtime) - models: new podq/models.py with ensure_llm_model() downloader - config: remove
  ollama_model/ollama_url, add llm_model_path - installer: remove Ollama install/pull steps - tests:
  update mocks for new APIs throughout

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **analysis**: Add embedding, analysis, and clustering engines
  ([`e005856`](https://github.com/g2010a/dein-zeugs/commit/e005856043a6bb5fc9873a193d25feb91acbe2f4))

Implements EmbeddingModel with MPS/CPU device selection and aired corpus caching,
  score/summarize/keywords/analyze_all_unanalyzed in analysis.py, and single-link agglomerative
  clustering in clustering.py.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **analysis**: Add intra_batch_uniqueness and standout_score post-pass
  ([`4a91832`](https://github.com/g2010a/dein-zeugs/commit/4a91832d805cc5ea2848e45af8b05720561ed5e4))

Comparison was previously only vs. the aired corpus, so near-duplicate new questions within a single
  batch were not penalised. Add a second pass after process_all_unprocessed that computes:

intra_batch_uniqueness = 1 - max cosine(this, other-unaired-item) standout_score =
  min(novelty_score, intra_batch_uniqueness)

Idempotent: skips writing when both fields already match the computed values, preserving the no-op
  re-run contract.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **analysis**: Analyze unprocessed MP3s in aired/ directory
  ([`4b8f167`](https://github.com/g2010a/dein-zeugs/commit/4b8f167c050e8c139ea46666896b292cad6c320d))

Files moved to aired/ without prior analysis are now transcribed, embedded, summarized, and stored
  like inbox items. The CLI gate also skips Getting Started when unanalyzed aired items exist.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **analysis**: Record first_seen timestamp from MP3 mtime in YAML
  ([`5af64f3`](https://github.com/g2010a/dein-zeugs/commit/5af64f383a8d6ce7c242a5a0ff3c46c84b4e6935))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **cli**: Add --clean-downloads flag with config-aware path derivation
  ([`27c1ea7`](https://github.com/g2010a/dein-zeugs/commit/27c1ea7c19dc6bacbb2f8a396f386ddb32915870))

Adds `--clean-downloads [--yes]` to delete all downloaded model files (LLM GGUF, Whisper HF cache,
  embedding HF cache, fastembed cache). All paths derived from config so custom model selections are
  respected.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **cli**: Add --clean-outputs flag and configurable output dirs
  ([`27f3f74`](https://github.com/g2010a/dein-zeugs/commit/27f3f741d2a79c851009a4d21d79aeb6259bc15b))

Adds --clean-outputs to clear transcripts/, analysis/, and reports/ while preserving inbox/. Output
  directory names are now configurable under a [paths] section in config.toml (defaults unchanged).
  Replaces Plattdeutsch user-facing messages with standard German.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **cli**: Add drain-loop orchestration with flock concurrency guard
  ([`a4ea9d8`](https://github.com/g2010a/dein-zeugs/commit/a4ea9d85e2fe16ac3f9fcc6a9b4d31495c3c0666))

Implements cli.main() with MAX_DRAIN=10 drain loop, fcntl exclusive lock (exit 0 on contention),
  --warm-models flag, and error report on exception.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **cli**: Add inbox sanity check and directory layout help
  ([`f9cefe9`](https://github.com/g2010a/dein-zeugs/commit/f9cefe9f5a7362ea589cac47d08d9eff05fbf2a1))

Exits early with a clear message if inbox/ does not exist, before any model download occurs. Adds
  --help epilog documenting the expected directory layout and the inbox/ requirement.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **cli**: Add step-by-step progress output to --warm-models
  ([`839629a`](https://github.com/g2010a/dein-zeugs/commit/839629a0b55b7f503f435d138d8bc1983e8d3a8f))

Print numbered step markers and download size hints directly to stdout so users see clear progress
  during the potentially long first-run model cache warm-up.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **cli**: Default root to ~/Podq, auto-open report, pre-warm LLM, migrate to Hochdeutsch
  ([`77869de`](https://github.com/g2010a/dein-zeugs/commit/77869dee46f1e7b766e40c342616c42d07e418ec))

Combines several closely-related CLI changes that share the same argparse surface and warm-models
  routine:

- Default root to ~/Podq when no argument is given; auto-create the directory tree via
  paths.ensure_dirs(), so first-run is friction-free. - Empty inbox now renders the Getting Started
  welcome page (instead of bailing with an error) and opens it via 'open'. - Auto-open the rendered
  report on success via subprocess.run(["open", ...]), guarded by PODQ_NO_OPEN for tests. -
  Reconfigure sys.stderr / sys.stdout for line-buffering at main() entry so tqdm progress streams
  appear in Automator log pipes in real time. - Rewrite _warm_models to patch tqdm *after* each
  library is imported (fixes the late-patch bug where fastembed's internal tqdm reference was never
  replaced) and add a third [3/3] LLM stage that pre-warms the 2 GB Llama model. New --skip-llm flag
  for CI / repeated installs. - Migrate Plattdeutsch user-facing strings to Hochdeutsch (argparse
  description, epilog, all help= strings, _warm_models prints, error report headline).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **i18n**: Translate user-facing messages to Plattdeutsch
  ([`b516f0a`](https://github.com/g2010a/dein-zeugs/commit/b516f0af535c48df0c3fab235722e4bced09294a))

All print() statements and argparse help/description/epilog strings are now in Low German. Log
  messages (internal) remain in English. Confirmation prompt accepts both 'j' (ja) and 'y'.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **installer**: Add Run podq.command Desktop launcher for non-Terminal use
  ([`246b32b`](https://github.com/g2010a/dein-zeugs/commit/246b32b73f298fcb90a6519ea9940729c83bf225))

Create a double-clickable zsh launcher that starts podq from the Desktop. Copies the launcher to
  ~/Desktop during install and sets executable permissions. Includes PYTHONUNBUFFERED=1 to ensure
  real-time progress output streams correctly.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **paths**: Auto-create inbox and aired dirs in ensure_dirs
  ([`3540ddd`](https://github.com/g2010a/dein-zeugs/commit/3540ddd7b7fee2fb346afae1736421e3f19f8478))

Extends ProjectPaths.ensure_dirs() to create inbox/ and aired/ in addition to analysis/ and
  reports/, supporting the new ~/Podq default-root first-run flow where no directory structure
  exists yet.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **report**: Add audio hotlinks per item
  ([`538459a`](https://github.com/g2010a/dein-zeugs/commit/538459aac6f2e4453802824a535cb97085689261))

Each standout card, repeat card, processed table row, and aired table row now has a ▶ Audio link
  pointing to file://{path}/{stem}.mp3 that opens the file in a new tab for direct playback.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **report**: Add card, chip, bar, and cluster-group CSS classes
  ([`9c7d0bf`](https://github.com/g2010a/dein-zeugs/commit/9c7d0bfb476f266bbd0bf6828996068cdd3c204b))

Adds .banner, .card, .card-repeat, .card-stem, .card-summary, .card-keywords, .card-meta, .chip,
  .chip-repeat, .bar, .bar-fill, .bar-green, .bar-amber, .bar-red, .aired-hint, .cluster-group,
  .cluster-group-new, and .cluster-group-mixed styles for the new Standouts card layout.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **report**: Add HTML report renderer with Jinja2 template
  ([`259a522`](https://github.com/g2010a/dein-zeugs/commit/259a5223cd2f5a83e925657541402003885afaab))

Renders aired/processed/unprocessed/clusters into a self-contained HTML dashboard with inlined
  CSS/JS. Auto-opens in browser; PODQ_NO_OPEN=1 skips.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **report**: Add rank badges to top-3 highlights
  ([`4105635`](https://github.com/g2010a/dein-zeugs/commit/410563562ebe920c5b5f255a4184a6125fba70dd))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **report**: Add search, filter chips, keyword cloud, seen tracking, sortable/paginated table
  ([`8192e52`](https://github.com/g2010a/dein-zeugs/commit/8192e52404b565084a393e0a9dc0a9e626306740))

- Global search bar (/) across stem, summary, keywords - Filter chips: Ungesehen / Highlights /
  Wiederholungen / KI-Fehler - Keyword cloud (top 50) with click-to-filter; chip clicks activate it
  - localStorage seen/unseen tracking with blue dot indicator and nav badge - Sortable columns on
  Alle Fragen table (stem, Ähnlichkeit, Neuheitswert) - Paginated table (25/50/100/Alle) with live
  row count in section header - data-* attributes on all cards and rows as filter/sort foundation -
  Novelty score displayed inline next to bar for faster scanning

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **report**: Add Standouts section as primary novelty surface
  ([`8499d2e`](https://github.com/g2010a/dein-zeugs/commit/8499d2e9cfe2127e1b928cd522827bd8168ea4a2))

Introduces standouts context var (top-N by standout_score, fallback to novelty_score),
  possible_repeats list, and new-only/mixed cluster split in report.py. Extends Jinja2 context with
  inbox_path, aired_path, aired_count, and total_questions_count for downstream template use.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **report**: Auto-open target section on nav link click
  ([`cee6e1d`](https://github.com/g2010a/dein-zeugs/commit/cee6e1d5fb4f77217da0c1bb2645e66a4f9745d9))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **report**: Drop Ähnlichkeit/Neuheitswert columns, merge dates, add collapsible sortable cluster
  groups
  ([`ade2996`](https://github.com/g2010a/dein-zeugs/commit/ade2996d60248d54868e85f6af74a05a0e5f4bf6))

Remove the Ähnlichkeit and Neuheitswert columns from the question table. Merge the two date columns
  (Erstmals gesehen + Zuletzt verarbeitet) into a single Datum column — secondary ↻ date shown only
  when analyzed_at differs from first_seen. Remove the static clusters section entirely.

Extend the existing group-by-cluster mode: each cluster header row now has a ▼/▶ collapse toggle to
  hide/show its items (collapsed rows are excluded from pagination). A cluster sort toolbar appears
  when grouped, offering sort by Anzahl (default), Name, or Datum (newest item). Default table sort
  changed from novelty to first_seen descending.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **report**: Restructure template with Standouts-first layout
  ([`897bdc5`](https://github.com/g2010a/dein-zeugs/commit/897bdc56e5d3c890443403919521250637e309f6))

Rewrites report.html.j2 so the page opens with a Standouts card section (open by default), followed
  by Mögliche Wiederholungen, the full processed table, clusters (split into Neue/Gemischte),
  Ausgestrahlte Fragen, and Unverarbeitete Dateien. Each standout card includes a novelty bar and an
  aired-hint footer with file:// folder links.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **skeleton**: Add project scaffold, config, paths, and utilities
  ([`0e4f782`](https://github.com/g2010a/dein-zeugs/commit/0e4f782eab2eceafab560ef4f2ab6a8d5f5615e4))

Adds pyproject.toml entry point, ProjectPaths dataclass, Config.load_or_create, atomic_write,
  rotating file logger, and unit tests for config and paths.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **templates**: Add Getting Started welcome page
  ([`82e9f2a`](https://github.com/g2010a/dein-zeugs/commit/82e9f2a43b79f82010d1969952b91ffcaf3ed43a))

A friendly Hochdeutsch landing page rendered to reports/report.html when the inbox is empty.
  Includes a clickable file:// link to the inbox folder so first-time users can open it in Finder
  and drop MP3 questions without needing to know paths.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **templates**: Redesign report as unified compact question list
  ([`631bf6a`](https://github.com/g2010a/dein-zeugs/commit/631bf6a0f96a16fe9ca199ab6d298926aa001f40))

HTML: - Single #all-questions table replaces separate standouts/repeats/processed/aired sections -
  Aired rows styled with .row-aired (dimmed) and 📡 chip - Columns: stem, summary, transcript,
  keywords, similarity, novelty bar+score, first-seen date, last-processed date, audio link -
  #clusters section shows named cluster cards grouped under Neue/Gemischte headings - Banner always
  contains Inbox/Aired folder file:// links

CSS: - Remove card, seen/unseen, chip-rank, aired-hint dead styles - Add .row-aired, .novelty-cell,
  .bar-mini, .bar-gray, .date-cell, .cluster-card, .cluster-name-row, .cluster-stems,
  .cluster-header-row

JS: - Remove seen/unseen tracking entirely - Filter chips: 'Neu' (data-section=processed) and
  'Ausgestrahlt' (data-section=aired) - Sort supports stem, similarity, novelty, first-seen,
  analyzed-at columns - New 'Nach Cluster gruppieren' toggle: inserts cluster header rows and groups
  items by data-cluster attribute; disabled during normal sort - Pagination skips
  .cluster-header-row rows

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **transcription**: Add WhisperTranscriber and transcribe_all_unprocessed
  ([`6e79477`](https://github.com/g2010a/dein-zeugs/commit/6e794772e0689a90d35fcf25d12a6408053aa5d5))

Implements lazy model loading with MPS/CPU device selection, atomic transcript writes, and
  PODQ_FORCE_CPU override. Smoke tests mock whisper so no GPU or model download is required.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Refactoring

- Remove dead code and fix double-read in embedding corpus
  ([`56c476c`](https://github.com/g2010a/dein-zeugs/commit/56c476ce23f100750310e765436609e782661c8d))

- WhisperTranscriber: drop unused `device` param and `_device` field - analysis.summarize: drop
  unused `timeout` param - embedding.aired_corpus: read transcript once instead of twice on cache
  miss - report: move atomic_write import to module top; guard inbox.glob with exists() check -
  analysis.keywords: replace manual dedup loop with dict.fromkeys - tests: remove
  test_podq_force_cpu_env_var (tested dead PODQ_FORCE_CPU code)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Remove slop from cli, models, and analysis
  ([`210ec6b`](https://github.com/g2010a/dein-zeugs/commit/210ec6bab9ce7e2cc2c3338215a7a2a6793ad595))

- Fix two stale ~/Podq comments/help strings left over from rename - Remove double blank line
  artifact left after enable_progress_bars removal - Drop redundant `import shutil` inside
  clean_downloads and clean_outputs (shutil is already imported at the top of models.py) - Inline
  _cosine() helper into its single call site in compute_intra_batch_scores; score() already used
  np.dot directly

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Rename package from podq to dein-zeugs
  ([`8539d2a`](https://github.com/g2010a/dein-zeugs/commit/8539d2a1059088c0d12bcabafb9747026f7ad2bb))

- Python package: podq/ → dein_zeugs/ - CLI entry point: podq → dein-zeugs - Runtime paths: ~/.podq/
  → ~/.dein_zeugs/, ~/Library/Logs/podq/ → dein_zeugs/, lock file .podq.lock → .dein_zeugs.lock -
  Default project root: ~/Podq → ~/DeinZeugs - All imports, patch targets, logger names updated
  throughout - README and installer doc fully translated to German

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Rename PyInstaller spec from podq.spec to dein_zeugs.spec
  ([`54a055a`](https://github.com/g2010a/dein-zeugs/commit/54a055ae2e03dc64dca85c825d798a50fb4d99a5))

Update entry point, templates datas path, and binary name to match the package rename from podq to
  dein-zeugs.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **pipeline**: Merge transcript and analysis into single YAML file
  ([`e32a0d1`](https://github.com/g2010a/dein-zeugs/commit/e32a0d141b4a3d5848d3e82771ec6b2c7a283fa0))

Replaces the two-step transcripts/{stem}.txt + analysis/{stem}.json pipeline with a single
  analysis/{stem}.yaml that contains the transcript, summary, keywords, scores, embedding, and
  metadata. Adds pyyaml dependency.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **report**: Unified item list, cluster names, drop standouts/repeats
  ([`9cb6c5b`](https://github.com/g2010a/dein-zeugs/commit/9cb6c5b0f445f37927021cc1eae9fad78714a777))

- Remove standouts and possible_repeats computation - Add _derive_cluster_name() from shared
  keywords then summary fallback - Enrich named_clusters with id/name/stems/is_mixed for template -
  Build stem→cluster_id map and attach cluster_id to every item - Expose first_seen/analyzed_at on
  all items (fallback to analyzed_at) - Pass named_clusters, aired_stems, cluster_names_json to
  template

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **tests**: Simplify mock side_effect sequencing
  ([`5e6868c`](https://github.com/g2010a/dein-zeugs/commit/5e6868c1e40302d7aa53e73dac2322145b280f95))

Replace iter()+lambda pattern with idiomatic MagicMock list side_effect.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Testing

- Add unit tests for analysis scoring, clustering, and report render
  ([`629f9aa`](https://github.com/g2010a/dein-zeugs/commit/629f9aa6daacb538b432994812f6dec1d4ff02d8))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **analysis**: Add scoring, clustering, and schema tests
  ([`b29c8f5`](https://github.com/g2010a/dein-zeugs/commit/b29c8f5a2d56d87d6bfd47769a8f864eacd5d334))

12 tests covering score() edge cases, keywords parsing, analyze_all_unanalyzed JSON schema
  validation, and build_clusters threshold/membership behaviour. Includes synthetic calibration
  pairs fixture for future real-data validation.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **analysis**: Cover intra_batch_uniqueness and standout_score
  ([`3f1e179`](https://github.com/g2010a/dein-zeugs/commit/3f1e179fd3742a53f536764eba05d3e3ab49d32f))

Covers three cases: - Three-item batch (two duplicates + one unique) — duplicates get
  intra_batch_uniqueness < 0.3, unique gets > 0.8. - Single-item batch — uniqueness = 1.0 by
  definition. - Idempotent re-run — file content byte-identical on second call.

Also extends the YAML schema check to require the two new fields.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **cli**: Add idempotency and concurrent lock-contention tests
  ([`5685acd`](https://github.com/g2010a/dein-zeugs/commit/5685acdb000e76dd9752b0dd258a090844e42d56))

test_cli_idempotency: verifies drain loop exits early on second run when

inbox already processed. test_cli_concurrent_drop: verifies flock prevents double processing; loser
  exits 0, winner renders exactly one report.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **cli**: Cover default root, auto-open, empty-inbox welcome, --skip-llm, warm progress
  ([`16bfa3b`](https://github.com/g2010a/dein-zeugs/commit/16bfa3b02d5e563e9b7050542c3447dd72830abf))

Extends and adds tests for the new CLI behaviour:

- test_cli_default_root_uses_home_podq: verifies ~/Podq is created when no root is supplied. -
  test_cli_opens_report_on_success / test_cli_no_open_env_suppresses_open: assert
  subprocess.run(["open", ...]) is invoked on success and that PODQ_NO_OPEN suppresses it. -
  test_cli_empty_inbox_renders_getting_started: empty inbox writes the welcome page directly and
  does not call render_report. - test_cli_warm_models_skip_llm: --skip-llm flag is wired through. -
  test_warm_progress.py (new): regression test that _warm_models streams >= 3 progress lines to
  stderr during downloads, catching the late-patch, block-buffered-stderr, and raw-print-downloader
  regressions in one shot.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **pipeline**: Update tests for YAML-based merged pipeline
  ([`83c86f0`](https://github.com/g2010a/dein-zeugs/commit/83c86f0ad18e5ee6b81b5174917eb3b956ed7ab8))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **report**: Extend tests for Standouts, clusters, banner, and aired links
  ([`389f156`](https://github.com/g2010a/dein-zeugs/commit/389f1566bf325c92fb83a54a147fa7796d3e47a2))

Adds assertions for: Standouts section appearing before processed/aired, standout_score sort order,
  novelty_score fallback when standout_score absent, banner count display, file:// inbox/aired links
  in cards, new-only cluster grouping, and mixed cluster grouping.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- **report**: Update tests for unified list redesign
  ([`fb8f6f3`](https://github.com/g2010a/dein-zeugs/commit/fb8f6f3eddf5798d945c04145c65f668595a749e))

- Remove test_standouts_section_is_first, test_standouts_sorted_by_standout_score,
  test_standouts_fallback_to_novelty_score (section removed) - Update test_report_sections: check
  #all-questions contains both aired and inbox items; aired rows carry class row-aired - Add
  first_seen field to _yaml_item fixture helper - Add test_clusters_have_names: cluster name derived
  from shared keywords - Add test_aired_items_have_date_columns: rows expose data-first-seen and
  data-analyzed-at attributes - Add test_no_gesehen_ui: btn-reset-seen absent - Add
  test_no_ki_fehler_button: data-filter=error absent - Add test_no_highlights_section: id=standouts
  absent - Add test_no_repeats_section: id=repeats absent

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
