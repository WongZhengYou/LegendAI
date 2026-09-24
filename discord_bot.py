"""Discord bot that speaks through a local Ollama twin model.

Setup:
1. https://discord.com/developers/applications -> New Application -> add a Bot
   - Privileged Gateway Intents: enable MESSAGE CONTENT INTENT
   - copy the bot token (keep it secret)
2. OAuth2 -> URL Generator: scope "bot"; permissions "Send Messages",
   "Read Message History" -> open the generated URL, invite bot to your server
3. Install deps (Windows):  py -m pip install discord.py requests
4. Run (PowerShell):
       $env:DISCORD_TOKEN="your-token-here"
       $env:TWIN_MODEL="legend"
       py discord_bot.py
   Ollama must be running on the same PC with the model created.

The bot replies when @mentioned or when someone replies to its message.
Context is built in the same shape as the training data (group format:
"username: message" for humans, plain text for the twin's own lines).
"""
import csv
import json
import os
import random
import re
from pathlib import Path
import requests
import discord

TOKEN = os.environ["DISCORD_TOKEN"]
MODEL = os.environ.get("TWIN_MODEL", "legend")
OLLAMA = "http://localhost:11434/api/chat"
HISTORY = 20  # recent messages used as context
ROOT = Path(__file__).resolve().parent

# Real links the twin actually sent (GIFs, YouTube, IG, FB...), from the
# Discord exports. The model can't memorize IDs like "watch?v=jEGTdEDaBEE" or
# "reel/C3NFYwdr5s6", so it invents them (or writes "[phone]", learned from
# PII-scrubbed training data) -> dead links. Snap each one to a real link
# from the same site: best keyword match, else a random one.
LINK = re.compile(r"https?://[^\s<>]+")
SITE_ALIASES = {"youtu.be": "youtube.com", "instagr.am": "instagram.com",
                "fb.watch": "facebook.com", "twitter.com": "x.com",
                "media.giphy.com": "giphy.com", "my.shp.ee": "shopee.com.my"}


def site(url):
    host = re.sub(r"^https?://", "", url).split("/")[0].split("?")[0].lower()
    host = re.sub(r"^(www|m|mobile|vm|l)\.", "", host)
    return SITE_ALIASES.get(host, host)


def link_words(url):
    path = re.sub(r"^https?://[^/]+", "", url).lower()
    # readable words only; random IDs / numbers don't help matching
    return {w for w in re.split(r"[^a-z]+", path)
            if len(w) >= 3 and w not in {"gif", "view", "watch", "reel", "www",
                                         "http", "https", "com", "status", "posts"}}


def load_real_links():
    cfg = ROOT / "twin.json"
    target = (json.loads(cfg.read_text(encoding="utf-8")).get("discord_username")
              if cfg.exists() else None)
    links = set()
    for base in (ROOT, ROOT.parent):  # works from project root or scripts/
        for path in (base / "data" / "raw").glob("*.csv"):
            with path.open(encoding="utf-8-sig", newline="") as fh:
                for row in csv.DictReader(fh):
                    if target and row.get("authorUsername") != target:
                        continue
                    links.update(LINK.findall(row.get("content", "")))
    by_site = {}
    for u in sorted(links):
        by_site.setdefault(site(u), []).append((u, link_words(u)))
    return links, by_site


REAL_LINKS, LINKS_BY_SITE = load_real_links()


def fix_link(match, seen=()):
    url = match.group(0)
    # real, just posted in the chat, or no exports on this PC
    if url in REAL_LINKS or url in seen or not REAL_LINKS:
        return url
    candidates = LINKS_BY_SITE.get(site(url))
    if not candidates:  # a site they never linked: surely made up
        return ""
    words = link_words(url)
    best, score = max(((u, len(words & w) / (len(words | w) or 1))
                       for u, w in candidates), key=lambda x: x[1])
    return best if score > 0 else random.choice(candidates)[0]


def clean_reply(reply, seen=()):
    # drop Qwen tool-call / thinking blocks, including unclosed ones
    reply = re.sub(r"<tool_call>.*?(</tool_call>|$)", "", reply, flags=re.S)
    reply = re.sub(r"<think>.*?(</think>|$)", "", reply, flags=re.S)
    # leftover tag fragments like "<t", "</tool_call>", "<think"
    reply = re.sub(r"</?(?:tool_call|think|t|to|too|tool|th|thi|thin)>?(?=\s|<|$)",
                   "", reply)
    reply = LINK.sub(lambda m: fix_link(m, seen), reply)
    # placeholders the model learned from the PII-scrubbed training data
    reply = re.sub(r"\S*\[(phone|email)\]\S*", "", reply)
    return re.sub(r"[ \t]+\n", "\n", reply).strip()

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"logged in as {client.user} - speaking as '{MODEL}' "
          f"({len(REAL_LINKS)} real links loaded)")


@client.event
async def on_message(msg):
    if msg.author == client.user:
        return
    mentioned = client.user in msg.mentions
    replied = (msg.reference and msg.reference.resolved
               and getattr(msg.reference.resolved, "author", None) == client.user)
    if not (mentioned or replied):
        return

    history = [m async for m in msg.channel.history(limit=HISTORY)]
    convo = []
    for m in reversed(history):  # oldest first
        text = m.clean_content.strip()
        if not text:
            continue
        if m.author == client.user:
            convo.append({"role": "assistant", "content": text})
        else:
            convo.append({"role": "user", "content": f"{m.author.display_name}: {text}"})
    # merge consecutive same-role turns (model expects alternation)
    merged = []
    for c in convo:
        if merged and merged[-1]["role"] == c["role"]:
            merged[-1]["content"] += "\n" + c["content"]
        else:
            merged.append(c)

    async with msg.channel.typing():
        r = requests.post(OLLAMA, json={
            "model": MODEL, "messages": merged, "stream": False,
            "think": False, "options": {"stop": ["<tool_call>", "<think>"]},
        }, timeout=300)
        r.raise_for_status()
        seen = set(LINK.findall("\n".join(c["content"] for c in merged)))
        reply = clean_reply(r.json()["message"]["content"], seen)[:1900]
    if reply:
        await msg.reply(reply, mention_author=False)


client.run(TOKEN)
