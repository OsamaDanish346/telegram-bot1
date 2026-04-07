import sqlite3
import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN =" 8778331918:AAE5uzWflufC_AkLDz62m4A80BsbIZoZtvI"
ADMIN_ID = 8289491009

# دلته خپل چینلونه اضافه کړئ (اډمین کولی شي وروسته بدل کړي)
CHANNELS = ["@afghan_reward", "@khanda_koor", "@nice_image1"]   # که خالي وي نو ټاسکونه غیر فعال دي

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

# ==================== ټاسکونه (یوازې په کلیک کولو چک کیږي) ====================
async def tasks_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not CHANNELS:
        await update.message.reply_text("⚠️ فعال ټاسکونه شتون نه لري.\nاډمین ته ووایاست چې چینلونه اضافه کړي.")
        return

    user_id = update.effective_user.id
    joined_all = True
    added_reward = False

    for ch in CHANNELS:
        try:
            member = await context.bot.get_chat_member(ch, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                joined_all = False
        except:
            joined_all = False

    if joined_all:
        # +1 AFN انعام
        cursor.execute("SELECT balance FROM users WHERE id=?", (user_id,))
        balance = (cursor.fetchone() or [0])[0]
        new_balance = balance + 1.0
        cursor.execute("UPDATE users SET balance=? WHERE id=?", (new_balance, user_id))
        conn.commit()
        await update.message.reply_text("✅ تاسو بریالۍ توګه ټول ټاسکونه پوره کړل دي!\n\n+۱ افغانۍ ستاسو حساب ته اضافه شوه.")
    else:
        await update.message.reply_text("⚠️ تاسو لا تر اوسه ټولو چینلونو ته جوائن نه یاست.\nلومړی ټولو چینلونو ته جوائن شئ او بیا ټاسک وکړئ.")

# ==================== START ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cursor.execute("INSERT OR IGNORE INTO users(id) VALUES(?)", (user.id,))
    conn.commit()

    if not await check_force_join(update, context):
        return

    await update.message.reply_text("✨ **ښه راغلاست!** د پیسو زیاتولو بوټ ته.\nلاندې انتخاب وکړئ:", 
                                    reply_markup=main_keyboard(), parse_mode="Markdown")

# ==================== STATUS ====================
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cursor.execute("SELECT balance FROM users WHERE id=?", (user.id,))
    balance = (cursor.fetchone() or [0])[0]

    text = f"""🤵🏻‍♂️ استعمالوونکی = {user.first_name}

💳 ایډي کارن : {user.id}
💵 ستاسو پيسو اندازه = {balance:.1f} AFN

🔗 د بیلانس زیاتولو لپاره [ 👫 کسان ] دعوت کړی بوټ ته!"""
    await update.message.reply_text(text)

# ==================== BONUS ====================
async def daily_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT balance, last_daily_bonus FROM users WHERE id=?", (user_id,))
    row = cursor.fetchone() or [0, None]
    balance = row[0]
    last_daily = row[1]

    if last_daily == today:
        await update.message.reply_text("❌ نن ورځ مو ډیلی بونس اخیستی دی.\nسبا بیا راشئ!")
    else:
        new_balance = balance + 0.5
        cursor.execute("UPDATE users SET balance=?, last_daily_bonus=? WHERE id=?", (new_balance, today, user_id))
        conn.commit()
        await update.message.reply_text("✅ ډیلی بونس ترلاسه شو!\n+۰.۵ افغانۍ اضافه شوه.")

async def weekly_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    cursor.execute("SELECT balance, last_weekly_bonus FROM users WHERE id=?", (user_id,))
    row = cursor.fetchone() or [0, None]
    balance = row[0]
    last_weekly = row[1]

    if last_weekly and (now - datetime.datetime.strptime(last_weekly, "%Y-%m-%d")).days < 7:
        await update.message.reply_text("❌ ویکلی بونس لا نه دی پوره شوی.")
        return

    new_balance = balance + 5.0
    cursor.execute("UPDATE users SET balance=?, last_weekly_bonus=? WHERE id=?", (new_balance, today_str, user_id))
    conn.commit()
    await update.message.reply_text("🎉 ویکلی بونس ترلاسه شو!\n+۵ افغانۍ اضافه شوه.")

# ==================== دعوت ====================
async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bot_username = "YOUR_BOT_USERNAME"   # ← خپل بوټ یوزرنیم ولیکئ
    link = f"https://t.me/{bot_username}?start={user_id}"

    text = f"""🎉 خپل ملګري راوباسئ او پیسې زیات کړئ!

✅ هر نوی یوزر = +۲ افغانۍ ستاسو حساب ته

🔗 ستاسو شخصي لینک:
{link}

اوس شریک کړئ او ګټه پیل کړئ! 🔥"""

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📋 لینک کاپي کړئ", url=link)]])
    await update.message.reply_text(text, reply_markup=keyboard, disable_web_page_preview=True)

# ==================== ویډرا ====================
async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cursor.execute("SELECT balance, phone FROM users WHERE id=?", (user_id,))
    row = cursor.fetchone() or [0, None]
    balance = row[0]
    phone = row[1]

    if not phone:
        await update.message.reply_text("📱 لومړی خپل فون نمبر داخل کړئ.\nد «📞 نمبر داخلول» بټن وکاروئ.")
        return
    if balance < 50:
        await update.message.reply_text(f"⚠️ ستاسو بیلانس کافی نه دی.\nویډرا لپاره لږ تر لږه ۵۰ افغانۍ پکار دي.\nستاسو بیلانس: {balance:.1f} AFN")
        return

    text = f"""💸 **ویډرا درخواست**

ستاسو اوسني بیلانس: **{balance:.1f} AFN**
📱 ثبت شوی نمبر: **{phone}**

د ویډرا لپاره مقدار ولیکئ (لږ تر لږه ۵۰):"""
    await update.message.reply_text(text, parse_mode="Markdown")
    context.user_data['awaiting_withdraw_amount'] = True

# ==================== MESSAGE HANDLER ====================
async def msg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()
    uid = user.id

    if uid != ADMIN_ID:
        if not await check_force_join(update, context):
            return

    # Withdraw amount
    if context.user_data.get('awaiting_withdraw_amount'):
        if text.replace('.', '', 1).isdigit():
            amount = float(text)
            cursor.execute("SELECT balance, phone FROM users WHERE id=?", (uid,))
            balance, phone = cursor.fetchone() or (0.0, None)
            if amount < 50 or amount > balance:
                await update.message.reply_text("❌ ناسم مقدار!")
            else:
                date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                cursor.execute("INSERT INTO withdrawals(user_id, amount, phone, date) VALUES(?,?,?,?)", 
                               (uid, amount, phone, date))
                cursor.execute("UPDATE users SET balance = balance - ? WHERE id=?", (amount, uid))
                conn.commit()
                await update.message.reply_text(f"✅ ویډرا درخواست ثبت شو!\nمقدار: {amount} AFN")
                context.user_data['awaiting_withdraw_amount'] = False
        return

    if text == "📊 حالت":
        await status(update, context)
    elif text == "💰 پیسی زیاتول":
        await update.message.reply_text("💰 انتخاب وکړئ:", reply_markup=earn_keyboard())
    elif text == "🎁 بونس":
        await update.message.reply_text("🎁 بونس انتخاب وکړئ:", reply_markup=bonus_keyboard())
    elif text == "📅 ډیلی بونس":
        await daily_bonus(update, context)
    elif text == "📆 ویکلی بونس":
        await weekly_bonus(update, context)
    elif text == "👥 دعوت":
        await referral(update, context)
    elif text == "🎯 ټاسکونه":
        await tasks_handler(update, context)          # یوازې دلته چک کیږي
    elif text == "📞 نمبر داخلول":
        await update.message.reply_text("📱 خپل ۱۰ رقمي فون نمبر ولیکئ:")
    elif text == "💸 ویډرا":
        await withdraw_start(update, context)
    elif text == "ℹ️ د ربات په اړه":
        await update.message.reply_text("ℹ️ دا ریوارډ بوټ دی. د ټاسکونو، دعوت او بونس له لارې پیسې ګټئ.")
    elif text == "🔙 بیرته":
        await start(update, context)

    # Phone number
    elif text.isdigit() and len(text) == 10:
        cursor.execute("UPDATE users SET phone=? WHERE id=?", (text, uid))
        conn.commit()
        await update.message.reply_text("✅ ستاسو نمبر ثبت شو!")
    elif text.isdigit():
        await update.message.reply_text("❌ نمبر باید دقیق ۱۰ رقمه وي!")

# ==================== RUN BOT ====================
if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", msg_handler))
    app.add_handler(MessageHandler(filters.TEXT & \~filters.COMMAND, msg_handler))

    print("✅ بوټ چلېدونکی دی...")
    app.run_polling()
