import sqlite3
import datetime
from telegram import *
from telegram.ext import *

TOKEN = "8778331918:AAE5uzWflufC_AkLDz62m4A80BsbIZoZtvI"
ADMIN_ID = 8289491009
BOT_USERNAME = "Afghan_Reward_bot"

# ================= DATABASE =================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY,
balance REAL DEFAULT 0,
phone TEXT,
last_daily TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS withdrawals(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
amount REAL,
phone TEXT,
status TEXT,
date TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS channels(
id INTEGER PRIMARY KEY AUTOINCREMENT,
username TEXT
)
""")

conn.commit()

# ================= KEYBOARDS =================
def main_kb():
    return ReplyKeyboardMarkup([
        ["📊 حالت"],
        ["💰 پیسی زیاتول", "🎁 بونس"],
        ["👥 دعوت"],
        ["📞 نمبر داخلول", "💸 ویډرا"]
    ], resize_keyboard=True)

def admin_kb():
    return ReplyKeyboardMarkup([
        ["👥 یوزران", "📊 احصایه"],
        ["📢 برودکاست", "💸 ویډرا درخواستونه"],
        ["➕ چینل اضافه", "➖ چینل حذف"],
        ["🔙 بیرته"]
    ], resize_keyboard=True)

# ================= SAFE USER =================
def get_user(uid):
    cursor.execute("SELECT * FROM users WHERE id=?", (uid,))
    user = cursor.fetchone()
    if not user:
        cursor.execute("INSERT INTO users(id) VALUES(?)", (uid,))
        conn.commit()
        return (uid, 0, None, None)
    return user

# ================= FORCE JOIN =================
async def force_join(update, context):
    cursor.execute("SELECT username FROM channels")
    channels = cursor.fetchall()

    if not channels:
        return True

    uid = update.effective_user.id
    buttons = []
    not_joined = False

    for ch in channels:
        ch = ch[0]
        try:
            member = await context.bot.get_chat_member(ch, uid)
            if member.status not in ["member", "administrator", "creator"]:
                not_joined = True
                link = f"https://t.me/{ch.replace('@','')}"
                buttons.append([InlineKeyboardButton(f"📢 {ch}", url=link)])
        except:
            not_joined = True

    if not_joined:
        buttons.append([InlineKeyboardButton("✅ چک کول", callback_data="check_join")])
        await update.message.reply_text(
            "⚠️ مهرباني وکړئ ټولو چینلونو ته جواین شئ:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return False

    return True

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    get_user(uid)

    if not await force_join(update, context):
        return

    await update.message.reply_text("✨ ښه راغلاست", reply_markup=main_kb())

# ================= CHECK JOIN =================
async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if await force_join(query, context):
        await query.message.reply_text("✅ تایید شو!", reply_markup=main_kb())

# ================= ADMIN =================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("❌ ته اډمین نه یې")

    await update.message.reply_text("⚙️ Admin Panel", reply_markup=admin_kb())

# ================= HANDLER =================
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id

    get_user(uid)

    if uid != ADMIN_ID:
        if not await force_join(update, context):
            return

    # ===== ADMIN =====
    if uid == ADMIN_ID:

        if text == "👥 یوزران":
            count = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0] or 0
            await update.message.reply_text(f"👥 ټول یوزران: {count}", reply_markup=admin_kb())

        elif text == "📊 احصایه":
            total = cursor.execute("SELECT SUM(balance) FROM users").fetchone()[0] or 0
            await update.message.reply_text(f"💰 ټول بیلانس: {total}", reply_markup=admin_kb())

        elif text == "📢 برودکاست":
            context.user_data["broadcast"] = True
            await update.message.reply_text("✉️ پیغام ولیکه:")

        elif context.user_data.get("broadcast"):
            users = cursor.execute("SELECT id FROM users").fetchall()
            for u in users:
                try:
                    await context.bot.send_message(u[0], text)
                except:
                    pass
            context.user_data["broadcast"] = False
            await update.message.reply_text("✅ واستول شو", reply_markup=admin_kb())

        elif text == "💸 ویډرا درخواستونه":
            data = cursor.execute("SELECT * FROM withdrawals").fetchall()
            msg = "\n".join([f"{d[0]} | {d[2]} AFN | {d[4]}" for d in data]) or "هیڅ نشته"
            await update.message.reply_text(msg, reply_markup=admin_kb())

        elif text == "➕ چینل اضافه":
            context.user_data["add_channel"] = True
            await update.message.reply_text("📢 یوزرنیم ولیکه: @channel")

        elif context.user_data.get("add_channel"):
            if text.startswith("@"):
                cursor.execute("INSERT INTO channels(username) VALUES(?)", (text,))
                conn.commit()
                context.user_data["add_channel"] = False
                await update.message.reply_text("✅ اضافه شو", reply_markup=admin_kb())
            else:
                await update.message.reply_text("❌ غلط یوزرنیم")

        elif text == "➖ چینل حذف":
            context.user_data["del_channel"] = True
            await update.message.reply_text("❌ کوم چینل حذف کوې؟")

        elif context.user_data.get("del_channel"):
            cursor.execute("DELETE FROM channels WHERE username=?", (text,))
            conn.commit()
            context.user_data["del_channel"] = False
            await update.message.reply_text("✅ حذف شو", reply_markup=admin_kb())

        elif text == "🔙 بیرته":
            await update.message.reply_text("اصلي مینو", reply_markup=main_kb())

    # ===== USER =====
    if text == "📊 حالت":
        bal = cursor.execute("SELECT balance FROM users WHERE id=?", (uid,)).fetchone()[0] or 0
        await update.message.reply_text(f"💰 {bal} AFN", reply_markup=main_kb())

    elif text == "🎁 بونس":
        today = datetime.date.today().isoformat()
        last = cursor.execute("SELECT last_daily FROM users WHERE id=?", (uid,)).fetchone()[0]

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
        await update.message.reply_text("📱 نمبر ولیکه:")

    elif context.user_data.get("phone"):
        if text.isdigit():
            cursor.execute("UPDATE users SET phone=? WHERE id=?", (text, uid))
            conn.commit()
            context.user_data["phone"] = False
            await update.message.reply_text("✅ ثبت شو", reply_markup=main_kb())
        else:
            await update.message.reply_text("❌ غلط نمبر")

    elif text == "💸 ویډرا":
        context.user_data["withdraw"] = True
        await update.message.reply_text("💸 مقدار ولیکه:")

    elif context.user_data.get("withdraw"):
        if text.replace('.', '', 1).isdigit():
            amount = float(text)
            bal, phone = cursor.execute("SELECT balance,phone FROM users WHERE id=?", (uid,)).fetchone()

            if amount <= bal:
                cursor.execute("INSERT INTO withdrawals(user_id,amount,phone,status,date) VALUES(?,?,?,?,?)",
                               (uid, amount, phone, "pending", str(datetime.datetime.now())))
                cursor.execute("UPDATE users SET balance=balance-? WHERE id=?", (amount, uid))
                conn.commit()
                context.user_data["withdraw"] = False
                await update.message.reply_text("✅ درخواست ثبت شو", reply_markup=main_kb())
            else:
                await update.message.reply_text("❌ بیلانس کم دی")

# ================= RUN =================
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin_panel))
app.add_handler(CallbackQueryHandler(check_join, pattern="check_join"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))

print("✅ BOT RUNNING...")
app.run_polling()
