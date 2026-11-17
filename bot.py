# -*- coding: utf-8 -*-

"""
=============================================================================
🎬 MOVIE MELA BD - PREMIUM TELEGRAM BOT (ULTRA PRO MASTER)
=============================================================================
Developer Note: 
This code is written without any shortcuts. Every function is detailed, 
properly structured, and protected with safe background tasks.
=============================================================================
"""

import os
import json
import asyncio
import logging
import uuid
import time
import html
import warnings
from datetime import datetime

# Python Version Warnings Hide
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

# ─── লগিং সেটআপ (এরর ধরার জন্য) ───
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# ⚙️ কনফিগারেশন এবং ডাটাবেস সেটিংস
# ═══════════════════════════════════════════════════════════════════════════
BOT_TOKEN = "9117805041:AAGQ7LJ7XjUI6ihn8GfuoF2fGl2mNORxABA"
BOT_USERNAME = "HotMovieeBot" 
ADMIN_ID = 7819952016

# লিংকসমূহ
VERIFY_HTML_LINK = "https://fantamovie.netlify.app"
MINI_APP_URL = "https://hotmoviee.sanityhossen50.workers.dev"
PLAYLIST_LINK = "https://t.me/addlist/UAYVd7EC_a01MGM1"

# চ্যানেল এবং সাপোর্ট
CHANNEL_1 = "@BacheIorPointS05"
CHANNEL_2 = "@moviemelach"
SUPPORT_USERNAME = "@None"

# ফায়ারবেস লিংক ও ক্রেডেনশিয়ালস
DATABASE_URL = "https://hotmoviee-e4250-default-rtdb.firebaseio.com"

FIREBASE_CRED_DICT = {
  "type": "service_account",
  "project_id": "hotmoviee-e4250",
  "private_key_id": "b0c1f42f4afc8796a15228ca486887727f80ed4e",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQCwPp/YZ+tHMI09\nAhzv8Hw6KadMQyB8C34v3/MV4I8ZeYLc7pLLbHt91EVxrvdGbwMB5njpmi0anTkF\nqixPFVXsBi6ZRhjrlS6xVDKIexx0V7ssejRHoxnP/nw5GqnDxKlOEknXociOD+SZ\nizUE0yYbWGy6NCRCFYyBv44pr2AOLnWlPZjFIbP3R9fIOtIW+MW6dip4+L9IRk9i\nu4rohLjmzuxHv7aLyyDd8tlMZrYqC5lLDxjMKToEGnAV1+U20fDy5T3B44RYqV99\n0NpEFT4vySlyRF7eg/C2h1LjW2lIwP6TGvxHGh4PWKg6UjsvK2WLR2Whqv19nFMF\nsLtJ2zKxAgMBAAECggEAAj44dmkzgUiw0iZefBRFXyUhZrL9Am8lWD0jVh4xRrZO\nmtAOKLjKT+U9dq9ZdiPwDRxj4g85rzrHMMIEGy6O6niAASiMpSTqfvcZceC6kZAo\nnEM4Op2CCi0M44TUxR58jCHnSYSwLX9YyLZ7l9fgcTJ8fG3bn0awbtn4rcxNrpMr\nORDYgzOI2RsJCLavzwZagYjPSTZ4zlmiAmGq2YZSlfKdVNYaNvaeO0Xm+rFBnKAe\nRSRtrJ5Oc6mImwhSTsvD/W7qL9wMD7BdPQWZzmmReOQ+NG8kAdzopdJqQkZDV0hI\nvIWMhmvtWvzd3w8ynLqHoAegyHg+1pOkOs2ZJOPmAQKBgQDXDQ+ad4c+QaSRirLO\ngN1E0CP1uy74NwfU5JvrcG7f/eECwYv+du+NJV+i5Y6HR32/rZO6ZhuHQcM0VADZ\n4pN7R+LWzTE12x5AbPdYMVsAuRTDGGRard8oQMN26iyt7uQlUH8flRZyjsXLRERG\n0KNnX2r4/av9CxyObQY6fEudMQKBgQDRzeVUqYM4gw6G5jhv6qqSXh0Pn0xKiVjD\nfCapkG7SQO3tyPpvwVLO6flq200HGRCUmvCk84AICtsg4Y1hYpiBUjw++LeMcS/i\nj2COXyOM5H3kKTlS1o/OgIoOWl5LkNCXbvlbcDgr0o50u2kvp1tAoKuNlE8DrGLS\ntM1oBb2NgQKBgQC/ba7wD2piLsixjcdxLyDIOodoHIHJDiN4jS+GOwVXeoUrkOJv\nV6wR9qzVMobXQPpc/8Q67t2eXxnGoOhJC/nAidMQ5oLhr/WT3+ulo/mgASDMMhBS\n7+dvy4azeezfv4Fy/d7LXEkpHJJRSKmGZ/6s7DErB5RrodJ/rekXcsFUYQKBgQCG\nDGiXZEssA0h31oZ+s0/SfwFQZvZmtUSaeit1sYutGMEsaXnhh4KyI3ox1PZtL42R\ndUGGEvJdsRn680HS1B0em31UurMDr5npxrPpo03iimcJLXGrxN1TEnui2ghffaJY\n7xWxX4z0Ku7MFKYLRYGfVEjoB7dIYI8vk0eeS/SlgQKBgGEt0M0aGWpXGCRW1bRL\n9qLybyNkQLXkXX6C37aVK3+6/7csmjsKykFIAoxw4cKr3pfGZc8bgEor/4AdNN5F\nFqOg4fXIBC0bNeh66zjbsnUAr+cea7AMN/M88Ck2Fm9aYz7goEzzyxnjoBjbfMCT\nE6dGQd6p0ogUM1v8VNcFzv2F\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-fbsvc@hotmoviee-e4250.iam.gserviceaccount.com",
  "client_id": "102807105017356933814",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40hotmoviee-e4250.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}

