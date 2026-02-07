import os
import random
import asyncio
import sqlite3
import time
import sys
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, constants
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Load environment variables
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
# Pastikan OWNER_ID diset di Railway Variables (berupa angka)
try:
    OWNER_ID = int(os.getenv("OWNER_ID", 0))
except (ValueError, TypeError):
    OWNER_ID = 0

# Failsafe untuk Railway
if not TOKEN or TOKEN == "YOUR_BOT_TOKEN_HERE":
    print("❌ ERROR: BOT_TOKEN tidak ditemukan di Environment Variables Railway!")
    sys.exit(1)

# --- DATABASE SYSTEM ---
DB_NAME = 'chaos_bot.db'

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

# --- DATABASE KONTEN (LOSS/18+) ---
BACOTAN_1_ORG = [
    "Gue curiga @{u1} diem-diem simpen foto sangean member grup ini di folder tersembunyi.",
    "Heh @{u1}, muka lo kayak orang habis ketahuan coli sama emak lo.",
    "Woi @{u1}, mending jujur, lo pernah sange sama salah satu admin di sini kan?",
    "@{u1} jangan nyimak doang anjing. Pilih: [Truth] atau [Dare]?",
    "Baru dapet info A1, @{u1} barusan ngetik pake tangan kiri sambil liat foto profil admin."
]

BACOTAN_2_ORG = [
    "@{u1} sama @{u2} mending keluar aja deh, bau-bau habis Check-in nih berduaan.",
    "Gue liat @{u1} tadi malem masuk kamar @{u2}, ngapain hayo?",
    "Kalo @{u1} sama @{u2} jadian, kira-kira siapa yang jadi 'babu'-nya?",
    "Gue denger @{u1} pernah khilaf sama @{u2} pas lagi mabok ya?"
]

