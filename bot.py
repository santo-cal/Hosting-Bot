# -*- coding: utf-8 -*-
import telebot
from telebot import types
import subprocess
import os
import zipfile
import tempfile
import shutil
import time
import psutil
import sqlite3
import logging
import threading
import re
import sys
import atexit
import html
from flask import Flask
from threading import Thread

# --- Flask Keep Alive ---
app = Flask(__name__)

@app.route('/')
def home():
    return "আমি মার্কো ফাইল হোস্ট (I'm Marco File Host)"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask, daemon=True)
    t.start()
    print("ফ্লাস্ক কিপ-অ্যালাইভ (Flask Keep-Alive) সার্ভার চালু হয়েছে।")
# --- End Flask Keep Alive ---

# --- Configuration ---
TOKEN = os.environ.get('BOT_TOKEN', '9115784893:AAGCwR20a3maDEF9TL5o5O5FmyGUtwbf3lM')

# ⚠️ নিচে আপনার আসল টেলিগ্রাম ইউজার আইডি দিন
OWNER_ID = 7010177964

YOUR_USERNAME = '@santobhai_dm'
UPDATE_CHANNEL = 'https://t.me/MohabbatBd'

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_BOTS_DIR = os.path.join(BASE_DIR, 'upload_bots')
IROTECH_DIR = os.path.join(BASE_DIR, 'inf')
DATABASE_PATH = os.path.join(IROTECH_DIR, 'bot_data.db')

FREE_USER_LIMIT = 5  # ফ্রি ইউজার কয়টি ফাইল রাখতে পারবে
MAX_FILE_SIZE_MB = 20

os.makedirs(UPLOAD_BOTS_DIR, exist_ok=True)
os.makedirs(IROTECH_DIR, exist_ok=True)

bot = telebot.TeleBot(TOKEN)

bot_scripts = {}
user_files = {}
active_users = set()
bot_locked = False

SCRIPTS_LOCK = threading.Lock()
DB_LOCK = threading.Lock()

# স্ক্রিপ্ট স্ক্যানের জন্য সিগনেচার (ZIP-এর b'PK' বাদ দেওয়া হয়েছে কারণ এটি এক্সট্রাক্ট করে চেক হবে)
MALWARE_SIGNATURES = [b'MZ', b'\x7fELF', b'\xfe\xed\xfa', b'\xce\xfa\xed\xfe', b'Rar!']
ENCRYPTED_FILE_INDICATORS = [b'openssl', b'cipher', b'GPG', b'PGP']
SUSPICIOUS_KEYWORDS = [b'ransomware', b'trojan', b'keylogger', b'rootkit', b'botnet']
SUSPICIOUS_EXTENSIONS = ('.exe', '.dll', '.bat', '.cmd', '.scr', '.com', '.pif', '.msi', '.apk', '.iso', '.img', '.sh')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Command Button Layouts ---
COMMAND_BUTTONS_LAYOUT_USER = [
    ["📤 ফাইল আপলোড", "📂 আমার ফাইলসমূহ"],
    ["⚡ বট স্পিড", "📊 পরিসংখ্যান"],
    ["📤 কমান্ড পাঠান", "📢 আপডেট চ্যানেল"],
    ["ℹ️ হেল্প ও নিয়মাবলী", "📞 সহায়তা নিন"]
]

COMMAND_BUTTONS_LAYOUT_OWNER = [
    ["📤 ফাইল আপলোড", "📂 আমার ফাইলসমূহ"],
    ["⚡ বট স্পিড", "📊 পরিসংখ্যান"],
    ["📤 কমান্ড পাঠান", "👑 অ্যাডমিন প্যানেল"],
    ["ℹ️ হেল্প ও নিয়মাবলী", "📞 সহায়তা নিন"]
]

