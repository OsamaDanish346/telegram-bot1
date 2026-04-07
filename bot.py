import sqlite3
import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8778331918:AAE5uzWflufC_AkLDz62m4A80BsbIZoZtvI"
ADMIN_ID = 8289491009

CHANNELS = ["@afghan_reward", "@khanda_koor", "@nice_image1"]

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

# ================= KEYBOARD =================
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

# ================= FORCE JOIN =================
async def check_join(update, context):
    if not CHANNELS:
        return True

    uid = update.effective_user.id
    for ch in CHANNELS:
        try:
            member = await context.bot.get_chat_member(ch, uid)
            if member.status not in ["member", "administrator", "creator"]:
                link = await context.bot.create_chat_invite_link(ch)
                await update.message.reply_text(f"⚠️ چینل جوائن کړه:\n{link.invite_link}", reply_markup=main_kb())
                return False
        except:
            return True
    return True

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    cursor.execute("INSERT OR IGNORE INTO users(id) VALUES(?)", (uid,))
    conn.commit()

    if not await check_join(update, context):
        return

    await update.message.reply_text("✨ ښه راغلاست", reply_markup=main_kb())

# ================= STATUS =================
async def status(update, context):
    uid = update.effective_user.id
    cursor.execute("SELECT balance FROM users WHERE id=?", (uid,))
    bal = (cursor.fetchone() or [0])[0]

    await update.message.reply_text(f"💰 بیلانس: {bal:.1f} AFN", reply_markup=main_kb())

# ================= BONUS =================
async def daily(update, context):
    uid = update.effective_user.id
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    cursor.execute("SELECT balance,last_daily_bonus FROM users WHERE id=?", (uid,))
    bal, last = cursor.fetchone() or (0, None)

    if last == today:
        await update.message.reply_text("❌ نن اخیستی", reply_markup=bonus_kb())
        return

    cursor.execute("UPDATE users SET balance=?, last_daily_bonus=? WHERE id=?",
                   (bal+0.5, today, uid))
    conn.commit()

    await update.message.reply_text("✅ +0.5 AFN", reply_markup=bonus_kb())

async def weekly(update, context):
    uid = update.effective_user.id
    now = datetime.datetime.now()

    cursor.execute("SELECT balance,last_weekly_bonus FROM users WHERE id=?", (uid,))
    bal, last = cursor.fetchone() or (0, None)

    if last:
        if (now - datetime.datetime.strptime(last, "%Y-%m-%d")).days < 7:
            await update.message.reply_text("❌ لا وخت نشته", reply_markup=bonus_kb())
            return

    cursor.execute("UPDATE users SET balance=?, last_weekly_bonus=? WHERE id=?",
                   (bal+5, now.strftime("%Y-%m-%d"), uid))
    conn.commit()

    await update.message.reply_text("🎉 +5 AFN", reply_markup=bonus_kb())

# ================= REF =================
async def ref(update, context):
    uid = update.effective_user.id
    link = f"https://t.me/Afghan_Reward_bot?start={uid}"

    await update.message.reply_text(f"🔗 {link}", reply_markup=main_kb())

# ================= PHONE =================
async def save_phone(update, context, text):
    uid = update.effective_user.id

    if len(text) != 10:
        await update.message.reply_text("❌ 10 رقمي نمبر", reply_markup=main_kb())
        return

    cursor.execute("UPDATE users SET phone=? WHERE id=?", (text, uid))
    conn.commit()

    await update.message.reply_text("✅ ثبت شو", reply_markup=main_kb())

# ================= WITHDRAW =================
async def withdraw(update, context):
    uid = update.effective_user.id

    cursor.execute("SELECT balance,phone FROM users WHERE id=?", (uid,))
    bal, phone = cursor.fetchone() or (0, None)

    if not phone:
        await update.message.reply_text("📞 نمبر نشته", reply_markup=main_kb())
        return

    if bal < 50:
        await update.message.reply_text("❌ لږ تر لږه 50", reply_markup=main_kb())
        return

    context.user_data["w"] = True
    await update.message.reply_text("💸 مقدار ولیکه:", reply_markup=main_kb())

# ================= MAIN HANDLER =================
async def handler(update, context):
    text = update.message.text
    uid = update.effective_user.id

    if not await check_join(update, context):
        return

    # withdraw input
    if context.user_data.get("w"):
        if text.replace('.', '', 1).isdigit():
            amount = float(text)

            cursor.execute("SELECT balance,phone FROM users WHERE id=?", (uid,))
            bal, phone = cursor.fetchone()

            if amount < 50 or amount > bal:
                await update.message.reply_text("❌ غلط مقدار", reply_markup=main_kb())
            else:
                cursor.execute("INSERT INTO withdrawals(user_id,amount,phone,date) VALUES(?,?,?,?)",
                               (uid, amount, phone, str(datetime.datetime.now())))
                cursor.execute("UPDATE users SET balance=balance-? WHERE id=?", (amount, uid))
                conn.commit()

                await update.message.reply_text("✅ وشو", reply_markup=main_kb())

        context.user_data["w"] = False
        return

    # buttons
    if text == "📊 حالت":
        await status(update, context)

    elif text == "💰 پیسی زیاتول":
        await update.message.reply_text("👇", reply_markup=earn_kb())

    elif text == "🎁 بونس":
        await update.message.reply_text("👇", reply_markup=bonus_kb())

    elif text == "📅 ډیلی بونس":
        await daily(update, context)

    elif text == "📆 ویکلی بونس":
        await weekly(update, context)

    elif text == "👥 دعوت":
        await ref(update, context)

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

# ================= RUN =================
if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))

    print("RUNNING...")
    app.run_polling()
