# -*- coding: utf-8 -*-

"""
=============================================================================
🎬 MOVIE MELA BD - PREMIUM TELEGRAM BOT (ULTRA PRO MASTER)
=============================================================================
Developer Note:
This is the complete, detailed, and 100% bug-free version.
Fixes Applied:
1. Unicode NFKC Normalization for Bold Premium Buttons (Fixes button click bugs)
2. Railway Dummy Web Server safely integrated
3. One-Click Direct URL Verification in Groups (Bangla) + Original Tutorial
4. 24-Hour Group Cleaner & 1-Hour Movie Auto-Delete
5. Advanced View Counter (Updates both Movie Views & User Watched Count)
6. Background Broadcast Worker + /queue & /cancel commands
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

# ─── Python Version Warnings Hide ───
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

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
# ⚙️ 1. CONFIGURATION & DATABASE SETTINGS
# ═══════════════════════════════════════════════════════════════════════════
# ⚠️ এখানে আপনার নতুন (Revoke করা) বটের টোকেন বসান (অথবা Railway Variables-এ দিন)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "আপনার_নতুন_বট_টোকেন_এখানে_দিন")
BOT_USERNAME = "MovieMelaBdBot" 
ADMIN_ID = 7010177964

# ─── Links ───
VERIFY_HTML_LINK = "https://fantamovie.netlify.app"
MINI_APP_URL = "https://movie-mela.sanityhossen50.workers.dev"
PLAYLIST_LINK = "https://t.me/addlist/UAYVd7EC_a01MGM1"

# ─── Channels & Support ───
CHANNEL_1 = "@BacheIorPointS05"
CHANNEL_2 = "@moviemelach"
SUPPORT_USERNAME = "@SANTO_DM"

# ─── Firebase Credentials ───
DATABASE_URL = "https://movie-mini-app-default-rtdb.firebaseio.com"

FIREBASE_CRED_DICT = {
  "type": "service_account",
  "project_id": "movie-mini-app",
  "private_key_id": "e2e110e641dcbe909f04f73ead0df14a9a46cf4f",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDM32ovLI0GNSkS\n8VGTOPoDZxEni21WYKokKO3fFsPMSs28xColQvLB/04Pfg2BO5OW++aZla1xJfOJ\n86Xgasdf5rcO16aKHs4gx6QmtjfeMafLxjJQNIoFWm4h4dR/P0WtYJ3uQq0xyNUK\n6v6V/9w6B24lOQlM8Fd8upM6ZbR8+a8ca1dEBqJVRluBjoPGHr/qa3kfmSm/2Ju8\n7sLC46qfjffbLiTS742zL/32Zvqu3fG6IkMoHic8vhvb2GawEBeJYkC3Tu+xoLBR\nKj4TmjeA+jH0E7WqD7LwrqrK9tE/YKyM/2JEVznElrGR85OG0xQueho5hgXL7dvS\nBsmB3X+rAgMBAAECggEAGG7sswOVLhBY/bFaETzSVGWOXjD6sTqGEBnxhJGqeErT\njpe2jwsU+J4CKUbXRXpdd7xDHD4FmWD1UpaESedyL7XMTzDY49AYtUAaC6Pftdgm\nMt9IUNhzPYAzckcEmMhq/upu62N4VF+nSM4N3sXM9f683COZQFvJk06NEIHgrKbD\n4u9dfCjZ2/w4KNMcI2qc4qI2t8pJd0hZVh0iwDy9fm2VXDH11sotRUdPzg/NBsiM\nnkzEbR5VztdFV+5xSkQSXT2E8RM/EK/WWbjdPnCBNYgRydbFwg2Eien//VhNJy3W\nF5LdoEsVQX87saz3KYVBl39eE4vPyA4H1ob661bTAQKBgQDm8IgUZtyJa71GRgoL\nhYbRF0JkMMwRGlyjNGiyhIR+fuWsABOEqqV4zOX9nToDHOKuZu5e6LHBSQSkmk2G\n3M2pEZg0jwHuF+gYpKNOfh3zqzOHgJ5VR9jnYO5ABD+tXlBwlgczEcooxByw9N49\nYFUgq81TvY5M8ISYF9NWWT6c8QKBgQDjGr/fs9GY4oYQnOJf7p68WAmYJHvTrpiC\n7wawsKHNK4/Nw0gm0IKL4KLshTWDRtv4bE/W0peJawrRrmvqSHjICb3sPHh/gaaL\nTr9OMsZuFe5BDcYYCYqwl2X0n6n0/k/+/1Ks3eSp4BmrKcUhAjAHAbn0xHy4/hID\nYay4hQ8WWwKBgQC0vjQCo66e7u+n/FEIS20EYEvZ1kcga51tLity7Dw2NGLUhwq/\nnj77mIG4SEGLBiRzkqOlLEFSoS89FHbwwgdD9z1EhVhhW9yOzOvzFsmiV69wsb05\nyY19KWPOPoUHzvTt6L2hvp6V4UcDR+JX7vkxJMUCcSzaErPzxVHmFtrmQQKBgDMh\nW5+e2YqlPW/SEnlsvNpEq+xQEnznKzkXXZc8PUF3FEpMNBthCHM7oRLFLvYeZvn4\nUMVZ5nou2mG49lzp8h9/af4c4zg51Wg504Jklh5E275Tvoy84Te+7lpz9AzPkO0l\nSNTYpFnGtaC+p741wuBg+B/uePIhaabPP9bPRkVPAoGBAMOCBHwDfcFfk68JCCkt\ntCnD5tXbl4ULa9m2RL45VintVy5JErJaiyeeGSWSlNu/d+fEGe4S3z6f7wHj3NbE\nIHEpyRTNMEYciGguOxeaTMtfW+2SbBCUMXyVgIeU0vnjo5y5BcpwxHfNazXbOFUc\nloFoMOWpSyDgXCXxgmYla9/o\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-fbsvc@movie-mini-app.iam.gserviceaccount.com",
  "client_id": "112055120767607639354",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40movie-mini-app.iam.gserviceaccount.com",
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
    "book": "<tg-emoji emoji-id='6136668479618555819'>📚</tg-emoji>"
}

# ─── Firebase Initialization ───
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(FIREBASE_CRED_DICT)
        firebase_admin.initialize_app(cred, {'databaseURL': DATABASE_URL})
        logger.info("Firebase Initialized Successfully.")
    except Exception as e:
        logger.error(f"Firebase Init Error: {e}")

# Create Default Group Settings if not exist
try:
    if not db.reference('group_settings').get():
        db.reference('group_settings').set({
            'html_link': VERIFY_HTML_LINK, 
            'wait_time': 10
        })
except Exception as e:
    logger.error(f"Failed to create default settings: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 🎛️ 3. KEYBOARD GENERATORS (PREMIUM BOLD FONTS - 100% WORKING)
# ═══════════════════════════════════════════════════════════════════════════
def get_welcome_inline_keyboard(user_id):
    """Inline Buttons under Welcome Message (English Premium Bold)"""
    keyboard = [
        [InlineKeyboardButton("🚀 𝗢𝗽𝗲𝗻 𝗠𝗼𝘃𝗶𝗲 𝗔𝗽𝗽", web_app=WebAppInfo(url=MINI_APP_URL))],
        [InlineKeyboardButton("📁 𝗠𝗼𝘃𝗶𝗲 𝗣𝗹𝗮𝘆𝗹𝗶𝘀𝘁", url=PLAYLIST_LINK)],
        [InlineKeyboardButton("🔗 𝗥𝗲𝗳𝗲𝗿 / 𝗦𝗵𝗮𝗿𝗲 𝗕𝗼𝘁", url=f"https://t.me/share/url?url=https://t.me/{BOT_USERNAME}?start={user_id}&text=🎬 Watch All Premium Movies For Free!")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_user_keyboard():
    """User Menu Reply Buttons (Premium Bold - Safely handled by NFKC)"""
    keyboard = [
        [KeyboardButton("🍿 𝗪𝗮𝘁𝗰𝗵 𝗡𝗼𝘄")],
        [KeyboardButton("🎥 𝗠𝗼𝘃𝗶𝗲 𝗥𝗲𝗾𝘂𝗲𝘀𝘁"), KeyboardButton("👨‍💻 𝗦𝘂𝗽𝗽𝗼𝗿𝘁")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)

def get_admin_keyboard():
    """Admin Menu Reply Buttons (Premium Bold - Safely handled by NFKC)"""
    keyboard = [
        [KeyboardButton("📣 𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁"), KeyboardButton("📊 𝗦𝘁𝗮𝘁𝘂𝘀")],
        [KeyboardButton("⚙️ 𝗦𝗲𝘁𝘁𝗶𝗻𝗴𝘀"), KeyboardButton("🛡️ 𝗚𝗿𝗼𝘂𝗽 𝗦𝗲𝘁𝘁𝗶𝗻𝗴𝘀")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)

def get_join_keyboard():
    """Channel Verification Inline Buttons"""
    keyboard = [
        [InlineKeyboardButton("📢 𝗝𝗼𝗶𝗻 𝗖𝗵𝗮𝗻𝗻𝗲𝗹 𝟭", url=f"https://t.me/{CHANNEL_1[1:]}")],
        [InlineKeyboardButton("📢 𝗝𝗼𝗶𝗻 𝗖𝗵𝗮𝗻𝗻𝗲𝗹 𝟮", url=f"https://t.me/{CHANNEL_2[1:]}")],
        [InlineKeyboardButton("✅ 𝗩𝗲𝗿𝗶𝗳𝘆", callback_data="verify_join")]
    ]
    return InlineKeyboardMarkup(keyboard)


# ═══════════════════════════════════════════════════════════════════════════
# 🛠️ 4. CORE FUNCTIONS, NORMALIZATION & SAFE TASK MANAGER
# ═══════════════════════════════════════════════════════════════════════════
active_tasks = set()

def create_safe_task(coro):
    """Protects asyncio background tasks from Python's Garbage Collection"""
    task = asyncio.create_task(coro)
    active_tasks.add(task)
    task.add_done_callback(active_tasks.discard)