# ═══════════════════════════════════════════════════════════════════════════
# 💎 PREMIUM EMOJIS DICTIONARY (For Text Messages)
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

# Create Default Group Settings
try:
    if not db.reference('group_settings').get():
        db.reference('group_settings').set({
            'html_link': VERIFY_HTML_LINK, 
            'wait_time': 10
        })
except Exception as e:
    logger.error(f"Failed to create default settings: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 🎛️ কীবোর্ড জেনারেটর (Standard 3D Emojis for Buttons)
# ═══════════════════════════════════════════════════════════════════════════
def get_welcome_inline_keyboard(user_id):
    """ওয়েলকাম মেসেজের নিচের ইনলাইন বাটনসমূহ"""
    keyboard = [
        [InlineKeyboardButton("🚀 Open Movie App", web_app=WebAppInfo(url=MINI_APP_URL))],
        [InlineKeyboardButton("📁 Movie Playlist", url=PLAYLIST_LINK)],
        [InlineKeyboardButton("🔗 Refer / Share Bot", url=f"https://t.me/share/url?url=https://t.me/{BOT_USERNAME}?start={user_id}&text=🎬 Watch All Premium Movies For Free!")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_user_keyboard():
    """সাধারণ ইউজারদের মেনু বাটনসমূহ"""
    keyboard = [
        [KeyboardButton("🍿 Watch Now")],
        [KeyboardButton("🎥 Movie Request"), KeyboardButton("👨‍💻 Support")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)

def get_admin_keyboard():
    """অ্যাডমিনদের স্পেশাল মেনু বাটনসমূহ"""
    keyboard = [
        [KeyboardButton("📣 Broadcast"), KeyboardButton("📊 Status")],
        [KeyboardButton("⚙️ Settings"), KeyboardButton("🛡️ Group Settings")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)

def get_join_keyboard():
    """চ্যানেল ভেরিফিকেশন বাটনসমূহ"""
    keyboard = [
        [InlineKeyboardButton("📢 Join Channel 1", url=f"https://t.me/{CHANNEL_1[1:]}")],
        [InlineKeyboardButton("📢 Join Channel 2", url=f"https://t.me/{CHANNEL_2[1:]}")],
        [InlineKeyboardButton("✅ Verify", callback_data="verify_join")]
    ]
    return InlineKeyboardMarkup(keyboard)


# ═══════════════════════════════════════════════════════════════════════════
# 🛠️ কোর ফাংশন এবং সেফ টাস্ক ম্যানেজার
# ═══════════════════════════════════════════════════════════════════════════
active_tasks = set()

def create_safe_task(coro):
    """
    পাইথনের Garbage Collector যেন ব্যাকগ্রাউন্ড টাস্ক কিল না করে, 
    তার জন্য এই সেফ টাস্ক ম্যানেজার ব্যবহার করা হয়েছে।
    """
    task = asyncio.create_task(coro)
    active_tasks.add(task)
    task.add_done_callback(active_tasks.discard)

async def is_user_joined(bot, user_id):
    """ইউজার দুটি চ্যানেলে জয়েন আছে কিনা তা চেক করে"""
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


# ═══════════════════════════════════════════════════════════════════════════
# 🔥 24-HOUR GROUP CLEANER: সকল মেসেজ ডিলিট করার লজিক
# ═══════════════════════════════════════════════════════════════════════════
async def schedule_24h_delete(chat_id, message_id):
    """গ্রুপের যেকোনো মেসেজকে ২৪ ঘণ্টা পর ডিলিট করার জন্য ফায়ারবেসে সেভ করে"""
    try:
        delete_time = time.time() + 86400  # 24 Hours in seconds
        db.reference(f'group_24h_queue/{chat_id}_{message_id}').set({
            'chat_id': chat_id,
            'message_id': message_id,
            'delete_at': delete_time
        })
    except Exception as e:
        logger.error(f"Failed to queue 24h deletion: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 🔄 ব্যাকগ্রাউন্ড ফায়ারবেস অটো-ডিলিট ইঞ্জিন (1 Hour Movie & 24 Hour Group)
# ═══════════════════════════════════════════════════════════════════════════
async def background_movie_delete_task(bot):
    """শুধুমাত্র মুভি ডিলিট করার ব্যাকগ্রাউন্ড টাস্ক"""
    logger.info("Movie 1-Hour Auto-Delete Engine Started.")
    while True:
        try:
            now_time = time.time()
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
                                text=f"{PE['trash']} <b>সময় শেষ!</b>\nসিকিউরিটির জন্য মুভিটি ডিলিট হয়ে গেছে। আবার দেখতে চাইলে অ্যাপ থেকে প্লে করুন।", 
                                parse_mode="HTML"
                            )
                        except Exception as e:
                            logger.error(f"Error deleting movie msg: {e}")
                        db.reference(f'delete_queue/{key}').delete()
        except Exception as e:
            logger.error(f"Movie Delete Loop Error: {e}")
            
        await asyncio.sleep(30)


async def background_group_cleaner_task(bot):
    """শুধুমাত্র গ্রুপের মেসেজ ২৪ ঘণ্টা পর ক্লিন করার টাস্ক"""
    logger.info("Group 24-Hour Cleaner Engine Started.")
    while True:
        try:
            now_time = time.time()
            group_queue = db.reference('group_24h_queue').get()
            
            if group_queue:
                for key, data in group_queue.items():
                    if now_time >= data.get('delete_at', 0):
                        chat_id = data.get('chat_id')
                        msg_id = data.get('msg_id')
                        try:
                            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                        except Exception as e:
                            # মেসেজ আগে ডিলিট হয়ে গেলে এরর ইগনোর করবে
                            pass
                        db.reference(f'group_24h_queue/{key}').delete()
        except Exception as e:
            logger.error(f"Group Cleaner Loop Error: {e}")
            
        await asyncio.sleep(60) # এটি প্রতি ১ মিনিট পর চেক করবে


# ═══════════════════════════════════════════════════════════════════════════
# 🧠 স্মার্ট টিউটোরিয়াল ও ওয়ার্নিং টাস্ক (100% Fixed & Parameter Checked)
# ═══════════════════════════════════════════════════════════════════════════
async def delete_single_message_task(bot, chat_id, message_id, delay):
    """নির্দিষ্ট সময় পর একটি সিঙ্গেল মেসেজ ডিলিট করার টাস্ক (যেমন টিউটোরিয়াল)"""
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.info(f"Message {message_id} Auto-Deleted in {chat_id}")
    except Exception as e:
        logger.warning(f"Failed to auto-delete message {message_id}: {e}")

async def warning_and_tutorial_task(bot, chat_id, message_id, token, user_id, first_name):
    """
    গ্রুপে ওয়ার্নিং দেওয়ার ২০ সেকেন্ড পর চেক করবে ইউজার ভেরিফাইড কিনা।
    ভেরিফাইড না হলে তাকে হুবহু অ্যাডমিনের সেট করা টিউটোরিয়াল সেন্ড করবে 
    এবং ৫ মিনিট পর সেটি ডিলিট করবে।
    """
    # প্রথমে ঠিক ২০ সেকেন্ড অপেক্ষা করবে
    await asyncio.sleep(20)
    
    # ২০ সেকেন্ড পর ওয়ার্নিং মেসেজটি গ্রুপ থেকে ডিলিট করবে
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.info(f"Group Warning Message {message_id} Deleted successfully.")
    except Exception as e:
        logger.warning(f"Could not delete group warning message: {e}")
    
    # এক্সট্রা ৫ সেকেন্ড বাফার টাইম (ইউজার ওয়েবসাইট থেকে ফেরার সুযোগ পাওয়ার জন্য)
    await asyncio.sleep(5)
    
    # এবার ডাটাবেসে চেক করবে ইউজার কি ভেরিফাইড হয়েছে?
    try:
        verify_data = db.reference(f'group_verified/{user_id}_{chat_id}').get()
        
        is_verified = False
        if verify_data and verify_data.get('expire_time', 0) > time.time():
            is_verified = True

        # যদি ইউজার ভেরিফাইড না হয়, তবেই টিউটোরিয়াল সেন্ড করবে
        if not is_verified:
            tutorial = db.reference('group_settings/tutorial').get()
            
            if tutorial and tutorial.get('file_id'):
                # কোনো এক্সট্রা টেক্সট নয়, একদম হুবহু অ্যাডমিনের দেওয়া অরিজিনাল ক্যাপশন
                original_caption = tutorial.get('caption', '')
                
                try:
                    tut_msg = await bot.send_video(
                        chat_id=chat_id, 
                        video=tutorial['file_id'], 
                        caption=original_caption, 
                        parse_mode="HTML"
                    )
                    
                    # 🔴 টিউটোরিয়ালটি ৫ মিনিট (৩০০ সেকেন্ড) পর অটো ডিলিট হওয়ার জন্য সেফ টাস্ক
                    create_safe_task(delete_single_message_task(bot, chat_id, tut_msg.message_id, 300))
                    
                    # টিউটোরিয়াল মেসেজটিও ২৪ ঘণ্টার ক্লিনার লিস্টে অ্যাড করে দেওয়া
                    await schedule_24h_delete(chat_id, tut_msg.message_id)
                    
                    logger.info(f"Tutorial sent and queued for 5-min deletion for user {user_id}")
                except Exception as tut_err:
                    logger.error(f"Failed to send tutorial video: {tut_err}")
                    
    except Exception as logic_err:
        logger.error(f"Tutorial Task Logic Error: {logic_err}")


# ═══════════════════════════════════════════════════════════════════════════
# 📌 ১. /start কমান্ড হ্যান্ডলার
# ═══════════════════════════════════════════════════════════════════════════
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    first_name = user.first_name

    # ইউজারকে ডাটাবেসে সেভ করা বা আপডেট করা
    try:
        db.reference(f'users/{user_id}').update({
            'username': user.username or first_name,
            'first_name': first_name,
            'last_seen': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"User Save Error: {e}")

    # 🛑 লজিক ১: গ্রুপ ভেরিফিকেশন লিংক থেকে ফিরে আসলে
    if context.args and context.args[0].startswith("confirm_"):
        token = context.args[0].replace("confirm_", "")
        token_data = db.reference(f'pending_tokens/{token}').get()

        if not token_data or str(token_data.get('user_id')) != str(user_id):
            await update.message.reply_text(
                f"{PE['error']} <b>ভুল বা মেয়াদোত্তীর্ণ লিংক!</b>\nদয়া করে গ্রুপ থেকে আবার লিংকে ক্লিক করুন।", 
                parse_mode="HTML"
            )
            return
        
        group_id = token_data['group_id']
        generate_time = token_data['generate_time']
        
        settings = db.reference('group_settings').get() or {}
        wait_time = settings.get('wait_time', 10)

        # সিকিউরিটি চেক (নির্ধারিত সময় অপেক্ষা করেছে কিনা)
        if time.time() - generate_time < wait_time:
            await update.message.reply_text(
                f"{PE['error']} <b>ফাঁকিবাজি ধরা পড়েছে!</b>\nআপনি পুরোপুরি {wait_time} সেকেন্ড অপেক্ষা করেননি।", 
                parse_mode="HTML"
            )
            return

        # ভেরিফিকেশন সফল হলে ২৪ ঘন্টার জন্য আনলক করে দেওয়া
        expire_time = time.time() + 86400
        db.reference(f'group_verified/{user_id}_{group_id}').set({'expire_time': expire_time})
        
        # টোকেন রিমুভ করা
        try:
            db.reference(f'pending_tokens/{token}').delete()
        except Exception:
            pass

        # গ্রুপে ফেরত যাওয়ার জন্য গ্রুপের লিংক বের করা
        try:
            group_info = await context.bot.get_chat(group_id)
            group_link = f"https://t.me/{group_info.username}" if group_info.username else ""
        except Exception:
            group_link = ""

        markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Group", url=group_link)]]) if group_link else None
        
        await update.message.reply_text(
            f"{PE['success']} <b>ভেরিফিকেশন সফল!</b> 🎉\n\nআপনি এখন পরবর্তী <b>২৪ ঘণ্টার</b> জন্য গ্রুপে আনলিমিটেড মেসেজ ও মুভি রিকোয়েস্ট করতে পারবেন।", 
            reply_markup=markup, 
            parse_mode="HTML"
        )
        return

    # 🛑 লজিক ২: মিনি অ্যাপ থেকে মুভি প্লে করতে আসলে (Deep Link)
    if context.args and context.args[0].startswith("movie_"):
        movie_id = context.args[0].replace("movie_", "")
        await send_movie_by_id(update, context, movie_id)
        return

    # 🛑 লজিক ৩: নরমাল স্টার্ট (চ্যানেল ভেরিফিকেশন চেক)
    joined = await is_user_joined(context.bot, user_id)
    if not joined:
        await update.message.reply_text(
            f"{PE['warning']} <b>বট ব্যবহার করতে অনুগ্রহ করে নিচের চ্যানেলগুলো জয়েন করুন এবং 'Verify' বাটনে ক্লিক করুন:</b>",
            reply_markup=get_join_keyboard(), 
            parse_mode="HTML"
        )
        return

    # যদি সব ঠিক থাকে, তবে ওয়েলকাম মেসেজ পাঠানো
    await send_welcome_message(update, context, user_id, first_name)


async def send_welcome_message(update, context, user_id, first_name):
    """ওয়েলকাম মেসেজ পাঠানোর সম্পূর্ণ প্রসেস"""
    welcome_caption = (
        f"{PE['crown']} হ্যালো <b>{html.escape(first_name)}</b>!\n\n"
        f"{PE['play']} উপরের টিউটোরিয়াল ভিডিওটি অন্তত একবার দেখে নিন।\n\n"
        f"{PE['fire']} এখানে পাবেন নিত্য নতুন মুভি ও সিরিজের বিশাল কালেকশন — দেরি না করে নিচের <b>Open Movie App</b> বাটনে ক্লিক করুন!"
    )
    
    # ডাটাবেস থেকে ওয়েলকাম ভিডিও চেক করা
    try:
        welcome_video_id = db.reference('settings/welcome_video').get()
    except Exception:
        welcome_video_id = None
    
    inline_kb = get_welcome_inline_keyboard(user_id)
    reply_kb = get_admin_keyboard() if user_id == ADMIN_ID else get_user_keyboard()
    
    target = update.message if update.message else update.callback_query.message
    
    # প্রথমে ভিডিও পাঠানোর চেষ্টা করা
    try:
        if welcome_video_id:
            try:
                await target.reply_video(
                    video=welcome_video_id, 
                    caption=welcome_caption, 
                    reply_markup=inline_kb, 
                    parse_mode="HTML"
                )
            except Exception as video_err:
                logger.warning(f"Welcome Video Send Error, falling back to text: {video_err}")
                await target.reply_text(welcome_caption, reply_markup=inline_kb, parse_mode="HTML")
        else:
            await target.reply_text(welcome_caption, reply_markup=inline_kb, parse_mode="HTML")
            
        # রিপ্লাই কীবোর্ড মেনু প্রম্পট
        await target.reply_text(
            f"{PE['arrow']} <b>মেনু থেকে আপনার প্রয়োজনীয় অপশন সিলেক্ট করুন:</b>", 
            reply_markup=reply_kb, 
            parse_mode="HTML"
        )
    except Exception as msg_error:
        logger.error(f"Welcome Message Final Error: {msg_error}")


# ═══════════════════════════════════════════════════════════════════════════
# 📌 ২. Channel Verify & Admin Callbacks
# ═══════════════════════════════════════════════════════════════════════════
async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    first_name = query.from_user.first_name
    
    # -- Channel Join Verification --
    if query.data == "verify_join":
        await query.answer()
        if await is_user_joined(context.bot, user_id):
            try:
                await query.message.delete()
            except Exception:
                pass
            await send_welcome_message(update, context, user_id, first_name)
        else:
            await query.answer("❌ আপনি এখনো সব চ্যানেল জয়েন করেননি!", show_alert=True)

    # -- Admin Callbacks --
    elif user_id == ADMIN_ID:
        await query.answer()
        if query.data == "change_html":
            await query.message.reply_text("📝 নতুন HTML পেজের লিংক দিন:")
            context.user_data['awaiting_html'] = True
            
        elif query.data == "change_time":
            await query.message.reply_text("⏱ নতুন ওয়েট টাইম দিন (যেমন: 10):")
            context.user_data['awaiting_time'] = True
            
        elif query.data == "set_tutorial":
            await query.message.reply_text(
                f"{PE['book']} <b>টিউটোরিয়াল সেট করুন:</b>\n\n"
                f"একটি ভিডিও সুন্দর ক্যাপশনসহ (HTML ফরম্যাটে) ফরোয়ার্ড করুন বা আপলোড করুন:", 
                parse_mode="HTML"
            )
            context.user_data['awaiting_tutorial'] = True


# ═══════════════════════════════════════════════════════════════════════════
# 📌 ৩. Group Security & 24H Cleaner 
# ═══════════════════════════════════════════════════════════════════════════
async def group_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    
    msg = update.message
    
    # 🔴 ১. সার্ভিস মেসেজ ইগনোর করা (জয়েন, লিভ, পিন ইত্যাদি)
    if msg.new_chat_members or msg.left_chat_member or msg.new_chat_title or msg.pinned_message:
        return
    
    user_id = update.effective_user.id
    group_id = update.message.chat_id

    # 🔴 ২. সকল মেসেজকে ২৪ ঘণ্টার ডিলিট লিস্টে অ্যাড করা (Master Cleaner System)
    await schedule_24h_delete(group_id, msg.message_id)

    # 🔴 ৩. অ্যাডমিন ও ওনার প্রোটেকশন (Double Checks)
    is_admin_or_owner = False
    
    # বেসিক চেক
    if user_id == ADMIN_ID or msg.sender_chat or user_id == 1087968824: 
        is_admin_or_owner = True
    else:
        # API দিয়ে রিয়েল অ্যাডমিন চেক
        try:
            admins = await context.bot.get_chat_administrators(group_id)
            if any(admin.user.id == user_id for admin in admins):
                is_admin_or_owner = True
        except Exception as check_err:
            logger.warning(f"Admin check failed, trying fallback: {check_err}")
            # Fallback Check
            try:
                member = await context.bot.get_chat_member(group_id, user_id)
                if member.status in ['creator', 'administrator']: 
                    is_admin_or_owner = True
            except Exception:
                pass

    # যদি ইউজার অ্যাডমিন বা ওনার হয়, তবে মেসেজ কাটবে না
    if is_admin_or_owner:
        return

    # 🔴 ৪. ভেরিফিকেশন চেক (ইউজার কি আনলক করা আছে?)
    is_verified = False
    try:
        verify_data = db.reference(f'group_verified/{user_id}_{group_id}').get()
        if verify_data and verify_data.get('expire_time', 0) > time.time(): 
            is_verified = True
    except Exception:
        pass

    # যদি ইউজার আনলক থাকে, তবে মেসেজ কাটবে না
    if is_verified:
        return

    # 🔴 ৫. ইউজার ভেরিফাইড নয়! মেসেজ ডিলিট করে ওয়ার্নিং দেওয়া
    try:
        await msg.delete()
    except Exception as e:
        logger.warning(f"Could not delete unverified user message: {e}")

    # সেটিংস নিয়ে আসা
    try:
        settings = db.reference('group_settings').get() or {}
    except Exception:
        settings = {}
        
    html_link = settings.get('html_link', VERIFY_HTML_LINK)
    wait_time = settings.get('wait_time', 10)

    # সিক্রেট টোকেন তৈরি ও সেভ করা
    secret_token = uuid.uuid4().hex
    try:
        db.reference(f'pending_tokens/{secret_token}').set({
            'user_id': user_id, 
            'group_id': group_id, 
            'generate_time': time.time()
        })
    except Exception as save_err:
        logger.error(f"Token Save Error: {save_err}")

    # 🔴 One-Click Direct URL Button (সরাসরি ওয়েবসাইটে নিয়ে যাবে)
    final_url = f"{html_link}?token={secret_token}&bot={BOT_USERNAME}"
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("🌐 Verify via Website", url=final_url)]])
    
    safe_name = html.escape(update.effective_user.first_name)
    
    warning_text = (
        f"{PE['shield']} <b>সিকিউরিটি ভেরিফিকেশন</b>\n━━━━━━━━━━━━━━━━━━\n"
        f"{PE['diamond']} <b>ইউজার:</b> {safe_name}\n\n"
        f"গ্রুপে মেসেজ করার জন্য আপনাকে ভেরিফাই করতে হবে।\n"
        f"{PE['arrow']} <b>'Verify via Website'</b> এ ক্লিক করে লিংকে যান।\n"
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
        
        # 🔴 ওয়ার্নিং মেসেজটিকেও ২৪ ঘণ্টার ক্লিনার লিস্টে যুক্ত করা হলো
        await schedule_24h_delete(group_id, warning_msg.message_id)
        
        # 🔴 ২০ সেকেন্ড পর চেক করার টাস্ক শুরু (Delete Warning + Send Tutorial if needed)
        # এখানে first_name প্যারামিটারটি সঠিকভাবে পাস করা হয়েছে
        create_safe_task(warning_and_tutorial_task(
            context.bot, group_id, warning_msg.message_id, secret_token, user_id, update.effective_user.first_name
        ))
    except Exception as send_err:
        logger.error(f"Group Warning Error: {send_err}")


# ═══════════════════════════════════════════════════════════════════════════
# 📌 ৪. Private Channel Auto-Upload
# ═══════════════════════════════════════════════════════════════════════════
async def channel_post_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post
    if not message or not (message.video or message.document): 
        return
    
    chat_username = message.chat.username
    # মেইন চ্যানেল হলে ইগনোর করবে
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
        # মুভিটি এডমিন প্যানেলের জন্য সেভ করে রাখা হলো
        db.reference('pending_telegram_movies').push(pending_movie_data)
        
        # এডমিনকে নোটিফাই করা
        await context.bot.send_message(
            chat_id=ADMIN_ID, 
            text=(
                f"{PE['telegram']} <b>নতুন মুভি রিসিভ হয়েছে!</b>\n\n"
                f"প্রাইভেট চ্যানেল থেকে <b>{title}</b> প্যানেলে যোগ হয়েছে। "
                f"এডমিন প্যানেলের 'মুভি আপলোড' পেজ থেকে এটি সিলেক্ট করে পাবলিশ করতে পারবেন。"
            ), 
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Pending Movie Save Error: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 📌 ৫. Deep Link Play & 1-Hour Auto Delete
# ═══════════════════════════════════════════════════════════════════════════
async def send_movie_by_id(update: Update, context: ContextTypes.DEFAULT_TYPE, movie_id):
    user_id = update.effective_user.id
    
    try:
        movie_data = db.reference(f'movies/{movie_id}').get()
        if not movie_data:
            await update.message.reply_text(
                f"{PE['error']} <b>দুঃখিত, এই মুভিটি খুঁজে পাওয়া যায়নি।</b>", 
                parse_mode="HTML"
            )
            return

        file_id = movie_data.get("telegramLink") or movie_data.get("file_id")
        movie_title = movie_data.get("title", "Movie")
        
        caption = (
            f"{PE['play']} <b>{movie_title}</b>\n\n"
            f"{PE['warning']} <i>এই ভিডিওটি ১ ঘন্টা পর স্বয়ংক্রিয়ভাবে ডিলিট হয়ে যাবে।</i>"
        )

        # ভিডিও বা ডকুমেন্ট সেন্ড করা
        try: 
            sent_msg = await context.bot.send_video(
                chat_id=user_id, video=file_id, caption=caption, parse_mode="HTML"
            )
        except Exception as vid_e:
            logger.warning(f"Failed to send as video: {vid_e}. Trying as document...")
            try:
                sent_msg = await context.bot.send_document(
                    chat_id=user_id, document=file_id, caption=caption, parse_mode="HTML"
                )
            except Exception as doc_e:
                await update.message.reply_text(
                    f"{PE['error']} মুভির ফাইলটি এরর দিচ্ছে। মুভিটি হয়তো ডিলিট হয়ে গেছে বা এক্সেস নেই।", 
                    parse_mode="HTML"
                )
                return

        # ডাটাবেসে ভিউজ (Views) আপডেট
        try:
            current_views = db.reference(f'movies/{movie_id}/views').get() or 0
            db.reference(f'movies/{movie_id}/views').set(current_views + 1)
        except Exception as view_err:
            logger.warning(f"Views update error: {view_err}")

        # 🔴 বুলেটপ্রুফ ফায়ারবেস ডিলিট সিস্টেমে অ্যাড করা (১ ঘন্টা পর)
        delete_timestamp = time.time() + 3600 
        
        try:
            db.reference(f'delete_queue/{user_id}_{sent_msg.message_id}').set({
                'chat_id': user_id,
                'msg_id': sent_msg.message_id,
                'delete_at': delete_timestamp
            })
            logger.info(f"Movie {movie_id} queued for deletion for user {user_id}")
        except Exception as q_err:
            logger.error(f"Delete Queue Error: {q_err}")
        
    except Exception as main_e:
        logger.error(f"Send Movie By ID Error: {main_e}")


# ═══════════════════════════════════════════════════════════════════════════
# 📌 ৬. Text Message Router (Command/Menu Flow)
# ═══════════════════════════════════════════════════════════════════════════
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    
    text = update.message.text
    user_id = update.effective_user.id

    # -------------------------------------
    # 🌟 User Menu Commands
    # -------------------------------------
    if text == "🍿 Watch Now":
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Open Movie App", web_app=WebAppInfo(url=MINI_APP_URL))]])
        await update.message.reply_text(
            f"{PE['arrow']} <b>নিচের বাটনে ক্লিক করে অ্যাপ ওপেন করুন:</b>", 
            reply_markup=markup, parse_mode="HTML"
        )
        
    elif text == "🎥 Movie Request":
        context.user_data['awaiting_movie_name'] = True
        await update.message.reply_text(
            f"{PE['play']} <b>মুভি রিকোয়েস্ট শুরু হচ্ছে...</b>\n\n"
            f"অনুগ্রহ করে যে মুভিটি চাচ্ছেন তার <b>নাম</b> লিখে সেন্ড করুন:", 
            parse_mode="HTML"
        )
        
    elif text == "👨‍💻 Support":
        await update.message.reply_text(
            f"{PE['admin']} <b>যেকোনো প্রয়োজনে যোগাযোগ করুন:</b>\n{SUPPORT_USERNAME}", 
            parse_mode="HTML"
        )
        
    # -------------------------------------
    # 👑 Admin Menu Commands
    # -------------------------------------
    elif text == "📣 Broadcast" and user_id == ADMIN_ID:
        await update.message.reply_text(f"{PE['megaphone']} ব্রডকাস্টের জন্য মেসেজ, ছবি বা ভিডিও পাঠান:")
        context.user_data['awaiting_broadcast'] = True
        
    elif text == "📊 Status" and user_id == ADMIN_ID:
        users = db.reference('users').get() or {}
        movies = db.reference('movies').get() or {}
        await update.message.reply_text(
            f"{PE['chart']} <b>বট স্ট্যাটাস:</b>\n\n👥 মোট ইউজার: {len(users)}\n🎬 মোট মুভি: {len(movies)}", 
            parse_mode="HTML"
        )
        
    elif text == "⚙️ Settings" and user_id == ADMIN_ID:
        await update.message.reply_text(f"{PE['gear']} <b>ওয়েলকাম ভিডিও সেট করতে ভিডিওটি পাঠান:</b>", parse_mode="HTML")
        context.user_data['awaiting_welcome_video'] = True
        
    elif text == "🛡️ Group Settings" and user_id == ADMIN_ID:
        settings = db.reference('group_settings').get() or {}
        html_link = settings.get('html_link', VERIFY_HTML_LINK)
        wait_time = settings.get('wait_time', 10)
        
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Change HTML Link", callback_data="change_html")],
            [InlineKeyboardButton(f"⏱ Change Wait Time ({wait_time}s)", callback_data="change_time")],
            [InlineKeyboardButton("📚 Set Tutorial Video", callback_data="set_tutorial")]
        ])
        
        await update.message.reply_text(
            f"{PE['shield']} <b>Group Security Settings</b>\n\n<b>Current HTML Link:</b>\n<code>{html_link}</code>", 
            reply_markup=markup, parse_mode="HTML"
        )

    # -------------------------------------
    # 🔍 Admin State Checkers (Input Receivers)
    # -------------------------------------
    elif context.user_data.get('awaiting_html') and user_id == ADMIN_ID:
        try:
            db.reference('group_settings/html_link').set(text)
            context.user_data['awaiting_html'] = False
            await update.message.reply_text(f"{PE['success']} HTML Link আপডেট হয়েছে!", parse_mode="HTML")
        except Exception as e:
            logger.error(f"Error saving HTML link: {e}")
        
    elif context.user_data.get('awaiting_time') and user_id == ADMIN_ID:
        try:
            db.reference('group_settings/wait_time').set(int(text))
            context.user_data['awaiting_time'] = False
            await update.message.reply_text(f"{PE['success']} Wait Time {text} সেকেন্ড করা হয়েছে!", parse_mode="HTML")
        except ValueError: 
            await update.message.reply_text(f"{PE['error']} সঠিক সংখ্যা দিন।", parse_mode="HTML")
        
    elif context.user_data.get('awaiting_broadcast') and user_id == ADMIN_ID:
        context.user_data['awaiting_broadcast'] = False
        users = db.reference('users').get() or {}
        success = 0
        
        await update.message.reply_text(f"{PE['megaphone']} ব্রডকাস্ট শুরু হচ্ছে... ({len(users)} জন ইউজার)", parse_mode="HTML")
        
        for uid in users.keys():
            try:
                await context.bot.copy_message(
                    chat_id=int(uid), 
                    from_chat_id=update.message.chat_id, 
                    message_id=update.message.message_id
                )
                success += 1
                await asyncio.sleep(0.05)
            except Exception:
                pass
                
        await update.message.reply_text(f"{PE['success']} ব্রডকাস্ট সম্পন্ন!\n✅ সফল: {success}", parse_mode="HTML")

    # -------------------------------------
    # 🙋‍♂️ User Movie Request State
    # -------------------------------------
    elif context.user_data.get('awaiting_movie_name'):
        context.user_data['req_movie_name'] = text
        context.user_data['awaiting_movie_name'] = False
        context.user_data['awaiting_movie_poster'] = True
        await update.message.reply_text(
            f"{PE['success']} <b>চমৎকার!</b>\n\nআপনি <b>{text}</b> মুভিটি চেয়েছেন।\nএবার এই মুভিটির একটি <b>পোস্টার (ছবি)</b> পাঠান:", 
            parse_mode="HTML"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 📌 ৭. Media Handler (Photo/Video/Doc)
# ═══════════════════════════════════════════════════════════════════════════
async def media_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    user_id = update.effective_user.id
    user = update.effective_user

    # -- User Movie Request (Poster Upload) --
    if context.user_data.get('awaiting_movie_poster'):
        if not update.message.photo:
            await update.message.reply_text(f"{PE['error']} <b>অনুগ্রহ করে শুধুমাত্র একটি ছবি (পোস্টার) পাঠান!</b>", parse_mode="HTML")
            return
            
        movie_name = context.user_data.get('req_movie_name', 'Unknown Movie')
        photo_id = update.message.photo[-1].file_id
        
        # ⚠️ এক ক্লিকে মুভির নাম কপি করার জন্য <code> ট্যাগ যুক্ত করা আছে
        caption = (
            f"{PE['fire']} <b>New Movie Request!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{PE['diamond']} <b>মুভির নাম:</b> <code>{movie_name}</code>\n"
            f"{PE['diamond']} <b>ইউজার:</b> {html.escape(user.first_name)}\n"
            f"{PE['diamond']} <b>ইউজার আইডি:</b> <code>{user_id}</code>\n"
            f"{PE['link']} <b>ইউজারনেম:</b> @{user.username if user.username else 'N/A'}"
        )
        
        try:
            await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=caption, parse_mode="HTML")
            await update.message.reply_text(
                f"{PE['success']} <b>রিকোয়েস্ট সফল!</b> 🎉\n\nআপনার মুভি রিকোয়েস্টটি অ্যাডমিনের কাছে পাঠানো হয়েছে। খুব শিগগিরই মুভিটি আপলোড করা হবে।", 
                parse_mode="HTML"
            )
        except Exception as req_err:
            logger.error(f"Movie Request Forward Error: {req_err}")
            await update.message.reply_text(f"{PE['error']} সাময়িক সমস্যা হচ্ছে, কিছুক্ষণ পর আবার চেষ্টা করুন।", parse_mode="HTML")
            
        # ক্লিয়ার স্টেট
        context.user_data['awaiting_movie_poster'] = False
        context.user_data.pop('req_movie_name', None)
        return

    # -- Admin Set Tutorial Video (100% Original Caption Check) --
    if context.user_data.get('awaiting_tutorial') and user_id == ADMIN_ID:
        if update.message.video:
            try:
                tutorial_data = {
                    'file_id': update.message.video.file_id,
                    'caption': update.message.caption_html or ""
                }
                db.reference('group_settings/tutorial').set(tutorial_data)
                context.user_data['awaiting_tutorial'] = False
                await update.message.reply_text(f"{PE['success']} <b>টিউটোরিয়াল ভিডিও এবং মেসেজ সেভ করা হয়েছে!</b>", parse_mode="HTML")
            except Exception as e:
                logger.error(f"Failed to save tutorial: {e}")
        else:
            await update.message.reply_text(f"{PE['error']} অনুগ্রহ করে ভিডিওসহ ক্যাপশন দিন।", parse_mode="HTML")
        return

    # -- Admin Welcome Video Setting --
    if context.user_data.get('awaiting_welcome_video') and user_id == ADMIN_ID:
        if update.message.video:
            try:
                db.reference('settings/welcome_video').set(update.message.video.file_id)
                context.user_data['awaiting_welcome_video'] = False
                await update.message.reply_text(f"{PE['success']} <b>ওয়েলকাম ভিডিও সেভ করা হয়েছে!</b>", parse_mode="HTML")
            except Exception as e:
                logger.error(f"Failed to save welcome video: {e}")
        else:
            await update.message.reply_text(f"{PE['error']} অনুগ্রহ করে ভিডিও দিন।", parse_mode="HTML")
        return
        
    # -- Admin Broadcast Media (Photo/Video) --
    if context.user_data.get('awaiting_broadcast') and user_id == ADMIN_ID:
        context.user_data['awaiting_broadcast'] = False
        users = db.reference('users').get() or {}
        success = 0
        
        await update.message.reply_text(f"{PE['megaphone']} ব্রডকাস্ট শুরু হচ্ছে... ({len(users)} জন ইউজার)", parse_mode="HTML")
        
        for uid in users.keys():
            try:
                await context.bot.copy_message(
                    chat_id=int(uid), 
                    from_chat_id=update.message.chat_id, 
                    message_id=update.message.message_id
                )
                success += 1
                await asyncio.sleep(0.05)
            except Exception:
                pass
                
        await update.message.reply_text(f"{PE['success']} ব্রডকাস্ট সম্পন্ন!\n✅ সফল: {success}", parse_mode="HTML")


# ═══════════════════════════════════════════════════════════════════════════
# 🚀 ৮. মেইন রান ফাংশন ও ইনিশিয়ালাইজেশন
# ═══════════════════════════════════════════════════════════════════════════
async def post_init(application: Application):
    """বট স্টার্ট হওয়ার পর ব্যাকগ্রাউন্ড প্রসেসগুলো চালু করবে"""
    # 🔴 ১ ঘন্টা মুভি অটো-ডিলিট এবং ২৪ ঘন্টা গ্রুপ ক্লিনার টাস্ক চালু করা হলো
    create_safe_task(background_movie_delete_task(application.bot))
    create_safe_task(background_group_cleaner_task(application.bot))

def main():
    """বটের মেইন এন্ট্রি পয়েন্ট"""
    
    # অ্যাপ্লিকেশন বিল্ড করা এবং post_init কানেক্ট করা
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    # Command Handlers
    application.add_handler(CommandHandler("start", start_command))
    
    # Callback Handlers
    application.add_handler(CallbackQueryHandler(callback_router))
    
    # Group & Channel Handlers
    application.add_handler(MessageHandler(filters.ChatType.GROUPS & ~filters.COMMAND, group_message_handler))
    application.add_handler(MessageHandler(filters.ChatType.CHANNEL & (filters.VIDEO | filters.Document.ALL), channel_post_handler))
    
    # Private Message & Media Handlers
    application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND, text_handler))
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & (filters.PHOTO | filters.VIDEO | filters.Document.ALL), media_handler))

    logger.info("Ultimate Premium Emoji Bot is running perfectly with Detailed Code and Protected Background Tasks...")
    
    # Polling Start (No Webhook)
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()