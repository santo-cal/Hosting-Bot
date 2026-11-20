# -*- coding: utf-8 -*-

"""
=============================================================================
🎬 HOT MOVIEE BOT - ULTIMATE MASTERPIECE (BOT 2 EDITION)
=============================================================================
Features Included:
1. Content Protection (Option 1: Movies Only) + Admin Panel ON/OFF Toggle
2. 3-Channel Force Join (Includes Private Channel Auto-Approve & /setch3)
3. 10-Minute (600s) Movie Auto-Delete + 24-Hour Group Cleaner
4. Dual Async Firebase Engine (httpx REST API + firebase_admin Fallback)
5. Unicode NFKC Normalization for Bold Premium Keyboard Buttons
6. Dynamic ?bot=HotMovieeBot Parameter on Mini App URL
7. One-Click Group Verification (Bangla) + Original Tutorial (5m Delete)
8. Private Channel Auto-Upload + Movie Request + Background Broadcast
=============================================================================
"""

import os
import re
import json
import asyncio
import logging
import uuid
import time
import html
import warnings
import unicodedata
from datetime import datetime

# ─── Hide Deprecation / EOL Warnings ───
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

import httpx
import firebase_admin
from firebase_admin import credentials, db
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    WebAppInfo, 
    ReplyKeyboardMarkup, 
    KeyboardButton
)
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    ChatJoinRequestHandler,
    ContextTypes, 
    filters
)
from aiohttp import web

# ─── Logging Setup ───
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# ⚙️ 1. CONFIGURATION & DATABASE SETTINGS (BOT 2)
# ═══════════════════════════════════════════════════════════════════════════
BOT_TOKEN = os.environ.get("BOT_TOKEN", "আপনার_নতুন_বট_টোকেন_এখানে_দিন")
BOT_USERNAME = "HotMovieeBot" 
ADMIN_ID = 7819952016

# ─── Movie Inbox Auto-Delete Timer (10 Minutes = 600 Seconds) ───
MOVIE_DELETE_SECONDS = 600
MOVIE_DELETE_LABEL = "10 minutes"

# ─── Links ───
VERIFY_HTML_LINK = "https://fantamovie.netlify.app"
MINI_APP_URL = "https://hotmoviee.sanityhossen50.workers.dev"
PLAYLIST_LINK = "https://t.me/addlist/UAYVd7EC_a01MGM1"

# ─── Channels & Support ───
CHANNEL_1 = "@BacheIorPointS05"
CHANNEL_2 = "@moviemelach"
CHANNEL_3_LINK = "https://t.me/+ApA7LXrNikY5MWE1"
CHANNEL_3_ID = 0  # ⚠️ এখানে -100... আইডি বসাতে পারেন অথবা বটকে অ্যাডমিন করে /setch3 ব্যবহার করুন
SUPPORT_USERNAME = "@None"

# ─── Firebase Credentials ───
DATABASE_URL = "https://hotmoviee-e4250-default-rtdb.firebaseio.com"

FIREBASE_CRED_DICT = {
  "type": "service_account",
  "project_id": "hotmoviee-e4250",
  "private_key_id": "6f130b98e77b0efa3d5f67ef57ba87bc9dde12b4",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQCmUL+Vn4o3em4t\nmStVeLPNcZiThh7uP+t9Br/2Cma93IOaHs6+0+nZvZNSqquv898chKo2XdQsYAd1\n2Y1a0Po9VXDveTYZO+boBpYFQRCDRRW0dCDLO8QCuCPhnrJnTnyDvX4dxpKP0N4T\ntUuAU3Hp1vR2iIk4tCDDRaESLp0mnVP7y701IAieZh/1WDnmHAuGmt6j9qiWmYq5\n69LiXIDp/g4mqHaEAmIQPfCfn+qh00ucXRNx9UU6mEMErKz5UcIvPdteHlAHmKM2\ns0l4mr5JoDQeOJsQEoU1JVNEN6z6SMD2DtttvmGp8WSiJh2K9vDXPAjmDw+Ij9au\nmdOZ8ZpvAgMBAAECggEAJeaq8lcMMX5mE2AffvflycDEa4IaFGNer/xUzKYsKcJR\n/1Jb/SLf3O4V37XjMFLcGmylOYSCcKZlrNaqHvMWw9lvxjMSQAflpCS0FXhxYejh\nfGEmhAoXriL2klkPAPni6EbLsc9p4PpRUZ50GUdq40ZIKacN1m0+NiHtBe63g2/i\n+rYnODpQ4lKYEru2QI1dLqU9umnt7ac8qZ5JiljicrgVrxFKdzrU0/nCkl9bmda0\ns5uPIs5yI8nNMLqP1FmaXMCl8GfoO2j1yxOUefgeOfWupAVWlp0nXsDe38wYk69a\nYbO4zQ0kPw44ykU0tAAio4lsF42F+jopY7ksscYhcQKBgQDTx5/0T+xQuEmyIq1R\nz468APGwpr5IXg/j7qqrSqjiLMPHxdH0fjmIFGyqWtaM7M4YnOzUc0Op+F/TqDWa\nB/JCp3oJS7eEQ+3hxhOj+7sIbmeJCSEPhP4D4dRMMQIBP7blEACYEpEvXK8UU8AD\ntHlgf5hh/F1B8YDLRPftktA3BwKBgQDJCuSz0pPpUolV9QWQt1czg35seUrQS6Wj\nJTpqYUWYins3DTmOaBUyPuWlS7rZHlida6lzJgWzbGNfmX27dP2uAq61TvaQMbEC\nMqK0hzMdZ0gVuKa2hDYEGGYicAum5heBeq7deWoGTDAyx/Zk03Exut39LwTkruZB\ndcIvVy5/WQKBgGG95WYVqQSMOX8coA99EuxUJzgXjQTLXNwe3+gUmiNg86707vS/\neQAEJS7uo80A0hHsAyX+WMFOn7OJE8wWVMpMj3dQ2c8SpuynxZLOcMDwa5qEexy1\njaLvDFNp3voClP/dRdjp4NYSGb/w81MCbW6LFSJMHiJ8OqwWFbMxKiXrAoGBAJGH\nISZKOGedJ2zhgLXRAX54oPtEkbNWDwCZ4j8/SnGxTJ/9IrzC+xT0EqgkuYyROvQ5\nCuAfleDbhNOe+DTJ6xgbOPxlvHWEgu1kWgL0Gzwdl0Ch+YwFCFTOlKA5GzYlOL6x\nYANR8D2+yOT5epJhvH6TFj4/2vru4B5ib751DWOBAoGBAMlJGcEo1n4t9+AJTc1d\nbcGg5kLUbJ8F3Od6DMiLA3QvGVjSd7Qp5rItkL8gYhW/ZjMehEmGkdUYIbAoJTYt\nbWuT15c3+oWUqIGDLl3v9wtp9KYL6aS+7UlqCFFOPHDPbiCBLJSGE8I04XAvpXmM\n2h7AqmtatkoO6iCX2q5tOPX7\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-fbsvc@hotmoviee-e4250.iam.gserviceaccount.com",
  "client_id": "102807105017356933814",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40hotmoviee-e4250.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}