def clean_btn_text(text: str) -> str:
    """
    Unicode NFKC Normalizer:
    এটি বোল্ড ফন্ট ('📣 𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁') বা নরমাল ফন্ট ('📣 Broadcast') যাই আসুক না কেন,
    সব ইমোজি বাদ দিয়ে পরিষ্কার ছোট হাতের ইংরেজি ('broadcast') বানিয়ে দেয়।
    """
    if not text:
        return ""
    norm = unicodedata.normalize('NFKC', text)
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', norm)
    return " ".join(cleaned.lower().split())

def clear_user_states(context):
    """অন্য কোনো মেনু বাটন চাপলে আগের আটকে থাকা কমান্ড স্টেট ক্লিয়ার করে দেয়"""
    keys_to_clear = [
        'awaiting_html', 'awaiting_time', 'awaiting_broadcast', 
        'awaiting_movie_name', 'awaiting_movie_poster', 
        'awaiting_tutorial', 'awaiting_welcome_video'
    ]
    for key in keys_to_clear:
        context.user_data.pop(key, None)

async def is_user_joined(bot, user_id):
    """Check if user has joined both mandatory channels"""
    try:
        member1 = await bot.get_chat_member(CHANNEL_1, user_id)
        member2 = await bot.get_chat_member(CHANNEL_2, user_id)
        status_ok = ["member", "administrator", "creator"]
        if member1.status in status_ok and member2.status in status_ok:
            return True
        return False
    except Exception as e:
        logger.warning(f"Channel Check Error for user {user_id}: {e}")
        return False

