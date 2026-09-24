"""Parse chat exports in data/raw into training JSONL in data/train.

Supported formats:
- WhatsApp .txt:  [M/D/YY, H:MM:SS AM/PM] Sender: message
  The exporter's messages are marked "You" = training target.
- Discord CSV (channelId,messageId,date,authorId,authorUsername,content,...):
  target author = twin.json "discord_username". Bot authors (names with
  spaces) are skipped.

Persona/model name comes from twin.json at project root.
Sessions split on >3h gaps; each session becomes chat-format examples
(others' merged messages -> user role, the person's -> assistant role).
Scrubs phone numbers/emails; skips calls, media stubs, deleted messages.
Also generates models/Modelfile matching the training system prompt.
"""
import csv, json, re, sys, unicodedata
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW, TRAIN = ROOT / "data" / "raw", ROOT / "data" / "train"

_cfg = ROOT / "twin.json"
CFG = json.loads(_cfg.read_text(encoding="utf-8")) if _cfg.exists() else {"name": "Junxen", "model": "junxen"}
SYSTEM = (f"You are {CFG['name']} chatting with friends. Reply exactly as "
          f"{CFG['name']} would - their tone, length, and language mix.")

LINE = re.compile(r"^\[(\d{1,2}/\d{1,2}/\d{2}), (\d{1,2}:\d{2}:\d{2})\s*([AP]M)\] (.*)$")
SENDER = re.compile(r"^([^:]{1,40}): (.*)$", re.S)
PHONE = re.compile(r"\+?\d[\d\s\-()]{7,}\d")
EMAIL = re.compile(r"\S+@\S+\.\S+")
DISCORD_MENTION = re.compile(r"<@!?\d+>")
DISCORD_EMOJI = re.compile(r"<a?(:\w+:)\d+>")
SKIP_BODIES = {"[Call]", "<Media omitted>", "image omitted", "video omitted",
               "sticker omitted", "audio omitted", "GIF omitted",
               "This message was deleted.", "You deleted this message."}
SESSION_GAP = timedelta(hours=3)
MAX_TURNS = 16          # max messages per training example

URL = re.compile(r"(https?://\S+)")

def clean(text):
    text = DISCORD_MENTION.sub("@user", DISCORD_EMOJI.sub(r"\1", text))
    # scrub PII only outside URLs (GIF/video links end in long digit IDs)
    pieces = URL.split(text)
    for i in range(0, len(pieces), 2):  # even indexes = non-URL text
        pieces[i] = PHONE.sub("[phone]", EMAIL.sub("[email]", pieces[i]))
    text = "".join(pieces)
    return "".join(ch for ch in text if unicodedata.category(ch) != "Cc" or ch == "\n").strip()

def parse_whatsapp(path):
    """Yield (datetime, sender, text); multiline messages merged. "You" = target."""
    msgs = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        raw = raw.lstrip("")  # strip LTR/RTL marks WhatsApp inserts
        m = LINE.match(raw)
        if m:
            date, time, ap, rest = m.groups()
            rest = rest.lstrip("")
            ts = datetime.strptime(f"{date} {time} {ap}", "%m/%d/%y %I:%M:%S %p")
            sm = SENDER.match(rest)
            if not sm:            # system line e.g. "- [Call]", encryption notice
                continue
            sender, body = sm.group(1).strip(), sm.group(2)
            if body.strip().strip("") in SKIP_BODIES or body.startswith("- ["):
                continue
            msgs.append([ts, sender, body])
        elif msgs and raw.strip():  # continuation of previous message
            msgs[-1][2] += "\n" + raw
    return msgs

