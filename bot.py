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
wallet TEXT,
invited_by INTEGER,
last_daily TEXT,
last_weekly TEXT
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
        ["📊 Statistics", "💸 Withdraw"],
        ["👥 Referral", "💰 Balance"],
        ["💼 Set Wallet", "📋 Tasks"],
        ["🎁 Bonus", "📜 Terms"]
    ], resize_keyboard=True)

def admin_kb():
    return ReplyKeyboardMarkup([
        ["👥 Users", "📊 Stats"],
        ["📢 Broadcast", "💸 Withdraw Requests"],
        ["➕ Add Channel", "➖ Delete Channel"],
        ["🔙 Back"]
    ], resize_keyboard=True)

# ================= USER =================
def get_user(uid):
    cursor.execute("SELECT * FROM users WHERE id=?", (uid,))
    user = cursor.fetchone()
    if not user:
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

        for ch in channels:
            ch = ch[0]
            try:
                member = await context.bot.get_chat_member(ch, uid)
                if member.status not in ["member","administrator","creator"]:
                    buttons.append([InlineKeyboardButton(f"📢 {ch}", url=f"https://t.me/{ch.replace('@','')}")])
            except:
                buttons.append([InlineKeyboardButton(f"📢 {ch}", url=f"https://t.me/{ch.replace('@','')}")])

        if buttons:
            buttons.append([InlineKeyboardButton("✅ Joined All", callback_data="check_join")])
            await update.message.reply_text(
                "🚀 Join all channels to continue:",
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
        args = context.args
        get_user(uid)

        # Referral System
        if args:
            ref = int(args[0])
            if ref != uid:
                cursor.execute("SELECT invited_by FROM users WHERE id=?", (uid,))
                if cursor.fetchone()[0] is None:
                    cursor.execute("UPDATE users SET invited_by=? WHERE id=?", (ref, uid))
                    cursor.execute("UPDATE users SET balance=balance+2 WHERE id=?", (ref,))
                    conn.commit()

                    try:
                        await context.bot.send_message(ref, "🎉 New referral joined! +2 ⭐")
                    except:
                        pass

        if not await force_join(update, context):
            return

        await update.message.reply_text(
"""🎉 Earn Stars Easily!

💰 Invite = 2 ⭐
🎁 Daily = 0.5 ⭐
🔥 Weekly = 2 ⭐
💸 Withdraw = 20 ⭐

👇 Use menu:""",
            reply_markup=main_kb()
        )

    except Exception as e:
        print(e)

# ================= CHECK JOIN =================
async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        await query.message.reply_text("✅ Verified! Use menu", reply_markup=main_kb())
    except:
        pass

# ================= ADMIN =================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("❌ Not Admin")

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

            if text == "👥 Users":
                count = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
                await update.message.reply_text(f"👥 {count}", reply_markup=admin_kb())

            elif text == "📊 Stats":
                total = cursor.execute("SELECT SUM(balance) FROM users").fetchone()[0] or 0
                await update.message.reply_text(f"💰 {total} ⭐", reply_markup=admin_kb())

            elif text == "📢 Broadcast":
                context.user_data["broadcast"] = True
                await update.message.reply_text("Send message:")

            elif context.user_data.get("broadcast"):
                users = cursor.execute("SELECT id FROM users").fetchall()
                for u in users:
                    try:
                        await context.bot.send_message(u[0], text)
                    except:
                        pass
                context.user_data["broadcast"] = False
                await update.message.reply_text("✅ Sent", reply_markup=admin_kb())

            elif text == "➕ Add Channel":
                context.user_data["add_channel"] = True
                await update.message.reply_text("Send @channel")

            elif context.user_data.get("add_channel"):
                if text.startswith("@"):
                    cursor.execute("INSERT INTO channels(username) VALUES(?)", (text,))
                    conn.commit()
                    context.user_data["add_channel"] = False
                    await update.message.reply_text("✅ Added", reply_markup=admin_kb())
                else:
                    await update.message.reply_text("❌ Invalid")

            elif text == "➖ Delete Channel":
                context.user_data["del_channel"] = True
                await update.message.reply_text("Send channel")

            elif context.user_data.get("del_channel"):
                cursor.execute("DELETE FROM channels WHERE username=?", (text,))
                conn.commit()
                context.user_data["del_channel"] = False
                await update.message.reply_text("✅ Deleted", reply_markup=admin_kb())

            elif text == "🔙 Back":
                await update.message.reply_text("Main Menu", reply_markup=main_kb())

        # ===== USER =====
        if text == "💰 Balance":
            bal = cursor.execute("SELECT balance FROM users WHERE id=?", (uid,)).fetchone()[0]
            await update.message.reply_text(f"💰 {bal} ⭐")

        elif text == "👥 Referral":
            link = f"https://t.me/{BOT_USERNAME}?start={uid}"
            count = cursor.execute("SELECT COUNT(*) FROM users WHERE invited_by=?", (uid,)).fetchone()[0]
            await update.message.reply_text(f"{link}\n👥 {count} referrals\n🎁 2 ⭐ each")

        elif text == "🎁 Bonus":
            today = str(datetime.date.today())
            last = cursor.execute("SELECT last_daily FROM users WHERE id=?", (uid,)).fetchone()[0]

            if last == today:
                await update.message.reply_text("❌ Already claimed")
            else:
                cursor.execute("UPDATE users SET balance=balance+0.5,last_daily=? WHERE id=?", (today, uid))
                conn.commit()
                await update.message.reply_text("🎁 +0.5 ⭐")

        elif text == "📋 Tasks":
            await update.message.reply_text("📋 Tasks coming soon")

        elif text == "💼 Set Wallet":
            context.user_data["wallet"] = True
            await update.message.reply_text("Send wallet:")

        elif context.user_data.get("wallet"):
            cursor.execute("UPDATE users SET wallet=? WHERE id=?", (text, uid))
            conn.commit()
            context.user_data["wallet"] = False
            await update.message.reply_text("✅ Saved")

        elif text == "💸 Withdraw":
            bal, wallet = cursor.execute("SELECT balance,wallet FROM users WHERE id=?", (uid,)).fetchone()

            if not wallet:
                await update.message.reply_text("❌ Set wallet first")
                return

            if bal < 20:
                await update.message.reply_text("❌ Minimum 20 ⭐")
                return

            await update.message.reply_text("✅ Request sent")

        elif text == "📊 Statistics":
            total = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            await update.message.reply_text(f"👥 Users: {total}")

        elif text == "📜 Terms":
            await update.message.reply_text(
"""📜 Terms:
1. No cheating
2. No fake referrals
3. Admin can ban anytime"""
            )

    except Exception as e:
        print("ERROR:", e)

# ================= RUN =================
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin_panel))
app.add_handler(CallbackQueryHandler(check_join, pattern="check_join"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))

print("✅ BOT RUNNING...")
app.run_polling()
