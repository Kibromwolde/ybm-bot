import asyncio
import logging
import re
import sqlite3
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

# ================= CONFIGURATION =================
BOT_TOKEN = "9092096363:AAH3SCTFEDyD74zQpffy2q3UZ1HgeC-dPAo"
ADMIN_ID = 1703459756  # Updated with your Telegram User ID
YBM_SUPPORT_USERNAME = "@YBMSupport"  # Replace with exact YBM Support handle
MAX_USERS = 100
FEE_AMOUNT = "250 ETB"
TELEBIRR_NAME = "Kibrom Weldegiyorgis"
TELEBIRR_NUMBER = "0914425378"
# =================================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ================= DUMMY WEB SERVER FOR RENDER =================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"YBM Telegram Bot is active and running!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logging.info(f"Health check server running on port {port}")
    server.serve_forever()

# Start the dummy web server in a background thread so Render passes its health check
threading.Thread(target=run_web_server, daemon=True).start()
# ===============================================================

# ================= DATABASE SETUP =================
conn = sqlite3.connect("yt_watch_pool.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    phone TEXT,
    channel_name TEXT,
    video_link TEXT,
    status TEXT DEFAULT 'pending_payment',
    watch_hours_completed INTEGER DEFAULT 0,
    joined_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS proofs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    photo_file_id TEXT,
    submitted_at TEXT,
    status TEXT DEFAULT 'pending'
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS watch_history (
    viewer_id INTEGER,
    target_user_id INTEGER,
    watched_at TEXT,
    PRIMARY KEY (viewer_id, target_user_id)
)
""")
conn.commit()


def get_approved_count():
    cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'approved'")
    return cursor.fetchone()[0]


# ================= FSM STATES =================
class RegState(StatesGroup):
    agree = State()
    full_name = State()
    phone = State()
    channel_name = State()
    video_link = State()
    payment_screenshot = State()


class ProofState(StatesGroup):
    waiting_screenshot = State()


# ================= KEYBOARDS =================
def main_menu_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 የእኔ መገለጫ (My Profile)"), KeyboardButton(text="🎬 የሰዓት ስራ (Watch Task 2Hrs)")],
            [KeyboardButton(text="📸 ማረጋገጫ ፎቶ መላክ (Submit Proof)"), KeyboardButton(text="🆘 YBM ድጋፍ (Support)")],
        ],
        resize_keyboard=True,
    )


def agreement_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ እስማማለሁ & ይመዝገቡ (I Agree & Register)", callback_data="agree_terms")],
            [InlineKeyboardButton(text="🆘 YBM Support ማነጋገር", url=f"https://t.me/{YBM_SUPPORT_USERNAME.lstrip('@')}")],
        ]
    )


# ================= HANDLERS =================
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    cursor.execute("SELECT status FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    approved_count = get_approved_count()
    spots_left = MAX_USERS - approved_count

    if row:
        status = row[0]
        if status == "approved":
            await message.answer(
                f"🇪🇹 እንኳን ወደ **የኢትዮጵያ ዩቲዩበሮች የሰዓት ማሳደጊያ (2,000K Watch-Time Pool)** በደህና መጡ!\n"
                f"ፈቃድ ያገኙ ፈጣሪዎች: **{approved_count}/{MAX_USERS}**",
                reply_markup=main_menu_kb(),
                parse_mode="Markdown",
            )
            return
        elif status == "under_review":
            await message.answer(
                "⏳ የእርስዎ የ **250 ETB ቴሌብር ክፍያ** በአስተዳዳሪዎች እየተጣራ ነው።\n"
                f"እርዳታ ከፈለጉ {YBM_SUPPORT_USERNAME} ያነጋግሩ።",
                parse_mode="Markdown",
            )
            return

    if spots_left <= 0:
        await message.answer(
            "🚫 **ምዝገባው ተጠናቋል!** ሁሉም **100/100** ቦታዎች ተይዘዋል።\n"
            f"ተጠባባቂ ዝርዝር ውስጥ ለመግባት {YBM_SUPPORT_USERNAME} ያነጋግሩ።",
            parse_mode="Markdown",
        )
        return

    welcome_text = (
        "🇪🇹 **ETHIOPIAN YOUTUBERS WATCH-TIME ACCELERATOR** 🇪🇹\n\n"
        f"🎯 **هدف:** 2,000+ ሰዓት ማሳደግ\n"
        f"👥 **የተፈቀደው όራ:** 100 ዩቲዩበሮች ብቻ (**{spots_left} ቦታዎች ቀርተዋል**)\n"
        f"💰 **የምዝገባ ክፍያ:** {FEE_AMOUNT}\n\n"
        "📜 **ጥብቅ ደንቦች (MANDATORY RULES):**\n"
        "1️⃣ የተሰጠዎትን የ **2 ሰዓት ቪዲዮ** ሙሉውን ማየት አለብዎት።\n"
        "2️⃣ **LIKE, SUBSCRIBE እና VIEW** ማድረግ ግዴታ ነው።\n"
        "3️⃣ ሰዓቱ መሞላቱን፣ ላይክ እና ሰብስክራይብ መደረጉን የሚያሳይ **ኦሪጅናል ስክሪንሾት** መላክ አለብዎት።\n\n"
        "ለመቀጠል ከታች ያለውን ቁልፍ ይጫኑ:"
    )
    await message.answer(welcome_text, reply_markup=agreement_kb(), parse_mode="Markdown")
    await state.set_state(RegState.agree)


@dp.callback_query(F.data == "agree_terms")
async def process_agreement(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("1️⃣ እባክዎ ሙሉ ስምዎን ያስገቡ (Full Name):", parse_mode="Markdown")
    await state.set_state(RegState.full_name)


@dp.message(RegState.full_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text.strip())
    await message.answer("2️⃣ ስልክ ቁጥርዎን ያስገቡ (ለምሳሌ 0911223344):", parse_mode="Markdown")
    await state.set_state(RegState.phone)


@dp.message(RegState.phone)
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await message.answer("3️⃣ የዩቲዩብ ቻናል ስምዎን ያስገቡ (YouTube Channel Name):", parse_mode="Markdown")
    await state.set_state(RegState.channel_name)


@dp.message(RegState.channel_name)
async def process_channel_fixed(message: types.Message, state: FSMContext):
    await state.update_data(channel_name=message.text.strip())
    await message.answer(
        "4️⃣ የ **2 ሰዓት ቪዲዮዎን ሊንክ** (ወይም የ 2 ሰዓት ፕሌይሊስት ሊንክ) ይላኩ:",
        parse_mode="Markdown",
    )
    await state.set_state(RegState.video_link)


@dp.message(RegState.video_link)
async def process_link(message: types.Message, state: FSMContext):
    link = message.text.strip()
    if not re.match(r"^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+\$", link):
        await message.answer("❌ ትክክለኛ ያልሆነ የዩቲዩብ ሊንክ ነው። እባክዎ ትክክለኛ `youtube.com` ወይም `youtu.be` ሊንክ ይላኩ:")
        return

    await state.update_data(video_link=link)

    payment_instructions = (
        "💳 **የቴሌብር ክፍያ ማጠናቀቂያ (TELEBIRR PAYMENT)**\n\n"
        f"እባክዎ **{FEE_AMOUNT}** ከዚህ በታች ባለው መለያ ያስተላልፉ:\n"
        f"👤 **ስም:** `{TELEBIRR_NAME}`\n"
        f"📱 **ቴሌብር ቁጥር:** `{TELEBIRR_NUMBER}`\n\n"
        "📸 **ክፍያውን ከፈጸሙ በኋላ የደረሰኝ ስክሪንሾት (Screenshot) እዚህ ይላኩ:**"
    )
    await message.answer(payment_instructions, parse_mode="Markdown")
    await state.set_state(RegState.payment_screenshot)


@dp.message(RegState.payment_screenshot, F.photo)
async def process_payment_screenshot(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else "No Username"
    photo_id = message.photo[-1].file_id

    cursor.execute("""
        INSERT OR REPLACE INTO users (user_id, username, full_name, phone, channel_name, video_link, status, joined_at)
        VALUES (?, ?, ?, ?, ?, ?, 'under_review', ?)
    """, (
        user_id,
        username,
        data["full_name"],
        data["phone"],
        data["channel_name"],
        data["video_link"],
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ))
    conn.commit()

    admin_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ አረጋግጥ (Approve)", callback_data=f"approve_user:{user_id}"),
                InlineKeyboardButton(text="❌ ውድቅ አድርግ (Reject)", callback_data=f"reject_user:{user_id}"),
            ]
        ]
    )

    caption = (
        "🆕 **አዲስ ፈጣሪ ምዝገባ (NEW CREATOR REGISTRATION)**\n\n"
        f"👤 **ስም:** {data['full_name']} ({username})\n"
        f"📱 **ስልክ:** {data['phone']}\n"
        f"📺 **ቻናል:** {data['channel_name']}\n"
        f"🔗 **ቪዲዮ ሊንክ:** {data['video_link']}\n"
        f"💰 **ክፍያ:** {FEE_AMOUNT} ወደ {TELEBIRR_NUMBER}"
    )
    await bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=caption, reply_markup=admin_kb, parse_mode="Markdown")

    await message.answer(
        "✅ **ምዝገባዎ እና ደረሰኝዎ ደርሷል!**\n\n"
        "ክፍያዎ በአስተዳዳሪው እየተጣራ ነው። ሲጸድቅ ማስታወቂያ ይደርስዎታል።\n"
        f"ጥያቄ ካለዎት **YBM Support**: {YBM_SUPPORT_USERNAME} ያነጋግሩ።",
        parse_mode="Markdown",
    )
    await state.clear()


@dp.message(RegState.payment_screenshot)
async def invalid_payment_media(message: types.Message):
    await message.answer("⚠️ እባክዎ የቴሌብር ክፍያ ደረሰኝ **ፎቶ (Screenshot)** ብቻ ይላኩ።")


# ================= ADMIN APPROVALS =================
@dp.callback_query(F.data.startswith("approve_user:"))
async def approve_user(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    target_id = int(callback.data.split(":")[1])

    if get_approved_count() >= MAX_USERS:
        await callback.answer("የተፈቀደላቸው አባላት ብዛት 100 ሞልቷል!", show_alert=True)
        return

    cursor.execute("UPDATE users SET status = 'approved' WHERE user_id = ?", (target_id,))
    conn.commit()

    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n✅ **ሁኔታ: ጸድቋል (APPROVED)**",
        parse_mode="Markdown",
    )
    await bot.send_message(
        chat_id=target_id,
        text="🎉 **እንኳን ደስ አለዎት! ምዝገባዎ ጸድቋል።**\n"
             "አሁን የ 100 ዩቲዩበሮች የሰዓት ማሳደጊያ ገንዳ (Pool) አባል ነዎት። ከታች ባለው ሜኑ ስራውን ይጀምሩ!",
        reply_markup=main_menu_kb(),
        parse_mode="Markdown",
    )


@dp.callback_query(F.data.startswith("reject_user