# --- Database Setup ---
def init_db():
    try:
        with DB_LOCK:
            conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS user_files (
                            user_id INTEGER,
                            file_name TEXT,
                            file_type TEXT,
                            PRIMARY KEY (user_id, file_name)
                        )''')
            c.execute('''CREATE TABLE IF NOT EXISTS active_users (user_id INTEGER PRIMARY KEY)''')
            conn.commit()
            conn.close()
    except Exception as e:
        logger.error(f"❌ ডাটাবেস তৈরিতে এরর: {e}")

def load_data():
    try:
        with DB_LOCK:
            conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
            c = conn.cursor()
            c.execute('SELECT user_id, file_name, file_type FROM user_files')
            for user_id, file_name, file_type in c.fetchall():
                user_files.setdefault(user_id, []).append((file_name, file_type))
            c.execute('SELECT user_id FROM active_users')
            active_users.update(user_id for (user_id,) in c.fetchall())
            conn.close()
    except Exception as e:
        logger.error(f"❌ ডাটা লোড করতে এরর: {e}")

init_db()
load_data()

# --- Malware Detection ---
def is_suspicious_file(file_content, file_name):
    file_lower = file_name.lower()
    if file_lower.endswith(SUSPICIOUS_EXTENSIONS):
        return True, f"সন্দেহজনক ফাইল এক্সটেনশন: {file_name}"
    for signature in MALWARE_SIGNATURES:
        if file_content.startswith(signature):
            return True, "সন্দেহজনক বাইনারি ফাইল সিগনেচার পাওয়া গেছে"
    file_sample = file_content[:min(len(file_content), 8192)]
    for indicator in ENCRYPTED_FILE_INDICATORS:
        if indicator in file_sample:
            return True, "এনক্রিপ্টেড/সন্দেহজনক কমান্ড ইন্ডিকেটর পাওয়া গেছে"
    sample_text = file_sample.decode('utf-8', errors='ignore').lower()
    for keyword in SUSPICIOUS_KEYWORDS:
        if keyword.decode('utf-8').lower() in sample_text:
            return True, f"সন্দেহজনক কিওয়ার্ড পাওয়া গেছে ({keyword.decode('utf-8')})"
    return False, "ফাইলটি নিরাপদ"

def scan_file_for_malware(file_content, file_name, user_id):
    if user_id == OWNER_ID:
        return True, "মালিক সিকিউরিটি চেক বাইপাস করেছেন"
    is_suspicious, reason = is_suspicious_file(file_content, file_name)
    if is_suspicious:
        return False, f"সিকিউরিটি ভায়োলেশন: {reason}"
    return True, "ফাইলটি নিরাপদ"

def scan_directory_for_malware(directory, user_id):
    if user_id == OWNER_ID:
        return True, "মালিক সিকিউরিটি চেক বাইপাস করেছেন"
    for root, _, files in os.walk(directory):
        for fname in files:
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'rb') as f:
                    content = f.read(16384)
                safe, reason = scan_file_for_malware(content, fname, user_id)
                if not safe:
                    return False, reason
            except Exception:
                return False, f"ফাইল স্ক্যান করা যায়নি: {fname}"
    return True, "সব ফাইল নিরাপদ"

# --- Helper Functions ---
def get_user_folder(user_id):
    user_folder = os.path.join(UPLOAD_BOTS_DIR, str(user_id))
    os.makedirs(user_folder, exist_ok=True)
    return user_folder

def sanitize_filename(user_id, raw_name):
    """ফাইলের নাম নিরাপদ করে এবং callback_data যেন 64 বাইটের বেশি না হয় তা নিশ্চিত করে"""
    base = os.path.basename(raw_name).replace(' ', '_')
    base = re.sub(r'[^a-zA-Z0-9._-]', '', base)
    name_part, ext = os.path.splitext(base)
    if not name_part:
        name_part = "script"
    # সর্বোচ্চ প্রিফিক্স: 'restart_{user_id}_' -> বাকি জায়গার মধ্যে ফিট করা
    prefix_len = len(f"restart_{user_id}_".encode('utf-8'))
    max_fname_bytes = 64 - prefix_len
    ext_bytes = ext.encode('utf-8')
    allowed_name_bytes = max(4, max_fname_bytes - len(ext_bytes))
    trimmed_name = name_part.encode('utf-8')[:allowed_name_bytes].decode('utf-8', errors='ignore')
    return f"{trimmed_name}{ext}"

def get_user_file_limit(user_id):
    return float('inf') if user_id == OWNER_ID else FREE_USER_LIMIT

def get_user_file_count(user_id):
    return len(user_files.get(user_id, []))

def is_bot_running(script_owner_id, file_name):
    script_key = f"{script_owner_id}_{file_name}"
    with SCRIPTS_LOCK:
        script_info = bot_scripts.get(script_key)
        if not script_info:
            return False
        process = script_info.get('process')
        if process:
            try:
                if process.poll() is None:
                    proc = psutil.Process(process.pid)
                    if proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE:
                        return True
            except Exception:
                pass
        # প্রসেস বন্ধ হয়ে থাকলে ক্লিনআপ
        log_f = script_info.get('log_file')
        if log_f and not log_f.closed:
            try:
                log_f.close()
            except Exception:
                pass
        bot_scripts.pop(script_key, None)
    return False

def kill_process_tree(process_info):
    try:
        process = process_info.get('process')
        if process and hasattr(process, 'pid'):
            try:
                parent = psutil.Process(process.pid)
                children = parent.children(recursive=True)
                for child in children:
                    try:
                        child.kill()
                    except Exception:
                        pass
                parent.kill()
            except psutil.NoSuchProcess:
                pass
            try:
                process.wait(timeout=2)
            except Exception:
                pass
    except Exception:
        pass
    finally:
        for handle_key in ('log_file',):
            handle = process_info.get(handle_key)
            if handle and not handle.closed:
                try:
                    handle.close()
                except Exception:
                    pass

def safe_reply(chat_id, text, reply_to_message_id=None, **kwargs):
    try:
        return bot.send_message(chat_id, text, reply_to_message_id=reply_to_message_id, **kwargs)
    except Exception:
        return bot.send_message(chat_id, text, **kwargs)

# --- Automatic Package Installation & Script Running ---
TELEGRAM_MODULES = {
    'telebot': 'pyTelegramBotAPI',
    'telegram': 'python-telegram-bot',
    'aiogram': 'aiogram',
    'pyrogram': 'pyrogram',
    'requests': 'requests',
    'psutil': 'psutil',
    'bs4': 'beautifulsoup4',
    'dotenv': 'python-dotenv',
    'pil': 'Pillow',
    'cv2': 'opencv-python',
    'yaml': 'PyYAML'
}

def attempt_install_pip(module_name, chat_id):
    package_name = TELEGRAM_MODULES.get(module_name.lower(), module_name)
    try:
        bot.send_message(chat_id, f"🐍 মিসিং প্যাকেজ <code>{html.escape(package_name)}</code> ইনস্টল করা হচ্ছে...", parse_mode='HTML')
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', package_name],
            capture_output=True, text=True, timeout=120
        )
        return result.returncode == 0
    except Exception as e:
        logger.error(f"pip install error: {e}")
        return False

def attempt_install_npm(module_name, user_folder, chat_id):
    if not shutil.which('npm'):
        bot.send_message(chat_id, "❌ সার্ভারে `npm` ইনস্টল করা নেই।")
        return False
    try:
        bot.send_message(chat_id, f"🟠 মিসিং মডিউল <code>{html.escape(module_name)}</code> ইনস্টল করা হচ্ছে...", parse_mode='HTML')
        result = subprocess.run(
            ['npm', 'install', module_name],
            capture_output=True, text=True, cwd=user_folder, timeout=120
        )
        return result.returncode == 0
    except Exception as e:
        logger.error(f"npm install error: {e}")
        return False

def run_script(script_path, script_owner_id, user_folder, file_name, chat_id, attempt=1):
    if attempt > 2:
        return
    script_key = f"{script_owner_id}_{file_name}"

    if not os.path.exists(script_path):
        remove_user_file_db(script_owner_id, file_name)
        bot.send_message(chat_id, f"❌ ফাইল `{html.escape(file_name)}` খুঁজে পাওয়া যায়নি।", parse_mode='HTML')
        return

    if is_bot_running(script_owner_id, file_name):
        bot.send_message(chat_id, f"⚠️ <code>{html.escape(file_name)}</code> ইতিমধ্যেই চালু আছে।", parse_mode='HTML')
        return

    log_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
    try:
        log_file = open(log_path, 'w', encoding='utf-8', errors='replace')
        process = subprocess.Popen(
            [sys.executable, '-u', script_path],
            cwd=user_folder,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1
        )

        # ২.৫ সেকেন্ড অপেক্ষা করে দেখা হচ্ছে স্ক্রিপ্ট ক্র্যাশ করে কিনা
        time.sleep(2.5)
        ret = process.poll()

        if ret is None:
            # স্ক্রিপ্ট সফলভাবে রানিং অবস্থায় আছে
            with SCRIPTS_LOCK:
                bot_scripts[script_key] = {
                    'process': process,
                    'log_file': log_file,
                    'file_name': file_name,
                    'script_owner_id': script_owner_id
                }
            bot.send_message(chat_id, f"✅ পাইথন স্ক্রিপ্ট <code>{html.escape(file_name)}</code> সফলভাবে চালু হয়েছে!", parse_mode='HTML')
        else:
            log_file.close()
            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                log_content = f.read()

            if ret != 0 and attempt == 1:
                match_py = re.search(r"(?:ModuleNotFoundError|ImportError): No module named ['\"]([^'\"]+)['\"]", log_content)
                if match_py:
                    missing_mod = match_py.group(1).split('.')[0].strip()
                    if attempt_install_pip(missing_mod, chat_id):
                        bot.send_message(chat_id, "🔄 প্যাকেজ ইনস্টল সম্পন্ন! আবার রান করা হচ্ছে...")
                        run_script(script_path, script_owner_id, user_folder, file_name, chat_id, attempt + 1)
                        return

            if ret == 0:
                bot.send_message(chat_id, f"ℹ️ স্ক্রিপ্ট <code>{html.escape(file_name)}</code> রান হয়ে সম্পন্ন হয়েছে (Exit Code: 0)। লগ দেখতে ফাইল প্যানেলে যান।", parse_mode='HTML')
            else:
                snippet = html.escape(log_content[-1000:] or "কোনো এরর লগ পাওয়া যায়নি।")
                bot.send_message(chat_id, f"❌ <code>{html.escape(file_name)}</code> চালু হতে ব্যর্থ (Code {ret}):\n<pre>{snippet}</pre>", parse_mode='HTML')

    except Exception as e:
        bot.send_message(chat_id, f"❌ এরর: <code>{html.escape(str(e))}</code>", parse_mode='HTML')

def run_js_script(script_path, script_owner_id, user_folder, file_name, chat_id, attempt=1):
    if attempt > 2:
        return
    script_key = f"{script_owner_id}_{file_name}"

    if not shutil.which('node'):
        bot.send_message(chat_id, "❌ সার্ভারে Node.js (`node`) ইনস্টল করা নেই।")
        return

    if not os.path.exists(script_path):
        remove_user_file_db(script_owner_id, file_name)
        bot.send_message(chat_id, f"❌ ফাইল <code>{html.escape(file_name)}</code> খুঁজে পাওয়া যায়নি।", parse_mode='HTML')
        return

    if is_bot_running(script_owner_id, file_name):
        bot.send_message(chat_id, f"⚠️ <code>{html.escape(file_name)}</code> ইতিমধ্যেই চালু আছে।", parse_mode='HTML')
        return

    log_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
    try:
        log_file = open(log_path, 'w', encoding='utf-8', errors='replace')
        process = subprocess.Popen(
            ['node', script_path],
            cwd=user_folder,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1
        )

        time.sleep(2.5)
        ret = process.poll()

        if ret is None:
            with SCRIPTS_LOCK:
                bot_scripts[script_key] = {
                    'process': process,
                    'log_file': log_file,
                    'file_name': file_name,
                    'script_owner_id': script_owner_id
                }
            bot.send_message(chat_id, f"✅ জেএস স্ক্রিপ্ট <code>{html.escape(file_name)}</code> সফলভাবে চালু হয়েছে!", parse_mode='HTML')
        else:
            log_file.close()
            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                log_content = f.read()

            if ret != 0 and attempt == 1:
                match_js = re.search(r"Cannot find module ['\"]([^'\"]+)['\"]", log_content)
                if match_js:
                    missing_mod = match_js.group(1).strip()
                    if not missing_mod.startswith(('.', '/')):
                        if attempt_install_npm(missing_mod, user_folder, chat_id):
                            bot.send_message(chat_id, "🔄 মডিউল ইনস্টল সম্পন্ন! আবার রান করা হচ্ছে...")
                            run_js_script(script_path, script_owner_id, user_folder, file_name, chat_id, attempt + 1)
                            return

            if ret == 0:
                bot.send_message(chat_id, f"ℹ️ জেএস স্ক্রিপ্ট <code>{html.escape(file_name)}</code> সম্পন্ন হয়েছে (Exit Code: 0)।", parse_mode='HTML')
            else:
                snippet = html.escape(log_content[-1000:] or "কোনো এরর লগ পাওয়া যায়নি।")
                bot.send_message(chat_id, f"❌ <code>{html.escape(file_name)}</code> চালু হতে ব্যর্থ (Code {ret}):\n<pre>{snippet}</pre>", parse_mode='HTML')

    except Exception as e:
        bot.send_message(chat_id, f"❌ এরর: <code>{html.escape(str(e))}</code>", parse_mode='HTML')

# --- Database Operations ---
def save_user_file(user_id, file_name, file_type='py'):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO user_files (user_id, file_name, file_type) VALUES (?, ?, ?)', (user_id, file_name, file_type))
        conn.commit()
        conn.close()
        user_files.setdefault(user_id, [])
        user_files[user_id] = [(fn, ft) for fn, ft in user_files[user_id] if fn != file_name]
        user_files[user_id].append((file_name, file_type))

def remove_user_file_db(user_id, file_name):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('DELETE FROM user_files WHERE user_id = ? AND file_name = ?', (user_id, file_name))
        conn.commit()
        conn.close()
        if user_id in user_files:
            user_files[user_id] = [f for f in user_files[user_id] if f[0] != file_name]

def add_active_user(user_id):
    active_users.add(user_id)
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('INSERT OR IGNORE INTO active_users (user_id) VALUES (?)', (user_id,))
        conn.commit()
        conn.close()

# --- Menus ---
def create_main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    layout = COMMAND_BUTTONS_LAYOUT_OWNER if user_id == OWNER_ID else COMMAND_BUTTONS_LAYOUT_USER
    for row in layout:
        markup.add(*[types.KeyboardButton(t) for t in row])
    return markup

def create_control_buttons(script_owner_id, file_name, is_running=True):
    markup = types.InlineKeyboardMarkup(row_width=2)
    if is_running:
        markup.row(
            types.InlineKeyboardButton("🔴 থামান (Stop)", callback_data=f'stop_{script_owner_id}_{file_name}'),
            types.InlineKeyboardButton("🔄 রিস্টার্ট", callback_data=f'restart_{script_owner_id}_{file_name}')
        )
    else:
        markup.row(
            types.InlineKeyboardButton("🟢 চালু করুন (Start)", callback_data=f'start_{script_owner_id}_{file_name}')
        )
    markup.row(
        types.InlineKeyboardButton("🗑️ ডিলিট", callback_data=f'delete_{script_owner_id}_{file_name}'),
        types.InlineKeyboardButton("📜 লগ (Logs)", callback_data=f'logs_{script_owner_id}_{file_name}')
    )
    markup.add(types.InlineKeyboardButton("🔙 ফাইল মেনুতে ফেরত", callback_data='check_files'))
    return markup

def create_admin_panel():
    markup = types.InlineKeyboardMarkup(row_width=1)
    lock_label = "🔓 বট আনলক করুন" if bot_locked else "🔒 বট লক করুন"
    markup.add(
        types.InlineKeyboardButton("📢 সম্প্রচার (Broadcast)", callback_data='admin_broadcast'),
        types.InlineKeyboardButton(lock_label, callback_data='admin_lock'),
        types.InlineKeyboardButton("🟢 সব কোড একসাথে রান", callback_data='admin_run_all'),
        types.InlineKeyboardButton("🔙 মেনু বন্ধ করুন", callback_data='close_menu')
    )
    return markup

def create_send_command_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton('📝 প্রসেসে কমান্ড পাঠান', callback_data='send_to_process'),
        types.InlineKeyboardButton('🔍 সব লগ দেখুন', callback_data='view_all_logs'),
        types.InlineKeyboardButton('🔙 মেনু বন্ধ করুন', callback_data='close_menu')
    )
    return markup

# --- Core Logic Functions ---
def _logic_send_welcome(message):
    user_id = message.from_user.id
    if bot_locked and user_id != OWNER_ID:
        bot.send_message(message.chat.id, "⚠️ বট বর্তমানে লক করা আছে। পরে চেষ্টা করুন।")
        return

    if user_id not in active_users:
        add_active_user(user_id)
        try:
            name_escaped = html.escape(message.from_user.first_name or "User")
            bot.send_message(OWNER_ID, f"🎉 নতুন ইউজার: {name_escaped} (<code>{user_id}</code>)", parse_mode='HTML')
        except Exception:
            pass

    user_status = "👑 মালিক (Owner)" if user_id == OWNER_ID else "🆓 ফ্রি ইউজার"
    limit_str = "আনলিমিটেড" if user_id == OWNER_ID else str(FREE_USER_LIMIT)
    first_name = html.escape(message.from_user.first_name or "বন্ধু")

    msg = (
        f"〽️ স্বাগতম, {first_name}!\n\n"
        f"🆔 আইডি: <code>{user_id}</code>\n"
        f"🔰 স্ট্যাটাস: {user_status}\n"
        f"📁 ফাইল: {get_user_file_count(user_id)} / {limit_str}\n\n"
        f"🤖 পাইথন (.py) বা জেএস (.js) বা প্রজেক্ট (.zip) আপলোড করে সহজেই রান করুন।"
    )
    bot.send_message(message.chat.id, msg, reply_markup=create_main_menu(user_id), parse_mode='HTML')

def _logic_upload_file(message):
    user_id = message.from_user.id
    if bot_locked and user_id != OWNER_ID:
        bot.reply_to(message, "⚠️ বট লক করা আছে।")
        return
    if get_user_file_count(user_id) >= get_user_file_limit(user_id):
        bot.reply_to(message, "⚠️ ফাইল লিমিট শেষ। নতুন ফাইল দিতে আগে পুরনো ফাইল ডিলিট করুন।")
        return
    bot.reply_to(message, "📤 আপনার <code>.py</code>, <code>.js</code>, অথবা <code>.zip</code> প্রজেক্ট ফাইল পাঠান।", parse_mode='HTML')

def _logic_check_files(chat_id, user_id, reply_to_message_id=None):
    user_files_list = user_files.get(user_id, [])
    if not user_files_list:
        safe_reply(chat_id, "📂 আপনার কোনো ফাইল আপলোড করা নেই।", reply_to_message_id)
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for file_name, file_type in sorted(user_files_list):
        status = "🟢" if is_bot_running(user_id, file_name) else "🔴"
        markup.add(types.InlineKeyboardButton(f"{status} {file_name}", callback_data=f'file_{user_id}_{file_name}'))
    safe_reply(chat_id, "📂 আপনার ফাইলসমূহ (কন্ট্রোল করতে ক্লিক করুন):", reply_to_message_id, reply_markup=markup)

def _logic_bot_speed(message):
    start = time.time()
    msg = bot.reply_to(message, "🏃 চেক করা হচ্ছে...")
    latency = round((time.time() - start) * 1000, 2)
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    bot.edit_message_text(
        f"⚡ রেসপন্স: {latency} ms\n💻 CPU: {cpu}% | 🧠 RAM: {ram}%\n🚦 স্ট্যাটাস: {'🔒 লকড' if bot_locked else '🔓 আনলকড'}",
        message.chat.id, msg.message_id
    )

def _logic_statistics(message):
    user_id = message.from_user.id
    total_files = sum(len(f) for f in user_files.values())
    with SCRIPTS_LOCK:
        scripts_snapshot = list(bot_scripts.values())
    running = sum(1 for v in scripts_snapshot if is_bot_running(v['script_owner_id'], v['file_name']))
    my_running = sum(1 for v in scripts_snapshot if v['script_owner_id'] == user_id and is_bot_running(user_id, v['file_name']))
    bot.reply_to(
        message,
        f"📊 পরিসংখ্যান:\n👥 মোট ইউজার: {len(active_users)}\n📂 মোট ফাইল: {total_files}\n🟢 মোট রানিং বট: {running}\n🤖 আপনার রানিং বট: {my_running}"
    )

def _logic_help(message):
    help_text = (
        "ℹ️ <b>ব্যবহারের নিয়মাবলী ও হেল্প:</b>\n\n"
        "১. সরাসরি <code>.py</code>, <code>.js</code> বা <code>.zip</code> ফাইল পাঠান।\n"
        "২. <code>.zip</code> ফাইলের ভেতরে অবশ্যই <code>main.py</code>, <code>bot.py</code>, <code>app.py</code>, <code>index.js</code> বা <code>main.js</code> থাকতে হবে।\n"
        "৩. ফ্রি ইউজার সর্বোচ্চ <b>৫টি</b> ফাইল হোস্ট করতে পারবেন।\n"
        "৪. <b>আমার ফাইলসমূহ</b> থেকে বট Start, Stop, Restart, Delete এবং Logs দেখতে পারবেন।\n"
        "৫. <b>কমান্ড পাঠান</b> মেনু থেকে চলমান স্ক্রিপ্টে ইনপুট (stdin) দিতে ও লগ দেখতে পারবেন।"
    )
    bot.reply_to(message, help_text, parse_mode='HTML')

@bot.message_handler(commands=['start', 'help'])
def cmd_start(message):
    _logic_send_welcome(message)

BUTTONS_LOGIC = {
    "📤 ফাইল আপলোড": _logic_upload_file,
    "📂 আমার ফাইলসমূহ": lambda m: _logic_check_files(m.chat.id, m.from_user.id, m.message_id),
    "⚡ বট স্পিড": _logic_bot_speed,
    "📊 পরিসংখ্যান": _logic_statistics,
    "📤 কমান্ড পাঠান": lambda m: bot.reply_to(m, "অপশন সিলেক্ট করুন:", reply_markup=create_send_command_menu()),
    "📢 আপডেট চ্যানেল": lambda m: bot.reply_to(m, "আমাদের আপডেট চ্যানেলে যুক্ত হোন:", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('📢 চ্যানেল', url=UPDATE_CHANNEL))),
    "ℹ️ হেল্প ও নিয়মাবলী": _logic_help,
    "📞 সহায়তা নিন": lambda m: bot.reply_to(m, "যেকোনো সহায়তার জন্য যোগাযোগ করুন:", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('📞 যোগাযোগ', url=f"https://t.me/{YOUR_USERNAME.lstrip('@')}"))),
    "👑 অ্যাডমিন প্যানেল": lambda m: bot.reply_to(m, "👑 অ্যাডমিন প্যানেল:", reply_markup=create_admin_panel()) if m.from_user.id == OWNER_ID else None
}

@bot.message_handler(func=lambda message: message.text in BUTTONS_LOGIC)
def handle_text(message):
    if bot_locked and message.from_user.id != OWNER_ID:
        bot.reply_to(message, "⚠️ বট বর্তমানে লক করা আছে।")
        return
    func = BUTTONS_LOGIC.get(message.text)
    if func:
        func(message)

@bot.message_handler(content_types=['document'])
def handle_doc(message):
    user_id = message.from_user.id
    if bot_locked and user_id != OWNER_ID:
        bot.reply_to(message, "⚠️ বট লক করা আছে।")
        return

    doc = message.document
    if doc.file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
        bot.reply_to(message, f"⚠️ ফাইল সাইজ {MAX_FILE_SIZE_MB}MB-এর বেশি হওয়া যাবে না।")
        return

    ext = os.path.splitext(doc.file_name)[1].lower()
    if ext not in ['.py', '.js', '.zip']:
        bot.reply_to(message, "⚠️ শুধুমাত্র .py, .js, অথবা .zip ফাইল গ্রহণযোগ্য।")
        return

    safe_name = sanitize_filename(user_id, doc.file_name)
    existing_names = [fn for fn, _ in user_files.get(user_id, [])]
    if ext != '.zip' and safe_name not in existing_names and get_user_file_count(user_id) >= get_user_file_limit(user_id):
        bot.reply_to(message, "⚠️ আপনার ফাইল লিমিট শেষ। আগে একটি ফাইল ডিলিট করুন।")
        return
    if ext == '.zip' and get_user_file_count(user_id) >= get_user_file_limit(user_id):
        bot.reply_to(message, "⚠️ আপনার ফাইল লিমিট শেষ। আগে একটি ফাইল ডিলিট করুন।")
        return

    msg = bot.reply_to(message, "⏳ ফাইল প্রসেস ও স্ক্যান করা হচ্ছে...")
    temp_dir = None
    try:
        file_info = bot.get_file(doc.file_id)
        content = bot.download_file(file_info.file_path)
        folder = get_user_folder(user_id)

        if ext == '.zip':
            temp_dir = tempfile.mkdtemp()
            zip_path = os.path.join(temp_dir, 'upload.zip')
            with open(zip_path, 'wb') as f:
                f.write(content)

            # নিরাপদ ZIP এক্সট্রাকশন (Zip Slip প্রতিরোধ)
            with zipfile.ZipFile(zip_path, 'r') as z:
                for member in z.infolist():
                    member_path = os.path.realpath(os.path.join(temp_dir, member.filename))
                    if not member_path.startswith(os.path.realpath(temp_dir) + os.sep) and member_path != os.path.realpath(temp_dir):
                        bot.edit_message_text("🚨 অবৈধ ZIP পাথ শনাক্ত হয়েছে!", message.chat.id, msg.message_id)
                        return
                z.extractall(temp_dir)
            os.remove(zip_path)

            # যদি জিপের ভেতর মাত্র একটি সাব-ফোল্ডার থাকে তবে ভেতরে ঢুকুন
            top_items = os.listdir(temp_dir)
            source_dir = temp_dir
            if len(top_items) == 1 and os.path.isdir(os.path.join(temp_dir, top_items[0])):
                source_dir = os.path.join(temp_dir, top_items[0])

            # ম্যালওয়্যার স্ক্যান
            safe, reason = scan_directory_for_malware(source_dir, user_id)
            if not safe:
                bot.edit_message_text(f"🚨 সিকিউরিটি অ্যালার্ট: {html.escape(reason)}", message.chat.id, msg.message_id, parse_mode='HTML')
                return

            # মেইন স্ক্রিপ্ট খোঁজা
            source_files = os.listdir(source_dir)
            main_script = None
            f_type = None
            for candidate in ['main.py', 'bot.py', 'app.py', 'index.js', 'main.js']:
                if candidate in source_files:
                    main_script = candidate
                    f_type = 'py' if candidate.endswith('.py') else 'js'
                    break

            if not main_script:
                bot.edit_message_text("❌ জিপে <code>main.py</code>, <code>bot.py</code>, <code>app.py</code>, বা <code>index.js</code> পাওয়া যায়নি।", message.chat.id, msg.message_id, parse_mode='HTML')
                return

            # আগের প্রসেস চললে বন্ধ করে ফাইল মুভ করা
            if is_bot_running(user_id, main_script):
                with SCRIPTS_LOCK:
                    info = bot_scripts.pop(f"{user_id}_{main_script}", None)
                if info:
                    kill_process_tree(info)

            for item in source_files:
                src = os.path.join(source_dir, item)
                dst = os.path.join(folder, item)
                if os.path.exists(dst):
                    if os.path.isdir(dst):
                        shutil.rmtree(dst)
                    else:
                        os.remove(dst)
                shutil.move(src, dst)

            # যদি requirements.txt থাকে তবে ইনস্টল চেষ্টা
            req_path = os.path.join(folder, 'requirements.txt')
            if f_type == 'py' and os.path.exists(req_path):
                bot.edit_message_text("📦 <code>requirements.txt</code> পাওয়া গেছে, প্যাকেজ ইনস্টল হচ্ছে...", message.chat.id, msg.message_id, parse_mode='HTML')
                subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', req_path], capture_output=True, text=True, timeout=180)

            save_user_file(user_id, main_script, f_type)
            bot.edit_message_text(f"✅ এক্সট্রাক্ট সম্পন্ন! <code>{html.escape(main_script)}</code> রান হচ্ছে...", message.chat.id, msg.message_id, parse_mode='HTML')
            target_fn = run_script if f_type == 'py' else run_js_script
            threading.Thread(target=target_fn, args=(os.path.join(folder, main_script), user_id, folder, main_script, message.chat.id), daemon=True).start()

        else:
            safe, reason = scan_file_for_malware(content, safe_name, user_id)
            if not safe:
                bot.edit_message_text(f"🚨 সিকিউরিটি অ্যালার্ট: {html.escape(reason)}", message.chat.id, msg.message_id, parse_mode='HTML')
                return

            if is_bot_running(user_id, safe_name):
                with SCRIPTS_LOCK:
                    info = bot_scripts.pop(f"{user_id}_{safe_name}", None)
                if info:
                    kill_process_tree(info)

            file_path = os.path.join(folder, safe_name)
            with open(file_path, 'wb') as f:
                f.write(content)

            save_user_file(user_id, safe_name, ext[1:])
            bot.edit_message_text(f"✅ <code>{html.escape(safe_name)}</code> সেভ হয়েছে! রান হচ্ছে...", message.chat.id, msg.message_id, parse_mode='HTML')
            target_fn = run_script if ext == '.py' else run_js_script
            threading.Thread(target=target_fn, args=(file_path, user_id, folder, safe_name, message.chat.id), daemon=True).start()

    except zipfile.BadZipFile:
        bot.edit_message_text("❌ এটি একটি ত্রুটিপূর্ণ (Corrupted) ZIP ফাইল।", message.chat.id, msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ এরর: <code>{html.escape(str(e))}</code>", message.chat.id, msg.message_id, parse_mode='HTML')
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

# --- Next Step Handlers ---
def process_broadcast(message):
    if message.from_user.id != OWNER_ID:
        return
    if message.text and message.text.strip().lower() == '/cancel':
        bot.reply_to(message, "❌ ব্রডকাস্ট বাতিল করা হয়েছে।")
        return

    users_snapshot = list(active_users)
    success = 0
    failed = 0
    status_msg = bot.reply_to(message, f"📢 {len(users_snapshot)} জন ইউজারের কাছে পাঠানো হচ্ছে...")

    for uid in users_snapshot:
        try:
            bot.copy_message(uid, message.chat.id, message.message_id)
            success += 1
            time.sleep(0.05)
        except Exception:
            failed += 1

    bot.edit_message_text(
        f"✅ ব্রডকাস্ট সম্পন্ন!\n📤 সফল: {success}\n❌ ব্যর্থ: {failed}",
        message.chat.id, status_msg.message_id
    )

def process_stdin_command(message, owner_id, fname):
    if message.text and message.text.strip().lower() == '/cancel':
        bot.reply_to(message, "❌ কমান্ড পাঠানো বাতিল করা হয়েছে।")
        return
    if not message.text:
        bot.reply_to(message, "⚠️ অনুগ্রহ করে টেক্সট কমান্ড পাঠান।")
        return

    script_key = f"{owner_id}_{fname}"
    if not is_bot_running(owner_id, fname):
        bot.reply_to(message, f"⚠️ <code>{html.escape(fname)}</code> এখন আর রানিং নেই।", parse_mode='HTML')
        return

    with SCRIPTS_LOCK:
        info = bot_scripts.get(script_key)
        proc = info.get('process') if info else None

    if proc and proc.stdin:
        try:
            proc.stdin.write(message.text + "\n")
            proc.stdin.flush()
            bot.reply_to(message, f"✅ কমান্ড <code>{html.escape(fname)}</code>-এ পাঠানো হয়েছে!", parse_mode='HTML')
        except Exception as e:
            bot.reply_to(message, f"❌ কমান্ড পাঠানো যায়নি: <code>{html.escape(str(e))}</code>", parse_mode='HTML')
    else:
        bot.reply_to(message, "❌ প্রসেসের ইনপুট স্ট্রিম পাওয়া যায়নি।")

# --- Callbacks ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = call.from_user.id
    data = call.data

    if bot_locked and uid != OWNER_ID:
        bot.answer_callback_query(call.id, "⚠️ বট লক করা আছে।", show_alert=True)
        return

    try:
        if data == 'check_files':
            bot.answer_callback_query(call.id)
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception:
                pass
            _logic_check_files(call.message.chat.id, uid)

        elif data == 'close_menu':
            bot.answer_callback_query(call.id)
            bot.delete_message(call.message.chat.id, call.message.message_id)

        elif data.startswith('file_'):
            _, owner_str, fname = data.split('_', 2)
            owner = int(owner_str)
            if uid != owner and uid != OWNER_ID:
                bot.answer_callback_query(call.id, "⛔ অনুমতি নেই!", show_alert=True)
                return
            bot.answer_callback_query(call.id)
            is_run = is_bot_running(owner, fname)
            bot.edit_message_text(
                f"⚙️ প্যানেল: <code>{html.escape(fname)}</code>\nস্ট্যাটাস: {'🟢 রানিং' if is_run else '🔴 বন্ধ'}",
                call.message.chat.id, call.message.message_id,
                reply_markup=create_control_buttons(owner, fname, is_run),
                parse_mode='HTML'
            )

        elif data.startswith('start_'):
            _, owner_str, fname = data.split('_', 2)
            owner = int(owner_str)
            if uid != owner and uid != OWNER_ID:
                bot.answer_callback_query(call.id, "⛔ অনুমতি নেই!", show_alert=True)
                return
            f_info = next((f for f in user_files.get(owner, []) if f[0] == fname), None)
            folder = get_user_folder(owner)
            path = os.path.join(folder, fname)
            if f_info and os.path.exists(path):
                bot.answer_callback_query(call.id, "চালু করা হচ্ছে...")
                target_fn = run_script if f_info[1] == 'py' else run_js_script
                threading.Thread(target=target_fn, args=(path, owner, folder, fname, call.message.chat.id), daemon=True).start()
                time.sleep(3)
                is_run = is_bot_running(owner, fname)
                bot.edit_message_text(
                    f"⚙️ প্যানেল: <code>{html.escape(fname)}</code>\nস্ট্যাটাস: {'🟢 রানিং' if is_run else '🔴 বন্ধ'}",
                    call.message.chat.id, call.message.message_id,
                    reply_markup=create_control_buttons(owner, fname, is_run),
                    parse_mode='HTML'
                )
            else:
                bot.answer_callback_query(call.id, "❌ ফাইল পাওয়া যায়নি!", show_alert=True)

        elif data.startswith('stop_'):
            _, owner_str, fname = data.split('_', 2)
            owner = int(owner_str)
            if uid != owner and uid != OWNER_ID:
                bot.answer_callback_query(call.id, "⛔ অনুমতি নেই!", show_alert=True)
                return
            with SCRIPTS_LOCK:
                info = bot_scripts.pop(f"{owner}_{fname}", None)
            if info:
                kill_process_tree(info)
            bot.answer_callback_query(call.id, "🔴 স্ক্রিপ্ট থামানো হয়েছে।")
            bot.edit_message_text(
                f"⚙️ প্যানেল: <code>{html.escape(fname)}</code>\nস্ট্যাটাস: 🔴 বন্ধ",
                call.message.chat.id, call.message.message_id,
                reply_markup=create_control_buttons(owner, fname, False),
                parse_mode='HTML'
            )

        elif data.startswith('restart_'):
            _, owner_str, fname = data.split('_', 2)
            owner = int(owner_str)
            if uid != owner and uid != OWNER_ID:
                bot.answer_callback_query(call.id, "⛔ অনুমতি নেই!", show_alert=True)
                return
            bot.answer_callback_query(call.id, "🔄 রিস্টার্ট করা হচ্ছে...")
            with SCRIPTS_LOCK:
                info = bot_scripts.pop(f"{owner}_{fname}", None)
            if info:
                kill_process_tree(info)
            f_info = next((f for f in user_files.get(owner, []) if f[0] == fname), None)
            folder = get_user_folder(owner)
            path = os.path.join(folder, fname)
            if f_info and os.path.exists(path):
                target_fn = run_script if f_info[1] == 'py' else run_js_script
                threading.Thread(target=target_fn, args=(path, owner, folder, fname, call.message.chat.id), daemon=True).start()
                time.sleep(3)
                is_run = is_bot_running(owner, fname)
                bot.edit_message_text(
                    f"⚙️ প্যানেল: <code>{html.escape(fname)}</code>\nস্ট্যাটাস: {'🟢 রানিং' if is_run else '🔴 বন্ধ'}",
                    call.message.chat.id, call.message.message_id,
                    reply_markup=create_control_buttons(owner, fname, is_run),
                    parse_mode='HTML'
                )

        elif data.startswith('delete_'):
            _, owner_str, fname = data.split('_', 2)
            owner = int(owner_str)
            if uid != owner and uid != OWNER_ID:
                bot.answer_callback_query(call.id, "⛔ অনুমতি নেই!", show_alert=True)
                return
            with SCRIPTS_LOCK:
                info = bot_scripts.pop(f"{owner}_{fname}", None)
            if info:
                kill_process_tree(info)
            folder = get_user_folder(owner)
            fpath = os.path.join(folder, fname)
            log_path = os.path.join(folder, f"{os.path.splitext(fname)[0]}.log")
            if os.path.exists(fpath):
                os.remove(fpath)
            if os.path.exists(log_path):
                os.remove(log_path)
            remove_user_file_db(owner, fname)
            bot.answer_callback_query(call.id, "🗑️ ডিলিট সম্পন্ন!")
            bot.edit_message_text(f"🗑️ <code>{html.escape(fname)}</code> ডিলিট করা হয়েছে!", call.message.chat.id, call.message.message_id, parse_mode='HTML')

        elif data.startswith('logs_'):
            _, owner_str, fname = data.split('_', 2)
            owner = int(owner_str)
            if uid != owner and uid != OWNER_ID:
                bot.answer_callback_query(call.id, "⛔ অনুমতি নেই!", show_alert=True)
                return
            bot.answer_callback_query(call.id)
            log_path = os.path.join(get_user_folder(owner), f"{os.path.splitext(fname)[0]}.log")
            if os.path.exists(log_path):
                with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()[-3500:].strip()
                safe_content = html.escape(content) if content else "লগ ফাইল খালি।"
                bot.send_message(call.message.chat.id, f"📜 <b>{html.escape(fname)}</b>-এর লগ:\n<pre>{safe_content}</pre>", parse_mode='HTML')
            else:
                bot.send_message(call.message.chat.id, f"ℹ️ <code>{html.escape(fname)}</code>-এর কোনো লগ এখনো তৈরি হয়নি।", parse_mode='HTML')

        elif data == 'send_to_process':
            bot.answer_callback_query(call.id)
            running_list = [(fn, ft) for fn, ft in user_files.get(uid, []) if is_bot_running(uid, fn)]
            if not running_list:
                bot.send_message(call.message.chat.id, "⚠️ আপনার কোনো স্ক্রিপ্ট বর্তমানে রানিং নেই।")
                return
            markup = types.InlineKeyboardMarkup(row_width=1)
            for fn, _ in running_list:
                markup.add(types.InlineKeyboardButton(f"🟢 {fn}", callback_data=f'sendcmd_{uid}_{fn}'))
            markup.add(types.InlineKeyboardButton("🔙 বন্ধ করুন", callback_data='close_menu'))
            bot.edit_message_text("📝 কোন রানিং প্রসেসে কমান্ড পাঠাতে চান?", call.message.chat.id, call.message.message_id, reply_markup=markup)

        elif data.startswith('sendcmd_'):
            _, owner_str, fname = data.split('_', 2)
            owner = int(owner_str)
            if uid != owner and uid != OWNER_ID:
                bot.answer_callback_query(call.id, "⛔ অনুমতি নেই!", show_alert=True)
                return
            bot.answer_callback_query(call.id)
            prompt = bot.send_message(call.message.chat.id, f"⌨️ <code>{html.escape(fname)}</code>-এ পাঠানোর জন্য টেক্সট/কমান্ড লিখুন (বাতিল করতে <code>/cancel</code>):", parse_mode='HTML')
            bot.register_next_step_handler(prompt, process_stdin_command, owner, fname)

        elif data == 'view_all_logs':
            bot.answer_callback_query(call.id)
            files_list = user_files.get(uid, [])
            if not files_list:
                bot.send_message(call.message.chat.id, "📂 আপনার কোনো ফাইল নেই।")
                return
            folder = get_user_folder(uid)
            sent_any = False
            for fn, _ in files_list:
                log_path = os.path.join(folder, f"{os.path.splitext(fn)[0]}.log")
                if os.path.exists(log_path):
                    with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()[-1500:].strip()
                    if content:
                        sent_any = True
                        bot.send_message(call.message.chat.id, f"📜 <b>{html.escape(fn)}</b>:\n<pre>{html.escape(content)}</pre>", parse_mode='HTML')
            if not sent_any:
                bot.send_message(call.message.chat.id, "ℹ️ কোনো ফাইলের লগ পাওয়া যায়নি।")

        # Admin Panel Logic
        elif data == 'admin_broadcast' and uid == OWNER_ID:
            bot.answer_callback_query(call.id)
            msg = bot.send_message(call.message.chat.id, "📢 সম্প্রচারের মেসেজটি পাঠান (টেক্সট/ছবি যেকোনো কিছু, বাতিল করতে <code>/cancel</code>):", parse_mode='HTML')
            bot.register_next_step_handler(msg, process_broadcast)

        elif data == 'admin_lock' and uid == OWNER_ID:
            global bot_locked
            bot_locked = not bot_locked
            bot.answer_callback_query(call.id, f"বট {'লক' if bot_locked else 'আনলক'} হয়েছে!", show_alert=True)
            bot.edit_message_text("👑 অ্যাডমিন প্যানেল:", call.message.chat.id, call.message.message_id, reply_markup=create_admin_panel())

        elif data == 'admin_run_all' and uid == OWNER_ID:
            bot.answer_callback_query(call.id, "সবার স্ক্রিপ্ট রান করা হচ্ছে...", show_alert=True)
            started_count = 0
            for u, files in list(user_files.items()):
                for fn, ft in list(files):
                    if not is_bot_running(u, fn):
                        folder = get_user_folder(u)
                        p = os.path.join(folder, fn)
                        if os.path.exists(p):
                            started_count += 1
                            target_fn = run_script if ft == 'py' else run_js_script
                            threading.Thread(target=target_fn, args=(p, u, folder, fn, call.message.chat.id), daemon=True).start()
            bot.send_message(call.message.chat.id, f"🟢 মোট {started_count}টি বন্ধ স্ক্রিপ্ট চালু করার চেষ্টা করা হয়েছে।")

    except Exception as e:
        logger.error(f"Callback error: {e}")
        try:
            bot.answer_callback_query(call.id, "এরর হয়েছে!")
        except Exception:
            pass

def cleanup():
    with SCRIPTS_LOCK:
        items = list(bot_scripts.values())
        bot_scripts.clear()
    for info in items:
        kill_process_tree(info)

atexit.register(cleanup)

if __name__ == '__main__':
    logger.info("🤖 মার্কো ফাইল হোস্ট বট চালু হচ্ছে...")
    keep_alive()
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
