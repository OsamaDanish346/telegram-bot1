import sqlite3
import datetime
import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ================= CONFIG =================
TOKEN = "8778331918:AAE5uzWflufC_AkLDz62m4A80BsbIZoZtvI"
ADMIN_ID = 8289491009
BOT_USERNAME = "Afghan_Reward_bot"

CHANNELS = ["@afghan_reward", "@khanda_koor", "@nice_image1"]

# ================= LOGGING =================
logging.basicConfig(level=logging.INFO)

# ================= DB =================
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

# ================= KEYBOARDS =================
def main_kb():
    return ReplyKeyboardMarkup([
        ["📊 حالت"],
        ["💰 پیسی زیاتول", "🎁 بونس"],
        ["👥 دعوت"],
        ["📞 نمبر داخلول", "💸 ویډرا"],
        ["ℹ️ د ربات په اړه"]
    ], resize_keyboard=True)

def earn_kb():
    return ReplyKeyboardMarkup([
        ["🎯 ټاسکونه"],
        ["👥 دعوت"],
        ["🎁 بونس"],
        ["🔙 بیرته"]
    ], resize_keyboard=True)

def bonus_kb():
    return ReplyKeyboardMarkup([
        ["📅 ډیلی بونس"],
        ["📆 ویکلی بونس"],
        ["🔙 بیرته"]
    ], resize_keyboard=True)

# ================= SAFE DB =================
def get_user(uid):
    cursor.execute("SELECT * FROM users WHERE id=?", (uid,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users(id) VALUES(?)", (uid,))
        conn.commit()
        return (uid, 0, None, None, None)
    return row

# ================= FORCE JOIN =================
async def check_join(update, context):
    try:
        if not CHANNELS:
            return True

        uid = update.effective_user.id
        for ch in CHANNELS:
            member = await context.bot.get_chat_member(ch, uid)
            if member.status not in ["member", "administrator", "creator"]:
                link = await context.bot.create_chat_invite_link(ch)
                await update.message.reply_text(
                    f"⚠️ چینل جوائن کړه:\n{link.invite_link}",
                    reply_markup=main_kb()
                )
                return False
        return True

    except Exception as e:
        logging.error(f"JOIN ERROR: {e}")
        return True

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    get_user(uid)

    if not await check_join(update, context):
        return

    await update.message.reply_text("✨ ښه راغلاست", reply_markup=main_kb())

# ================= STATUS =================
async def status(update, context):
    uid = update.effective_user.id
    user = get_user(uid)
    balance = user[1]

    await update.message.reply_text(
        f"💰 بیلانس: {balance:.1f} AFN",
        reply_markup=main_kb()
    )

# ================= BONUS =================
async def daily(update, context):
    uid = update.effective_user.id
    user = get_user(uid)

    today = datetime.datetime.now().strftime("%Y-%m-%d")

    if user[3] == today:
        await update.message.reply_text("❌ نن اخیستی", reply_markup=bonus_kb())
        return

    new_balance = user[1] + 0.5
    cursor.execute("UPDATE users SET balance=?, last_daily_bonus=? WHERE id=?",
                   (new_balance, today, uid))
    conn.commit()

    await update.message.reply_text("✅ +0.5 AFN", reply_markup=bonus_kb())

async def weekly(update, context):
    uid = update.effective_user.id
    user = get_user(uid)

    now = datetime.datetime.now()

    if user[4]:
        last = datetime.datetime.strptime(user[4], "%Y-%m-%d")
        if (now - last).days < 7:
            await update.message.reply_text("❌ لا وخت نشته", reply_markup=bonus_kb())
            return

    new_balance = user[1] + 5
    cursor.execute("UPDATE users SET balance=?, last_weekly_bonus=? WHERE id=?",
                   (new_balance, now.strftime("%Y-%m-%d"), uid))
    conn.commit()

    await update.message.reply_text("🎉 +5 AFN", reply_markup=bonus_kb())

# ================= REF =================
async def referral(update, context):
    uid = update.effective_user.id
    link = f"https://t.me/{BOT_USERNAME}?start={uid}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 کاپي", url=link)]
    ])

    await update.message.reply_text(link, reply_markup=keyboard)

# ================= PHONE =================
async def save_phone(update, context, text):
    uid = update.effective_user.id

    if not text.isdigit() or len(text) != 10:
        await update.message.reply_text("❌ 10 رقمي نمبر", reply_markup=main_kb())
        return

    cursor.execute("UPDATE users SET phone=? WHERE id=?", (text, uid))
    conn.commit()

    await update.message.reply_text("✅ ثبت شو", reply_markup=main_kb())

# ================= WITHDRAW =================
async def withdraw(update, context):
    uid = update.effective_user.id
    user = get_user(uid)

    balance = user[1]
    phone = user[2]

    if not phone:
        await update.message.reply_text("📞 نمبر نشته", reply_markup=main_kb())
        return

    if balance < 50:
        await update.message.reply_text("❌ لږ تر لږه 50", reply_markup=main_kb())
        return

    context.user_data["withdraw"] = True
    await update.message.reply_text("💸 مقدار ولیکه:", reply_markup=main_kb())

# ================= HANDLER =================
async def handler(update, context):
    try:
        text = update.message.text
        uid = update.effective_user.id

        logging.info(f"USER {uid}: {text}")

        if not await check_join(update, context):
            return

        # withdraw input
        if context.user_data.get("withdraw"):
            if text.replace('.', '', 1).isdigit():
                amount = float(text)
                user = get_user(uid)

                if amount < 50 or amount > user[1]:
                    await update.message.reply_text("❌ غلط مقدار", reply_markup=main_kb())
                else:
                    cursor.execute("INSERT INTO withdrawals(user_id,amount,phone,date) VALUES(?,?,?,?)",
                                   (uid, amount, user[2], str(datetime.datetime.now())))
                    cursor.execute("UPDATE users SET balance=balance-? WHERE id=?", (amount, uid))
                    conn.commit()

                    await update.message.reply_text("✅ وشو", reply_markup=main_kb())

            context.user_data["withdraw"] = False
            return

        # buttons
        if text == "📊 حالت":
            await status(update, context)

        elif text == "💰 پیسی زیاتول":
            await update.message.reply_text("👇 انتخاب کړه", reply_markup=earn_kb())

        elif text == "🎁 بونس":
            await update.message.reply_text("👇 انتخاب کړه", reply_markup=bonus_kb())

        elif text == "📅 ډیلی بونس":
            await daily(update, context)

        elif text == "📆 ویکلی بونس":
            await weekly(update, context)

        elif text == "👥 دعوت":
            await referral(update, context)

        elif text == "📞 نمبر داخلول":
            await update.message.reply_text("📱 نمبر ولیکه:", reply_markup=main_kb())

        elif text == "💸 ویډرا":
            await withdraw(update, context)

        elif text == "🔙 بیرته":
            await update.message.reply_text("اصلي مینو", reply_markup=main_kb())

        elif text == "ℹ️ د ربات په اړه":
            await update.message.reply_text("Reward Bot", reply_markup=main_kb())

        elif text.isdigit():
            await save_phone(update, context, text)

        else:
            await update.message.reply_text("❓ نا معلوم", reply_markup=main_kb())

    except Exception as e:
        logging.error(f"MAIN ERROR: {e}")
        await update.message.reply_text("⚠️ error شو", reply_markup=main_kb())

# ================= RUN =================
if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))

    print("✅ BOT RUNNING...")
    app.run_polling()
