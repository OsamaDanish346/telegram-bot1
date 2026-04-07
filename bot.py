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
last_daily TEXT,
last_weekly TEXT,
inviter INTEGER
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
        ["📞 نمبر داخلول", "💸 ویډرا"],
        ["ℹ️ د ربات په اړه"]
    ], resize_keyboard=True)

def earn_kb():
    return ReplyKeyboardMarkup([
        ["🎯 ټاسکونه"],
        ["👥 دعوت"],
        ["🎁 بونس"],
        ["📆 ویکلی بونس"],
        ["🔙 بیرته"]
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
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users(id) VALUES(?)", (uid,))
        conn.commit()

# ================= FORCE JOIN =================
async def force_join(update, context):
    try:
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
                    buttons.append([InlineKeyboardButton(f"📢 {ch}", url=f"https://t.me/{ch.replace('@','')}")])
            except:
                not_joined = True

        if not_joined:
            buttons.append([InlineKeyboardButton("✅ چک کول", callback_data="check_join")])

            if update.message:
                await update.message.reply_text(
                    "⚠️ مهرباني وکړئ ټولو چینلونو ته جواین شئ:",
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
            else:
                await update.callback_query.message.reply_text(
                    "⚠️ مهرباني وکړئ ټولو چینلونو ته جواین شئ:",
                    reply_markup=InlineKeyboardMarkup(buttons)
                )

            return False

        return True
    except:
        return True

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = update.effective_user.id
        get_user(uid)

        # INVITE SYSTEM + MESSAGE
        if context.args:
            try:
                ref = int(context.args[0])
                if ref != uid:
                    cursor.execute("SELECT inviter FROM users WHERE id=?", (uid,))
                    if cursor.fetchone()[0] is None:

                        cursor.execute("UPDATE users SET inviter=? WHERE id=?", (ref, uid))
                        cursor.execute("UPDATE users SET balance=balance+2 WHERE id=?", (ref,))
                        conn.commit()

                        # message to new user
                        await update.message.reply_text(
                            "🎉 ښه راغلاست!\n\n"
                            "👥 ته د دعوت له لارې داخل شوې!\n"
                            "💰 تاسو کولی شئ د بونس، دعوت او ټاسک له لارې پیسې وګټئ!\n\n"
                            "🚀 همدا اوس پیل کړه!"
                        )

                        # message to inviter
                        try:
                            await context.bot.send_message(
                                chat_id=ref,
                                text="🎉 مبارک!\n\n👤 یو نوی یوزر ستاسو له لینک څخه داخل شو\n💰 +2 افغانۍ اضافه شوه!"
                            )
                        except:
                            pass
            except:
                pass

        if not await force_join(update, context):
            return

        await update.message.reply_text("✨ ښه راغلاست", reply_markup=main_kb())

    except Exception as e:
        print("START ERROR:", e)

# ================= CHECK JOIN =================
async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()

        fake = Update(update.update_id, message=query.message)

        if await force_join(fake, context):
            await query.message.reply_text("✅ تایید شو!", reply_markup=main_kb())
    except:
        pass

# ================= ADMIN =================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("❌ ته اډمین نه یې")

    await update.message.reply_text("⚙️ Admin Panel", reply_markup=admin_kb())

# ================= HANDLER =================
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text
        uid = update.effective_user.id
        get_user(uid)

        if uid != ADMIN_ID:
            if not await force_join(update, context):
                return

        # ===== ADMIN =====
        if uid == ADMIN_ID:

            if text == "👥 یوزران":
                count = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
                await update.message.reply_text(f"👥 ټول یوزران: {count}", reply_markup=admin_kb())

            elif text == "📊 احصایه":
                total = cursor.execute("SELECT SUM(balance) FROM users").fetchone()[0] or 0
                await update.message.reply_text(f"💰 ټول بیلانس: {total}", reply_markup=admin_kb())

            elif text == "📢 برودکاست":
                context.user_data["bc"] = True
                await update.message.reply_text("✉️ پیغام ولیکه:")

            elif context.user_data.get("bc"):
                for u in cursor.execute("SELECT id FROM users").fetchall():
                    try:
                        await context.bot.send_message(u[0], text)
                    except:
                        pass
                context.user_data["bc"] = False
                await update.message.reply_text("✅ واستول شو", reply_markup=admin_kb())

        # ===== USER =====
        if text == "📊 حالت":
            bal = cursor.execute("SELECT balance FROM users WHERE id=?", (uid,)).fetchone()[0] or 0
            await update.message.reply_text(f"💰 ستاسو بیلانس: {bal:.1f} AFN")

        elif text == "💰 پیسی زیاتول":
            await update.message.reply_text("💰 انتخاب وکړئ:", reply_markup=earn_kb())

        elif text == "🎯 ټاسکونه":
            cursor.execute("UPDATE users SET balance=balance+1 WHERE id=?", (uid,))
            conn.commit()
            await update.message.reply_text("✅ +1 AFN اضافه شوه")

        elif text == "🎁 بونس":
            today = datetime.date.today().isoformat()
            last = cursor.execute("SELECT last_daily FROM users WHERE id=?", (uid,)).fetchone()[0]

            if last == today:
                await update.message.reply_text("❌ نن بونس اخیستی دی")
            else:
                cursor.execute("UPDATE users SET balance=balance+0.5,last_daily=? WHERE id=?", (today, uid))
                conn.commit()
                await update.message.reply_text("✅ +0.5 AFN")

        elif text == "📆 ویکلی بونس":
            now = datetime.datetime.now()
            last = cursor.execute("SELECT last_weekly FROM users WHERE id=?", (uid,)).fetchone()[0]

            if last and (now - datetime.datetime.strptime(last, "%Y-%m-%d")).days < 7:
                await update.message.reply_text("❌ ویکلی بونس لا نشته")
            else:
                cursor.execute("UPDATE users SET balance=balance+5,last_weekly=? WHERE id=?", (now.strftime("%Y-%m-%d"), uid))
                conn.commit()
                await update.message.reply_text("🎉 +5 AFN")

        elif text == "👥 دعوت":
            link = f"https://t.me/{BOT_USERNAME}?start={uid}"
            await update.message.reply_text(f"🔗 ستاسو لینک:\n{link}")

        elif text == "📞 نمبر داخلول":
            context.user_data["phone"] = True
            await update.message.reply_text("📱 خپل 10 رقمي نمبر ولیکه")

        elif context.user_data.get("phone"):
            if text.isdigit() and len(text) == 10:
                cursor.execute("UPDATE users SET phone=? WHERE id=?", (text, uid))
                conn.commit()
                context.user_data["phone"] = False
                await update.message.reply_text("✅ نمبر ثبت شو")
            else:
                await update.message.reply_text("❌ نمبر باید 10 رقمه وي")

        elif text == "💸 ویډرا":
            context.user_data["wd"] = True
            await update.message.reply_text("💸 مقدار ولیکه (min 50 AFN)")

        elif context.user_data.get("wd"):
            if text.replace('.', '', 1).isdigit():
                amount = float(text)
                bal = cursor.execute("SELECT balance FROM users WHERE id=?", (uid,)).fetchone()[0]

                if amount >= 50 and amount <= bal:
                    cursor.execute("UPDATE users SET balance=balance-? WHERE id=?", (amount, uid))
                    cursor.execute("INSERT INTO withdrawals(user_id,amount,phone,status,date) VALUES(?,?,?,?,?)",
                                   (uid, amount, "", "pending", str(datetime.datetime.now())))
                    conn.commit()
                    await update.message.reply_text("✅ ویډرا ثبت شو")
                else:
                    await update.message.reply_text("❌ مقدار ناسم دی")

        elif text == "ℹ️ د ربات په اړه":
            await update.message.reply_text(
                "🤖 Afghan Reward Bot\n\n"
                "💰 پیسې د لاندې لارو وګټئ:\n"
                "• 🎯 ټاسکونه\n"
                "• 👥 دعوت\n"
                "• 🎁 بونس\n\n"
                "🚀 اسانه، چټک او ریښتینی!"
            )

    except Exception as e:
        print("HANDLER ERROR:", e)

# ================= RUN =================
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin_panel))
app.add_handler(CallbackQueryHandler(check_join, pattern="check_join"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))

print("✅ BOT RUNNING...")
app.run_polling()
