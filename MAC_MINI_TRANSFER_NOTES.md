# Mac Mini Transfer Notes — Large Files Not in Git

## Git History Note (2026-02-12)

The `investigative_wiki` repo had a problem: large data files (571MB embeddings JSON, 184MB pkl) were committed to git months ago, then later gitignored. Gitignore only stops *future* commits — it doesn't remove files already in history. So every `git clone` would download 750MB of dead weight.

**What was done:** Deleted the old `.git/` folder and created a fresh one with `git init`. This means the repo on GitHub has a single commit instead of the original 88. All current files are intact, just no history. The old `.git/` was backed up then deleted.

**Also fixed:** The `.gitignore` file had inline comments like `archive/  # some comment` which don't work in git — the `# some comment` becomes part of the pattern, so nothing was actually being ignored. Moved all comments to their own lines above the patterns.

**If this matters later:** If you ever need the old 88-commit history, it's gone from this machine. The GitHub repo `BrianMills2718/investigative-wiki` only has the fresh history.

---

These files are gitignored (too large for GitHub) but may be needed on the Mac Mini.

## Classification

### MUST TRANSFER — Irreplaceable Data

| File | Size | Why |
|------|------|-----|
| `investigative_wiki/investigative_wiki.db` | 376K | Your knowledge graph. 95 entities, 21 claims. This IS your research. |
| `investigative_wiki/data/wikidata_properties_complete.db` | 6.1M | 13,054 Wikidata P-codes. Scraped, hard to regenerate. |
| `investigative_wiki/data/custom_pcodes.db` | 152K | Your custom P-code extensions. |
| `investigative_wiki/data/pcode_cache.db` | 16K | Lookup cache. Small, easy to regenerate, but why not. |
| `sam_gov/data/exports/` | 2.6G | 22,210 Discord export files (Bellingcat, OSINT communities). Collected over months. Not re-downloadable. |
| `sam_gov/data/articles/` | 82M | Collected articles. May not be re-fetchable. |
| `sam_gov/data/research_v2/` | 97M | Research output from past investigations. |
| `sam_gov/data/research_output/` | 25M | More research output. |
| `sam_gov/.env` | 4K | All API keys. Copy manually. |
| `investigative_wiki/.env` | 4K | API keys. |
| `theory-forge/.env` | 4K | API keys. |
| `process_tracing/.env` | 4K | API keys. |
| `twitter_explorer/.env` | 4K | API keys. |
| `process_tracing/output/` | 13M | Past process tracing runs (French Rev, American Rev examples). Useful reference. |

### CAN REGENERATE — But Expensive/Slow

| File | Size | How to Regenerate |
|------|------|-------------------|
| `investigative_wiki/data/pcode_embeddings_with_types.pkl` | 176M | `python scripts/utilities/generate_pcode_embeddings_with_types.py` (needs sentence-transformers, ~30 min). Used for P-code similarity lookups in the wiki. |
| `investigative_wiki/archive/20251124_consolidation/data_reference/embeddings_legacy/pcode_embeddings.json` | 571M | Older JSON format of the same P-code embeddings. Superseded by the pkl above. Probably don't need on Mac Mini unless you want the raw JSON format. |
| `investigative_wiki/archive/20251124_consolidation/finetuning_data/` | ~40M | Gemini finetuning training data (gemini_full_vocab_train.jsonl, gemini_3way_vocab_train.jsonl). Historical reference. |
| `sam_gov/data/pdf_cache/` | 758M | 212 cached PDFs. Re-fetched on demand. Saves bandwidth but not critical. |
| `investigative_wiki/archive/` (rest) | ~400M | Other old finetuning experiments, wiki snapshots. Historical reference only. |

### DON'T TRANSFER — Rebuild from scratch

| File | Size | Why |
|------|------|-----|
| All `.venv/` dirs | ~9.2G total | Recreate with `pip install -e .` or `uv sync`. Platform-specific binaries won't work cross-platform anyway (WSL2 → macOS). |
| `sam_gov/data/logs/` | 69M | Old logs. No value. |
| `sam_gov/data/reddit/` | 402M | Cached Reddit data. Re-fetchable. |
| `sam_gov/data/archives/` | 64M | Old data archives. |