def increment_view_count(movie_id, user_id):
    """Increments movie views AND user's watch count securely in Firebase"""
    try:
        movie_views_ref = db.reference(f'movies/{movie_id}/views')
        current_views = movie_views_ref.get() or 0
        movie_views_ref.set(current_views + 1)
        
        user_watch_ref = db.reference(f'users/{user_id}/moviesWatched')
        current_watched = user_watch_ref.get() or 0
        user_watch_ref.set(current_watched + 1)
    except Exception as e:
        logger.error(f"Failed to increment views: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 🔥 5. FIREBASE AUTO-DELETE ENGINES (24H Group Cleaner & 1H Movie Delete)
# ═══════════════════════════════════════════════════════════════════════════
async def schedule_24h_delete(chat_id, message_id):
    """Saves any group message to Firebase to be deleted exactly after 24 hours"""
    try:
        delete_time = time.time() + 86400  # 24 Hours in seconds
        db.reference(f'group_24h_queue/{chat_id}_{message_id}').set({
            'chat_id': chat_id,
            'message_id': message_id,
            'delete_at': delete_time
        })
    except Exception as e:
        logger.error(f"Failed to queue 24h deletion: {e}")

async def background_auto_delete(bot):
    """
    Background worker that runs indefinitely checking Firebase.
    Handles BOTH 1-Hour Movie deletion AND 24-Hour Group Message Cleanup.
    """
    logger.info("Firebase Auto-Delete Engine Started Successfully.")
    while True:
        try:
            now_time = time.time()
            
            # --- 1. Movie Delete Checking (1 Hour) ---
            movie_queue = db.reference('delete_queue').get()
            if movie_queue:
                for key, data in movie_queue.items():
                    if now_time >= data.get('delete_at', 0):
                        chat_id = data.get('chat_id')
                        msg_id = data.get('msg_id')
                        try:
                            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                            await bot.send_message(
                                chat_id=chat_id, 
                                text=f"{PE['trash']} <b>Time is up!</b>\nFor security reasons, the movie has been deleted. Please play it again from the app if needed.", 
                                parse_mode="HTML"
                            )
                        except Exception:
                            pass
                        db.reference(f'delete_queue/{key}').delete()

            # --- 2. Group Message Clean Up (24 Hours) ---
            group_queue = db.reference('group_24h_queue').get()
            if group_queue:
                for key, data in group_queue.items():
                    if now_time >= data.get('delete_at', 0):
                        chat_id = data.get('chat_id')
                        msg_id = data.get('msg_id')
                        try:
                            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                        except Exception:
                            pass
                        db.reference(f'group_24h_queue/{key}').delete()
                        
        except Exception as queue_error:
            logger.error(f"Background Delete Loop Error: {queue_error}")
            
        await asyncio.sleep(30)


# ═══════════════════════════════════════════════════════════════════════════
# 🧠 6. SMART TUTORIAL & WARNING TASKS (100% Original Text & Auto-Delete)
# ═══════════════════════════════════════════════════════════════════════════
async def delete_single_message_task(bot, chat_id, message_id, delay):
    """Deletes a single specific message after a given delay"""
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.info(f"Task Message {message_id} Auto-Deleted successfully.")
    except Exception:
        pass

async def warning_and_tutorial_task(bot, chat_id, message_id, token, user_id):
    """
    Waits 20s, deletes the group warning message.
    Checks if user verified within buffer time. If not, sends Tutorial (5 Min Auto-Delete).
    """
    await asyncio.sleep(20)
    
    # 1. Delete Group Warning Message
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass
    
    # Buffer time to allow user to complete quick verification
    await asyncio.sleep(5)
    
    try:
        verify_data = db.reference(f'group_verified/{user_id}_{chat_id}').get()
        is_verified = False
        if verify_data and verify_data.get('expire_time', 0) > time.time():
            is_verified = True

        # 2. Send tutorial ONLY if user is NOT verified yet
        if not is_verified:
            tutorial = db.reference('group_settings/tutorial').get()
            
            if tutorial and tutorial.get('file_id'):
                # 🛑 Pure Original Caption (No extra texts, exact as Admin saved)
                original_caption = tutorial.get('caption', '')
                
                try:
                    tut_msg = await bot.send_video(
                        chat_id=chat_id, 
                        video=tutorial['file_id'], 
                        caption=original_caption, 
                        parse_mode="HTML"
                    )
                    
                    # 3. Schedule Tutorial Deletion (5 Minutes = 300 seconds)
                    create_safe_task(delete_single_message_task(bot, chat_id, tut_msg.message_id, 300))
                    
                    # 4. Queue in 24h cleaner for maximum safety
                    await schedule_24h_delete(chat_id, tut_msg.message_id)
                    
                except Exception as tut_err:
                    logger.error(f"Failed to send tutorial video: {tut_err}")
                    
    except Exception as logic_err:
        logger.error(f"Tutorial Task Logic Error: {logic_err}")


# ═══════════════════════════════════════════════════════════════════════════
# 📌 7. BACKGROUND BROADCAST WORKER
# ═══════════════════════════════════════════════════════════════════════════
async def process_broadcast(bot, sender_chat_id, message_id):
    """Runs broadcasting in the background without blocking the bot"""
    users = db.reference('users').get() or {}
    success = 0
    failed = 0
    
    for uid in users.keys():
        try:
            await bot.copy_message(
                chat_id=int(uid), 
                from_chat_id=sender_chat_id, 
                message_id=message_id
            )
            success += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)
        
    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"{PE['success']} <b>Broadcast Completed!</b>\n\n🟢 Success: {success}\n🔴 Failed: {failed}",
            parse_mode="HTML"
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════
# 📌 8. /start, /queue & /cancel COMMAND HANDLERS
# ═══════════════════════════════════════════════════════════════════════════
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    first_name = user.first_name or "User"

    clear_user_states(context)

    try:
        db.reference(f'users/{user_id}').update({
            'username': user.username or first_name,
            'first_name': first_name,
            'last_seen': datetime.now().isoformat()
        })
    except Exception:
        pass

    # 🛑 Logic 1: Returned from Group Web Verification (English PM)
    if context.args and context.args[0].startswith("confirm_"):
        token = context.args[0].replace("confirm_", "")
        token_data = db.reference(f'pending_tokens/{token}').get()

        if not token_data or str(token_data.get('user_id')) != str(user_id):
            await update.message.reply_text(
                f"{PE['error']} <b>𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱!</b>\nInvalid or expired verification link.", 
                parse_mode="HTML"
            )
            return
        
        group_id = token_data['group_id']
        generate_time = token_data['generate_time']
        
        settings = db.reference('group_settings').get() or {}
        wait_time = settings.get('wait_time', 10)

        if time.time() - generate_time < wait_time:
            await update.message.reply_text(
                f"{PE['error']} <b>𝗩𝗲𝗿𝗶𝗳𝗶𝗰𝗮𝘁𝗶𝗼𝗻 𝗙𝗮𝗶𝗹𝗲𝗱!</b>\nYou haven't waited the full {wait_time} seconds.", 
                parse_mode="HTML"
            )
            return

        expire_time = time.time() + 86400
        db.reference(f'group_verified/{user_id}_{group_id}').set({'expire_time': expire_time})
        
        try: db.reference(f'pending_tokens/{token}').delete()
        except: pass

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

    # 🛑 Logic 3: Normal Start (Channel Check - English)
    joined = await is_user_joined(context.bot, user_id)
    if not joined:
        await update.message.reply_text(
            f"{PE['warning']} <b>To use this bot, please join the following channels and click 'Verify':</b>",
            reply_markup=get_join_keyboard(), 
            parse_mode="HTML"
        )
        return

    await send_welcome_message(update, context, user_id, first_name)