# ═══════════════════════════════════════════════════════════════════════════
# 💎 2. PREMIUM EMOJIS DICTIONARY (For Text Messages Only)
# ═══════════════════════════════════════════════════════════════════════════
PE = {
    "success": "<tg-emoji emoji-id='6136416068685538337'>✅</tg-emoji>",
    "error": "<tg-emoji emoji-id='6134366742220120758'>❌</tg-emoji>",
    "warning": "<tg-emoji emoji-id='6134210817727407026'>⚠️</tg-emoji>",
    "crown": "<tg-emoji emoji-id='6113945852059856673'>👑</tg-emoji>",
    "play": "<tg-emoji emoji-id='6113763307359837382'>▶️</tg-emoji>",
    "fire": "<tg-emoji emoji-id='6136714586092479640'>🔥</tg-emoji>",
    "arrow": "<tg-emoji emoji-id='6134334916512456762'>⏩</tg-emoji>",
    "trash": "<tg-emoji emoji-id='6114016504271872719'>🗑️</tg-emoji>",
    "admin": "<tg-emoji emoji-id='6134440439563953332'>👨‍💻</tg-emoji>",
    "gear": "<tg-emoji emoji-id='6136668479618555819'>⚙️</tg-emoji>",
    "chart": "<tg-emoji emoji-id='6134234951148642215'>📊</tg-emoji>",
    "shield": "<tg-emoji emoji-id='6156447285052974009'>🛡</tg-emoji>",
    "diamond": "<tg-emoji emoji-id='6129509499280563691'>💎</tg-emoji>",
    "telegram": "<tg-emoji emoji-id='6136707074194677371'>✈️</tg-emoji>",
    "megaphone": "<tg-emoji emoji-id='6113819747525075278'>📢</tg-emoji>",
    "link": "<tg-emoji emoji-id='6136547082367934726'>🔗</tg-emoji>",
    "book": "<tg-emoji emoji-id='6136668479618555819'>📚</tg-emoji>",
    "lock": "<tg-emoji emoji-id='614113935604982164'>🔒</tg-emoji>"
}

