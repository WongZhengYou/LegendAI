# AI Twin — Long-Term Plan

**Goal:** A local model that replicates Junxen — writing/chat style, knowledge & memory,
decision-making style — and works as a personal task assistant.

**Constraints:** Local-only training & inference. Hardware: RTX 5070 Laptop (8 GB VRAM),
32 GB RAM, Ryzen AI 7 350. Privacy first: personal data never leaves this machine
(enforced by .gitignore — never add a cloud git remote to this repo with data tracked).

**Philosophy:** Slow and steady. Each phase produces something usable on its own.
All progress logged in PROGRESS.md so any future Claude session can resume.

---

## Phase 0 — Setup  ⬅ CURRENT
- [x] Project structure + git
- [ ] Install Ollama (https://ollama.com/download/windows)
- [ ] Pull base chat model: `ollama pull qwen3:8b` (daily driver, fits 8 GB VRAM quantized)
- [ ] Pull embedding model: `ollama pull nomic-embed-text` (for RAG/memory)
- [ ] Smoke test: `ollama run qwen3:8b`

## Phase 1 — Persona + Memory (no training) — target: usable assistant in days
- [ ] Write `persona/PERSONA.md` — interview-built profile: bio, tone, phrases,
      languages/code-switching habits, values, how decisions get made
- [ ] Build simple chat script (`scripts/chat.py`) that loads persona as system prompt
- [ ] Add RAG memory: embed notes/facts in `memory/`, retrieve per query
- [ ] Every chat is logged to `logs/` — this becomes Phase 3 training data

## Phase 2 — Data Collection & Curation — ongoing, weeks
- [ ] Export chat logs (WhatsApp: chat > ⋮ > More > Export chat, WITHOUT media)
      → drop .txt files into `data/raw/`
- [ ] `scripts/parse_chats.py` — parse exports into (context → Junxen's reply) pairs
- [ ] Clean: strip other people's private info, dedupe, filter junk
- [ ] Format as chat-template JSONL in `data/train/`
- [ ] Milestone: ~1,000+ quality examples = enough for a first style LoRA

## Phase 3 — Fine-Tuning (QLoRA, local) — repeatable cycle
- Base model: Qwen3-4B (or Llama-3.2-3B) — 4-bit QLoRA fits in 8 GB VRAM
- Stack: WSL2 + Unsloth (fastest/least VRAM) or Windows-native transformers+peft
- [ ] Set up training env (separate .venv; WSL2 recommended for Unsloth)
- [ ] Train style LoRA on data/train — start 1-3 epochs, lr 2e-4, rank 16
- [ ] Export merged GGUF → load into Ollama with persona baked into Modelfile
- [ ] Evaluate: blind test — does it sound like Junxen? Log verdicts
- [ ] Re-train each time dataset grows meaningfully (every few weeks/months)

## Phase 4 — Assistant Duties
- [ ] Tool use: drafts messages/emails, summarizes, reminds
- [ ] Continuous learning loop: corrections in daily use → new training data
- [ ] Optional: voice, UI (Open WebUI), phone access over LAN

## Key decisions on record
- 2026-09-15: Local-only compute. Goals = style + knowledge + tasks + decision style.
  Data source: chat logs. Base ecosystem: Ollama + Qwen family (strong multilingual).
- 2026-09-15 (later): Scope narrowed — priority is TEXT CHAT STYLE replication only.
  No speech. Phase 1 (persona/RAG) now optional; go straight Phase 0 -> 2 -> 3.
  From-scratch pretraining ruled out (explained: infeasible on personal data/compute).
  Fine-tune target: qwen3:4b via QLoRA. User homework: install Ollama, pull
  qwen3:8b + qwen3:4b, export WhatsApp/Telegram chats (no media) into data/raw/.