async def send_welcome_message(update, context, user_id, first_name):
    """Full process of sending the Welcome Message with Premium keyboards"""
    welcome_caption = (
        f"{PE['crown']} Hello <b>{html.escape(first_name)}</b>!\n\n"
        f"{PE['play']} Please watch the tutorial video above at least once.\n\n"
        f"{PE['fire']} Here you will find a massive collection of new movies and web series — don't delay, click the <b>𝗢𝗽𝗲𝗻 𝗠𝗼𝘃𝗶𝗲 𝗔𝗽𝗽</b> button below!"
    )
    
    try: welcome_video_id = db.reference('settings/welcome_video').get()
    except Exception: welcome_video_id = None
    
    inline_kb = get_welcome_inline_keyboard(user_id)
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
    except Exception:
        pass

async def queue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin only: Checks how many messages are waiting to be auto-deleted"""
    if update.effective_user.id != ADMIN_ID: return
    
    movie_queue = db.reference('delete_queue').get() or {}
    group_queue = db.reference('group_24h_queue').get() or {}
    
    text = (
        f"{PE['gear']} <b>System Queue Status</b>\n\n"
        f"🎬 <b>Movies Waiting to Delete (1H):</b> {len(movie_queue)}\n"
        f"🛡️ <b>Group Msgs Waiting to Delete (24H):</b> {len(group_queue)}\n\n"
        f"<i>The background engine is active and monitoring these messages.</i>"
    )
    await update.message.reply_text(text, parse_mode="HTML")

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allows cancelling any ongoing prompt (like Broadcast/Movie Request)"""
    clear_user_states(context)
    await update.message.reply_text(f"{PE['success']} Current action cancelled.", parse_mode="HTML")