# ─── Firebase SDK Backup Initialization ───
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(FIREBASE_CRED_DICT)
        firebase_admin.initialize_app(cred, {'databaseURL': DATABASE_URL})
        logger.info("Firebase Admin SDK initialized as backup.")
    except Exception as e:
        logger.warning(f"Firebase Admin SDK init skipped (REST API will be used): {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 🔥 3. DUAL ASYNC FIREBASE ENGINE (REST API Primary + SDK Fallback)
# ═══════════════════════════════════════════════════════════════════════════
async def fb_request(method: str, path: str, data=None):
    """
    Async Firebase Realtime Database Wrapper:
    ১. প্রথমে সুপারফাস্ট Async REST API (httpx) ব্যবহার করে।
    ২. কোনো কারণে REST API ব্লক হলে (যেমন 401), সাথে সাথে firebase_admin SDK দিয়ে কাজ করে।
    """
    clean_path = path.strip('/')
    url = f"{DATABASE_URL.rstrip('/')}/{clean_path}.json"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            if method == "GET":
                resp = await client.get(url)
            elif method == "PUT":
                resp = await client.put(url, json=data)
            elif method == "POST":
                resp = await client.post(url, json=data)
            elif method == "PATCH":
                resp = await client.patch(url, json=data)
            elif method == "DELETE":
                resp = await client.delete(url)
            else:
                return None

            if resp.status_code in (200, 204):
                if not resp.text or resp.text.strip() == "null":
                    return None
                return resp.json()
            else:
                logger.warning(f"Firebase REST HTTP {resp.status_code} on {clean_path}: {resp.text}")
    except Exception as rest_err:
        logger.warning(f"Firebase REST Error on {clean_path}: {rest_err}")

    if firebase_admin._apps:
        try:
            loop = asyncio.get_running_loop()
            ref = db.reference(clean_path)
            if method == "GET":
                return await loop.run_in_executor(None, ref.get)
            elif method == "PUT":
                await loop.run_in_executor(None, ref.set, data)
                return data
            elif method == "POST":
                res = await loop.run_in_executor(None, ref.push, data)
                return {"name": res.key}
            elif method == "PATCH":
                await loop.run_in_executor(None, ref.update, data)
                return data
            elif method == "DELETE":
                await loop.run_in_executor(None, ref.delete)
                return None
        except Exception as sdk_err:
            logger.error(f"Firebase SDK Fallback Error on {clean_path}: {sdk_err}")
            raise sdk_err

    raise RuntimeError("Firebase connection failed via both REST API and Admin SDK.")

async def fb_get(path: str):
    return await fb_request("GET", path)

async def fb_set(path: str, data):
    return await fb_request("PUT", path, data)

async def fb_push(path: str, data):
    return await fb_request("POST", path, data)

async def fb_update(path: str, data):
    return await fb_request("PATCH", path, data)

async def fb_delete(path: str):
    return await fb_request("DELETE", path)


# ═══════════════════════════════════════════════════════════════════════════
# 🎛️ 4. KEYBOARD GENERATORS (PREMIUM BOLD FONTS + 3 CHANNELS)
# ═══════════════════════════════════════════════════════════════════════════
def build_mini_app_url(bot_uname: str) -> str:
    """Appends ?bot=HotMovieeBot so Mini App always redirects back to Bot 2"""
    sep = "&" if "?" in MINI_APP_URL else "?"
    return f"{MINI_APP_URL}{sep}bot={bot_uname}"

def get_welcome_inline_keyboard(user_id, bot_uname):
    """Inline Buttons under Welcome Message (English Premium Bold)"""
    app_url = build_mini_app_url(bot_uname)
    keyboard = [
        [InlineKeyboardButton("🚀 𝗢𝗽𝗲𝗻 𝗠𝗼𝘃𝗶𝗲 𝗔𝗽𝗽", web_app=WebAppInfo(url=app_url))],
        [InlineKeyboardButton("📁 𝗠𝗼𝘃𝗶𝗲 𝗣𝗹𝗮𝘆𝗹𝗶𝘀𝘁", url=PLAYLIST_LINK)],
        [InlineKeyboardButton("🔗 𝗥𝗲𝗳𝗲𝗿 / 𝗦𝗵𝗮𝗿𝗲 𝗕𝗼𝘁", url=f"https://t.me/share/url?url=https://t.me/{bot_uname}?start={user_id}&text=🎬 Watch All Premium Movies For Free!")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_user_keyboard():
    """User Menu Reply Buttons"""
    keyboard = [
        [KeyboardButton("🍿 𝗪𝗮𝘁𝗰𝗵 𝗡𝗼𝘄")],
        [KeyboardButton("🎥 𝗠𝗼𝘃𝗶𝗲 𝗥𝗲𝗾𝘂𝗲𝘀𝘁"), KeyboardButton("👨‍💻 𝗦𝘂𝗽𝗽𝗼𝗿𝘁")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)

def get_admin_keyboard():
    """Admin Menu Reply Buttons"""
    keyboard = [
        [KeyboardButton("📣 𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁"), KeyboardButton("📊 𝗦𝘁𝗮𝘁𝘂𝘀")],
        [KeyboardButton("⚙️ 𝗦𝗲𝘁𝘁𝗶𝗻𝗴𝘀"), KeyboardButton("🛡️ 𝗚𝗿𝗼𝘂𝗽 𝗦𝗲𝘁𝘁𝗶𝗻𝗴𝘀")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)

def get_join_keyboard():
    """3-Channel Force Join Verification Buttons"""
    keyboard = [
        [InlineKeyboardButton("📢 𝗝𝗼𝗶𝗻 𝗖𝗵𝗮𝗻𝗻𝗲𝗹 𝟭", url=f"https://t.me/{CHANNEL_1[1:]}")],
        [InlineKeyboardButton("📢 𝗝𝗼𝗶𝗻 𝗖𝗵𝗮𝗻𝗻𝗲𝗹 𝟮", url=f"https://t.me/{CHANNEL_2[1:]}")],
        [InlineKeyboardButton("🔒 𝗝𝗼𝗶𝗻 𝗣𝗿𝗶𝘃𝗮𝘁𝗲 𝗖𝗵𝗮𝗻𝗻𝗲𝗹 𝟯", url=CHANNEL_3_LINK)],
        [InlineKeyboardButton("✅ 𝗩𝗲𝗿𝗶𝗳𝘆", callback_data="verify_join")]
    ]
    return InlineKeyboardMarkup(keyboard)


# ═══════════════════════════════════════════════════════════════════════════
# 🛠️ 5. CORE HELPERS, CHANNEL 3 CHECK & CONTENT PROTECTION FLAG
# ═══════════════════════════════════════════════════════════════════════════
active_tasks = set()

def create_safe_task(coro):
    """Protects asyncio background tasks from Python's Garbage Collection"""
    task = asyncio.create_task(coro)
    active_tasks.add(task)
    task.add_done_callback(active_tasks.discard)
    return task

def clean_btn_text(text: str) -> str:
    """Normalizes Bold Unicode & strips emojis cleanly"""
    if not text:
        return ""
    norm = unicodedata.normalize('NFKC', text)
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', norm)
    return " ".join(cleaned.lower().split())

def clear_user_states(context):
    """Clears any pending input states when a menu button or command is triggered"""
    keys_to_clear = [
        'awaiting_html', 'awaiting_time', 'awaiting_broadcast', 
        'awaiting_movie_name', 'awaiting_movie_poster', 
        'awaiting_tutorial', 'awaiting_welcome_video'
    ]
    for key in keys_to_clear:
        context.user_data.pop(key, None)

async def get_channel_3_id() -> int:
    """Gets Private Channel 3 numeric ID from config or Firebase"""
    if CHANNEL_3_ID and int(CHANNEL_3_ID) != 0:
        return int(CHANNEL_3_ID)
    try:
        saved_id = await fb_get('settings/channel_3_id')
        if saved_id:
            return int(saved_id)
    except Exception:
        pass
    return 0

async def is_protect_content_enabled() -> bool:
    """Checks if Movie Content Protection is ON (Default: True)"""
    try:
        val = await fb_get('settings/protect_content')
        if val is None:
            return True
        return bool(val)
    except Exception:
        return True

async def is_user_joined(bot, user_id):
    """Checks if user has joined Channel 1, Channel 2, AND Private Channel 3"""
    status_ok = ["member", "administrator", "creator"]
    try:
        member1 = await bot.get_chat_member(CHANNEL_1, user_id)
        member2 = await bot.get_chat_member(CHANNEL_2, user_id)
        if member1.status not in status_ok or member2.status not in status_ok:
            return False

        # Check Private Channel 3
        ch3_id = await get_channel_3_id()
        if ch3_id != 0:
            try:
                member3 = await bot.get_chat_member(ch3_id, user_id)
                if member3.status in status_ok:
                    return True
            except Exception as ch3_err:
                logger.warning(f"Channel 3 get_chat_member error: {ch3_err}")

            # Fallback for Join-Request links: check if user submitted a join request
            try:
                req_flag = await fb_get(f'ch3_requested/{user_id}')
                if req_flag:
                    return True
            except Exception:
                pass
            return False

        return True
    except Exception as e:
        logger.warning(f"Channel Check Error for user {user_id}: {e}")
        return False

async def increment_view_count(movie_id, user_id):
    """Increments movie views AND user's watch count securely in Firebase"""
    try:
        current_views = await fb_get(f'movies/{movie_id}/views') or 0
        await fb_set(f'movies/{movie_id}/views', int(current_views) + 1)
        
        current_watched = await fb_get(f'users/{user_id}/moviesWatched') or 0
        await fb_set(f'users/{user_id}/moviesWatched', int(current_watched) + 1)
    except Exception as e:
        logger.error(f"Failed to increment views: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 🔥 6. FIREBASE AUTO-DELETE ENGINES (10-Min Movie & 24H Group Cleaner)
# ═══════════════════════════════════════════════════════════════════════════
async def schedule_24h_delete(chat_id, message_id):
    """Saves any group message to Firebase to be deleted after 24 hours"""
    try:
        delete_time = time.time() + 86400
        await fb_set(f'group_24h_queue/{chat_id}_{message_id}', {
            'chat_id': chat_id,
            'message_id': message_id,
            'delete_at': delete_time
        })
    except Exception as e:
        logger.error(f"Failed to queue 24h deletion: {e}")

async def background_auto_delete(bot):
    """
    Background worker checking Firebase every 20 seconds:
    1. Sent Movies (after 10 minutes / 600s)
    2. Group Messages (after 24 hours)
    """
    logger.info("Firebase Auto-Delete Engine (10-Min Movie + 24H Group) Started Successfully.")
    while True:
        try:
            now_time = time.time()
            
            # --- 1. Movie Delete Checking (10 Minutes) ---
            movie_queue = await fb_get('delete_queue')
            if isinstance(movie_queue, dict):
                for key, data in movie_queue.items():
                    if isinstance(data, dict) and now_time >= data.get('delete_at', 0):
                        chat_id = data.get('chat_id')
                        msg_id = data.get('msg_id')
                        try:
                            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                            await bot.send_message(
                                chat_id=chat_id, 
                                text=f"{PE['trash']} <b>Time is up!</b>\nFor security reasons, the movie has been deleted after {MOVIE_DELETE_LABEL}. Please play it again from the app if needed.", 
                                parse_mode="HTML"
                            )
                        except Exception:
                            pass
                        try:
                            await fb_delete(f'delete_queue/{key}')
                        except Exception:
                            pass

            # --- 2. Group Message Clean Up (24 Hours) ---
            group_queue = await fb_get('group_24h_queue')
            if isinstance(group_queue, dict):
                for key, data in group_queue.items():
                    if isinstance(data, dict) and now_time >= data.get('delete_at', 0):
                        chat_id = data.get('chat_id')
                        msg_id = data.get('message_id') or data.get('msg_id')
                        try:
                            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                        except Exception:
                            pass
                        try:
                            await fb_delete(f'group_24h_queue/{key}')
                        except Exception:
                            pass
                        
        except Exception as queue_error:
            logger.error(f"Background Delete Loop Error: {queue_error}")
            
        await asyncio.sleep(20)


# ═══════════════════════════════════════════════════════════════════════════
# 🧠 7. SMART TUTORIAL & WARNING TASKS (100% Original Text & 5-Min Delete)
# ═══════════════════════════════════════════════════════════════════════════
async def delete_single_message_task(bot, chat_id, message_id, delay):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

async def warning_and_tutorial_task(bot, chat_id, message_id, token, user_id):
    await asyncio.sleep(20)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass
    
    await asyncio.sleep(5)
    
    try:
        verify_data = await fb_get(f'group_verified/{user_id}_{chat_id}')
        is_verified = isinstance(verify_data, dict) and verify_data.get('expire_time', 0) > time.time()

        if not is_verified:
            tutorial = await fb_get('group_settings/tutorial')
            if isinstance(tutorial, dict) and tutorial.get('file_id'):
                original_caption = tutorial.get('caption', '')
                try:
                    tut_msg = await bot.send_video(
                        chat_id=chat_id, 
                        video=tutorial['file_id'], 
                        caption=original_caption, 
                        parse_mode="HTML"
                    )
                    create_safe_task(delete_single_message_task(bot, chat_id, tut_msg.message_id, 300))
                    await schedule_24h_delete(chat_id, tut_msg.message_id)
                except Exception as tut_err:
                    logger.error(f"Failed to send tutorial video: {tut_err}")
    except Exception as logic_err:
        logger.error(f"Tutorial Task Logic Error: {logic_err}")


# ═══════════════════════════════════════════════════════════════════════════
# 📌 8. BACKGROUND BROADCAST WORKER
# ═══════════════════════════════════════════════════════════════════════════
async def process_broadcast(bot, sender_chat_id, message_id):
    try:
        users = await fb_get('users')
    except Exception as e:
        try:
            await bot.send_message(
                chat_id=ADMIN_ID,
                text=f"{PE['error']} <b>Broadcast Failed (Database Error):</b>\n<code>{html.escape(str(e))}</code>",
                parse_mode="HTML"
            )
        except Exception:
            pass
        return

    if not isinstance(users, dict) or len(users) == 0:
        try:
            await bot.send_message(
                chat_id=ADMIN_ID,
                text=f"{PE['warning']} <b>No users found in database to broadcast!</b>",
                parse_mode="HTML"
            )
        except Exception:
            pass
        return

    success = 0
    failed = 0
    last_error = ""
    
    for uid in users.keys():
        try:
            await bot.copy_message(
                chat_id=int(uid), 
                from_chat_id=sender_chat_id, 
                message_id=message_id
            )
            success += 1
        except Exception as err:
            failed += 1
            last_error = str(err)
        await asyncio.sleep(0.05)
        
    report_text = (
        f"{PE['success']} <b>Broadcast Completed!</b>\n\n"
        f"🟢 <b>Success:</b> {success}\n"
        f"🔴 <b>Failed:</b> {failed}"
    )
    if failed > 0 and last_error:
        report_text += f"\n\n<i>Last Error: {html.escape(last_error[:100])}</i>"

    try:
        await bot.send_message(chat_id=ADMIN_ID, text=report_text, parse_mode="HTML")
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════
# 📌 9. /start, /queue, /cancel & /setch3 COMMAND HANDLERS
# ═══════════════════════════════════════════════════════════════════════════
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    first_name = user.first_name or "User"

    clear_user_states(context)

    try:
        await fb_update(f'users/{user_id}', {
            'username': user.username or first_name,
            'first_name': first_name,
            'last_seen': datetime.now().isoformat()
        })
    except Exception as e:
        logger.warning(f"User Save Error: {e}")

    # 🛑 Logic 1: Group Web Verification Return
    if context.args and context.args[0].startswith("confirm_"):
        token = context.args[0].replace("confirm_", "")
        try:
            token_data = await fb_get(f'pending_tokens/{token}')
        except Exception:
            token_data = None

        if not isinstance(token_data, dict) or str(token_data.get('user_id')) != str(user_id):
            await update.message.reply_text(
                f"{PE['error']} <b>𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱!</b>\nInvalid or expired verification link.", 
                parse_mode="HTML"
            )
            return
        
        group_id = token_data['group_id']
        generate_time = token_data['generate_time']
        
        try:
            settings = await fb_get('group_settings') or {}
        except Exception:
            settings = {}
        wait_time = settings.get('wait_time', 10)

        if time.time() - generate_time < wait_time:
            await update.message.reply_text(
                f"{PE['error']} <b>𝗩𝗲𝗿𝗶𝗳𝗶𝗰𝗮𝘁𝗶𝗼𝗻 𝗙𝗮𝗶𝗹𝗲𝗱!</b>\nYou haven't waited the full {wait_time} seconds.", 
                parse_mode="HTML"
            )
            return

        expire_time = time.time() + 86400
        try:
            await fb_set(f'group_verified/{user_id}_{group_id}', {'expire_time': expire_time})
            await fb_delete(f'pending_tokens/{token}')
        except Exception as e:
            logger.error(f"Verification Save Error: {e}")

        try:
            group_info = await context.bot.get_chat(group_id)
            group_link = f"https://t.me/{group_info.username}" if group_info.username else ""
        except Exception:
            group_link = ""

        markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 𝗕𝗮𝗰𝗸 𝘁𝗼 𝗚𝗿𝗼𝘂𝗽", url=group_link)]]) if group_link else None
        
        await update.message.reply_text(
            f"{PE['success']} <b>𝗔𝗰𝗰𝗲𝘀𝘀 𝗚𝗿𝗮𝗻𝘁𝗲𝗱!</b> 🎉\n\nYou can now send unlimited messages and movie requests in the group for the next <b>24 Hours</b>.", 
            reply_markup=markup, 
            parse_mode="HTML"
        )
        return

    # 🛑 Logic 2: Deep Link (Movie Play from Mini App)
    if context.args and context.args[0].startswith("movie_"):
        movie_id = context.args[0].replace("movie_", "")
        await send_movie_by_id(update, context, movie_id)
        return

    # 🛑 Logic 3: Normal Start (3-Channel Force Join)
    joined = await is_user_joined(context.bot, user_id)
    if not joined:
        await update.message.reply_text(
            f"{PE['warning']} <b>To use this bot, please join all 3 channels below and click 'Verify':</b>",
            reply_markup=get_join_keyboard(), 
            parse_mode="HTML"
        )
        return

    await send_welcome_message(update, context, user_id, first_name)

async def send_welcome_message(update, context, user_id, first_name):
    """Sends Welcome Message (Unprotected so users can use Refer/Share)"""
    bot_uname = context.bot.username or BOT_USERNAME
    welcome_caption = (
        f"{PE['crown']} Hello <b>{html.escape(first_name)}</b>!\n\n"
        f"{PE['play']} Please watch the tutorial video above at least once.\n\n"
        f"{PE['fire']} Here you will find a massive collection of new movies and web series — don't delay, click the <b>𝗢𝗽𝗲𝗻 𝗠𝗼𝘃𝗶𝗲 𝗔𝗽𝗽</b> button below!"
    )
    
    try:
        welcome_video_id = await fb_get('settings/welcome_video')
    except Exception:
        welcome_video_id = None
    
    inline_kb = get_welcome_inline_keyboard(user_id, bot_uname)
    reply_kb = get_admin_keyboard() if user_id == ADMIN_ID else get_user_keyboard()
    target = update.message if update.message else update.callback_query.message
    
    try:
        if welcome_video_id:
            try:
                await target.reply_video(
                    video=welcome_video_id, 
                    caption=welcome_caption, 
                    reply_markup=inline_kb, 
                    parse_mode="HTML"
                )
            except Exception:
                await target.reply_text(welcome_caption, reply_markup=inline_kb, parse_mode="HTML")
        else:
            await target.reply_text(welcome_caption, reply_markup=inline_kb, parse_mode="HTML")
            
        await target.reply_text(
            f"{PE['arrow']} <b>Please select your required option from the menu below:</b>", 
            reply_markup=reply_kb, 
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Welcome Send Error: {e}")

async def setch3_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin only: Sets Private Channel 3 ID via forwarded message or direct ID"""
    if update.effective_user.id != ADMIN_ID:
        return

    ch3_id = None
    if context.args:
        try:
            ch3_id = int(context.args[0])
        except ValueError:
            pass
    elif update.message.reply_to_message and update.message.reply_to_message.forward_origin:
        origin = update.message.reply_to_message.forward_origin
        if hasattr(origin, "chat") and origin.chat:
            ch3_id = origin.chat.id

    if ch3_id:
        try:
            await fb_set('settings/channel_3_id', ch3_id)
            await update.message.reply_text(
                f"{PE['success']} <b>Private Channel 3 Connected!</b>\n"
                f"Channel ID: <code>{ch3_id}</code>\n\n"
                f"<i>Make sure @{context.bot.username or BOT_USERNAME} is an Admin in that channel!</i>",
                parse_mode="HTML"
            )
        except Exception as e:
            await update.message.reply_text(f"{PE['error']} Error: <code>{html.escape(str(e))}</code>", parse_mode="HTML")
    else:
        await update.message.reply_text(
            f"{PE['warning']} <b>How to connect Private Channel 3:</b>\n\n"
            f"1️⃣ Forward any 1 post from your Private Channel to this bot.\n"
            f"2️⃣ Reply to that forwarded message with <code>/setch3</code>\n"
            f"<i>(Or send <code>/setch3 -100xxxxxxxxxx</code> directly)</i>",
            parse_mode="HTML"
        )

async def queue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin only: Checks auto-delete queues"""
    if update.effective_user.id != ADMIN_ID: return
    
    try:
        movie_queue = await fb_get('delete_queue') or {}
        group_queue = await fb_get('group_24h_queue') or {}
        
        text = (
            f"{PE['gear']} <b>System Queue Status</b>\n\n"
            f"🎬 <b>Movies Waiting to Delete ({MOVIE_DELETE_LABEL}):</b> {len(movie_queue)}\n"
            f"🛡️ <b>Group Msgs Waiting to Delete (24H):</b> {len(group_queue)}\n\n"
            f"<i>The background engine is active and monitoring these messages.</i>"
        )
        await update.message.reply_text(text, parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"{PE['error']} Database Error: <code>{html.escape(str(e))}</code>", parse_mode="HTML")

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_user_states(context)
    await update.message.reply_text(f"{PE['success']} Current action cancelled.", parse_mode="HTML")


# ═══════════════════════════════════════════════════════════════════════════
# 📌 10. PRIVATE CHANNEL 3 AUTO-APPROVE JOIN REQUEST HANDLER
# ═══════════════════════════════════════════════════════════════════════════
async def join_request_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Automatically approves & records join requests for Private Channel 3"""
    req = update.chat_join_request
    if not req:
        return
    user_id = req.from_user.id
    chat_id = req.chat.id

    ch3_id = await get_channel_3_id()
    if ch3_id and int(chat_id) == int(ch3_id):
        try:
            await fb_set(f'ch3_requested/{user_id}', True)
        except Exception as e:
            logger.warning(f"Failed to save ch3 request for {user_id}: {e}")
        try:
            await req.approve()
            logger.info(f"Auto-approved join request for user {user_id} in Channel 3.")
        except Exception as e:
            logger.warning(f"Could not auto-approve join request (ensure bot has Invite Users permission): {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 📌 11. INLINE CALLBACK ROUTER (Verify + Settings Toggle + Group Settings)
# ═══════════════════════════════════════════════════════════════════════════
async def build_settings_panel():
    """Builds the Admin Settings inline panel showing Protection Toggle & Welcome Video"""
    protect_on = await is_protect_content_enabled()
    welcome_vid = await fb_get('settings/welcome_video')
    ch3_id = await get_channel_3_id()

    protect_label = "🔒 𝗠𝗼𝘃𝗶𝗲 𝗣𝗿𝗼𝘁𝗲𝗰𝘁𝗶𝗼𝗻: 𝗢𝗡 ✅" if protect_on else "🔓 𝗠𝗼𝘃𝗶𝗲 𝗣𝗿𝗼𝘁𝗲𝗰𝘁𝗶𝗼𝗻: 𝗢𝗙𝗙 ❌"
    vid_status = "✅ Set" if welcome_vid else "❌ Not Set"
    ch3_status = f"<code>{ch3_id}</code>" if ch3_id != 0 else "❌ Not Set (/setch3)"

    text = (
        f"{PE['gear']} <b>𝗕𝗼𝘁 𝗦𝗲𝘁𝘁𝗶𝗻𝗴𝘀</b>\n━━━━━━━━━━━━━━━━━━\n"
        f"🔒 <b>Movie Forward/Copy Protection:</b> {'ON (Protected)' if protect_on else 'OFF (Allowed)'}\n"
        f"🎬 <b>Welcome Video:</b> {vid_status}\n"
        f"📢 <b>Private Channel 3 ID:</b> {ch3_status}\n\n"
        f"<i>Tap below to toggle Movie Protection ON/OFF or change Welcome Video:</i>"
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(protect_label, callback_data="toggle_protect")],
        [InlineKeyboardButton("🎬 𝗦𝗲𝘁 𝗪𝗲𝗹𝗰𝗼𝗺𝗲 𝗩𝗶𝗱𝗲𝗼", callback_data="set_welcome_video")]
    ])
    return text, markup

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    first_name = query.from_user.first_name or "User"
    
    # -- 3-Channel Join Verification --
    if query.data == "verify_join":
        await query.answer()
        if await is_user_joined(context.bot, user_id):
            try: await query.message.delete()
            except Exception: pass
            await send_welcome_message(update, context, user_id, first_name)
        else:
            await query.answer("❌ You haven't joined all 3 channels yet!", show_alert=True)

    # -- Admin Callbacks --
    elif user_id == ADMIN_ID:
        if query.data == "toggle_protect":
            try:
                current_state = await is_protect_content_enabled()
                new_state = not current_state
                await fb_set('settings/protect_content', new_state)
                
                panel_text, panel_markup = await build_settings_panel()
                await query.message.edit_text(panel_text, reply_markup=panel_markup, parse_mode="HTML")
                await query.answer(f"Movie Protection turned {'ON ✅' if new_state else 'OFF ❌'}!")
            except Exception as e:
                await query.answer(f"Error: {str(e)[:80]}", show_alert=True)

        elif query.data == "set_welcome_video":
            await query.answer()
            clear_user_states(context)
            context.user_data['awaiting_welcome_video'] = True
            await query.message.reply_text(
                f"{PE['gear']} <b>Send a video to set as the Welcome Video:</b>\n<i>(Send /cancel to stop)</i>", 
                parse_mode="HTML"
            )

        elif query.data == "change_html":
            await query.answer()
            clear_user_states(context)
            await query.message.reply_text("📝 Send the new HTML page link:\n<i>(Send /cancel to stop)</i>", parse_mode="HTML")
            context.user_data['awaiting_html'] = True
            
        elif query.data == "change_time":
            await query.answer()
            clear_user_states(context)
            await query.message.reply_text("⏱ Send the new wait time in seconds (e.g., 10):\n<i>(Send /cancel to stop)</i>", parse_mode="HTML")
            context.user_data['awaiting_time'] = True
            
        elif query.data == "set_tutorial":
            await query.answer()
            clear_user_states(context)
            await query.message.reply_text(
                f"{PE['book']} <b>𝗦𝗲𝘁 𝗧𝘂𝘁𝗼𝗿𝗶𝗮𝗹 𝗩𝗶𝗱𝗲𝗼:</b>\n\n"
                f"Forward or upload a video with a beautiful caption (HTML formatted):\n<i>(Send /cancel to stop)</i>", 
                parse_mode="HTML"
            )
            context.user_data['awaiting_tutorial'] = True


# ═══════════════════════════════════════════════════════════════════════════
# 📌 12. GROUP MESSAGE HANDLER & 24H CLEANER (Bangla Text + 1-Click URL)
# ═══════════════════════════════════════════════════════════════════════════
async def group_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    
    msg = update.message
    user_id = update.effective_user.id
    group_id = update.message.chat_id

    await schedule_24h_delete(group_id, msg.message_id)

    if msg.new_chat_members or msg.left_chat_member or msg.new_chat_title or msg.pinned_message:
        return

    is_admin_or_owner = False
    if user_id == ADMIN_ID or msg.sender_chat or user_id == 1087968824: 
        is_admin_or_owner = True
    else:
        try:
            admins = await context.bot.get_chat_administrators(group_id)
            if any(admin.user.id == user_id for admin in admins):
                is_admin_or_owner = True
        except Exception:
            try:
                member = await context.bot.get_chat_member(group_id, user_id)
                if member.status in ['creator', 'administrator']: 
                    is_admin_or_owner = True
            except Exception: pass

    if is_admin_or_owner:
        return

    try:
        verify_data = await fb_get(f'group_verified/{user_id}_{group_id}')
        if isinstance(verify_data, dict) and verify_data.get('expire_time', 0) > time.time(): 
            return
    except Exception: pass

    try: await msg.delete()
    except Exception: pass

    try:
        settings = await fb_get('group_settings') or {}
    except Exception:
        settings = {}
        
    html_link = settings.get('html_link', VERIFY_HTML_LINK)
    wait_time = settings.get('wait_time', 10)
    bot_uname = context.bot.username or BOT_USERNAME

    secret_token = uuid.uuid4().hex
    try:
        await fb_set(f'pending_tokens/{secret_token}', {
            'user_id': user_id, 
            'group_id': group_id, 
            'generate_time': time.time()
        })
    except Exception as e:
        logger.error(f"Token Save Error: {e}")

    final_url = f"{html_link}?token={secret_token}&bot={bot_uname}"
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("🌐 ওয়েবসাইটে ভেরিফাই করুন", url=final_url)]])
    
    safe_name = html.escape(update.effective_user.first_name or "User")
    
    warning_text = (
        f"{PE['shield']} <b>সিকিউরিটি ভেরিফিকেশন</b>\n━━━━━━━━━━━━━━━━━━\n"
        f"{PE['diamond']} <b>ইউজার:</b> {safe_name}\n\n"
        f"গ্রুপে মেসেজ করার জন্য আপনাকে ভেরিফাই করতে হবে।\n"
        f"{PE['arrow']} <b>'ওয়েবসাইটে ভেরিফাই করুন'</b> বাটনে ক্লিক করে লিংকে যান।\n"
        f"{PE['arrow']} <b>{wait_time} সেকেন্ড</b> অপেক্ষা করে ফিরে আসুন।\n\n"
        f"<i>⚠️ মেসেজটি ২০ সেকেন্ড পর ডিলিট হয়ে যাবে।</i>"
    )
    
    try:
        warning_msg = await context.bot.send_message(
            chat_id=group_id, 
            text=warning_text, 
            reply_markup=markup, 
            parse_mode="HTML"
        )
        
        await schedule_24h_delete(group_id, warning_msg.message_id)
        
        create_safe_task(warning_and_tutorial_task(
            context.bot, group_id, warning_msg.message_id, secret_token, user_id
        ))
    except Exception as send_err:
        logger.error(f"Group Warning Error: {send_err}")


# ═══════════════════════════════════════════════════════════════════════════
# 📌 13. PRIVATE CHANNEL AUTO-UPLOAD
# ═══════════════════════════════════════════════════════════════════════════
async def channel_post_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post
    if not message or not (message.video or message.document): 
        return
    
    chat_username = message.chat.username
    if chat_username and chat_username in [CHANNEL_1.replace("@", ""), CHANNEL_2.replace("@", "")]:
        return

    ch3_id = await get_channel_3_id()
    if ch3_id and message.chat.id == int(ch3_id):
        return
        
    file_id = message.video.file_id if message.video else message.document.file_id
    title = message.caption if message.caption else "Untitled Movie"
    
    pending_movie_data = {
        "title": title,
        "file_id": file_id,
        "timestamp": int(time.time() * 1000)
    }
    
    try:
        await fb_push('pending_telegram_movies', pending_movie_data)
        
        await context.bot.send_message(
            chat_id=ADMIN_ID, 
            text=(
                f"{PE['telegram']} <b>𝗡𝗲𝘄 𝗠𝗼𝘃𝗶𝗲 𝗥𝗲𝗰𝗲𝗶𝘃𝗲𝗱!</b>\n\n"
                f"<b>{html.escape(title)}</b> has been added to the panel from the private channel. "
                f"You can select and publish it from the 'Upload Movie' page in the Admin Panel."
            ), 
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Pending Movie Save Error: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 📌 14. DEEP LINK PLAY, PROTECTION & 10-MINUTE AUTO-DELETE
# ═══════════════════════════════════════════════════════════════════════════
async def send_movie_by_id(update: Update, context: ContextTypes.DEFAULT_TYPE, movie_id):
    user_id = update.effective_user.id
    
    try:
        movie_data = await fb_get(f'movies/{movie_id}')
        if not isinstance(movie_data, dict):
            await update.message.reply_text(
                f"{PE['error']} <b>Sorry, this movie was not found.</b>", 
                parse_mode="HTML"
            )
            return

        file_id = movie_data.get("telegramLink") or movie_data.get("file_id")
        movie_title = movie_data.get("title", "Movie")
        
        # 🔴 Check Admin Content Protection Switch (True/False)
        protect_flag = await is_protect_content_enabled()
        
        caption = (
            f"{PE['play']} <b>{html.escape(movie_title)}</b>\n\n"
            f"{PE['warning']} <i>This video will be automatically deleted after {MOVIE_DELETE_LABEL}.</i>"
        )

        try: 
            sent_msg = await context.bot.send_video(
                chat_id=user_id, 
                video=file_id, 
                caption=caption, 
                parse_mode="HTML",
                protect_content=protect_flag
            )
        except Exception:
            try:
                sent_msg = await context.bot.send_document(
                    chat_id=user_id, 
                    document=file_id, 
                    caption=caption, 
                    parse_mode="HTML",
                    protect_content=protect_flag
                )
            except Exception:
                await update.message.reply_text(
                    f"{PE['error']} The movie file encountered an error or does not belong to this bot.", 
                    parse_mode="HTML"
                )
                return

        await increment_view_count(movie_id, user_id)

        # 🔴 Bulletproof 10-Minute Delete System Queue (600 Seconds)
        delete_timestamp = time.time() + MOVIE_DELETE_SECONDS 
        try:
            await fb_set(f'delete_queue/{user_id}_{sent_msg.message_id}', {
                'chat_id': user_id,
                'msg_id': sent_msg.message_id,
                'delete_at': delete_timestamp
            })
        except Exception as e:
            logger.error(f"Delete Queue Save Error: {e}")
        
    except Exception as main_e:
        logger.error(f"Send Movie By ID Error: {main_e}")


# ═══════════════════════════════════════════════════════════════════════════
# 📌 15. TEXT MESSAGE ROUTER (NFKC Normalized & Error-Handled)
# ═══════════════════════════════════════════════════════════════════════════
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    text = update.message.text
    user_id = update.effective_user.id
    bot_uname = context.bot.username or BOT_USERNAME
    
    btn = clean_btn_text(text)

    # -------------------------------------
    # 🌟 User Menu Commands
    # -------------------------------------
    if btn == "watch now":
        clear_user_states(context)
        app_url = build_mini_app_url(bot_uname)
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("🚀 𝗢𝗽𝗲𝗻 𝗠𝗼𝘃𝗶𝗲 𝗔𝗽𝗽", web_app=WebAppInfo(url=app_url))]])
        await update.message.reply_text(
            f"{PE['arrow']} <b>Click the button below to open the app:</b>", 
            reply_markup=markup, parse_mode="HTML"
        )
        return
        
    elif btn == "movie request":
        clear_user_states(context)
        context.user_data['awaiting_movie_name'] = True
        await update.message.reply_text(
            f"{PE['play']} <b>Movie Request Started...</b>\n\n"
            f"Please type and send the <b>name</b> of the movie you want:\n<i>(Send /cancel to stop)</i>", 
            parse_mode="HTML"
        )
        return
        
    elif btn == "support":
        clear_user_states(context)
        await update.message.reply_text(
            f"{PE['admin']} <b>For any assistance, please contact:</b>\n{SUPPORT_USERNAME}", 
            parse_mode="HTML"
        )
        return
        
    # -------------------------------------
    # 👑 Admin Menu Commands
    # -------------------------------------
    elif btn == "broadcast" and user_id == ADMIN_ID:
        clear_user_states(context)
        context.user_data['awaiting_broadcast'] = True
        await update.message.reply_text(
            f"{PE['megaphone']} <b>Send message, photo, or video for broadcast:</b>\n<i>(Send /cancel to stop)</i>",
            parse_mode="HTML"
        )
        return
        
    elif btn == "status" and user_id == ADMIN_ID:
        clear_user_states(context)
        try:
            users = await fb_get('users')
            movies = await fb_get('movies')
            user_count = len(users) if isinstance(users, dict) else 0
            movie_count = len(movies) if isinstance(movies, dict) else 0
            
            total_views = 0
            if isinstance(movies, dict):
                for m in movies.values():
                    if isinstance(m, dict):
                        total_views += int(m.get('views', 0) or 0)

            await update.message.reply_text(
                f"{PE['chart']} <b>Bot Status:</b>\n\n"
                f"👥 <b>Total Users:</b> {user_count}\n"
                f"🎬 <b>Total Movies:</b> {movie_count}\n"
                f"👁️ <b>Total Views:</b> {total_views}", 
                parse_mode="HTML"
            )
        except Exception as e:
            await update.message.reply_text(
                f"{PE['error']} <b>Status Error:</b>\n<code>{html.escape(str(e))}</code>",
                parse_mode="HTML"
            )
        return
        
    elif btn == "group settings" and user_id == ADMIN_ID:
        clear_user_states(context)
        try:
            settings = await fb_get('group_settings') or {}
            html_link = settings.get('html_link', VERIFY_HTML_LINK)
            wait_time = settings.get('wait_time', 10)
            has_tutorial = "✅ Set" if isinstance(settings.get('tutorial'), dict) and settings['tutorial'].get('file_id') else "❌ Not Set"
            
            markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 𝗖𝗵𝗮𝗻𝗴𝗲 𝗛𝗧𝗠𝗟 𝗟𝗶𝗻𝗸", callback_data="change_html")],
                [InlineKeyboardButton(f"⏱ 𝗖𝗵𝗮𝗻𝗴𝗲 𝗪𝗮𝗶𝘁 𝗧𝗶𝗺𝗲 ({wait_time}s)", callback_data="change_time")],
                [InlineKeyboardButton("📚 𝗦𝗲𝘁 𝗧𝘂𝘁𝗼𝗿𝗶𝗮𝗹 𝗩𝗶𝗱𝗲𝗼", callback_data="set_tutorial")]
            ])
            
            await update.message.reply_text(
                f"{PE['shield']} <b>Group Security Settings</b>\n\n"
                f"🔗 <b>Current HTML Link:</b>\n<code>{html.escape(str(html_link))}</code>\n\n"
                f"⏱ <b>Wait Time:</b> {wait_time} Seconds\n"
                f"📚 <b>Tutorial Video:</b> {has_tutorial}", 
                reply_markup=markup, parse_mode="HTML"
            )
        except Exception as e:
            await update.message.reply_text(
                f"{PE['error']} <b>Group Settings Error:</b>\n<code>{html.escape(str(e))}</code>",
                parse_mode="HTML"
            )
        return

    elif btn == "settings" and user_id == ADMIN_ID:
        clear_user_states(context)
        try:
            panel_text, panel_markup = await build_settings_panel()
            await update.message.reply_text(panel_text, reply_markup=panel_markup, parse_mode="HTML")
        except Exception as e:
            await update.message.reply_text(
                f"{PE['error']} <b>Settings Error:</b>\n<code>{html.escape(str(e))}</code>",
                parse_mode="HTML"
            )
        return

    # -------------------------------------
    # 🔍 Admin State Checkers
    # -------------------------------------
    if context.user_data.get('awaiting_html') and user_id == ADMIN_ID:
        try:
            await fb_update('group_settings', {'html_link': text.strip()})
            context.user_data['awaiting_html'] = False
            await update.message.reply_text(f"{PE['success']} <b>HTML Link updated successfully!</b>", parse_mode="HTML")
        except Exception as e:
            await update.message.reply_text(f"{PE['error']} Error: <code>{html.escape(str(e))}</code>", parse_mode="HTML")
        return
        
    elif context.user_data.get('awaiting_time') and user_id == ADMIN_ID:
        try:
            new_time = int(text.strip())
            await fb_update('group_settings', {'wait_time': new_time})
            context.user_data['awaiting_time'] = False
            await update.message.reply_text(f"{PE['success']} <b>Wait Time set to {new_time} seconds!</b>", parse_mode="HTML")
        except ValueError: 
            await update.message.reply_text(f"{PE['error']} Please enter a valid number.", parse_mode="HTML")
        except Exception as e:
            await update.message.reply_text(f"{PE['error']} Error: <code>{html.escape(str(e))}</code>", parse_mode="HTML")
        return
        
    elif context.user_data.get('awaiting_broadcast') and user_id == ADMIN_ID:
        context.user_data['awaiting_broadcast'] = False
        await update.message.reply_text(f"{PE['megaphone']} <b>Broadcasting in background...</b>", parse_mode="HTML")
        create_safe_task(process_broadcast(context.bot, update.message.chat_id, update.message.message_id))
        return

    # -------------------------------------
    # 🙋‍♂️ User Movie Request State
    # -------------------------------------
    elif context.user_data.get('awaiting_movie_name'):
        context.user_data['req_movie_name'] = text
        context.user_data['awaiting_movie_name'] = False
        context.user_data['awaiting_movie_poster'] = True
        await update.message.reply_text(
            f"{PE['success']} <b>Awesome!</b>\n\nYou requested the movie <b>{html.escape(text)}</b>.\nNow, please send a <b>Poster (Image)</b> of this movie:", 
            parse_mode="HTML"
        )
        return


# ═══════════════════════════════════════════════════════════════════════════
# 📌 16. MULTI-MEDIA HANDLER (Photo/Video/Animation/Doc)
# ═══════════════════════════════════════════════════════════════════════════
async def media_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    user_id = update.effective_user.id
    user = update.effective_user

    # -- User Movie Request (Poster Upload) --
    if context.user_data.get('awaiting_movie_poster'):
        if not update.message.photo:
            await update.message.reply_text(f"{PE['error']} <b>Please send only a photo (poster)!</b>", parse_mode="HTML")
            return
            
        movie_name = context.user_data.get('req_movie_name', 'Unknown Movie')
        photo_id = update.message.photo[-1].file_id
        
        caption = (
            f"{PE['fire']} <b>New Movie Request!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{PE['diamond']} <b>Movie Name:</b> <code>{html.escape(movie_name)}</code>\n"
            f"{PE['diamond']} <b>User:</b> {html.escape(user.first_name or 'User')}\n"
            f"{PE['diamond']} <b>User ID:</b> <code>{user_id}</code>\n"
            f"{PE['link']} <b>Username:</b> @{user.username if user.username else 'N/A'}"
        )
        
        try:
            await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=caption, parse_mode="HTML")
            await update.message.reply_text(
                f"{PE['success']} <b>Request Successful!</b> 🎉\n\nYour movie request has been sent to the admin. It will be uploaded very soon.", 
                parse_mode="HTML"
            )
        except Exception:
            await update.message.reply_text(f"{PE['error']} Temporary issue occurred, please try again later.", parse_mode="HTML")
            
        context.user_data['awaiting_movie_poster'] = False
        context.user_data.pop('req_movie_name', None)
        return

    # -- Admin Set Tutorial Video (100% Original Caption Preserved) --
    if context.user_data.get('awaiting_tutorial') and user_id == ADMIN_ID:
        if update.message.video:
            try:
                tutorial_data = {
                    'file_id': update.message.video.file_id,
                    'caption': update.message.caption_html or ""
                }
                await fb_set('group_settings/tutorial', tutorial_data)
                context.user_data['awaiting_tutorial'] = False
                await update.message.reply_text(f"{PE['success']} <b>Tutorial video and message saved!</b>", parse_mode="HTML")
            except Exception as e:
                await update.message.reply_text(f"{PE['error']} Failed to save tutorial: <code>{html.escape(str(e))}</code>", parse_mode="HTML")
        else:
            await update.message.reply_text(f"{PE['error']} Please provide a video with a caption.", parse_mode="HTML")
        return

    # -- Admin Welcome Video Setting --
    if context.user_data.get('awaiting_welcome_video') and user_id == ADMIN_ID:
        file_id = None
        if update.message.video:
            file_id = update.message.video.file_id
        elif update.message.animation:
            file_id = update.message.animation.file_id
        elif update.message.document:
            file_id = update.message.document.file_id

        if file_id:
            try:
                await fb_set('settings/welcome_video', file_id)
                context.user_data['awaiting_welcome_video'] = False
                await update.message.reply_text(f"{PE['success']} <b>Welcome video saved successfully!</b>", parse_mode="HTML")
            except Exception as e:
                await update.message.reply_text(f"{PE['error']} Failed to save video: <code>{html.escape(str(e))}</code>", parse_mode="HTML")
        else:
            await update.message.reply_text(f"{PE['error']} Please send a valid video file.", parse_mode="HTML")
        return
        
    # -- Admin Broadcast Media (Photo/Video/Animation/Document) --
    if context.user_data.get('awaiting_broadcast') and user_id == ADMIN_ID:
        context.user_data['awaiting_broadcast'] = False
        await update.message.reply_text(f"{PE['megaphone']} <b>Media Broadcast Background Task Starting...</b>", parse_mode="HTML")
        create_safe_task(process_broadcast(context.bot, update.message.chat_id, update.message.message_id))
        return


# ═══════════════════════════════════════════════════════════════════════════
# 🚀 17. DUMMY WEB SERVER (FOR RAILWAY) & APP INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════
async def start_dummy_server():
    """Railway-তে রান করার জন্য ডামি ওয়েব সার্ভার (যাতে পোর্ট এরর না আসে)"""
    try:
        app = web.Application()
        app.router.add_get('/', lambda r: web.Response(text="HotMovieeBot is running flawlessly!"))
        runner = web.AppRunner(app)
        await runner.setup()
        port = int(os.environ.get("PORT", 8080))
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logger.info(f"Dummy Web Server started on port {port} for Railway.")
    except Exception as e:
        logger.warning(f"Dummy server skipped or already running: {e}")

async def post_init(application: Application):
    """বট স্টার্ট হওয়ার পর ব্যাকগ্রাউন্ড প্রসেসগুলো ও ডিফল্ট সেটিংস চালু করবে"""
    try:
        if not await fb_get('group_settings'):
            await fb_set('group_settings', {'html_link': VERIFY_HTML_LINK, 'wait_time': 10})
        if await fb_get('settings/protect_content') is None:
            await fb_set('settings/protect_content', True)
    except Exception as e:
        logger.warning(f"Initial settings check failed: {e}")

    create_safe_task(background_auto_delete(application.bot))
    create_safe_task(start_dummy_server())

def main():
    """বটের মেইন এন্ট্রি পয়েন্ট"""
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    # ─── Commands ───
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("setch3", setch3_command))
    application.add_handler(CommandHandler("queue", queue_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    
    # ─── Join Request & Callback Handlers ───
    application.add_handler(ChatJoinRequestHandler(join_request_handler))
    application.add_handler(CallbackQueryHandler(callback_router))
    
    # ─── Group & Channel Handlers ───
    application.add_handler(MessageHandler(filters.ChatType.GROUPS & ~filters.COMMAND, group_message_handler))
    application.add_handler(MessageHandler(filters.ChatType.CHANNEL & (filters.VIDEO | filters.Document.ALL), channel_post_handler))
    
    # ─── Private Message & Media Handlers ───
    application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND, text_handler))
    application.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & (filters.PHOTO | filters.VIDEO | filters.ANIMATION | filters.Document.ALL), 
        media_handler
    ))

    logger.info("HotMovieeBot (10-Min Delete + Content Protection + 3-Channel Join) is running...")
    application.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
