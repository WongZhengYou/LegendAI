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
       py scripts\discord_bot.py
   Ollama must be running on the same PC with the model created.

The bot replies when @mentioned or when someone replies to its message.
Context is built in the same shape as the training data (group format:
"username: message" for humans, plain text for the twin's own lines).
"""
import os
import re
import requests
import discord

TOKEN = os.environ["DISCORD_TOKEN"]
MODEL = os.environ.get("TWIN_MODEL", "legend")
OLLAMA = "http://localhost:11434/api/chat"
HISTORY = 20  # recent messages used as context

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"logged in as {client.user} - speaking as '{MODEL}'")


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
        r = requests.post(OLLAMA, json={"model": MODEL, "messages": merged,
                                        "stream": False}, timeout=300)
        r.raise_for_status()
        reply = r.json()["message"]["content"]
        reply = re.sub(r"<tool_call>.?(</tool_call>|$)", "", reply, flags=re.S)
        reply = re.sub(r"<think>.?(</think>|$)", "", reply, flags=re.S)
        reply = reply.strip()[:1900]
    if reply:
        await msg.reply(reply, mention_author=False)


client.run(TOKEN)
