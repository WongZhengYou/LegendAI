# Replicating on Another PC

Two different goals — pick yours:

## A. Just RUN the twin on another PC (10 min, any decent PC, no GPU required)
Copy these 2 files (USB/local network — they contain your trained style, treat as private):
- `models/junxen-v1.gguf`
- `models/Modelfile`

On the new PC:
1. Install Ollama (https://ollama.com/download)
2. In the folder with both files: `ollama create junxen -f Modelfile`
3. `ollama run junxen`

## B. Replicate the full TRAINING pipeline

### Hardware requirements
- NVIDIA GPU, 8 GB+ VRAM (RTX 30-series or newer; 50-series needs cu128 torch — already in setup script)
- 16 GB+ RAM (24 GB+ WSL allocation needed for merge step — see .wslconfig below)
- ~40 GB free disk
- Windows 11 (or native Linux — skip the WSL parts)

### What to copy from this PC
- The whole `C:\Users\jxtf9\ai-twin\` folder. It contains everything:
  scripts/, training/ (setup_wsl.sh has ALL environment fixes baked in),
  models/, PLAN.md, PROGRESS.md, and your data/ (PRIVATE — USB, never cloud)
- `C:\Users\jxtf9\.wslconfig` → same place on new PC (24GB memory + swap;
  merge step OOMs at the 15GB WSL default)

### Install on the new PC (in order)
1. NVIDIA driver (recent; check `nvidia-smi` works)
2. Ollama + `ollama pull qwen3:8b` (optional, for comparison chats)
3. `wsl --install -d Ubuntu` (PowerShell, then reboot if asked)
4. Inside WSL: `bash /mnt/c/<path>/ai-twin/training/setup_wsl.sh`
   (~8 GB of downloads; ends with "CUDA OK: True")
5. Verify GPU visible in WSL: `nvidia-smi`

### The pipeline (identical to this PC)
```
py scripts/parse_chats.py                       # data/raw -> data/train/pairs.jsonl
wsl: python training/train_lora.py --epochs 3   # ~10 min on 8GB GPU
wsl: python training/export_gguf.py             # merge + q4_k_m GGUF (downloads 8GB base, once)
ollama create junxen -f models/Modelfile        # after moving GGUF to models/junxen-v1.gguf
```
Note: export writes to training/out/gguf_gguf/*.Q4_K_M.gguf — move/rename to models/junxen-v1.gguf.

### Exact known-good package versions
`training/requirements-known-good.txt` (pip freeze from the working env).
If future installs break, recreate with: `pip install -r requirements-known-good.txt`
Environment quirks & why: see PROGRESS.md 2026-09-16.

## C. Setting up for a DIFFERENT person (e.g. "legend")

The pipeline is person-agnostic — identity lives in one file: `twin.json`.

1. Copy the STARTER BUNDLE to the new PC (ai-twin-starter.zip — contains code
   and docs only, NO chat data and NO trained model; those stay with their owner)
2. Follow section B installs (Ollama, WSL2 Ubuntu, setup_wsl.sh, .wslconfig)
3. Edit `twin.json`:  {"name": "Legend", "model": "legend"}
4. Data — MUST come from legend's own phone, with their knowledge/consent:
   they export their own WhatsApp chats (Export chat > Without media).
   WhatsApp marks the exporter's messages as "You" — that is who the model
   learns to imitate, so exporting from anyone else's phone trains the wrong person.
   Put the .txt files in data/raw/
5. Run the pipeline:
   - `py scripts/parse_chats.py`      (also generates models/Modelfile for "legend")
   - in WSL: `python training/train_lora.py --epochs 3`
   - in WSL: `python training/export_gguf.py`  (auto-names models/legend-v1.gguf)
   - `ollama create legend -f models/Modelfile`
   - `ollama run legend`
6. If legend's exports use a different date format (e.g. DD/MM/YYYY or 24h time,
   depends on phone region/language), parsing may yield 0 examples — adjust the
   LINE regex + strptime format in scripts/parse_chats.py, or ask Claude to.
