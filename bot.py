import sqlite3
import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

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
        ["📊 Profile"],
        ["💰 Earn", "🎁 Bonus"],
        ["👥 Invite"],
        ["📞 Add Number", "💸 Withdraw"],
        ["ℹ️ About"]
    ], resize_keyboard=True)

def earn_kb():
    return ReplyKeyboardMarkup([
        ["🎯 Tasks"],
        ["👥 Invite"],
        ["🎁 Bonus"],
        ["📆 Weekly Bonus"],
        ["🔙 Back"]
    ], resize_keyboard=True)

def admin_kb():
    return ReplyKeyboardMarkup([
        ["👥 Users", "📊 Stats"],
        ["📢 Broadcast", "💸 Withdraw Requests"],
        ["➕ Add Channel", "➖ Remove Channel"],
        ["🔙 Back"]
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
        channels = cursor.execute("SELECT username FROM channels").fetchall()
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
                    buttons.append([InlineKeyboardButton(f"Join {ch}", url=f"https://t.me/{ch.replace('@','')}")])
            except:
                not_joined = True

        if not_joined:
            buttons.append([InlineKeyboardButton("✅ Check Join", callback_data="check_join")])

            msg = "⚠️ Please join all required channels first:"

            if update.message:
                await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(buttons))
            else:
                await update.callback_query.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(buttons))

            return False

        return True
    except:
        return True

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = update.effective_user.id
        get_user(uid)

        # Invite system
        if context.args:
            try:
                ref = int(context.args[0])
                if ref != uid:
                    inviter = cursor.execute("SELECT inviter FROM users WHERE id=?", (uid,)).fetchone()[0]

                    if inviter is None:
                        cursor.execute("UPDATE users SET inviter=? WHERE id=?", (ref, uid))
                        cursor.execute("UPDATE users SET balance=balance+2 WHERE id=?", (ref,))
                        conn.commit()

                        # New user message
                        await update.message.reply_text(
                            "🎉 Welcome!\n\nYou joined using an invite link!\nEarn money via tasks, bonus, and referrals 🚀"
                        )

                        # Notify inviter
                        try:
                            await context.bot.send_message(
                                ref,
                                "🎉 New user joined via your link!\n💰 +2 AFN added to your balance"
                            )
                        except:
                            pass
            except:
                pass

        if not await force_join(update, context):
            return

        await update.message.reply_text("✨ Welcome to Reward Bot", reply_markup=main_kb())

    except Exception as e:
        print("START ERROR:", e)

# ================= CHECK JOIN =================
async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    fake = Update(update.update_id, message=query.message)

    if await force_join(fake, context):
        await query.message.reply_text("✅ Verified!", reply_markup=main_kb())