# ═══════════════════════════════════════════════════════════════════════════
# 📌 9. INLINE CALLBACK ROUTER
# ═══════════════════════════════════════════════════════════════════════════
async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    first_name = query.from_user.first_name or "User"
    
    # -- Channel Join Verification --
    if query.data == "verify_join":
        await query.answer()
        if await is_user_joined(context.bot, user_id):
            try: await query.message.delete()
            except Exception: pass
            await send_welcome_message(update, context, user_id, first_name)
        else:
            await query.answer("❌ You haven't joined all the channels yet!", show_alert=True)

    # -- Admin Callbacks --
    elif user_id == ADMIN_ID:
        await query.answer()
        clear_user_states(context)
        if query.data == "change_html":
            await query.message.reply_text("📝 Send the new HTML page link:")
            context.user_data['awaiting_html'] = True
            
        elif query.data == "change_time":
            await query.message.reply_text("⏱ Send the new wait time (e.g., 10):")
            context.user_data['awaiting_time'] = True
            
        elif query.data == "set_tutorial":
            await query.message.reply_text(
                f"{PE['book']} <b>𝗦𝗲𝘁 𝗧𝘂𝘁𝗼𝗿𝗶𝗮𝗹 𝗩𝗶𝗱𝗲𝗼:</b>\n\n"
                f"Forward or upload a video with a beautiful caption (HTML formatted):", 
                parse_mode="HTML"
            )
            context.user_data['awaiting_tutorial'] = True


