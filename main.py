import os
import random
import asyncio
import sqlite3
import time
import sys
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, constants
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
try:
    OWNER_ID = int(os.getenv("OWNER_ID", 0))
except:
    OWNER_ID = 0

if not TOKEN:
    print("❌ ERROR: BOT_TOKEN kosong!")
    sys.exit(1)

DB_NAME = 'chaos_bot.db'

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS members 
                 (chat_id INTEGER, user_id INTEGER, username TEXT, PRIMARY KEY (chat_id, user_id))''')
    conn.commit()
    conn.close()

def add_member(chat_id, user_id, username):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO members VALUES (?, ?, ?)", (chat_id, user_id, username))
    conn.commit()
    conn.close()

def get_random_members(chat_id, count=1):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT username FROM members WHERE chat_id = ? ORDER BY RANDOM() LIMIT ?", (chat_id, count))
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows if r[0]]

# --- KONTEN (LOSS 18+) ---
BACOTAN_1_ORG = [
    "Gue curiga @{u1} diem-diem simpen foto sangean member grup ini.",
    "Heh @{u1}, muka lo kayak orang habis ketahuan coli sama emak lo.",
    "Woi @{u1}, jujur aja lo pernah sange sama salah satu admin kan?",
    "@{u1} jangan nyimak doang anjing. Pilih: [Truth] atau [Dare]?"
    "@{u1} nyanyi dulu?"
    "@{u1} vn perkenalan diri?"
]

BACOTAN_2_ORG = [
    "@{u1} sama @{u2} mending, tukeran id aja.",
    "kak si @{u1} dia pengen kenalan @{u2}",
    "Kalo @{u1} sama @{u2} jadian, siapa yang jadi babu-nya?"
]

# --- UI MARKUP ---
def get_main_markup(user_id, is_mute_active=False):
    gacha_text = "🔒 Lagi Ada Yang Kena Mute" if is_mute_active else "🎲 Gacha Mute (Zonk Anjing)"
    gacha_cb = "null" if is_mute_active else "gacha_mute"
    
    keyboard = [
        [InlineKeyboardButton(gacha_text, callback_data=gacha_cb)],
        [InlineKeyboardButton("😈 TOD Bar-bar", callback_data="tod_manual")],
        [InlineKeyboardButton("⚙️ Set Timer / Admin", callback_data="set_timer_menu")]
    ]
    # Tombol khusus owner muncul di bawah menu utama
    if user_id == OWNER_ID:
        keyboard.append([InlineKeyboardButton("📤 BACKUP DATABASE (OWNER)", callback_data="send_db")])
        
    return InlineKeyboardMarkup(keyboard)

# --- HANDLERS ---
async def track_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in [constants.ChatType.GROUP, constants.ChatType.SUPERGROUP]:
        username = update.effective_user.username or update.effective_user.first_name
        add_member(update.effective_chat.id, update.effective_user.id, username)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    msg = (
        "🔥 **CHAOS BOT v2.0** 🔥\n\n"
        "Gue bakal bikin grup lo makin berisik.\n"
        "✅ **Gacha Mute**: Judi nasib biar diem.\n"
        "✅ **Auto Bacot**: Fitnah & Tag random member.\n"
        "✅ **TOD**: Truth or Dare gak ngotak.\n\n"
        "👇 Pake tombol di bawah buat setting:"
    )
    await update.message.reply_text(msg, reply_markup=get_main_markup(user_id), parse_mode="Markdown")

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    user_id = query.from_user.id
    user_name = query.from_user.username or query.from_user.first_name
    
    # Ambil status mute dari context
    mute_status = context.chat_data.get("is_mute_active", False)

    if query.data == "gacha_mute":
        if mute_status:
            return await query.answer("Masih ada yang kena mute!", show_alert=True)
        
        await query.answer("Muter nasib...")
        if random.random() < 0.3:
            try:
                context.chat_data["is_mute_active"] = True
                await query.edit_message_text(f"💀 **ZONK!** @{user_name} kena mute 1 menit. Mampus!", reply_markup=get_main_markup(user_id, True), parse_mode="Markdown")
                await context.bot.restrict_chat_member(chat_id, user_id, permissions={"can_send_messages": False})
                await asyncio.sleep(60)
                await context.bot.restrict_chat_member(chat_id, user_id, permissions={"can_send_messages": True, "can_send_other_messages": True, "can_add_web_page_previews": True, "can_send_polls": True})
                context.chat_data["is_mute_active"] = False
                await query.message.reply_text(f"🔓 @{user_name} udah bebas. Jangan bacot lagi lo!")
            except:
                await query.message.reply_text("❌ Gagal Mute. Gue bukan admin grup ini!")
                context.chat_data["is_mute_active"] = False
        else:
            await query.message.reply_text(f"✅ @{user_name} Hoki lo kali ini.")

    elif query.data == "tod_manual":
        members = get_random_members(chat_id, 1)
        if members:
            txt = f"🔥 **TOD TIME!**\n\nWoi @{members[0]}, milih sekarang atau gue kick: \n1. **TRUTH** \n2. **DARE**"
            await query.message.reply_text(txt, parse_mode="Markdown")
        else:
            await query.answer("Grup sepi banget, gak ada member terdaftar.", show_alert=True)

    elif query.data == "set_timer_menu":
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.status not in [constants.ChatMemberStatus.ADMINISTRATOR, constants.ChatMemberStatus.OWNER] and user_id != OWNER_ID:
            return await query.answer("Cuma Admin yang bisa setting timer!", show_alert=True)
        
        keys = [
            [InlineKeyboardButton("5 Menit", callback_data="t_5"), InlineKeyboardButton("15 Menit", callback_data="t_15")],
            [InlineKeyboardButton("OFF / Matikan", callback_data="t_0")],
            [InlineKeyboardButton("🔙 Kembali", callback_data="back_to_main")]
        ]
        await query.edit_message_text("⚙️ **SETTING AUTO BACOT**\nPilih jeda waktu bot nge-tag orang:", reply_markup=InlineKeyboardMarkup(keys), parse_mode="Markdown")

    elif query.data == "back_to_main":
        await query.edit_message_text("Pilih menu:", reply_markup=get_main_markup(user_id, mute_status))

    elif query.data == "send_db":
        if user_id != OWNER_ID:
            return await query.answer("Lu bukan owner!", show_alert=True)
        try:
            with open(DB_NAME, 'rb') as f:
                await context.bot.send_document(chat_id=user_id, document=f, caption=f"📅 Backup: {time.ctime()}")
            await query.answer("DB dikirim ke PC (Private Chat)!", show_alert=True)
        except Exception as e:
            await query.message.reply_text(f"Gagal: {e}")

    elif query.data.startswith("t_"):
        mins = int(query.data.split("_")[1])
        jobs = context.job_queue.get_jobs_by_name(f"bc_{chat_id}")
        for j in jobs: j.schedule_removal()
        
        if mins > 0:
            context.job_queue.run_repeating(auto_bacot_job, interval=mins*60, first=10, chat_id=chat_id, name=f"bc_{chat_id}")
            await query.edit_message_text(f"✅ Oke! Gue bakal bacot tiap {mins} menit di sini.", reply_markup=get_main_markup(user_id, mute_status))
        else:
            await query.edit_message_text("✅ Auto Bacot dimatikan.", reply_markup=get_main_markup(user_id, mute_status))

async def auto_bacot_job(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    mode = random.choice([1, 2])
    members = get_random_members(chat_id, mode)
    if members:
        if mode == 1:
            txt = random.choice(BACOTAN_1_ORG).format(u1=members[0])
        else:
            txt = random.choice(BACOTAN_2_ORG).format(u1=members[0], u2=members[1])
        await context.bot.send_message(chat_id, f"🚨 **PENGUMUMAN**\n\n{txt}", parse_mode="Markdown")

async def restore_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    if update.message.document and update.message.document.file_name == DB_NAME:
        f = await context.bot.get_file(update.message.document.file_id)
        await f.download_to_drive(DB_NAME)
        await update.message.reply_text("✅ DB Berhasil di-restore!")

if __name__ == '__main__':
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, track_members))
    app.add_handler(MessageHandler(filters.Document.FileExtension("db"), restore_db))
    print("Bot Chaos Nyala...")
    app.run_polling(drop_pending_updates=True)
