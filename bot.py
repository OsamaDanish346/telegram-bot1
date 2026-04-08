import os
import psycopg2
import asyncio
from telegram import *
from telegram.ext import *
from flask import Flask, request

TOKEN = os.getenv("8778331918:AAE5uzWflufC_AkLDz62m4A80BsbIZoZtvI")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
BOT_USERNAME = os.getenv("BOT_USERNAME")
DATABASE_URL = os.getenv("DATABASE_URL")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# ================= DATABASE =================
def get_conn():
    return psycopg2.connect(DATABASE_URL)

def setup_db():
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
    id BIGINT PRIMARY KEY,
    balance FLOAT DEFAULT 0,
    wallet TEXT,
    invited_by BIGINT,
    last_daily TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS channels(
    id SERIAL PRIMARY KEY,
    username TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS task_channels(
    id SERIAL PRIMARY KEY,
    username TEXT
    )
    """)

    conn.commit()
    conn.close()

setup_db()

# ================= BOT =================
app_bot = Application.builder().token(TOKEN).build()

# ================= USER =================
def get_user(uid):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE id=%s", (uid,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users(id) VALUES(%s)", (uid,))
        conn.commit()

    conn.close()

# ================= FORCE JOIN =================
async def force_join(update, context):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT username FROM channels")
    channels = cursor.fetchall()
    conn.close()

    if not channels:
        return True

    uid = update.effective_user.id
    buttons = []

    for ch in channels:
        ch = ch[0]
        try:
            member = await context.bot.get_chat_member(ch, uid)
            if member.status not in ["member","administrator","creator"]:
                buttons.append([InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{ch.replace('@','')}")])
        except:
            buttons.append([InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{ch.replace('@','')}")])

    if buttons:
        buttons.append([InlineKeyboardButton("✅ Joined All", callback_data="check_join")])
        await update.message.reply_text(
            "🚀 Join all channels:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return False

    return True

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    args = context.args
    get_user(uid)

    conn = get_conn()
    cursor = conn.cursor()

    # referral
    if args:
        ref = int(args[0])
        if ref != uid:
            cursor.execute("SELECT invited_by FROM users WHERE id=%s", (uid,))
            if cursor.fetchone()[0] is None:
                cursor.execute("UPDATE users SET invited_by=%s WHERE id=%s", (ref, uid))
                cursor.execute("UPDATE users SET balance=balance+2 WHERE id=%s", (ref,))
                conn.commit()

    conn.close()

    if not await force_join(update, context):
        return

    await update.message.reply_text(
        "🎉 Earn Stars Easily!\n\nInvite=2⭐\nDaily=0.5⭐\nWithdraw=20⭐",
        reply_markup=ReplyKeyboardMarkup([
            ["📊 Statistics","💸 Withdraw"],
            ["👥 Referral","💰 Balance"],
            ["💼 Set Wallet","📋 Tasks"],
            ["🎁 Bonus","📜 Terms"]
        ], resize_keyboard=True)
    )

# ================= TASK =================
async def tasks(update, context):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT username FROM task_channels")
    channels = cursor.fetchall()
    conn.close()

    buttons = []
    for ch in channels:
        ch = ch[0]
        buttons.append([InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{ch.replace('@','')}")])

    buttons.append([InlineKeyboardButton("✅ Check Tasks", callback_data="check_tasks")])

    await update.message.reply_text(
        "📋 Complete tasks:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def check_tasks(update, context):
    query = update.callback_query
    await query.answer()

    uid = query.from_user.id

    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT username FROM task_channels")
    channels = cursor.fetchall()

    ok = True
    for ch in channels:
        ch = ch[0]
        try:
            member = await context.bot.get_chat_member(ch, uid)
            if member.status not in ["member","administrator","creator"]:
                ok = False
        except:
            ok = False

    if ok:
        cursor.execute("UPDATE users SET balance=balance+0.3 WHERE id=%s", (uid,))
        conn.commit()
        await query.message.reply_text("🎉 +0.3⭐")
    else:
        await query.message.reply_text("❌ Join all")

    conn.close()

# ================= HANDLER =================
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    get_user(uid)

    conn = get_conn()
    cursor = conn.cursor()

    if text == "📋 Tasks":
        await tasks(update, context)

    elif text == "💰 Balance":
        cursor.execute("SELECT balance FROM users WHERE id=%s", (uid,))
        bal = cursor.fetchone()[0]
        await update.message.reply_text(f"{bal} ⭐")

    conn.close()

# ================= ADD HANDLERS =================
app_bot.add_handler(CommandHandler("start", start))
app_bot.add_handler(CallbackQueryHandler(check_tasks, pattern="check_tasks"))
app_bot.add_handler(MessageHandler(filters.TEXT, handler))

# ================= WEBHOOK =================
flask_app = Flask(__name__)

@flask_app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), app_bot.bot)
    asyncio.run(app_bot.process_update(update))
    return "ok"

@flask_app.route("/")
def home():
    return "Bot is running"

# ================= START BOT =================
async def start_bot():
    await app_bot.initialize()
    await app_bot.start()
    await app_bot.bot.set_webhook(f"{WEBHOOK_URL}/{TOKEN}")

if __name__ == "__main__":
    asyncio.run(start_bot())
    flask_app.run(host="0.0.0.0", port=8000)
