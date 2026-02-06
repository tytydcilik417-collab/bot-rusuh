import os
import random
import asyncio
import sqlite3
import time
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Load token
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# --- DATABASE SETUP (SQLite) ---
def init_db():
    conn = sqlite3.connect('chaos_bot.db')
    c = conn.cursor()
    # Tabel buat simpan user yang aktif di tiap grup
    c.execute('''CREATE TABLE IF NOT EXISTS members 
                 (chat_id INTEGER, user_id INTEGER, username TEXT, PRIMARY KEY (chat_id, user_id))''')
    # Tabel buat simpan settingan timer grup
    c.execute('''CREATE TABLE IF NOT EXISTS settings 
                 (chat_id INTEGER PRIMARY KEY, timer_min INTEGER)''')
    conn.commit()
    conn.close()

def add_member(chat_id, user_id, username):
    conn = sqlite3.connect('chaos_bot.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO members VALUES (?, ?, ?)", (chat_id, user_id, username))
    conn.commit()
    conn.close()

def get_random_members(chat_id, count=1):
    conn = sqlite3.connect('chaos_bot.db')
    c = conn.cursor()
    c.execute("SELECT username FROM members WHERE chat_id = ? ORDER BY RANDOM() LIMIT ?", (chat_id, count))
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows if r[0]]

# --- DATABASE BACOTAN (LOSS/18+) ---
BACOTAN_1_ORG = [
    "KENA LO @{u1}, vn perkenalan diri dulu.",
    "KENA LO @{u1}, vn nyanyi.",
    "KENA LO @{u1}, cuma boleh jawab YA atau GA, lo pernah sange sama salah satu admin di sini kan?",
    "@{u1} jangan nyimak doang anjing. Pilih: [Truth] atau [Dare]?"
]

BACOTAN_2_ORG = [
    "@{u1} sama @{u2} HEHE, kenalan dulu udah gue bantu nih.",
    "KAK @{u1} ni orang @{u2}, mau kenalan tapi malu, kasih id aja kak",
    "si @{u1} sama @{u2} keknya cocok gasih"
]

# --- UI MARKUP ---
def get_main_markup(is_mute_active=False):
    gacha_text = "🔒 Lagi Ada Yang Kena Mute" if is_mute_active else "🎲 Gacha Mute (Zonk Anjing)"
    gacha_callback = "null" if is_mute_active else "gacha_mute"
    
    keyboard = [
        [InlineKeyboardButton(gacha_text, callback_query_data=gacha_callback)],
        [InlineKeyboardButton("😈 TOD Bar-bar", callback_query_data="tod_manual")],
        [InlineKeyboardButton("⚙️ Set Timer Bacot", callback_query_data="set_timer_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- HANDLERS ---
async def track_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Catat setiap user yang ngetik di grup ke database."""
    if update.effective_chat.type in ["group", "supergroup"]:
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        add_member(chat_id, user_id, username)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 **BOT CHAOS AKTIF** 🔥\nFull UI, No Sensor, Loss Reee!\n\nBot bakal otomatis nyatet member yang aktif buat jadi target fitnah.",
        reply_markup=get_main_markup()
    )

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    user_id = query.from_user.id
    user_name = query.from_user.username or query.from_user.first_name
    
    await query.answer()

    if query.data == "gacha_mute":
        if random.random() < 0.3: # Peluang 30%
            try:
                # Set status mute di bot context (sederhana)
                context.chat_data["is_mute_active"] = True
                await query.edit_message_text(f"💀 MAMPUS! @{user_name} kena zonk. Diem lo 1 menit!", reply_markup=get_main_markup(True))
                
                await context.bot.restrict_chat_member(chat_id, user_id, permissions={"can_send_messages": False})
                await asyncio.sleep(60)
                await context.bot.restrict_chat_member(chat_id, user_id, permissions={"can_send_messages": True, "can_send_other_messages": True})
                
                context.chat_data["is_mute_active"] = False
                await query.message.reply_text(f"🔓 @{user_name} udah bebas. Gacha lagi gih!")
                await query.edit_message_reply_markup(reply_markup=get_main_markup(False))
            except Exception as e:
                await query.message.reply_text("❌ Waduh, gue nggak punya izin buat Mute orang.")
        else:
            await query.message.reply_text(f"✅ @{user_name} Hoki lo anjing, nggak kena.")

    elif query.data == "set_timer_menu":
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.status not in ["administrator", "creator"]:
            return await query.answer("Cuma admin yang bisa setting!", show_alert=True)
        
        keys = [[InlineKeyboardButton("5 Menit", callback_query_data="t_5"), InlineKeyboardButton("15 Menit", callback_query_data="t_15")],
                [InlineKeyboardButton("OFF", callback_query_data="t_0")]]
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keys))

    elif query.data.startswith("t_"):
        minutes = int(query.data.split("_")[1])
        jobs = context.job_queue.get_jobs_by_name(f"bacot_{chat_id}")
        for j in jobs: j.schedule_removal()

        if minutes > 0:
            context.job_queue.run_repeating(auto_bacot_job, interval=minutes*60, first=10, chat_id=chat_id, name=f"bacot_{chat_id}")
            await query.edit_message_text(f"✅ Oke, gue bakal bacot tiap {minutes} menit.", reply_markup=get_main_markup())
        else:
            await query.edit_message_text("✅ Bot mode anteng.", reply_markup=get_main_markup())

# --- AUTO BACOT JOB ---
async def auto_bacot_job(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    
    # Pilih mau tag 1 atau 2 orang
    mode = random.choice([1, 2])
    members = get_random_members(chat_id, mode)

    if not members: return

    if len(members) == 1:
        txt = random.choice(BACOTAN_1_ORG).format(u1=members[0])
    else:
        txt = random.choice(BACOTAN_2_ORG).format(u1=members[0], u2=members[1])

    await context.bot.send_message(chat_id, f"🚨 **KABAR BURUNG**\n\n{txt}")

# --- MAIN ---
if __name__ == '__main__':
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    # Penting: bot harus bisa 'lihat' semua chat buat catat member
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, track_members))
    
    print("Bot Chaos Running...")
    app.run_polling()
