import asyncio
import logging
import re
import json
import os
import sys
from datetime import datetime

import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# ================== CONFIGURATION ==================
TELEGRAM_BOT_TOKEN = "8436714104:AAGKZ1B3w-m4BA7sPxYfozs6iubOdRHsPmw" # আপনার টোকেন
TELEGRAM_CHAT_ID = "-1003387766593"
ADMIN_ID = 8308179143

PANEL_USER = "Mominbro"
PANEL_PASS = "Momin"

# ================== URLS & HEADERS ==================
BASE_URL = "http://139.99.63.204"
LOGIN_PAGE_URL = f"{BASE_URL}/ints/login"
LOGIN_ACTION_URL = f"{BASE_URL}/ints/signin"
DATA_URL = f"{BASE_URL}/ints/client/res/data_smscdr.php"
REFERER_URL = f"{BASE_URL}/ints/client/SMSCDRStats"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": BASE_URL
}

# ================== SETUP ==================
bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

sent_messages = []
is_polling_active = True # Render এ ডিফল্টভাবে চালু থাকবে
credential_mode = {}
client_session = None 

logging.basicConfig(level=logging.WARNING)

# ================== WEB SERVER FOR RENDER (KEEP ALIVE) ==================
async def handle(request):
    return web.Response(text="Bot is Running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render এই PORT এনভায়রনমেন্ট ভেরিয়েবলটি দেয়
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"🌐 Web Server running on port {port}")

# ================== HELPER FUNCTIONS ==================
def mask_number(number):
    s = str(number)
    if len(s) <= 6: return s
    if len(s) > 10: return s[:5] + "***" + s[-4:]
    return s[:3] + "***" + s[-3:]

def get_otp_code(text):
    if not text: return "Pending"
    text = str(text)
    match_hyphen = re.search(r'(\d{3})[- ](\d{3})', text)
    if match_hyphen: return match_hyphen.group(1) + match_hyphen.group(2)
    match_digits = re.search(r'(?:code|is|pin|otp|:|#|^)\s*(\d{4,8})\b', text, re.IGNORECASE)
    if match_digits: return match_digits.group(1)
    match_any = re.search(r'\b\d{6}\b', text)
    if match_any: return match_any.group(0)
    return "No-Code"

def get_country_info(row_data, phone_number=""):
    text = (str(row_data) + str(phone_number)).upper()
    if "VENEZUELA" in text or text.startswith("58"): return "Venezuela", "🇻🇪"
    if "BRAZIL" in text or text.startswith("55"): return "Brazil", "🇧🇷"
    if "ARGENTINA" in text or text.startswith("54"): return "Argentina", "🇦🇷"
    if "COLOMBIA" in text or text.startswith("57"): return "Colombia", "🇨🇴"
    if "PERU" in text or text.startswith("51"): return "Peru", "🇵🇪"
    if "NEPAL" in text or text.startswith("977"): return "Nepal", "🇳🇵"
    if "INDIA" in text or text.startswith("91"): return "India", "🇮🇳"
    if "BANGLADESH" in text or text.startswith("880"): return "Bangladesh", "🇧🇩"
    if "PAKISTAN" in text or text.startswith("92"): return "Pakistan", "🇵🇰"
    if "INDONESIA" in text or text.startswith("62"): return "Indonesia", "🇮🇩"
    if "VIETNAM" in text or text.startswith("84"): return "Vietnam", "🇻🇳"
    if "THAILAND" in text or text.startswith("66"): return "Thailand", "🇹🇭"
    if "PHILIPPINES" in text or text.startswith("63"): return "Philippines", "🇵🇭"
    if "MYANMAR" in text or text.startswith("95"): return "Myanmar", "🇲🇲"
    if "CAMBODIA" in text or text.startswith("855"): return "Cambodia", "🇰🇭"
    if "LAOS" in text or text.startswith("856"): return "Laos", "🇱🇦"
    if "AFGHAN" in text or text.startswith("93"): return "Afghanistan", "🇦🇫"
    if "CHINA" in text or text.startswith("86"): return "China", "🇨🇳"
    if "MALAYSIA" in text or text.startswith("60"): return "Malaysia", "🇲🇾"
    if "SRI LANKA" in text or text.startswith("94"): return "Sri Lanka", "🇱🇰"
    if "SUDAN" in text or text.startswith("249"): return "Sudan", "🇸🇩"
    if "EGYPT" in text or text.startswith("20"): return "Egypt", "🇪🇬"
    if "SAUDI" in text or text.startswith("966"): return "Saudi Arabia", "🇸🇦"
    if "UAE" in text or text.startswith("971"): return "UAE", "🇦🇪"
    if "IRAN" in text or text.startswith("98"): return "Iran", "🇮🇷"
    if "TURKEY" in text or text.startswith("90"): return "Turkey", "🇹🇷"
    if "KENYA" in text or text.startswith("254"): return "Kenya", "🇰🇪"
    if "NIGERIA" in text or text.startswith("234"): return "Nigeria", "🇳🇬"
    if "MOROCCO" in text or text.startswith("212"): return "Morocco", "🇲🇦"
    if "SOUTH AFRICA" in text or text.startswith("27"): return "South Africa", "🇿🇦"
    if "USA" in text or text.startswith("1"): return "USA", "🇺🇸"
    if "UK" in text or text.startswith("44"): return "UK", "🇬🇧"
    if "RUSSIA" in text or text.startswith("7"): return "Russia", "🇷🇺"
    if "GERMANY" in text or text.startswith("49"): return "Germany", "🇩🇪"
    if "FRANCE" in text or text.startswith("33"): return "France", "🇫🇷"
    if "CANADA" in text: return "Canada", "🇨🇦"
    if "ROMANIA" in text or text.startswith("40"): return "Romania", "🇷🇴"
    if "NETHERLANDS" in text or text.startswith("31"): return "Netherlands", "🇳🇱"
    return "Unknown", "🏳️"