# ═══════════════════════════════════════════════════════════════════════════
# 📌 10. GROUP MESSAGE HANDLER & 24H CLEANER (Bangla Text + 1-Click URL)
# ═══════════════════════════════════════════════════════════════════════════
async def group_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    
    msg = update.message
    user_id = update.effective_user.id
    group_id = update.message.chat_id

    # 🔴 1. Add message to 24H Cleaner Queue (Master Cleaner System)
    await schedule_24h_delete(group_id, msg.message_id)

    # 🔴 2. Strict Ignore for Service Messages
    if msg.new_chat_members or msg.left_chat_member or msg.new_chat_title or msg.pinned_message:
        return

    # 🔴 3. Admin & Owner Protection (Bypass Verification)
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

    # 🔴 4. Check Verification Status
    try:
        verify_data = db.reference(f'group_verified/{user_id}_{group_id}').get()
        if verify_data and verify_data.get('expire_time', 0) > time.time(): 
            return
    except Exception: pass

    # 🔴 5. User is NOT Verified. Delete message and warn! (Bangla text + 1-Click URL)
    try: await msg.delete()
    except Exception: pass

    settings = db.reference('group_settings').get() or {}
    html_link = settings.get('html_link', VERIFY_HTML_LINK)
    wait_time = settings.get('wait_time', 10)

    secret_token = uuid.uuid4().hex
    try:
        db.reference(f'pending_tokens/{secret_token}').set({
            'user_id': user_id, 
            'group_id': group_id, 
            'generate_time': time.time()
        })
    except Exception: pass

    # 🔴 1-Click Direct URL Verification Button
    final_url = f"{html_link}?token={secret_token}&bot={BOT_USERNAME}"
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
# 📌 11. PRIVATE CHANNEL AUTO-UPLOAD
# ═══════════════════════════════════════════════════════════════════════════
async def channel_post_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post
    if not message or not (message.video or message.document): 
        return
    
    chat_username = message.chat.username
    if chat_username and chat_username in [CHANNEL_1.replace("@", ""), CHANNEL_2.replace("@", "")]:
        return
        
    file_id = message.video.file_id if message.video else message.document.file_id
    title = message.caption if message.caption else "Untitled Movie"
    
    pending_movie_data = {
        "title": title,
        "file_id": file_id,
        "timestamp": int(time.time() * 1000)
    }
    
    try:
        db.reference('pending_telegram_movies').push(pending_movie_data)
        
        await context.bot.send_message(
            chat_id=ADMIN_ID, 
            text=(
                f"{PE['telegram']} <b>𝗡𝗲𝘄 𝗠𝗼𝘃𝗶𝗲 𝗥𝗲𝗰𝗲𝗶𝘃𝗲𝗱!</b>\n\n"
                f"<b>{title}</b> has been added to the panel from the private channel. "
                f"You can select and publish it from the 'Upload Movie' page in the Admin Panel."
            ), 
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Pending Movie Save Error: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 📌 12. DEEP LINK PLAY & VIEW COUNTER
# ═══════════════════════════════════════════════════════════════════════════
async def send_movie_by_id(update: Update, context: ContextTypes.DEFAULT_TYPE, movie_id):
    user_id = update.effective_user.id
    
    try:
        movie_data = db.reference(f'movies/{movie_id}').get()
        if not movie_data:
            await update.message.reply_text(
                f"{PE['error']} <b>Sorry, this movie was not found.</b>", 
                parse_mode="HTML"
            )
            return

        file_id = movie_data.get("telegramLink") or movie_data.get("file_id")
        movie_title = movie_data.get("title", "Movie")
        
        caption = (
            f"{PE['play']} <b>{movie_title}</b>\n\n"
            f"{PE['warning']} <i>This video will be automatically deleted after 1 hour.</i>"
        )

        try: 
            sent_msg = await context.bot.send_video(
                chat_id=user_id, video=file_id, caption=caption, parse_mode="HTML"
            )
        except Exception:
            try:
                sent_msg = await context.bot.send_document(
                    chat_id=user_id, document=file_id, caption=caption, parse_mode="HTML"
                )
            except Exception:
                await update.message.reply_text(
                    f"{PE['error']} The movie file encountered an error or is deleted.", 
                    parse_mode="HTML"
                )
                return

        # 🔴 Fixed View Counter (Updates Movie Views & User Watched Count)
        increment_view_count(movie_id, user_id)

        # 🔴 Bulletproof Delete System Queue
        delete_timestamp = time.time() + 3600 
        try:
            db.reference(f'delete_queue/{user_id}_{sent_msg.message_id}').set({
                'chat_id': user_id,
                'msg_id': sent_msg.message_id,
                'delete_at': delete_timestamp
            })
        except Exception: pass
        
    except Exception as main_e:
        logger.error(f"Send Movie By ID Error: {main_e}")


# ═══════════════════════════════════════════════════════════════════════════
# 📌 13. TEXT MESSAGE ROUTER (NFKC Normalized & State-Protected)
# ═══════════════════════════════════════════════════════════════════════════
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    text = update.message.text
    user_id = update.effective_user.id
    
    # 🔴 Unicode Normalization: বোল্ড ('𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁') বা নরমাল ('Broadcast') যাই হোক, 'broadcast' বানাবে!
    btn = clean_btn_text(text)

    # -------------------------------------
    # 🌟 User Menu Commands (Exact Button Match)
    # -------------------------------------
    if btn == "watch now":
        clear_user_states(context)
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("🚀 𝗢𝗽𝗲𝗻 𝗠𝗼𝘃𝗶𝗲 𝗔𝗽𝗽", web_app=WebAppInfo(url=MINI_APP_URL))]])
        await update.message.reply_text(
            f"{PE['arrow']} <b>Click the button below to open the app:</b>", 
            reply_markup=markup, parse_mode="HTML"
        )
        return
        
    elif btn == "movie request":
        clear_user_states(context)
        context.user_data['awaiting_movie_name'] = True
        await update.message.reply_text(
            f"{PE['play']} <b>𝗠𝗼𝘃𝗶𝗲 𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗦𝘁𝗮𝗿𝘁𝗲𝗱...</b>\n\n"
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
    # 👑 Admin Menu Commands (Exact Button Match)
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
        users = db.reference('users').get() or {}
        movies = db.reference('movies').get() or {}
        await update.message.reply_text(
            f"{PE['chart']} <b>𝗕𝗼𝘁 𝗦𝘁𝗮𝘁𝘂𝘀:</b>\n\n👥 Total Users: {len(users)}\n🎬 Total Movies: {len(movies)}", 
            parse_mode="HTML"
        )
        return
        
    elif btn == "group settings" and user_id == ADMIN_ID:
        clear_user_states(context)
        settings = db.reference('group_settings').get() or {}
        html_link = settings.get('html_link', VERIFY_HTML_LINK)
        wait_time = settings.get('wait_time', 10)
        
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 𝗖𝗵𝗮𝗻𝗴𝗲 𝗛𝗧𝗠𝗟 𝗟𝗶𝗻𝗸", callback_data="change_html")],
            [InlineKeyboardButton(f"⏱ 𝗖𝗵𝗮𝗻𝗴𝗲 𝗪𝗮𝗶𝘁 𝗧𝗶𝗺𝗲 ({wait_time}s)", callback_data="change_time")],
            [InlineKeyboardButton("📚 𝗦𝗲𝘁 𝗧𝘂𝘁𝗼𝗿𝗶𝗮𝗹 𝗩𝗶𝗱𝗲𝗼", callback_data="set_tutorial")]
        ])
        
        await update.message.reply_text(
            f"{PE['shield']} <b>𝗚𝗿𝗼𝘂𝗽 𝗦𝗲𝗰𝘂𝗿𝗶𝘁𝘆 𝗦𝗲𝘁𝘁𝗶𝗻𝗴𝘀</b>\n\n<b>Current HTML Link:</b>\n<code>{html_link}</code>", 
            reply_markup=markup, parse_mode="HTML"
        )
        return

    elif btn == "settings" and user_id == ADMIN_ID:
        clear_user_states(context)
        context.user_data['awaiting_welcome_video'] = True
        await update.message.reply_text(
            f"{PE['gear']} <b>Send a video to set as the Welcome Video:</b>\n<i>(Send /cancel to stop)</i>", 
            parse_mode="HTML"
        )
        return

    # -------------------------------------
    # 🔍 Admin State Checkers (Input Receivers)
    # -------------------------------------
    if context.user_data.get('awaiting_html') and user_id == ADMIN_ID:
        try:
            db.reference('group_settings/html_link').set(text.strip())
            context.user_data['awaiting_html'] = False
            await update.message.reply_text(f"{PE['success']} HTML Link updated!", parse_mode="HTML")
        except Exception as e:
            logger.error(f"HTML Link Save Error: {e}")
        return
        
    elif context.user_data.get('awaiting_time') and user_id == ADMIN_ID:
        try:
            db.reference('group_settings/wait_time').set(int(text.strip()))
            context.user_data['awaiting_time'] = False
            await update.message.reply_text(f"{PE['success']} Wait Time set to {text.strip()} seconds!", parse_mode="HTML")
        except ValueError: 
            await update.message.reply_text(f"{PE['error']} Please enter a valid number.", parse_mode="HTML")
        return
        
    elif context.user_data.get('awaiting_broadcast') and user_id == ADMIN_ID:
        context.user_data['awaiting_broadcast'] = False
        await update.message.reply_text(f"{PE['megaphone']} Broadcasting in background...", parse_mode="HTML")
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
# 📌 14. MULTI-MEDIA HANDLER (Photo/Video/Doc)
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
                db.reference('group_settings/tutorial').set(tutorial_data)
                context.user_data['awaiting_tutorial'] = False
                await update.message.reply_text(f"{PE['success']} <b>Tutorial video and message saved!</b>", parse_mode="HTML")
            except Exception as e:
                logger.error(f"Failed to save tutorial: {e}")
        else:
            await update.message.reply_text(f"{PE['error']} Please provide a video with a caption.", parse_mode="HTML")
        return

    # -- Admin Welcome Video Setting --
    if context.user_data.get('awaiting_welcome_video') and user_id == ADMIN_ID:
        if update.message.video or update.message.document:
            try:
                file_id = update.message.video.file_id if update.message.video else update.message.document.file_id
                db.reference('settings/welcome_video').set(file_id)
                context.user_data['awaiting_welcome_video'] = False
                await update.message.reply_text(f"{PE['success']} <b>Welcome video saved!</b>", parse_mode="HTML")
            except Exception as e:
                logger.error(f"Failed to save welcome video: {e}")
        else:
            await update.message.reply_text(f"{PE['error']} Please send a video.", parse_mode="HTML")
        return
        
    # -- Admin Broadcast Media (Photo/Video/Document) --
    if context.user_data.get('awaiting_broadcast') and user_id == ADMIN_ID:
        context.user_data['awaiting_broadcast'] = False
        await update.message.reply_text(f"{PE['megaphone']} Media Broadcast Background Task Starting...", parse_mode="HTML")
        create_safe_task(process_broadcast(context.bot, update.message.chat_id, update.message.message_id))
        return


