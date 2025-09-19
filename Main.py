import os
import json
import random
import asyncio

from telegram import Update, ChatInviteLink
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

DATA_FILE = "data.json"

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

if not BOT_TOKEN or not OWNER_ID:
    print("BOT_TOKEN ya OWNER_ID set karo environment vars me")
    exit(1)

default_data = {
    "sudos": [OWNER_ID],
    "auto_reply_enabled": False,
    "auto_replies": ["Hello! Bot ready."],
    "name_change_enabled": False,
    "allowed_exec": ["whoami", "ls", "pwd"],
}

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return default_data.copy()

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

data = load_data()

def is_sudo(user_id: int) -> bool:
    return user_id in data.get("sudos", [])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is online!")

async def addsudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_sudo(update.effective_user.id):
        return await update.message.reply_text("⛔ Unauthorized")
    if not context.args:
        return await update.message.reply_text("Usage: /addsudo <user_id>")
    try:
        new_id = int(context.args[0])
        if new_id in data["sudos"]:
            return await update.message.reply_text("User already sudo.")
        data["sudos"].append(new_id)
        save_data(data)
        await update.message.reply_text(f"✅ Added sudo: {new_id}")
    except:
        await update.message.reply_text("Invalid ID.")

async def remsudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_sudo(update.effective_user.id):
        return await update.message.reply_text("⛔ Unauthorized")
    if not context.args:
        return await update.message.reply_text("Usage: /remsudo <user_id>")
    try:
        rid = int(context.args[0])
        if rid in data["sudos"]:
            data["sudos"].remove(rid)
            save_data(data)
            await update.message.reply_text(f"✅ Removed sudo: {rid}")
        else:
            await update.message.reply_text("User not sudo.")
    except:
        await update.message.reply_text("Invalid ID.")

async def listsudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lst = "\n".join(str(x) for x in data.get("sudos", []))
    await update.message.reply_text("Sudo users:\n" + lst)

async def toggle_autoreply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_sudo(update.effective_user.id):
        return await update.message.reply_text("⛔ Unauthorized")
    data["auto_reply_enabled"] = not data.get("auto_reply_enabled", False)
    save_data(data)
    await update.message.reply_text(f"Auto-reply {'enabled' if data['auto_reply_enabled'] else 'disabled'}")

async def addreply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_sudo(update.effective_user.id):
        return await update.message.reply_text("⛔ Unauthorized")
    txt = " ".join(context.args)
    if not txt:
        return await update.message.reply_text("Usage: /addreply <message>")
    data["auto_replies"].append(txt)
    save_data(data)
    await update.message.reply_text("✅ Auto-reply added.")

async def rmreply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_sudo(update.effective_user.id):
        return await update.message.reply_text("⛔ Unauthorized")
    if not context.args:
        return await update.message.reply_text("Usage: /rmreply <index>")
    try:
        idx = int(context.args[0])
        removed = data["auto_replies"].pop(idx)
        save_data(data)
        await update.message.reply_text(f"Removed reply: {removed}")
    except:
        await update.message.reply_text("Invalid index.")

async def listreply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = [f"{i}: {msg}" for i, msg in enumerate(data.get("auto_replies", []))]
    await update.message.reply_text("Auto-replies:\n" + ("\n".join(lines) if lines else "None"))

async def togglename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_sudo(update.effective_user.id):
        return await update.message.reply_text("⛔ Unauthorized")
    data["name_change_enabled"] = not data.get("name_change_enabled", False)
    save_data(data)
    await update.message.reply_text(f"Group name change {'enabled' if data['name_change_enabled'] else 'disabled'}")

async def setname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_sudo(update.effective_user.id):
        return await update.message.reply_text("⛔ Unauthorized")
    if not data.get("name_change_enabled"):
        return await update.message.reply_text("Name change disabled. Use /togglename first.")
    if not context.args:
        return await update.message.reply_text("Usage: /setname <new name>")
    new_name = " ".join(context.args)
    try:
        await context.bot.set_chat_title(update.effective_chat.id, new_name)
        await update.message.reply_text(f"✅ New name: {new_name}")
    except Exception as e:
        await update.message.reply_text(f"Error changing name: {e}")

async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_sudo(update.effective_user.id):
        return await update.message.reply_text("⛔ Unauthorized")
    try:
        link = await context.bot.create_chat_invite_link(chat_id=update.effective_chat.id)
        await update.message.reply_text(f"Invite link:\n{link.invite_link}")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_sudo(update.effective_user.id):
        return await update.message.reply_text("⛔ Unauthorized")
    target_id = None
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    elif context.args:
        try:
            if context.args[0].startswith("@"):
                member = await context.bot.get_chat_member(update.effective_chat.id, context.args[0])
                target_id = member.user.id
            else:
                target_id = int(context.args[0])
        except:
            pass
    if not target_id:
        return await update.message.reply_text("Usage: /kick <user_id or @username> or reply to user")
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target_id)
        await update.message.reply_text(f"✅ Kicked {target_id}")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and not update.message.text.startswith("/"):
        if data.get("auto_reply_enabled"):
            await update.message.reply_text(random.choice(data.get("auto_replies", ["Hi!"])))

def main():
    from telegram.ext import ApplicationBuilder
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addsudo", addsudo))
    app.add_handler(CommandHandler("remsudo", remsudo))
    app.add_handler(CommandHandler("listsudo", listsudo))
    app.add_handler(CommandHandler("autoreply", toggle_autoreply))
    app.add_handler(CommandHandler("addreply", addreply))
    app.add_handler(CommandHandler("rmreply", rmreply))
    app.add_handler(CommandHandler("listreply", listreply))
    app.add_handler(CommandHandler("togglename", togglename))
    app.add_handler(CommandHandler("setname", setname))
    app.add_handler(CommandHandler("invite", invite))
    app.add_handler(CommandHandler("kick", kick))

    # message handler
    app.add_handler(MessageHandler(filters.ALL & ~filters.Command, on_message))

    print("Bot is starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
