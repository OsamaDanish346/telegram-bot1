import sqlite3
from telegram import *
from telegram.ext import *

TOKEN = "8778331918:AAE5uzWflufC_AkLDz62m4A80BsbIZoZtvI"
ADMIN_ID = 8289491009

conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY,
balance INTEGER DEFAULT 0,
phone TEXT
)
""")
conn.commit()


# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    cursor.execute("INSERT OR IGNORE INTO users(id) VALUES(?)", (user.id,))
    conn.commit()

    kb = [
        ["📊 حالت", "🎁 بونس"],
        ["👥 دعوت", "💰 پیسی زیاتول"],
        ["ℹ️ د ربات په اړه"]
    ]

    await update.message.reply_text("اصلي مینو", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))


# ---------------- STATUS ----------------
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    cursor.execute("SELECT balance FROM users WHERE id=?", (user.id,))
    balance = cursor.fetchone()[0]

    text = f"""
🤵🏻‍♂️استعمالوونکی = {user.first_name}

💳 ایډي کارن : {user.id}
💵ستاسو پيسو اندازه= {balance}

🔗 د بیلانس زیاتولو لپاره  [ 👫 کسان ] دعوت کړی،
بوټ ته!
"""
    await update.message.reply_text(text)


# ---------------- TASK CHECK ----------------
async def check_tasks(update, context):
    # دلته کولای شې چینل چک اضافه کړې
    return True


# ---------------- ADMIN ----------------
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("❌ تاسو اډمین نه یاست")

    kb = [
        ["👥 یوزران", "📊 احصایه"],
        ["📢 برودکاست", "💰 ریوارډ کنټرول"],
        ["➕ چینل اضافه", "⚙️ سیټینګ"],
        ["🔙 بیرته"]
    ]

    await update.message.reply_text("👑 Admin Panel", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))


# ---------------- MESSAGE HANDLER ----------------
async def msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    uid = user.id

    # ✅ ADMIN BYPASS
    if uid != ADMIN_ID:
        if not await check_tasks(update, context):
            return

    # -------- MAIN BUTTONS --------
    if text == "📊 حالت":
        await status(update, context)

    elif text == "💰 پیسی زیاتول":
        kb = [
            ["🎯 تسکونه"],
            ["👥 دعوت"],
            ["🎁 بونس"],
            ["🔙 بیرته"]
        ]
        await update.message.reply_text("انتخاب:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

    elif text == "🎯 تسکونه":
        await update.message.reply_text("✅ تاسو بریالۍ توګه ټاسک ترسره کړ")

    elif text == "🎁 بونس":
        await update.message.reply_text("🎁 بونس ترلاسه شو")

    elif text == "👥 دعوت":
        await update.message.reply_text(f"خپل لینک:\nhttps://t.me/YOUR_BOT?start={uid}")

    elif text == "ℹ️ د ربات په اړه":
        await update.message.reply_text("دا یو ریوارډ بوټ دی")

    elif text == "🔙 بیرته":
        await start(update, context)

    # -------- ADMIN BUTTONS --------
    elif text == "📊 احصایه":
        if uid == ADMIN_ID:
            cursor.execute("SELECT COUNT(*) FROM users")
            total = cursor.fetchone()[0]
            await update.message.reply_text(f"👥 ټول یوزران: {total}")

    elif text == "👥 یوزران":
        if uid == ADMIN_ID:
            await update.message.reply_text("📋 یوزر لیست")

    elif text == "📢 برودکاست":
        if uid == ADMIN_ID:
            await update.message.reply_text("📢 پیغام ولیکه")

    elif text == "💰 ریوارډ کنټرول":
        if uid == ADMIN_ID:
            await update.message.reply_text("💰 ریوارډ تنظیم")

    elif text == "➕ چینل اضافه":
        if uid == ADMIN_ID:
            await update.message.reply_text("چینل یوزرنیم ولیکه")

    elif text == "⚙️ سیټینګ":
        if uid == ADMIN_ID:
            await update.message.reply_text("سیټینګ خلاص شو")

    # -------- PHONE NUMBER --------
    elif text == "📞 نمبر داخلول":
        await update.message.reply_text("📱 خپل 10 رقمي نمبر ولیکه:")

    elif text.isdigit():
        if len(text) == 10:
            cursor.execute("UPDATE users SET phone=? WHERE id=?", (text, uid))
            conn.commit()
            await update.message.reply_text("✅ ستاسو نمبر ثبت شو")
        elif len(text) < 10:
            await update.message.reply_text("❌ نمبر کم دی (10 رقمه)")
        else:
            await update.message.reply_text("❌ نمبر زیات دی (10 رقمه)")


# ---------------- MAIN ----------------
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(MessageHandler(filters.TEXT, msg))

print("Bot Running...")
app.run_polling()
