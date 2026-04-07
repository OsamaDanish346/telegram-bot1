import sqlite3
import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8778331918:AAE5uzWflufC_AkLDz62m4A80BsbIZoZtvI"
ADMIN_ID = 8289491009
BOT_USERNAME = "Afghan_Reward_bot"

CHANNELS = ["@afghan_reward"]

# ================= DATABASE =================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, phone TEXT, last_daily TEXT, last_weekly TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS withdrawals(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, phone TEXT, status TEXT, date TEXT)")
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

def admin_kb():
    return ReplyKeyboardMarkup([
        ["👥 یوزران", "📊 احصایه"],
        ["📢 برودکاست", "💰 ریوارد کنټرول"],
        ["📣 آټو پوسټ", "💸 ویډرا درخواستونه"],
        ["⚙️ سیټینګ", "🔙 بیرته"]
    ], resize_keyboard=True)

# ================= FORCE JOIN =================
async def force_join(update, context):
    if not CHANNELS:
        return True
    uid = update.effective_user.id
    for ch in CHANNELS:
        try:
            member = await context.bot.get_chat_member(ch, uid)
            if member.status not in ["member", "administrator", "creator"]:
                link = await context.bot.create_chat_invite_link(ch)
                await update.message.reply_text(f"⚠️ چینل ته جواین شه:\n{link.invite_link}")
                return False
        except:
            return False
    return True

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cursor.execute("INSERT OR IGNORE INTO users(id) VALUES(?)", (user.id,))
    conn.commit()

    if not await force_join(update, context):
        return

    await update.message.reply_text("✨ ښه راغلاست!", reply_markup=main_kb())

# ================= ADMIN =================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ ته اډمین نه یې")
        return
    await update.message.reply_text("⚙️ Admin Panel", reply_markup=admin_kb())

# ================= HANDLER =================
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id

    if uid != ADMIN_ID:
        if not await force_join(update, context):
            return

    # ===== ADMIN PART =====
    if uid == ADMIN_ID:
        if text == "👥 یوزران":
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            await update.message.reply_text(f"👥 ټول یوزران: {count}", reply_markup=admin_kb())

        elif text == "📊 احصایه":
            cursor.execute("SELECT SUM(balance) FROM users")
            total = cursor.fetchone()[0] or 0
            await update.message.reply_text(f"💰 ټول بیلانس: {total}", reply_markup=admin_kb())

        elif text == "📢 برودکاست":
            context.user_data["broadcast"] = True
            await update.message.reply_text("✉️ پیغام ولیکه:", reply_markup=admin_kb())

        elif context.user_data.get("broadcast"):
            cursor.execute("SELECT id FROM users")
            users = cursor.fetchall()
            for u in users:
                try:
                    await context.bot.send_message(u[0], text)
                except:
                    pass
            context.user_data["broadcast"] = False
            await update.message.reply_text("✅ واستول شو", reply_markup=admin_kb())

        elif text == "💸 ویډرا درخواستونه":
            cursor.execute("SELECT * FROM withdrawals WHERE status='pending'")
            data = cursor.fetchall()
            msg = "📋 درخواستونه:\n"
            for d in data:
                msg += f"\nID:{d[0]} | {d[2]} AFN"
            await update.message.reply_text(msg, reply_markup=admin_kb())

        elif text == "🔙 بیرته":
            await update.message.reply_text("اصلي مینو", reply_markup=main_kb())
            return

    # ===== USER PART =====
    if text == "📊 حالت":
        cursor.execute("SELECT balance FROM users WHERE id=?", (uid,))
        bal = cursor.fetchone()[0]
        await update.message.reply_text(f"💰 بیلانس: {bal}", reply_markup=main_kb())

    elif text == "🎁 بونس":
        today = datetime.date.today().isoformat()
        cursor.execute("SELECT last_daily FROM users WHERE id=?", (uid,))
        last = cursor.fetchone()[0]
        if last == today:
            await update.message.reply_text("❌ اخیستی دی", reply_markup=main_kb())
        else:
            cursor.execute("UPDATE users SET balance=balance+1,last_daily=? WHERE id=?", (today, uid))
            conn.commit()
            await update.message.reply_text("✅ +1 AFN", reply_markup=main_kb())

    elif text == "👥 دعوت":
        link = f"https://t.me/{BOT_USERNAME}?start={uid}"
        await update.message.reply_text(link, reply_markup=main_kb())

    elif text == "📞 نمبر داخلول":
        context.user_data["phone"] = True
        await update.message.reply_text("📱 نمبر ولیکه:", reply_markup=main_kb())

    elif context.user_data.get("phone"):
        if text.isdigit():
            cursor.execute("UPDATE users SET phone=? WHERE id=?", (text, uid))
            conn.commit()
            context.user_data["phone"] = False
            await update.message.reply_text("✅ ثبت شو", reply_markup=main_kb())
        else:
            await update.message.reply_text("❌ غلط نمبر", reply_markup=main_kb())

    elif text == "💸 ویډرا":
        context.user_data["withdraw"] = True
        await update.message.reply_text("💸 مقدار ولیکه:", reply_markup=main_kb())

    elif context.user_data.get("withdraw"):
        if text.replace('.', '', 1).isdigit():
            amount = float(text)
            cursor.execute("SELECT balance,phone FROM users WHERE id=?", (uid,))
            bal, phone = cursor.fetchone()
            if amount <= bal:
                cursor.execute("INSERT INTO withdrawals(user_id,amount,phone,status,date) VALUES(?,?,?,?,?)",
                               (uid, amount, phone, "pending", str(datetime.datetime.now())))
                cursor.execute("UPDATE users SET balance=balance-? WHERE id=?", (amount, uid))
                conn.commit()
                context.user_data["withdraw"] = False
                await update.message.reply_text("✅ درخواست ثبت شو", reply_markup=main_kb())
            else:
                await update.message.reply_text("❌ بیلانس کم دی", reply_markup=main_kb())

    elif text == "🔙 بیرته":
        await update.message.reply_text("اصلي مینو", reply_markup=main_kb())

# ================= RUN =================
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin_panel))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))

print("BOT RUNNING...")
app.run_polling()
