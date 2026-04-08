import os
import logging
import psycopg2
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# ================= LOGGING =================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================= ENVIRONMENT VARIABLES =================
TOKEN = "8778331918:AAE5uzWflufC_AkLDz62m4A80BsbIZoZtvI"
ADMIN_ID = 8289491009
BOT_USERNAME = os.getenv("BOT_USERNAME", "Afghan_reward_bot")   # که غواړئ بدل کړئ
DATABASE_URL = os.getenv("DATABASE_URL")
WEBHOOK_URL = "https://worker-production-f5b3.up.railway.app"

# مهم چک
if not TOKEN:
    logger.error("❌ BOT_TOKEN missing!")
    raise ValueError("BOT_TOKEN is required")

if not DATABASE_URL:
    logger.error("❌ DATABASE_URL missing in Environment Variables!")
    raise ValueError("DATABASE_URL is required")

logger.info("✅ All environment variables loaded successfully")

# ================= DATABASE =================
try:
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cursor = conn.cursor()
    logger.info("✅ Database connected successfully")
except Exception as e:
    logger.error(f"❌ Database connection failed: {e}")
    raise

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

# ================= TELEGRAM APPLICATION =================
application = Application.builder().token(TOKEN).build()

# ================= HELPER =================
def get_user(uid):
    cursor.execute("SELECT * FROM users WHERE id=%s", (uid,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users(id) VALUES(%s)", (uid,))
        conn.commit()

# ================= FORCE JOIN =================
async def force_join(update, context):
    cursor.execute("SELECT username FROM channels")
    channels = cursor.fetchall()
    if not channels:
        return True

    uid = update.effective_user.id
    buttons = []
    for ch in channels:
        ch = ch[0]
        try:
            member = await context.bot.get_chat_member(ch, uid)
            if member.status not in ["member", "administrator", "creator"]:
                buttons.append([InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{ch.replace('@','')}")])
        except:
            buttons.append([InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{ch.replace('@','')}")])

    if buttons:
        buttons.append([InlineKeyboardButton("✅ Joined All", callback_data="check_join")])
        await update.message.reply_text("🚀 Join all channels:", reply_markup=InlineKeyboardMarkup(buttons))
        return False
    return True

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    args = context.args
    get_user(uid)

    if args:
        try:
            ref = int(args[0])
            if ref != uid:
                cursor.execute("SELECT invited_by FROM users WHERE id=%s", (uid,))
                if cursor.fetchone()[0] is None:
                    cursor.execute("UPDATE users SET invited_by=%s WHERE id=%s", (ref, uid))
                    cursor.execute("UPDATE users SET balance=balance+2 WHERE id=%s", (ref,))
                    conn.commit()
        except:
            pass

    if not await force_join(update, context):
        return

    await update.message.reply_text(
        "🎉 Earn Stars Easily!\n\nInvite=2⭐\nDaily=0.5⭐\nWithdraw=20⭐",
        reply_markup=ReplyKeyboardMarkup([
            ["📊 Statistics", "💸 Withdraw"],
            ["👥 Referral", "💰 Balance"],
            ["💼 Set Wallet", "📋 Tasks"],
            ["🎁 Bonus", "📜 Terms"]
        ], resize_keyboard=True)
    )

# ================= TASKS =================
async def tasks(update, context):
    cursor.execute("SELECT username FROM task_channels")
    channels = cursor.fetchall()

    buttons = []
    for ch in channels:
        ch = ch[0]
        buttons.append([InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{ch.replace('@','')}")])

    buttons.append([InlineKeyboardButton("✅ Check Tasks", callback_data="check_tasks")])

    await update.message.reply_text("📋 Complete tasks:", reply_markup=InlineKeyboardMarkup(buttons))

async def check_tasks(update, context):
    query = update.callback_query
    await query.answer()

    uid = query.from_user.id
    cursor.execute("SELECT username FROM task_channels")
    channels = cursor.fetchall()

    ok = True
    for ch in channels:
        ch = ch[0]
        try:
            member = await context.bot.get_chat_member(ch, uid)
            if member.status not in ["member", "administrator", "creator"]:
                ok = False
        except:
            ok = False

    if ok:
        cursor.execute("UPDATE users SET balance=balance+0.3 WHERE id=%s", (uid,))
        conn.commit()
        await query.message.reply_text("🎉 +0.3⭐")
    else:
        await query.message.reply_text("❌ Join all")

# ================= CHECK JOIN =================
async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if await force_join(query, context):
        await query.message.reply_text(
            "✅ Verified!",
            reply_markup=ReplyKeyboardMarkup([
                ["📊 Statistics", "💸 Withdraw"],
                ["👥 Referral", "💰 Balance"],
                ["💼 Set Wallet", "📋 Tasks"],
                ["🎁 Bonus", "📜 Terms"]
            ], resize_keyboard=True)
        )

# ================= MESSAGE HANDLER =================
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    get_user(uid)

    if not await force_join(update, context):
        return

    if text == "📋 Tasks":
        await tasks(update, context)
    elif text == "💰 Balance":
        cursor.execute("SELECT balance FROM users WHERE id=%s", (uid,))
        bal = cursor.fetchone()[0]
        await update.message.reply_text(f"{bal} ⭐")

# ================= ADD HANDLERS =================
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(check_tasks, pattern="check_tasks"))
application.add_handler(CallbackQueryHandler(check_join, pattern="check_join"))
application.add_handler(MessageHandler(filters.TEXT & \~filters.COMMAND, handler))

# ================= FLASK APP =================
flask_app = Flask(__name__)

@flask_app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        application.update_queue.put_nowait(update)
        return "ok", 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "error", 500

@flask_app.route("/")
def home():
    return "✅ Bot is running on Railway!"

# ================= MAIN =================
if __name__ == "__main__":
    try:
        application.bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
        logger.info(f"✅ Webhook set to: {WEBHOOK_URL}/{TOKEN}")
    except Exception as e:
        logger.error(f"❌ Failed to set webhook: {e}")

    port = int(os.environ.get("PORT", 8000))
    flask_app.run(host="0.0.0.0", port=port)