# ================== ASYNC NETWORK ==================
async def get_client_session():
    global client_session
    if client_session is None or client_session.closed:
        jar = aiohttp.CookieJar(unsafe=True)
        client_session = aiohttp.ClientSession(cookie_jar=jar, headers=HEADERS)
    return client_session

async def perform_login(session):
    global PANEL_USER, PANEL_PASS
    print("--- Login Attempt ---")
    try:
        async with session.get(LOGIN_PAGE_URL) as resp:
            html = await resp.text()
            match = re.search(r"What is\s+(\d+)\s+\+\s+(\d+)\s+=\s+\?", html)
            if match:
                ans = int(match.group(1)) + int(match.group(2))
                login_data = {"username": PANEL_USER, "password": PANEL_PASS, "capt": ans}
                login_headers = HEADERS.copy()
                login_headers["Referer"] = LOGIN_PAGE_URL
                async with session.post(LOGIN_ACTION_URL, data=login_data, headers=login_headers) as post_resp:
                    if post_resp.status == 200:
                        print("✅ Logged In")
                        return True
    except Exception as e: print(f"Login Error: {e}")
    return False

async def get_sms_data(session, limit="25"):
    today = datetime.now()
    fdate1 = f"{today.strftime('%Y-%m-%d')} 00:00:00"
    fdate2 = f"{today.strftime('%Y-%m-%d')} 23:59:59"
    params = {"fdate1": fdate1, "fdate2": fdate2, "sEcho": "1", "iDisplayLength": limit, "sSortDir_0": "desc", "iColumns": "7"}
    fetch_headers = HEADERS.copy()
    fetch_headers["Referer"] = REFERER_URL
    try:
        async with session.get(DATA_URL, params=params, headers=fetch_headers) as resp:
            text = await resp.text()
            if "Login" in text or "<html" in text:
                if await perform_login(session): return await get_sms_data(session, limit)
                return None
            return json.loads(text)
    except: return None

# ================== HANDLERS ==================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("🚀 **Bot Active on Render**")

@dp.callback_query()
async def callback_otp(call: types.CallbackQuery):
    await call.answer(text=f"{call.data}", show_alert=True)

# ================== MAIN LOOP ==================
async def scanner_loop():
    print("--- Scanner Started ---")
    session = await get_client_session()
    if await perform_login(session):
        idata = await get_sms_data(session, "2000")
        if idata and "aaData" in idata:
            for row in idata["aaData"]:
                try: sent_messages.append(f"{row[2]}_{row[0]}")
                except: pass
        print("History Cleared.")

    while True:
        try:
            data = await get_sms_data(session, "25")
            if data and "aaData" in data:
                for row in data["aaData"]:
                    try:
                        msg_time = row[0]
                        full_row_text = " ".join([str(x) for x in row])
                        phone_number = row[2]
                        if str(phone_number) == "0" or len(str(phone_number)) < 5: continue
                        unique_id = f"{phone_number}_{msg_time}"
                        if unique_id not in sent_messages:
                            flag, country_name = get_country_info(full_row_text)
                            otp = get_otp_code(full_row_text)
                            service = "WhatsApp"
                            masked_num = mask_number(phone_number)
                            text_body = (
                                f"✅ <b>{flag} {country_name} {service} OTP Received!</b>\n"
                                f"━━━━━━━━━━━━━━\n"
                                f"📱 <b>Number:</b> <code>{masked_num}</code>\n"
                                f"🌍 <b>Country:</b> {flag} {country_name}\n"
                                f"⚙️ <b>Service:</b> {service}\n"
                                f"🔐 <b>OTP Code:</b> <code>{otp}</code>\n"
                                f"⏳ <b>Time:</b> {msg_time}\n"
                                f"━━━━━━━━━━━━━━\n"
                                f"<b>Message:</b>\n"
                                f"<blockquote><code>{otp}</code></blockquote>"
                            )
                            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"❐ {otp}", callback_data=otp)]])
                            await bot.send_message(TELEGRAM_CHAT_ID, text_body, reply_markup=kb)
                            sent_messages.append(unique_id)
                            if len(sent_messages) > 5000: sent_messages.pop(0)
                    except: continue
        except: pass
        await asyncio.sleep(5)

async def main():
    # ওয়েব সার্ভার এবং বট একসাথে রান হবে
    await asyncio.gather(
        start_web_server(),
        scanner_loop(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass
