import sqlite3
import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8778331918:AAE5uzWflufC_AkLDz62m4A80BsbIZoZtvI"   # ✅ space لرې شو
ADMIN_ID = 8289491009

CHANNELS = ["@afghan_reward", "@khanda_koor", "@nice_image1"]

conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY,
    balance REAL DEFAULT 0.0,
    phone TEXT,
    last_daily_bonus TEXT,
    last_weekly_bonus TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS withdrawals(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    phone TEXT,
    status TEXT DEFAULT 'pending',
    date TEXT
)
""")
conn.commit()

# ==================== KEYBOARDS ====================
def main_keyboard():
    return ReplyKeyboardMarkup([
        ["📊 حالت"],
        ["💰 پیسی زیاتول", "🎁 بونس"],
        ["👥 دعوت"],
        ["📞 نمبر داخلول", "💸 ویډرا"],
        ["ℹ️ د ربات په اړه"]
    ], resize_keyboard=True)

def earn_keyboard():
    return ReplyKeyboardMarkup([
        ["🎯 ټاسکونه"],
        ["👥 دعوت"],
        ["🎁 بونس"],
        ["🔙 بیرته"]
    ], resize_keyboard=True)

def bonus_keyboard():
    return ReplyKeyboardMarkup([
        ["📅 ډیلی بونس"],
        ["📆 ویکلی بونس"],
        ["🔙 بیرته"]
    ], resize_keyboard=True)

def admin_keyboard():
    return ReplyKeyboardMarkup([
        ["👥 یوزران", "📊 احصایه"],
        ["📢 برودکاست", "💰 ریوارد کنټرول"],
        ["📣 آټو پوسټ", "💸 ویډرا درخواستونه"],
        ["⚙️ سیټینګ", "🔙 بیرته"]
    ], resize_keyboard=True)

# ==================== FORCE JOIN ====================
async def check_force_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not CHANNELS:
        return True
    user_id = update.effective_user.id
    for ch in CHANNELS:
        try:
            member = await context.bot.get_chat_member(ch, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                link = await context.bot.create_chat_invite_link(ch)
                await update.message.reply_text(f"⚠️ لومړی دا چینل ته جوائن شئ:\n{link.invite_link}")
                return False
        except:
            pass
    return True

# ==================== ټاسکونه ====================
async def tasks_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not CHANNELS:
        await update.message.reply_text("⚠️ فعال ټاسکونه شتون نه لري.\nاډمین ته ووایاست چې چینلونه اضافه کړي.")
        return

    user_id = update.effective_user.id
    joined_all = True

    for ch in CHANNELS:
        try:
            member = await context.bot.get_chat_member(ch, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                joined_all = False
        except:
            joined_all = False

    if joined_all:
        cursor.execute("SELECT balance FROM users WHERE id=?", (user_id,))
        balance = (cursor.fetchone() or [0])[0]
        new_balance = balance + 1.0
        cursor.execute("UPDATE users SET balance=? WHERE id=?", (new_balance, user_id))
        conn.commit()
        await update.message.reply_text("✅ تاسو بریالۍ توګه ټول ټاسکونه پوره کړل دي!\n+۱ افغانۍ اضافه شوه.")
    else:
        await update.message.reply_text("⚠️ ټولو چینلونو ته لا نه یاست جوائن.")

# ==================== START ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cursor.execute("INSERT OR IGNORE INTO users(id) VALUES(?)", (user.id,))
    conn.commit()

    if not await check_force_join(update, context):
        return

    await update.message.reply_text("✨ ښه راغلاست!", reply_markup=main_keyboard())

# ==================== STATUS ====================
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cursor.execute("SELECT balance FROM users WHERE id=?", (user.id,))
    balance = (cursor.fetchone() or [0])[0]

    text = f"""🤵🏻‍♂️ استعمالوونکی = {user.first_name}

💳 ایډي کارن : {user.id}
💵 ستاسو پيسو اندازه = {balance:.1f} AFN
"""
    await update.message.reply_text(text)

# ==================== دعوت ====================
async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bot_username = "AfghanRewardBot"   # ✅ بدل شو

    link = f"https://t.me/{bot_username}?start={user_id}"

    await update.message.reply_text(f"🔗 ستاسو لینک:\n{link}")

# ==================== MESSAGE ====================
async def msg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "📊 حالت":
        await status(update, context)

    elif text == "👥 دعوت":
        await referral(update, context)

# ==================== RUN ====================
if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    # ✅ مهم اصلاح دلته دی
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_handler))

    print("Bot Running...")
    app.run_polling()