# ================= ADMIN =================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("❌ You are not admin")

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
                await update.message.reply_text(f"Total Users: {count}", reply_markup=admin_kb())

            elif text == "📊 Stats":
                total = cursor.execute("SELECT SUM(balance) FROM users").fetchone()[0] or 0
                await update.message.reply_text(f"Total Balance: {total}", reply_markup=admin_kb())

            elif text == "📢 Broadcast":
                context.user_data.clear()
                context.user_data["broadcast"] = True
                await update.message.reply_text("Send message:")

            elif context.user_data.get("broadcast"):
                users = cursor.execute("SELECT id FROM users").fetchall()
                for u in users:
                    try:
                        await context.bot.send_message(u[0], text)
                    except:
                        pass
                context.user_data.clear()
                await update.message.reply_text("✅ Sent", reply_markup=admin_kb())

            elif text == "➕ Add Channel":
                context.user_data.clear()
                context.user_data["add_channel"] = True
                await update.message.reply_text("Send channel username (e.g. @channel)")

            elif context.user_data.get("add_channel"):
                if text.startswith("@"):
                    exists = cursor.execute("SELECT * FROM channels WHERE username=?", (text,)).fetchone()
                    if exists:
                        await update.message.reply_text("Already exists", reply_markup=admin_kb())
                    else:
                        cursor.execute("INSERT INTO channels(username) VALUES(?)", (text,))
                        conn.commit()
                        await update.message.reply_text("✅ Added", reply_markup=admin_kb())
                    context.user_data.clear()
                else:
                    await update.message.reply_text("Invalid format")

            elif text == "➖ Remove Channel":
                context.user_data.clear()
                context.user_data["remove_channel"] = True
                await update.message.reply_text("Send channel username")

            elif context.user_data.get("remove_channel"):
                cursor.execute("DELETE FROM channels WHERE username=?", (text,))
                conn.commit()
                context.user_data.clear()
                await update.message.reply_text("✅ Removed", reply_markup=admin_kb())

            elif text == "🔙 Back":
                await update.message.reply_text("Main Menu", reply_markup=main_kb())

        # ===== USER =====
        if text == "📊 Profile":
            bal = cursor.execute("SELECT balance FROM users WHERE id=?", (uid,)).fetchone()[0] or 0
            await update.message.reply_text(f"💰 Balance: {bal:.1f} AFN")

        elif text == "💰 Earn":
            await update.message.reply_text("Choose:", reply_markup=earn_kb())

        elif text == "🎯 Tasks":
            cursor.execute("UPDATE users SET balance=balance+1 WHERE id=?", (uid,))
            conn.commit()
            await update.message.reply_text("✅ +1 AFN")

        elif text == "🎁 Bonus":
            today = datetime.date.today().isoformat()
            last = cursor.execute("SELECT last_daily FROM users WHERE id=?", (uid,)).fetchone()[0]

            if last == today:
                await update.message.reply_text("❌ Already claimed")
            else:
                cursor.execute("UPDATE users SET balance=balance+0.5,last_daily=? WHERE id=?", (today, uid))
                conn.commit()
                await update.message.reply_text("✅ +0.5 AFN")

        elif text == "📆 Weekly Bonus":
            now = datetime.datetime.now()
            last = cursor.execute("SELECT last_weekly FROM users WHERE id=?", (uid,)).fetchone()[0]

            if last and (now - datetime.datetime.strptime(last, "%Y-%m-%d")).days < 7:
                await update.message.reply_text("❌ Not ready yet")
            else:
                cursor.execute("UPDATE users SET balance=balance+5,last_weekly=? WHERE id=?", (now.strftime("%Y-%m-%d"), uid))
                conn.commit()
                await update.message.reply_text("🎉 +5 AFN")

        elif text == "👥 Invite":
            link = f"https://t.me/{BOT_USERNAME}?start={uid}"
            await update.message.reply_text(f"Your link:\n{link}")

        elif text == "📞 Add Number":
            context.user_data.clear()
            context.user_data["phone"] = True
            await update.message.reply_text("Send 10-digit phone number")

        elif context.user_data.get("phone"):
            if text.isdigit() and len(text) == 10:
                cursor.execute("UPDATE users SET phone=? WHERE id=?", (text, uid))
                conn.commit()
                context.user_data.clear()
                await update.message.reply_text("✅ Saved")
            else:
                await update.message.reply_text("❌ Invalid number")

        elif text == "💸 Withdraw":
            context.user_data.clear()
            context.user_data["withdraw"] = True
            await update.message.reply_text("Enter amount (min 50)")

        elif context.user_data.get("withdraw"):
            if text.replace('.', '', 1).isdigit():
                amount = float(text)
                bal = cursor.execute("SELECT balance FROM users WHERE id=?", (uid,)).fetchone()[0]

                if amount >= 50 and amount <= bal:
                    cursor.execute("UPDATE users SET balance=balance-? WHERE id=?", (amount, uid))
                    cursor.execute("INSERT INTO withdrawals(user_id,amount,phone,status,date) VALUES(?,?,?,?,?)",
                                   (uid, amount, "", "pending", str(datetime.datetime.now())))
                    conn.commit()
                    context.user_data.clear()
                    await update.message.reply_text("✅ Request sent")
                else:
                    await update.message.reply_text("❌ Invalid amount")

        elif text == "ℹ️ About":
            await update.message.reply_text(
                "🤖 Reward Bot\n\n"
                "Earn money by:\n"
                "• Tasks\n• Invites\n• Bonuses\n\n"
                "Fast • Simple • Real 💰"
            )

    except Exception as e:
        print("ERROR:", e)

# ================= RUN =================
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin_panel))
app.add_handler(CallbackQueryHandler(check_join, pattern="check_join"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))

print("BOT RUNNING...")
app.run_polling()
