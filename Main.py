# main.py
import os
import json
import asyncio
import random
from pathlib import Path
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

DATA_FILE = "data.json"
DEFAULT_DELAY = 2  # seconds

# Load bot token and owner id from environment (Replit Secrets)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

if not BOT_TOKEN or not OWNER_ID:
    raise SystemExit("Error: Set BOT_TOKEN and OWNER_ID as environment variables (Replit Secrets).")

# Storage helpers
def load_data():
    p = Path(DATA_FILE)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}  # mapping: chat_id_str -> {enabled:bool, delay_seconds:int, auto_replies:list}

def save_data(d):
    Path(DATA_FILE).write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")

data = load_data()

def get_chat_cfg(chat_id: int):
    key = str(chat_id)
    cfg = data.get(key)
    if not cfg:
        cfg = {"enabled": False, "delay_seconds": DEFAULT_DELAY, "auto_replies": ["Hi! I'm here."]}
        data[key] = cfg
        save_data(data)
    return cfg

def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

# --- Commands ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot online. Owner can use /enable in a group to activate features.")

async def enable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_owner(user.id):
        return await update.message.reply_text("⛔ Only the owner can enable the bot for this group.")
    if update.effective_chat.type == "private":
        return await update.message.reply_text("Use this command inside a group where you want the bot active.")
    cfg = get_chat_cfg(update.effective_chat.id)
    cfg["enabled"] = True
    save_data(data)
    await update.message.reply_text("✅ Bot features enabled for this group.")

async def disable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_owner(user.id):
        return await update.message.reply_text("⛔ Only the owner can disable the bot for this group.")
    if update.effective_chat.type == "private":
        return await update.message.reply_text("Use this command inside the target group.")
    cfg = get_chat_cfg(update.effective_chat.id)
    cfg["enabled"] = False
    save_data(data)
    await update.message.reply_text("⛔ Bot features disabled for this group.")

async def setdelay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_owner(user.id):
        return await update.message.reply_text("⛔ Only the owner can set delay.")
    if update.effective_chat.type == "private":
        return await update.message.reply_text("Use this inside the target group.")
    if not context.args:
        return await update.message.reply_text("Usage: /setdelay <seconds> (e.g. /setdelay 3)")
    try:
        sec = float(context.args[0])
        if sec < 0:
            raise ValueError
    except:
        return await update.message.reply_text("Invalid seconds. Use a non-negative number.")
    cfg = get_chat_cfg(update.effective_chat.id)
    cfg["delay_seconds"] = sec
    save_data(data)
    await update.message.reply_text(f"⏱️ Reply delay set to {sec} seconds for this group.")

async def addreply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_owner(user.id):
        return await update.message.reply_text("⛔ Only the owner can add replies.")
    if update.effective_chat.type == "private":
        return await update.message.reply_text("Use this inside the target group.")
    text = " ".join(context.args).strip()
    if not text:
        return await update.message.reply_text("Usage: /addreply <text>")
    cfg = get_chat_cfg(update.effective_chat.id)
    cfg.setdefault("auto_replies", []).append(text)
    save_data(data)
    await update.message.reply_text("✅ Auto-reply added.")

async def rmreply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_owner(user.id):
        return await update.message.reply_text("⛔ Only the owner can remove replies.")
    if update.effective_chat.type == "private":
        return await update.message.reply_text("Use this inside the target group.")
    if not context.args:
        return await update.message.reply_text("Usage: /rmreply <index>")
    try:
        idx = int(context.args[0])
        cfg = get_chat_cfg(update.effective_chat.id)
        removed = cfg["auto_replies"].pop(idx)
        save_data(data)
        await update.message.reply_text(f"Removed reply: {removed}")
    except Exception as e:
        await update.message.reply_text("Invalid index.")

async def listreply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = get_chat_cfg(update.effective_chat.id)
    lines = [f"{i}: {t}" for i, t in enumerate(cfg.get("auto_replies", []))]
    text = "Auto replies:\n" + ("\n".join(lines) if lines else "No replies set.")
    await update.message.reply_text(text)

# --- Auto reply behavior ---
async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return
    if msg.text.startswith("/"):
        return  # skip commands
    chat = update.effective_chat
    cfg = get_chat_cfg(chat.id)
    if not cfg.get("enabled"):
        return
    # choose reply and wait for delay
    reply = random.choice(cfg.get("auto_replies", ["Hello!"]))
    delay = cfg.get("delay_seconds", DEFAULT_DELAY)
    # Asynchronously sleep so the bot can handle other updates
    await asyncio.sleep(delay)
    try:
        await msg.reply_text(reply)
    except Exception:
        pass

# --- App setup ---
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("enable", enable))
    app.add_handler(CommandHandler("disable", disable))
    app.add_handler(CommandHandler("setdelay", setdelay))
    app.add_handler(CommandHandler("addreply", addreply))
    app.add_handler(CommandHandler("rmreply", rmreply))
    app.add_handler(CommandHandler("listreply", listreply))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    print("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()
