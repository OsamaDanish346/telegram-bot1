import sqlite3
import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8778331918:AAE5uzWflufC_AkLDz62m4A80BsbIZoZtvI"
ADMIN_ID = 8289491009

CHANNELS = ["@afghan_reward", "@khanda_koor", "@nice_image1"]

conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

# ================= DATABASE =================
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

# ================= FORCE JOIN =================
async def check_force_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not CHANNELS:
        return True

    user_id = update.effective_user.id
    for ch in CHANNELS:
        try:
            member = await context.bot.get_chat_member(ch, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                link = await context.bot.create_chat_invite_link(ch)
                await update.message.reply_text(f"⚠️ لومړی چینل جوائن کړئ:\n{link.invite_link}")
                return False
        except Exception as e:
            print("Force join error:", e)
            return True

    return True

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    cursor.execute("INSERT OR IGNORE INTO users(id) VALUES(?)", (user.id,))
    conn.commit()

    if not await check_force_join(update, context):
        return

    await update.message.reply_text(
        "✨ ښه راغلاست!",
        reply_markup=main_keyboard()
    )

# ================= STATUS =================
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    cursor.execute("SELECT balance FROM users WHERE id=?", (user.id,))
    balance = (cursor.fetchone() or [0])[0]

    text = f"""👤 {user.first_name}

🆔 {user.id}
💰 {balance:.1f} AFN
"""
    await update.message.reply_text(text, reply_markup=main_keyboard())

# ================= BONUS =================
async def daily_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    cursor.execute("SELECT balance, last_daily_bonus FROM users WHERE id=?", (uid,))
    row = cursor.fetchone() or [0, None]

    if row[1] == today:
        await update.message.reply_text("❌ نن مو اخیستی", reply_markup=bonus_keyboard())
        return

    new_balance = row[0] + 0.5
    cursor.execute("UPDATE users SET balance=?, last_daily_bonus=? WHERE id=?",
                   (new_balance, today, uid))
    conn.commit()

    await update.message.reply_text("✅ +0.5 AFN", reply_markup=bonus_keyboard())

async def weekly_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    now = datetime.datetime.now()

    cursor.execute("SELECT balance, last_weekly_bonus FROM users WHERE id=?", (uid,))
    row = cursor.fetchone() or [0, None]

    if row[1]:
        last = datetime.datetime.strptime(row[1], "%Y-%m-%d")
        if (now - last).days < 7:
            await update.message.reply_text("❌ لا وخت نه دی", reply_markup=bonus_keyboard())
            return

    new_balance = row[0] + 5
    today = now.strftime("%Y-%m-%d")

    cursor.execute("UPDATE users SET balance=?, last_weekly_bonus=? WHERE id=?",
                   (new_balance, today, uid))
    conn.commit()

    await update.message.reply_text("🎉 +5 AFN", reply_markup=bonus_keyboard())

# ================= REFERRAL =================
async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    bot_username = "Afghan_Reward_bot"

    link = f"https://t.me/{bot_username}?start={uid}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 لینک کاپي کړئ", url=link)]
    ])

    await update.message.reply_text(
        f"🔗 ستاسو لینک:\n{link}",
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

# ================= PHONE =================
async def save_phone(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    uid = update.effective_user.id

    if not text.isdigit() or len(text) != 10:
        await update.message.reply_text("❌ 10 رقمي نمبر ولیکه", reply_markup=main_keyboard())
        return

    cursor.execute("UPDATE users SET phone=? WHERE id=?", (text, uid))
    conn.commit()

    await update.message.reply_text("✅ ثبت شو", reply_markup=main_keyboard())

# ================= WITHDRAW =================
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    cursor.execute("SELECT balance, phone FROM users WHERE id=?", (uid,))
    row = cursor.fetchone() or (0, None)

    if not row[1]:
        await update.message.reply_text("📞 لومړی نمبر ورکړه", reply_markup=main_keyboard())
        return

    if row[0] < 50:
        await update.message.reply_text("❌ لږ تر لږه 50 AFN", reply_markup=main_keyboard())
        return

    context.user_data["withdraw"] = True
    await update.message.reply_text("💸 مقدار ولیکه:")

# ================= MESSAGE HANDLER =================
async def msg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id

    if not await check_force_join(update, context):
        return

    if context.user_data.get("withdraw"):
        if text.replace('.', '', 1).isdigit():
            amount = float(text)

            cursor.execute("SELECT balance, phone FROM users WHERE id=?", (uid,))
            balance, phone = cursor.fetchone()

            if amount < 50 or amount > balance:
                await update.message.reply_text("❌ غلط مقدار")
            else:
                cursor.execute("INSERT INTO withdrawals(user_id, amount, phone, date) VALUES(?,?,?,?)",
                               (uid, amount, phone, str(datetime.datetime.now())))
                cursor.execute("UPDATE users SET balance=balance-? WHERE id=?", (amount, uid))
                conn.commit()

                await update.message.reply_text("✅ ویډرا ثبت شو", reply_markup=main_keyboard())

        context.user_data["withdraw"] = False
        return

    if text == "📊 حالت":
        await status(update, context)

    elif text == "💰 پیسی زیاتول":
        await update.message.reply_text("انتخاب:", reply_markup=earn_keyboard())

    elif text == "🎁 بونس":
        await update.message.reply_text("انتخاب:", reply_markup=bonus_keyboard())

    elif text == "📅 ډیلی بونس":
        await daily_bonus(update, context)

    elif text == "📆 ویکلی بونس":
        await weekly_bonus(update, context)

    elif text == "👥 دعوت":
        await referral(update, context)

    elif text == "📞 نمبر داخلول":
        await update.message.reply_text("📱 خپل 10 رقمي نمبر ولیکه:")

    elif text == "💸 ویډرا":
        await withdraw(update, context)

    elif text == "🔙 بیرته":
        await update.message.reply_text("اصلي مینو", reply_markup=main_keyboard())

    elif text == "ℹ️ د ربات په اړه":
        await update.message.reply_text("دا ریوارډ بوټ دی", reply_markup=main_keyboard())

    elif text.isdigit():
        await save_phone(update, context, text)

# ================= RUN =================
if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_handler))

    print("✅ RUNNING...")
    app.run_polling()