def parse_discord_csv(path):
    """Yield (datetime, sender, text). twin.json discord_username -> "You"."""
    target = CFG.get("discord_username")
    if not target:
        print(f"SKIP {path.name}: set \"discord_username\" in twin.json to use Discord exports")
        return []
    msgs = []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            author, body = row["authorUsername"], row["content"].strip()
            if not body or " " in author:   # attachment/sticker-only rows; bots
                continue
            ts = datetime.strptime(row["date"], "%m/%d/%Y, %I:%M:%S %p")
            sender = "You" if author == target else author
            msgs.append([ts, sender, body])
    msgs.sort(key=lambda m: m[0])
    return msgs

def to_sessions(msgs):
    sessions, cur = [], []
    for ts, sender, body in msgs:
        if cur and ts - cur[-1][0] > SESSION_GAP:
            sessions.append(cur); cur = []
        cur.append((ts, sender, body))
    if cur:
        sessions.append(cur)
    return sessions

def session_to_examples(session, is_group):
    # collapse into alternating role turns
    turns = []  # (role, text)
    for ts, sender, body in session:
        body = clean(body)
        if not body:
            continue
        if sender == "You":
            role, text = "assistant", body
        else:
            role = "user"
            text = f"{sender}: {body}" if is_group else body
        if turns and turns[-1][0] == role:
            turns[-1] = (role, turns[-1][1] + "\n" + text)
        else:
            turns.append((role, text))
    # need user->assistant alternation; drop a leading assistant turn
    if turns and turns[0][0] == "assistant":
        turns = turns[1:]
    if turns and turns[-1][0] == "user":
        turns = turns[:-1]
    examples = []
    for i in range(0, len(turns), MAX_TURNS):
        chunk = turns[i:i + MAX_TURNS]
        if chunk and chunk[0][0] == "assistant":
            chunk = chunk[1:]
        if chunk and chunk[-1][0] == "user":
            chunk = chunk[:-1]
        if len(chunk) >= 2:
            examples.append({"messages": [{"role": "system", "content": SYSTEM}] +
                             [{"role": r, "content": t} for r, t in chunk]})
    return examples

def write_modelfile():
    mf = ROOT / "models" / "Modelfile"
    mf.parent.mkdir(exist_ok=True)
    mf.write_text(
        f'FROM ./{CFG["model"]}-v1.gguf\n'
        f'SYSTEM """{SYSTEM}"""\n'
        "PARAMETER temperature 0.7\nPARAMETER top_p 0.8\n"
        "PARAMETER top_k 20\nPARAMETER repeat_penalty 1.05\n",
        encoding="utf-8",
    )
    return mf

def main():
    TRAIN.mkdir(parents=True, exist_ok=True)
    all_ex, stats = [], []
    files = sorted(RAW.glob("*.txt")) + sorted(RAW.glob("*.csv"))
    for path in files:
        msgs = parse_whatsapp(path) if path.suffix == ".txt" else parse_discord_csv(path)
        if not msgs:
            continue
        senders = {s for _, s, _ in msgs}
        is_group = len(senders - {"You"}) > 1
        n_you = sum(1 for _, s, _ in msgs if s == "You")
        ex = [e for sess in to_sessions(msgs) for e in session_to_examples(sess, is_group)]
        all_ex.extend(ex)
        stats.append(f"{path.name}: {len(msgs)} msgs ({n_you} target), "
                     f"{'group' if is_group else '1-on-1'}, {len(ex)} examples")
    # dedupe identical examples
    seen, out = set(), []
    for e in all_ex:
        key = json.dumps(e, ensure_ascii=False, sort_keys=True)
        if key not in seen:
            seen.add(key); out.append(e)
    dst = TRAIN / "pairs.jsonl"
    with dst.open("w", encoding="utf-8") as f:
        for e in out:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    n_targets = sum(sum(1 for m in e["messages"] if m["role"] == "assistant") for e in out)
    print("\n".join(stats))
    print(f"\nTOTAL: {len(out)} examples, {n_targets} target replies -> {dst}")
    print(f"Modelfile for {CFG['model']!r} -> {write_modelfile()}")

if __name__ == "__main__":
    main()