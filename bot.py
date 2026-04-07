import sqlite3
import datetime
from telegram import (
    Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes
)

TOKEN = "8778331918:AAE5uzWflufC_AkLDz62m4A80BsbIZoZtvI"
ADMIN_ID = 8289491009

# ================= DATABASE =================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY,
    balance REAL DEFAULT 0,
    phone TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS channels(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT
)
""")

conn.commit()

# ================= KEYBOARD =================
def main_menu():
    return ReplyKeyboardMarkup([
        ["📊 حالت"],
        ["💰 پیسی زیاتول", "🎁 بونس"],
        ["👥 دعوت"],
        ["📞 نمبر داخلول", "💸 ویډرا"],
        ["ℹ️ د ربات په اړه"]
    ], resize_keyboard=True)

def admin_menu():
    return ReplyKeyboardMarkup([
        ["➕ چینل اضافه", "➖ چینل حذف"],
        ["📊 احصایه"],
        ["🔙 بیرته"]
    ], resize_keyboard=True)

# ================= FORCE JOIN =================
async def force_join(update, context):
    cursor.execute("SELECT username FROM channels")
    channels = cursor.fetchall()

    if not channels:
        return True

    buttons = []
    not_joined = False

    for ch in channels:
        ch = ch[0]
        try:
            member = await context.bot.get_chat_member(ch, update.effective_user.id)
            if member.status not in ["member", "administrator", "creator"]:
                not_joined = True
                buttons.append([InlineKeyboardButton(f"📢 {ch}", url=f"https://t.me/{ch.replace('@','')}")])
        except:
            not_joined = True

    if not_joined:
        buttons.append([InlineKeyboardButton("✅ چک کول", callback_data="check_join")])
        await update.message.reply_text(
            "⚠️ مهرباني وکړئ لاندې چینلونو ته Join شئ:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return False

    return True

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    cursor.execute("INSERT OR IGNORE INTO users(id) VALUES(?)", (user.id,))
    conn.commit()

    if not await force_join(update, context):
        return

    await update.message.reply_text("✨ ښه راغلاست!", reply_markup=main_menu())

# ================= CHECK JOIN BUTTON =================
async def check_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if await force_join(update, context):
        await query.message.reply_text("✅ تاسو Join کړي!", reply_markup=main_menu())

# ================= STATUS =================
async def status(update, context):
    uid = update.effective_user.id
    cursor.execute("SELECT balance FROM users WHERE id=?", (uid,))
    bal = cursor.fetchone()[0]

    await update.message.reply_text(f"💰 بیلانس: {bal} AFN", reply_markup=main_menu())

# ================= PHONE =================
async def save_phone(update, context):
    uid = update.effective_user.id
    phone = update.message.text

    if not phone.isdigit() or len(phone) != 10:
        await update.message.reply_text("❌ ۱۰ رقمي نمبر ولیکئ")
        return

    cursor.execute("UPDATE users SET phone=? WHERE id=?", (phone, uid))
    conn.commit()

    await update.message.reply_text("✅ نمبر ثبت شو", reply_markup=main_menu())

# ================= WITHDRAW =================
async def withdraw(update, context):
    uid = update.effective_user.id
    cursor.execute("SELECT balance, phone FROM users WHERE id=?", (uid,))
    bal, phone = cursor.fetchone()

    if not phone:
        await update.message.reply_text("❌ نمبر داخل کړئ")
        return

    if bal < 50:
        await update.message.reply_text("❌ لږ تر لږه 50 AFN پکار دی")
        return

    await update.message.reply_text("💸 ویډرا درخواست ثبت شو", reply_markup=main_menu())

# ================= ADMIN =================
async def admin(update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("⚙️ Admin Panel", reply_markup=admin_menu())

async def add_channel(update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("چینل یوزرنیم ولیکئ @example")

    context.user_data["add_channel"] = True

async def save_channel(update, context):
    if context.user_data.get("add_channel"):
        ch = update.message.text
        cursor.execute("INSERT INTO channels(username) VALUES(?)", (ch,))
        conn.commit()

        context.user_data["add_channel"] = False
        await update.message.reply_text("✅ چینل اضافه شو", reply_markup=admin_menu())

async def stats(update, context):
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]

    await update.message.reply_text(f"👥 ټول یوزران: {count}", reply_markup=admin_menu())

# ================= MESSAGE =================
async def msg(update, context):
    text = update.message.text

    if context.user_data.get("add_channel"):
        await save_channel(update, context)
        return

    if text == "📊 حالت":
        await status(update, context)

    elif text == "📞 نمبر داخلول":
        await update.message.reply_text("📱 نمبر ولیکئ")

    elif text.isdigit():
        await save_phone(update, context)

    elif text == "💸 ویډرا":
        await withdraw(update, context)

    elif text == "➕ چینل اضافه":
        await add_channel(update, context)

    elif text == "📊 احصایه":
        await stats(update, context)

    elif text == "🔙 بیرته":
        await start(update, context)

# ================= RUN =================
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))

from telegram.ext import CallbackQueryHandler
app.add_handler(CallbackQueryHandler(check_join_callback, pattern="check_join"))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg))

print("Bot Running...")
app.run_polling()