## Transfer Method

**Option A: rsync over Tailscale (recommended)**
```bash
# After setting up Tailscale on both machines:
# From WSL2:
rsync -avz --progress ~/projects/sam_gov/data/exports/ macmini:~/projects/sam_gov/data/exports/
rsync -avz --progress ~/projects/sam_gov/data/articles/ macmini:~/projects/sam_gov/data/articles/
rsync -avz --progress ~/projects/sam_gov/data/research_v2/ macmini:~/projects/sam_gov/data/research_v2/
rsync -avz --progress ~/projects/sam_gov/data/research_output/ macmini:~/projects/sam_gov/data/research_output/
rsync -avz --progress ~/projects/investigative_wiki/investigative_wiki.db macmini:~/projects/investigative_wiki/
rsync -avz --progress ~/projects/investigative_wiki/data/ macmini:~/projects/investigative_wiki/data/
rsync -avz --progress ~/projects/process_tracing/output/ macmini:~/projects/process_tracing/output/

# .env files (do these one by one, verify contents)
scp ~/projects/sam_gov/.env macmini:~/projects/sam_gov/.env
scp ~/projects/investigative_wiki/.env macmini:~/projects/investigative_wiki/.env
scp ~/projects/theory-forge/.env macmini:~/projects/theory-forge/.env
scp ~/projects/process_tracing/.env macmini:~/projects/process_tracing/.env
scp ~/projects/twitter_explorer/.env macmini:~/projects/twitter_explorer/.env
```

**Option B: USB drive**
```bash
# Create a transfer bundle
mkdir -p /mnt/usb/transfer
cp -r ~/projects/sam_gov/data/exports/ /mnt/usb/transfer/sam_gov_exports/
cp -r ~/projects/sam_gov/data/articles/ /mnt/usb/transfer/sam_gov_articles/
cp ~/projects/investigative_wiki/investigative_wiki.db /mnt/usb/transfer/
cp -r ~/projects/investigative_wiki/data/ /mnt/usb/transfer/wiki_data/
# etc.
```

### NEW: Task Graph Runner System (2026-02-16)

| File | Size | Why |
|------|------|-----|
| `~/.openclaw/mcp_registry.toml` | <1K | MCP server startup configs for task graph runner. Uses `~` paths — portable. |
| `~/projects/data/task_graph/model_floors.json` | <1K | Cumulative learning — proven min/max difficulty tiers per task. NOT regenerable. |
| `~/projects/data/task_graph/experiments.jsonl` | varies | Historical experiment records. Optional but valuable for analyzer continuity. |

These files are part of the `llm_client` task graph runner built on 2026-02-16. See `~/projects/moltbot/TASK_GRAPH_WIRING.md` for the full integration spec.

## Total Transfer Size

- **Must transfer**: ~2.8G (mostly Discord exports)
- **Nice to have**: ~950M (PDF cache, embeddings, old output) + task_graph data files
- **Don't transfer**: ~9.7G (venvs, logs, caches)

## After Transfer: Mac Mini Setup

On the Mac Mini, after cloning repos and transferring data:
```bash
# Each project needs its venv recreated
cd ~/projects/sam_gov && python3 -m venv .venv && .venv/bin/pip install -e .
cd ~/projects/investigative_wiki && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd ~/projects/process_tracing && python3 -m venv .venv && .venv/bin/pip install -e .
cd ~/projects/theory-forge && python3 -m venv .venv && .venv/bin/pip install -e .
cd ~/projects/twitter_explorer && uv sync

# llm_client (required by everything)
cd ~/projects/llm_client && python3 -m venv .venv && .venv/bin/pip install -e ".[all-agents]"

# Verify task graph runner
python3 -c "from llm_client.task_graph import load_graph; print('ok')"

# Generate MCP registry (or copy from WSL2)
# See TASK_GRAPH_WIRING.md section 2

# Dry-run smoke test
~/.openclaw/bin/run_task.py --dry-run ~/.openclaw/tasks/templates/smoke_test.yaml
```

See also:
- `MAC_MINI_TOOLING_SETUP.md` — System tools, config files, MCP servers, venv recreation
- `TASK_GRAPH_WIRING.md` — Task graph runner integration spec