# --- UI MARKUP ---
def get_main_markup(is_mute_active=False):
    gacha_text = "🔒 Lagi Ada Yang Kena Mute" if is_mute_active else "🎲 Gacha Mute (Zonk Anjing)"
    # Di sini ganti jadi callback_data
    gacha_callback = "null" if is_mute_active else "gacha_mute"
    
    keyboard = [
        [InlineKeyboardButton(gacha_text, callback_data=gacha_callback)],
        [InlineKeyboardButton("😈 TOD Bar-bar", callback_data="tod_manual")],
        [InlineKeyboardButton("⚙️ Set Timer / Admin", callback_data="set_timer_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Pastikan di bagian menu Admin juga diganti:
def get_admin_setup_markup(): # Jika kamu pakai fungsi ini
    keys = [
        [InlineKeyboardButton("5 Menit", callback_data="t_5"), 
         InlineKeyboardButton("15 Menit", callback_data="t_15")],
        [InlineKeyboardButton("OFF", callback_data="t_0")],
        [InlineKeyboardButton("📤 Backup DB (Owner)", callback_data="send_db")],
        [InlineKeyboardButton("🔙 Kembali", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keys)

# --- HANDLERS ---
async def track_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in [constants.ChatType.GROUP, constants.ChatType.SUPERGROUP]:
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        add_member(chat_id, user_id, username)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 **BOT CHAOS AKTIF (V2)** 🔥\nFull UI, No Sensor, Mode Loss!\n\nBot otomatis nyatet member aktif. Klik tombol buat mulai.",
        reply_markup=get_main_markup()
    )

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    user_id = query.from_user.id
    user_name = query.from_user.username or query.from_user.first_name
    
    await query.answer()

    if query.data == "gacha_mute":
        if random.random() < 0.3:
            try:
                context.chat_data["is_mute_active"] = True
                await query.edit_message_text(f"💀 MAMPUS! @{user_name} kena zonk. Diem lo 1 menit!", reply_markup=get_main_markup(True))
                
                await context.bot.restrict_chat_member(chat_id, user_id, permissions={"can_send_messages": False})
                await asyncio.sleep(60)
                await context.bot.restrict_chat_member(chat_id, user_id, permissions={"can_send_messages": True, "can_send_other_messages": True, "can_add_web_page_previews": True, "can_send_polls": True})
                
                context.chat_data["is_mute_active"] = False
                await query.message.reply_text(f"🔓 @{user_name} udah bebas. Gacha lagi gih!")
                await query.edit_message_reply_markup(reply_markup=get_main_markup(False))
            except Exception:
                await query.message.reply_text("❌ Gue butuh izin Admin buat mute orang!")
        else:
            await query.message.reply_text(f"✅ @{user_name} hoki, nggak kena mute.")

    elif query.data == "set_timer_menu":
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.status not in [constants.ChatMemberStatus.ADMINISTRATOR, constants.ChatMemberStatus.OWNER] and user_id != OWNER_ID:
            return await query.answer("Cuma Admin/Owner yang boleh nyentuh ini!", show_alert=True)
        
        keys = [
            [InlineKeyboardButton("5 Menit", callback_query_data="t_5"), InlineKeyboardButton("15 Menit", callback_query_data="t_15")],
            [InlineKeyboardButton("OFF", callback_query_data="t_0")],
            [InlineKeyboardButton("📤 Backup DB (Owner)", callback_query_data="send_db")],
            [InlineKeyboardButton("🔙 Kembali", callback_query_data="back_to_main")]
        ]
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keys))

    elif query.data == "back_to_main":
        await query.edit_message_reply_markup(reply_markup=get_main_markup(context.chat_data.get("is_mute_active", False)))

    elif query.data == "send_db":
        if user_id != OWNER_ID:
            return await query.answer("Lu bukan bos gue!", show_alert=True)
        try:
            with open(DB_NAME, 'rb') as db_file:
                await context.bot.send_document(chat_id=user_id, document=db_file, filename=DB_NAME, caption="🚀 Backup DB Terbaru.")
            await query.answer("DB udah dikirim ke PM!", show_alert=True)
        except Exception as e:
            await query.message.reply_text(f"Gagal backup: {e}")

    elif query.data.startswith("t_"):
        minutes = int(query.data.split("_")[1])
        jobs = context.job_queue.get_jobs_by_name(f"bacot_{chat_id}")
        for j in jobs: j.schedule_removal()

        if minutes > 0:
            context.job_queue.run_repeating(auto_bacot_job, interval=minutes*60, first=10, chat_id=chat_id, name=f"bacot_{chat_id}")
            await query.edit_message_text(f"✅ Oke, gue bakal bacot tiap {minutes} menit.", reply_markup=get_main_markup())
        else:
            await query.edit_message_text("✅ Bot mode anteng (OFF).", reply_markup=get_main_markup())

# --- AUTOMATIC JOB ---
async def auto_bacot_job(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    mode = random.choice([1, 2])
    members = get_random_members(chat_id, mode)

    if not members: return

    if len(members) == 1:
        txt = random.choice(BACOTAN_1_ORG).format(u1=members[0])
    else:
        txt = random.choice(BACOTAN_2_ORG).format(u1=members[0], u2=members[1])

    await context.bot.send_message(chat_id, f"🚨 **INFO PENTING**\n\n{txt}")

# --- RESTORE DATABASE ---
async def restore_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != OWNER_ID: return

    if update.message.document and update.message.document.file_name == DB_NAME:
        db_file = await context.bot.get_file(update.message.document.file_id)
        await db_file.download_to_drive(DB_NAME)
        await update.message.reply_text("✅ Database di-restore! Data member lama aman.")
    else:
        await update.message.reply_text("Kirim file 'chaos_bot.db' buat restore.")

# --- MAIN ---
if __name__ == '__main__':
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, track_members))
    # Handler Restore via kirim file DB
    app.add_handler(MessageHandler(filters.Document.FileExtension("db"), restore_db))
    
    print("Chaos Bot is Running on Railway...")
    app.run_polling()
