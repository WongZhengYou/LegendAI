# Progress Log

> For future Claude sessions: read PLAN.md first, then this file bottom-up.
> Append an entry after every working session. Never commit data/ or memory/.

## 2026-09-15 — Session 1: Kickoff
- Hardware verified: RTX 5070 Laptop 8GB VRAM, 32GB RAM, Ryzen AI 7 350
- Python 3.12.10 ✅, git ✅, Ollama ❌ not yet installed
- Decisions: local-only training; QLoRA on small model later; Ollama+Qwen stack
- Created project structure + PLAN.md
- NEXT UP: user installs Ollama, pulls qwen3:8b + nomic-embed-text;
  then build PERSONA.md via interview, then scripts/chat.py

## 2026-09-15 — Session 1 (cont.)
- User confirmed: text-only, "type and chat like me". Skip speech, Phase 1 optional.
- Gave user steps 1-3 (Ollama install, pull qwen3:8b/4b, export chats to data/raw/)
- NEXT SESSION: check data/raw/ for exports -> write scripts/parse_chats.py
  (parse WhatsApp .txt / Telegram JSON -> context->reply JSONL, scrub PII, dedupe)

## 2026-09-16 — Session 2: Data parsed
- User completed all homework: Ollama + qwen3:8b/4b pulled, 5 WhatsApp exports in data/raw
- Confirmed identity: only sender "You" is Junxen (others incl. "Zheng You" are other people)
- Wrote scripts/parse_chats.py: US-format WhatsApp parser, 3h session split,
  alternating roles, group-name prefixes, PII scrub (phones/emails), dedupe
- Result: 137 examples / 554 target replies -> data/train/pairs.jsonl (below 1k
  milestone; OK for first experimental LoRA — user can add more exports later)
- NEXT: install Ubuntu WSL2 -> Unsloth env -> training/train_lora.py (QLoRA qwen3-4b)

## 2026-09-16 — Session 2 (cont.): FIRST TWIN TRAINED ✅
- WSL2 Ubuntu 26.04 + twin-env (unsloth). Fixes needed, now baked into setup_wsl.sh
  or pinned: torchvision must be cu128 build; datasets>=5.0.1 (py3.14 pickle fix);
  python3-dev required (triton); .wslconfig memory=24GB+swap=24GB (merge OOMs at 15GB)
- Trained qwen3-4b QLoRA: 51 steps/3 epochs in ~7 min. Export via export_gguf.py
  (standalone process). GGUF: models/junxen-v1.gguf (2.4GB q4_k_m)
- Ollama model created: `ollama run junxen` — first replies look promisingly Junxen-ish
- Cleaned intermediates (~8GB). Kept: lora adapter, HF cache (16bit base for retrains)
- NEXT: user evaluates twin in real use; collect more chat exports into data/raw;
  retrain cycle = parse_chats.py -> train_lora.py -> export_gguf.py -> ollama create

## 2026-09-17 — Session 3: Pipeline made person-agnostic
- Identity now in twin.json ({"name","model"}); parse_chats.py generates the
  matching models/Modelfile; export_gguf.py auto-names models/<model>-v1.gguf
- setup_wsl.sh now includes ALL env fixes; requirements-known-good.txt frozen
- REPLICATE.md: run-only (A), full pipeline (B), new person "legend" (C)
- Starter bundle (code only, no data): OneDrive\Desktop\ai-twin-starter.zip
- Plan: user sets up "legend" twin on another PC with legend's own exports
