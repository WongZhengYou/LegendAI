# Legend Twin — New PC Checklist

Copy this WHOLE folder to the new PC via USB (it contains legend's chat data —
keep it off cloud drives). Below, YOURNAME = the Windows username on the new PC,
and the folder is assumed at C:\Users\YOURNAME\legend-twin

Already done on the source PC (skip): twin.json is configured for legend;
Discord export parsed -> data/train/pairs.jsonl (652 examples, 2,971 targets).

## Install (in order)
1. NVIDIA driver — verify:            nvidia-smi
2. Ollama:                             https://ollama.com/download/windows
3. Python 3.12 (Microsoft Store) — verify:  py --version
4. WSL2 Ubuntu (PowerShell as Admin):  wsl --install -d Ubuntu   (reboot if asked)
5. WSL memory — notepad $env:USERPROFILE\.wslconfig  -> paste:
       [wsl2]
       memory=24GB
       swap=24GB
   (16GB-RAM PC: memory=12GB, swap=32GB)   then:   wsl --shutdown
6. Training env (one-time, ~8GB downloads, ends with "CUDA OK: True"):
       wsl -d Ubuntu -u root -- bash /mnt/c/Users/YOURNAME/legend-twin/training/setup_wsl.sh

## Build legend
7.  cd C:\Users\YOURNAME\legend-twin
8.  py scripts\parse_chats.py          (re-check: ~652 examples; add more exports to data/raw anytime)
9.  wsl -d Ubuntu -u root -- bash -c "source ~/twin-env/bin/activate; cd /mnt/c/Users/YOURNAME/legend-twin/training; python train_lora.py --epochs 3"
10. wsl -d Ubuntu -u root -- bash -c "source ~/twin-env/bin/activate; cd /mnt/c/Users/YOURNAME/legend-twin/training; python export_gguf.py"
    (downloads the 8GB base model once; ends by writing models\legend-v1.gguf)
11. cd models
    ollama create legend -f Modelfile
    ollama run legend

Troubleshooting: every environment failure we ever hit and its fix is in
PROGRESS.md (2026-09-16). Or install Claude Code, open this folder, and say:
"read NEWPC-CHECKLIST.md and set up the legend twin".