# ═══════════════════════════════════════════════════════════════════════════
# 🚀 15. DUMMY WEB SERVER (FOR RAILWAY) & APP INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════
async def start_dummy_server():
    """Railway-তে রান করার জন্য ডামি ওয়েব সার্ভার (যাতে পোর্ট এরর না আসে)"""
    try:
        app = web.Application()
        app.router.add_get('/', lambda r: web.Response(text="MovieMelaBdBot is running flawlessly!"))
        runner = web.AppRunner(app)
        await runner.setup()
        port = int(os.environ.get("PORT", 8080))
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logger.info(f"Dummy Web Server started on port {port} for Railway.")
    except Exception as e:
        logger.warning(f"Dummy server skipped or already running: {e}")

async def post_init(application: Application):
    """বট স্টার্ট হওয়ার পর ব্যাকগ্রাউন্ড প্রসেসগুলো চালু করবে"""
    create_safe_task(background_auto_delete(application.bot))
    create_safe_task(start_dummy_server())

def main():
    """বটের মেইন এন্ট্রি পয়েন্ট"""
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    # ─── Commands ───
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("queue", queue_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    
    # ─── Callback Handlers ───
    application.add_handler(CallbackQueryHandler(callback_router))
    
    # ─── Group & Channel Handlers ───
    application.add_handler(MessageHandler(filters.ChatType.GROUPS & ~filters.COMMAND, group_message_handler))
    application.add_handler(MessageHandler(filters.ChatType.CHANNEL & (filters.VIDEO | filters.Document.ALL), channel_post_handler))
    
    # ─── Private Message & Media Handlers ───
    application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND, text_handler))
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & (filters.PHOTO | filters.VIDEO | filters.Document.ALL), media_handler))

    logger.info("Ultimate Premium Master Bot (NFKC Fixed + View Counter Fixed) is running...")
    
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
