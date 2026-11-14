# -*- coding: utf-8 -*-
"""
Marco File Host — Professional Telegram Bot Hosting
====================================================
Python (.py), JavaScript (.js) ও .zip প্রজেক্ট আপলোড করে
রান / স্টপ / রিস্টার্ট / লগ দেখার সুবিধা সহ।
"""

import os
import sys
import re
import time
import uuid
import signal
import shutil
import sqlite3
import logging
import zipfile
import tempfile
import atexit
import hashlib
import subprocess
import threading
from threading import Thread

import telebot
import psutil
from telebot import types
from flask import Flask

# ═══════════════════════════════════════════════════════════════════
#                          CONFIGURATION
# ═══════════════════════════════════════════════════════════════════
TOKEN          = os.environ.get('BOT_TOKEN', '9115784893:AAGCwR20a3maDEF9TL5o5O5FmyGUtwbf3lM').strip()
YOUR_USERNAME  = os.environ.get('YOUR_USERNAME', '@santobhai_dm').strip()
UPDATE_CHANNEL = os.environ.get('UPDATE_CHANNEL', 'https://t.me/MohabbatBd').strip()

try:
    OWNER_ID = int(os.environ.get('OWNER_ID', '7010177964'))
except (ValueError, TypeError):
    OWNER_ID = 7010177964

BASE_DIR         = os.path.abspath(os.path.dirname(__file__))
UPLOAD_BOTS_DIR  = os.path.join(BASE_DIR, 'upload_bots')
IROTECH_DIR      = os.path.join(BASE_DIR, 'inf')
DATABASE_PATH    = os.path.join(IROTECH_DIR, 'bot_data.db')

FREE_USER_LIMIT      = int(os.environ.get('FREE_USER_LIMIT', '5'))
MAX_FILE_SIZE        = 20 * 1024 * 1024      # 20 MB
ALLOWED_EXTENSIONS   = {'.py', '.js', '.zip'}
SCRIPT_STARTUP_GRACE = 3
LOG_TAIL_BYTES       = 4000

os.makedirs(UPLOAD_BOTS_DIR, exist_ok=True)
os.makedirs(IROTECH_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════════════════════
#                            LOGGING
# ═══════════════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-7s | %(threadName)s | %(message)s'
)
logger = logging.getLogger("MarcoBot")

# ═══════════════════════════════════════════════════════════════════
#                       FLASK KEEP-ALIVE
# ═══════════════════════════════════════════════════════════════════
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "আমি মার্কো ফাইল হোস্ট (I'am Marco File Host)"

@flask_app.route('/health')
def health():
    return "OK", 200

def _run_flask():
    port = int(os.environ.get("PORT", 8080))
    try:
        flask_app.run(host='0.0.0.0', port=port, debug=False,
                      use_reloader=False, threaded=True)
    except OSError as e:
        logger.error(f"Flask bind error on {port}: {e}")
    except Exception as e:
        logger.error(f"Flask error: {e}")

def keep_alive():
    Thread(target=_run_flask, daemon=True).start()
    logger.info("✅ ফ্লাস্ক কিপ-অ্যালাইভ সার্ভার চালু হয়েছে।")

# ═══════════════════════════════════════════════════════════════════
#                          BOT INIT
# ═══════════════════════════════════════════════════════════════════
if not TOKEN or ':' not in TOKEN:
    logger.critical("❌ BOT_TOKEN সঠিকভাবে সেট করা হয়নি — থামানো হচ্ছে।")
    sys.exit(1)

bot = telebot.TeleBot(TOKEN, parse_mode=None)

STATE_LOCK  = threading.RLock()
SCRIPT_LOCK = threading.RLock()

bot_scripts   = {}
user_files    = {}
active_users  = set()
bot_locked    = False
file_callback_registry = {}
_pending_cmd_targets   = {}

# ═══════════════════════════════════════════════════════════════════
#                     MALWARE SIGNATURES
# ═══════════════════════════════════════════════════════════════════
MALWARE_SIGNATURES = [
    b'MZ', b'\x7fELF', b'\xfe\xed\xfa', b'\xce\xfa\xed\xfe', b'\xca\xfe\xba\xbe',
]
ENCRYPTED_FILE_INDICATORS = [b'openssl', b'encrypted', b'cipher',
                              b'AES-', b'DES-', b'RSA-', b'GPG']
SUSPICIOUS_KEYWORDS = [b'ransomware', b'trojan', b'backdoor',
                        b'keylogger', b'rootkit', b'botnet']

# ═══════════════════════════════════════════════════════════════════
#                         DATABASE
# ═══════════════════════════════════════════════════════════════════
def _connect():
    return sqlite3.connect(DATABASE_PATH, check_same_thread=False, timeout=15)

def init_db():
    try:
        with STATE_LOCK:
            conn = _connect()
            c = conn.cursor()
            c.execute("""CREATE TABLE IF NOT EXISTS user_files (
                            user_id   INTEGER,
                            file_name TEXT,
                            file_type TEXT,
                            PRIMARY KEY (user_id, file_name))""")
            c.execute("""CREATE TABLE IF NOT EXISTS active_users (
                            user_id INTEGER PRIMARY KEY)""")
            conn.commit()
            conn.close()
    except Exception as e:
        logger.error(f"❌ DB init error: {e}")

def load_data():
    try:
        with STATE_LOCK:
            conn = _connect()
            c = conn.cursor()
            c.execute("SELECT user_id, file_name, file_type FROM user_files")
            for uid, fname, ftype in c.fetchall():
                user_files.setdefault(uid, []).append((fname, ftype))
            c.execute("SELECT user_id FROM active_users")
            active_users.update(uid for (uid,) in c.fetchall())
            conn.close()
        logger.info(f"📊 Loaded {len(user_files)} users, {len(active_users)} active")
    except Exception as e:
        logger.error(f"❌ DB load error: {e}")

def save_user_file(user_id, file_name, file_type='py'):
    with STATE_LOCK:
        try:
            conn = _connect()
            c = conn.cursor()
            c.execute(
                "INSERT OR REPLACE INTO user_files (user_id, file_name, file_type) VALUES (?, ?, ?)",
                (user_id, file_name, file_type)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"save_user_file DB error: {e}")
        lst = user_files.setdefault(user_id, [])
        user_files[user_id] = [(fn, ft) for fn, ft in lst if fn != file_name]
        user_files[user_id].append((file_name, file_type))

def remove_user_file_db(user_id, file_name):
    with STATE_LOCK:
        try:
            conn = _connect()
            c = conn.cursor()
            c.execute("DELETE FROM user_files WHERE user_id = ? AND file_name = ?",
                      (user_id, file_name))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"remove_user_file DB error: {e}")
        if user_id in user_files:
            user_files[user_id] = [f for f in user_files[user_id] if f[0] != file_name]

def add_active_user(user_id):
    with STATE_LOCK:
        if user_id in active_users:
            return False
        active_users.add(user_id)
        try:
            conn = _connect()
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO active_users (user_id) VALUES (?)", (user_id,))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"add_active_user DB error: {e}")
        return True

init_db()
load_data()

# ═══════════════════════════════════════════════════════════════════
#                       HELPERS
# ═══════════════════════════════════════════════════════════════════
def get_user_folder(user_id):
    folder = os.path.join(UPLOAD_BOTS_DIR, str(user_id))
    os.makedirs(folder, exist_ok=True)
    return folder

def get_user_file_limit(user_id):
    return float('inf') if user_id == OWNER_ID else FREE_USER_LIMIT

def get_user_file_count(user_id):
    with STATE_LOCK:
        return len(user_files.get(user_id, []))

def _script_key(owner, fname):
    return f"{owner}_{fname}"

def _safe_log_path(script_path):
    """স্ক্রিপ্টের পাশে লগ ফাইলের পাথ।"""
    d = os.path.dirname(script_path)
    b = os.path.splitext(os.path.basename(script_path))[0]
    return os.path.join(d, f"{b}.log")

# ═══════════════════════════════════════════════════════════════════
#                    MALWARE DETECTION
# ═══════════════════════════════════════════════════════════════════
def is_suspicious_file(content: bytes, file_name: str):
    ext = os.path.splitext(file_name)[1].lower()
    if ext in ('.zip', '.py', '.js'):
        sample = content[:4096].decode('utf-8', errors='ignore').lower()
        for kw in SUSPICIOUS_KEYWORDS:
            if kw.decode().lower() in sample:
                return True, "সন্দেহজনক কীওয়ার্ড পাওয়া গেছে"
        return False, "ফাইলটি নিরাপদ"
    for sig in MALWARE_SIGNATURES:
        if content.startswith(sig):
            return True, "ম্যালওয়্যার সিগনেচার পাওয়া গেছে"
    sample = content[:4096]
    for ind in ENCRYPTED_FILE_INDICATORS:
        if ind in sample:
            return True, "এনক্রিপ্টেড ফাইল ইন্ডিকেটর পাওয়া গেছে"
    return False, "ফাইলটি নিরাপদ"

def scan_file_for_malware(content, file_name, user_id):
    if user_id == OWNER_ID:
        return True, "মালিক সিকিউরিটি চেক বাইপাস করেছেন"
    bad, reason = is_suspicious_file(content, file_name)
    return (False, f"সিকিউরিটি ভায়োলেশন: {reason}") if bad else (True, "ফাইলটি নিরাপদ")

# ═══════════════════════════════════════════════════════════════════
#                    PROCESS MANAGEMENT
# ═══════════════════════════════════════════════════════════════════
ZOMBIE = getattr(psutil, 'STATUS_ZOMBIE', 'zombie')

def is_bot_running(owner, fname):
    key = _script_key(owner, fname)
    with SCRIPT_LOCK:
        info = bot_scripts.get(key)
    if not info:
        return False
    proc = info.get('process')
    if not proc or proc.poll() is not None:
        return False
    try:
        p = psutil.Process(proc.pid)
        return p.is_running() and p.status() != ZOMBIE
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return False
    except Exception:
        return False

def _cleanup_process_info(info):
    proc = info.get('process')
    if proc:
        try:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    try: proc.wait(timeout=2)
                    except Exception: pass
        except Exception as e:
            logger.warning(f"Process terminate warn: {e}")
    log_file = info.get('log_file')
    if log_file and not getattr(log_file, 'closed', True):
        try: log_file.close()
        except Exception: pass

def stop_script(key):
    with SCRIPT_LOCK:
        info = bot_scripts.pop(key, None)
    if info:
        _cleanup_process_info(info)
        return True
    return False

def kill_process_tree(process_info):
    _cleanup_process_info(process_info)

# ═══════════════════════════════════════════════════════════════════
#                    AUTO PACKAGE INSTALLER
# ═══════════════════════════════════════════════════════════════════
TELEGRAM_MODULES = {
    'telebot': 'pyTelegramBotAPI',
    'telegram': 'python-telegram-bot',
    'aiogram': 'aiogram',
    'pyrogram': 'pyrogram',
    'requests': 'requests',
    'psutil': 'psutil',
}

def attempt_install_pip(module_name, message):
    package = TELEGRAM_MODULES.get(module_name.lower(), module_name)
    try:
        bot.reply_to(message, f"🐍 `{module_name}` ইনস্টল হচ্ছে…", parse_mode='Markdown')
        r = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '--quiet', package],
            capture_output=True, text=True, timeout=180
        )
        if r.returncode == 0:
            bot.reply_to(message, f"✅ `{package}` ইনস্টল সম্পন্ন।", parse_mode='Markdown')
            return True
        bot.reply_to(message, f"❌ ইনস্টল ব্যর্থ: `{r.stderr[-200:]}`", parse_mode='Markdown')
        return False
    except Exception as e:
        logger.error(f"pip install error: {e}")
        return False

def attempt_install_npm(module_name, user_folder, message):
    try:
        bot.reply_to(message, f"🟠 `{module_name}` ইনস্টল হচ্ছে…", parse_mode='Markdown')
        r = subprocess.run(
            ['npm', 'install', module_name],
            capture_output=True, text=True, cwd=user_folder, timeout=180
        )
        if r.returncode == 0:
            bot.reply_to(message, f"✅ `{module_name}` ইনস্টল সম্পন্ন।", parse_mode='Markdown')
            return True
        bot.reply_to(message, f"❌ npm ইনস্টল ব্যর্থ: `{r.stderr[-200:]}`", parse_mode='Markdown')
        return False
    except Exception as e:
        logger.error(f"npm install error: {e}")
        return False

# ═══════════════════════════════════════════════════════════════════
#                     SCRIPT RUNNERS
# ═══════════════════════════════════════════════════════════════════
def _run_generic(interpreter, script_path, script_owner_id, work_dir,
                 file_name, message, error_pattern, installer, kind_label,
                 attempt=1):
    if attempt > 2:
        try: bot.reply_to(message, f"❌ '{file_name}' ২ বার চেষ্টার পরেও চালু হয়নি।")
        except Exception: pass
        return

    key = _script_key(script_owner_id, file_name)

    if not script_path or not os.path.exists(script_path):
        remove_user_file_db(script_owner_id, file_name)
        try: bot.reply_to(message, f"❌ ফাইল পাওয়া যায়নি: `{file_name}`", parse_mode='Markdown')
        except Exception: pass
        return

    log_path = _safe_log_path(script_path)
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
    except Exception:
        pass

    log_file = None
    process  = None
    try:
        log_file = open(log_path, 'w', encoding='utf-8', errors='ignore')
        cmd = [interpreter]
        if interpreter == sys.executable:
            cmd.append('-u')
        cmd.append(script_path)

        process = subprocess.Popen(
            cmd, cwd=work_dir,
            stdout=log_file, stderr=subprocess.STDOUT, stdin=subprocess.PIPE,
            text=True, encoding='utf-8', errors='ignore', bufsize=1,
        )

        with SCRIPT_LOCK:
            bot_scripts[key] = {
                'process': process, 'log_file': log_file, 'log_path': log_path,
                'file_name': file_name, 'script_owner_id': script_owner_id,
                'work_dir': work_dir,
            }

        time.sleep(SCRIPT_STARTUP_GRACE)

        if process.poll() is not None:
            try: log_file.flush()
            except Exception: pass
            stderr = ""
            try:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    stderr = f.read()
            except Exception:
                pass

            with SCRIPT_LOCK:
                bot_scripts.pop(key, None)
            try: log_file.close()
            except Exception: pass

            match = re.search(error_pattern, stderr)
            if match and installer(match.group(1).strip().strip("'\""), message):
                bot.reply_to(message, "🔄 পুনরায় চালু করা হচ্ছে…")
                Thread(
                    target=_run_generic,
                    args=(interpreter, script_path, script_owner_id, work_dir,
                          file_name, message, error_pattern, installer,
                          kind_label, attempt + 1),
                    daemon=True
                ).start()
                return

            tail = (stderr or "(কোনো আউটপুট নেই)")[-800:]
            bot.reply_to(
                message,
                f"❌ {kind_label} '{file_name}' চালু হতে পারেনি:\n```\n{tail}\n```",
                parse_mode='Markdown'
            )
            return

        bot.reply_to(message, f"✅ {kind_label} `{file_name}` চালু হয়েছে!", parse_mode='Markdown')

    except Exception as e:
        logger.exception(f"run {kind_label} error")
        if process and process.poll() is None:
            try: process.kill()
            except Exception: pass
        if log_file and not log_file.closed:
            try: log_file.close()
            except Exception: pass
        with SCRIPT_LOCK:
            bot_scripts.pop(key, None)
        try: bot.reply_to(message, f"❌ এরর: `{e}`", parse_mode='Markdown')
        except Exception: pass

def run_script(script_path, owner, work_dir, fname, message, attempt=1):
    _run_generic(
        interpreter=sys.executable,
        script_path=script_path, script_owner_id=owner, work_dir=work_dir,
        file_name=fname, message=message,
        error_pattern=r"ModuleNotFoundError: No module named ['\"]([^'\"]+)['\"]",
        installer=lambda mod, m: attempt_install_pip(mod, m),
        kind_label="🐍 পাইথন স্ক্রিপ্ট", attempt=attempt,
    )

def run_js_script(script_path, owner, work_dir, fname, message, attempt=1):
    _run_generic(
        interpreter='node',
        script_path=script_path, script_owner_id=owner, work_dir=work_dir,
        file_name=fname, message=message,
        error_pattern=r"Cannot find module ['\"]([^'\"]+)['\"]",
        installer=lambda mod, m: attempt_install_npm(mod, work_dir, m),
        kind_label="🟨 জেএস স্ক্রিপ্ট", attempt=attempt,
    )

# ═══════════════════════════════════════════════════════════════════
#                    ZIP SAFE EXTRACTION
# ═══════════════════════════════════════════════════════════════════
def safe_extract_zip(zip_path, dest_dir):
    dest_real = os.path.realpath(dest_dir)
    with zipfile.ZipFile(zip_path, 'r') as z:
        for m in z.infolist():
            target = os.path.realpath(os.path.join(dest_real, m.filename))
            if target != dest_real and not target.startswith(dest_real + os.sep):
                raise ValueError(f"Zip Slip detected: {m.filename}")
        z.extractall(dest_real)

def _find_entry(extracted_dir):
    candidates = ['main.py', 'bot.py', 'app.py', 'index.js', 'main.js']
    for root, _, files in os.walk(extracted_dir):
        for c in candidates:
            if c in files:
                return os.path.relpath(os.path.join(root, c), extracted_dir).replace('\\', '/')
    return None

# ═══════════════════════════════════════════════════════════════════
#                    CALLBACK TOKEN HELPERS
# ═══════════════════════════════════════════════════════════════════
def make_file_cb(action, owner, fname):
    raw = f"{action}_{owner}_{fname}"
    if len(raw.encode('utf-8')) <= 60:
        return raw
    token = hashlib.md5(f"{owner}_{fname}".encode()).hexdigest()[:14]
    file_callback_registry[token] = (owner, fname)
    return f"{action}_h_{token}"

def parse_file_cb(data):
    if data.startswith(('file_h_', 'start_h_', 'stop_h_',
                        'restart_h_', 'delete_h_', 'logs_h_')):
        try:
            action, _, token = data.split('_', 2)
            if token in file_callback_registry:
                owner, fname = file_callback_registry[token]
                return action, owner, fname
        except Exception:
            pass
        return None
    try:
        action, owner_s, fname = data.split('_', 2)
        return action, int(owner_s), fname
    except Exception:
        return None

# ═══════════════════════════════════════════════════════════════════
#                     KEYBOARDS / MENUS
# ═══════════════════════════════════════════════════════════════════
COMMAND_BUTTONS_LAYOUT_USER = [
    ["📤 ফাইল আপলোড", "📂 আমার ফাইলসমূহ"],
    ["⚡ বট স্পিড",   "📊 পরিসংখ্যান"],
    ["📤 কমান্ড পাঠান", "📢 আপডেট চ্যানেল"],
    ["ℹ️ হেল্প ও নিয়মাবলী", "📞  সহায়তা নিন"],
]
COMMAND_BUTTONS_LAYOUT_OWNER = [
    ["📤 ফাইল আপলোড", "📂 আমার ফাইলসমূহ"],
    ["⚡ বট স্পিড",   "📊 পরিসংখ্যান"],
    ["📤 কমান্ড পাঠান", "👑 অ্যাডমিন প্যানেল"],
    ["ℹ️ হেল্প ও নিয়মাবলী", "📞  সহায়তা নিন"],
]

def create_main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    layout = COMMAND_BUTTONS_LAYOUT_OWNER if user_id == OWNER_ID else COMMAND_BUTTONS_LAYOUT_USER
    for row in layout:
        markup.add(*[types.KeyboardButton(t) for t in row])
    return markup

def create_control_buttons(owner, fname, is_running=True):
    m = types.InlineKeyboardMarkup(row_width=2)
    if is_running:
        m.row(
            types.InlineKeyboardButton("🔴 থামান", callback_data=make_file_cb('stop', owner, fname)),
            types.InlineKeyboardButton("🔄 রিস্টার্ট", callback_data=make_file_cb('restart', owner, fname)),
        )
    else:
        m.row(types.InlineKeyboardButton("🟢 চালু করুন", callback_data=make_file_cb('start', owner, fname)))
    m.row(
        types.InlineKeyboardButton("🗑️ ডিলিট", callback_data=make_file_cb('delete', owner, fname)),
        types.InlineKeyboardButton("📜 লগ",     callback_data=make_file_cb('logs',   owner, fname)),
    )
    m.add(types.InlineKeyboardButton("🔙 ফাইল মেনুতে ফেরত", callback_data='check_files'))
    return m

def create_admin_panel():
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(
        types.InlineKeyboardButton("📢 সম্প্রচার", callback_data='admin_broadcast'),
        types.InlineKeyboardButton("🔒 বট লক/আনলক", callback_data='admin_lock'),
        types.InlineKeyboardButton("🟢 সব কোড একসাথে রান", callback_data='admin_run_all'),
        types.InlineKeyboardButton("🔙 মেনু বন্ধ করুন", callback_data='close_menu'),
    )
    return m

def create_send_command_menu():
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(
        types.InlineKeyboardButton("📝 প্রসেসে কমান্ড পাঠান", callback_data='send_to_process'),
        types.InlineKeyboardButton("🔍 সব লগ দেখুন", callback_data='view_all_logs'),
        types.InlineKeyboardButton("🔙 মেনু বন্ধ করুন", callback_data='close_menu'),
    )
    return m

# ═══════════════════════════════════════════════════════════════════
#                       CORE LOGIC
#  (chat_id + user_id স্পষ্টভাবে পাস করা হয় — callback-safe)
# ═══════════════════════════════════════════════════════════════════
def _logic_send_welcome(message):
    user_id = message.from_user.id
    if bot_locked and user_id != OWNER_ID:
        bot.send_message(message.chat.id, "⚠️ বট এই মুহূর্তে লক করা আছে।")
        return
    if add_active_user(user_id):
        try:
            bot.send_message(
                OWNER_ID,
                f"🎉 নতুন ইউজার: {message.from_user.first_name} (`{user_id}`)",
                parse_mode='Markdown'
            )
        except Exception:
            pass
    status = "👑 মালিক (Owner)" if user_id == OWNER_ID else "🆓 ফ্রি ইউজার"
    limit  = "আনলিমিটেড" if user_id == OWNER_ID else str(FREE_USER_LIMIT)
    msg = (
        f"〽️ স্বাগতম, {message.from_user.first_name}!\n\n"
        f"🆔 আইডি: `{user_id}`\n"
        f"🔰 স্ট্যাটাস: {status}\n"
        f"📁 ফাইল: {get_user_file_count(user_id)} / {limit}\n\n"
        f"🤖 পাইথন বা জেএস কোড সহজেই রান করুন।"
    )
    bot.send_message(message.chat.id, msg,
                     reply_markup=create_main_menu(user_id), parse_mode='Markdown')

def _logic_upload_file(message):
    uid = message.from_user.id
    if bot_locked and uid != OWNER_ID:
        bot.reply_to(message, "⚠️ বট লক করা আছে।")
        return
    if get_user_file_count(uid) >= get_user_file_limit(uid):
        bot.reply_to(message, "⚠️ ফাইল লিমিট শেষ। আগে কিছু ফাইল ডিলিট করুন।")
        return
    bot.reply_to(message, "📤 আপনার `.py`, `.js` অথবা `.zip` প্রজেক্ট পাঠান।")

def _logic_check_files(chat_id, user_id):
    with STATE_LOCK:
        files = list(user_files.get(user_id, []))
    if not files:
        bot.send_message(chat_id, "📂 আপনার কোনো ফাইল নেই।")
        return
    m = types.InlineKeyboardMarkup(row_width=1)
    for fname, _ in sorted(files):
        icon = "🟢" if is_bot_running(user_id, fname) else "🔴"
        m.add(types.InlineKeyboardButton(
            f"{icon} {fname}",
            callback_data=make_file_cb('file', user_id, fname)
        ))
    bot.send_message(chat_id, "📂 আপনার ফাইলসমূহ:", reply_markup=m)

def _logic_bot_speed(chat_id):
    start = time.time()
    try:
        msg = bot.send_message(chat_id, "🏃 চেক করা হচ্ছে…")
        ms = round((time.time() - start) * 1000, 2)
        bot.edit_message_text(
            f"⚡ রেসপন্স: {ms} ms\n"
            f"🚦 স্ট্যাটাস: {'🔒 লকড' if bot_locked else '🔓 আনলকড'}",
            chat_id, msg.message_id
        )
    except Exception:
        pass

def _logic_statistics(chat_id, user_id):
    with STATE_LOCK:
        total_files = sum(len(f) for f in user_files.values())
        n_users     = len(active_users)
    with SCRIPT_LOCK:
        items = list(bot_scripts.items())
    running = sum(1 for _, info in items
                  if is_bot_running(info['script_owner_id'], info['file_name']))
    mine    = sum(1 for _, info in items
                  if info['script_owner_id'] == user_id
                  and is_bot_running(user_id, info['file_name']))
    bot.send_message(
        chat_id,
        f"📊 পরিসংখ্যান:\n👥 ইউজার: {n_users}\n"
        f"📂 মোট ফাইল: {total_files}\n🟢 মোট রানিং: {running}\n"
        f"🤖 আপনার রানিং: {mine}"
    )

# ═══════════════════════════════════════════════════════════════════
#                     MESSAGE HANDLERS
# ═══════════════════════════════════════════════════════════════════
@bot.message_handler(commands=['start', 'help'])
def cmd_start(message):
    try:
        bot.clear_step_handler_by_chat_id(message.chat.id)
    except Exception:
        pass
    try:
        _logic_send_welcome(message)
    except Exception as e:
        logger.exception("start error")
        try: bot.reply_to(message, f"❌ এরর: {e}")
        except Exception: pass

BUTTONS_LOGIC = {
    "📤 ফাইল আপলোড":      _logic_upload_file,
    "📂 আমার ফাইলসমূহ":    lambda m: _logic_check_files(m.chat.id, m.from_user.id),
    "⚡ বট স্পিড":         lambda m: _logic_bot_speed(m.chat.id),
    "📊 পরিসংখ্যান":       lambda m: _logic_statistics(m.chat.id, m.from_user.id),
    "📤 কমান্ড পাঠান":     lambda m: bot.reply_to(
        m, "অপশন সিলেক্ট করুন:", reply_markup=create_send_command_menu()),
    "📢 আপডেট চ্যানেল":    lambda m: bot.reply_to(
        m, "চ্যানেলে যুক্ত হোন:",
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton('📢 চ্যানেল', url=UPDATE_CHANNEL))),
    "ℹ️ হেল্প ও নিয়মাবলী": lambda m: bot.reply_to(
        m,
        "📖 *নিয়মাবলী*\n\n• শুধু .py, .js, .zip গ্রহণযোগ্য\n"
        "• ফাইল সাইজ সর্বোচ্চ 20 MB\n• আপলোড করলে অটো রান হবে\n"
        "• সন্দেহজনক ফাইল ব্লক করা হবে",
        parse_mode='Markdown'),
    "📞  সহায়তা নিন":      lambda m: bot.reply_to(
        m, "সাপোর্ট:",
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton('📞 যোগাযোগ',
                                        url=f"https://t.me/{YOUR_USERNAME.lstrip('@')}"))),
}

@bot.message_handler(func=lambda m: m.text == "👑 অ্যাডমিন প্যানেল")
def _admin_panel_btn(message):
    if message.from_user.id == OWNER_ID:
        bot.reply_to(message, "👑 অ্যাডমিন প্যানেল:", reply_markup=create_admin_panel())
    else:
        bot.reply_to(message, "⛔ অনুমতি নেই।")

@bot.message_handler(content_types=['text'],
                     func=lambda m: m.text in BUTTONS_LOGIC)
def handle_text(message):
    fn = BUTTONS_LOGIC.get(message.text)
    if fn:
        try:
            fn(message)
        except Exception as e:
            logger.exception("button handler error")
            try: bot.reply_to(message, f"❌ এরর: {e}")
            except Exception: pass

# ─── Document handler ───
@bot.message_handler(content_types=['document'])
def handle_doc(message):
    uid = message.from_user.id
    if bot_locked and uid != OWNER_ID:
        bot.reply_to(message, "⚠️ বট লক করা আছে।")
        return
    if get_user_file_count(uid) >= get_user_file_limit(uid):
        bot.reply_to(message, "⚠️ ফাইল লিমিট শেষ।")
        return

    doc = message.document
    if not doc or not doc.file_name:
        bot.reply_to(message, "⚠️ ফাইলের নাম পাওয়া যায়নি।")
        return
    if doc.file_size and doc.file_size > MAX_FILE_SIZE:
        bot.reply_to(message, "⚠️ ফাইল 20 MB এর বড়।")
        return
    ext = os.path.splitext(doc.file_name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        bot.reply_to(message, "⚠️ শুধু `.py`, `.js`, `.zip` গ্রহণযোগ্য।")
        return

    msg = bot.reply_to(message, "⏳ প্রসেস হচ্ছে…")
    try:
        file_info = bot.get_file(doc.file_id)
        content   = bot.download_file(file_info.file_path)
    except Exception as e:
        try: bot.edit_message_text(f"❌ ডাউনলোড ব্যর্থ: {e}",
                                    message.chat.id, msg.message_id)
        except Exception: pass
        return

    if uid != OWNER_ID:
        safe, reason = scan_file_for_malware(content, doc.file_name, uid)
        if not safe:
            try: bot.edit_message_text(f"🚨 *সিকিউরিটি অ্যালার্ট*\n\n{reason}",
                                        message.chat.id, msg.message_id,
                                        parse_mode='Markdown')
            except Exception: pass
            return

    folder = get_user_folder(uid)

    # ─── ZIP ───
    if ext == '.zip':
        temp_dir = tempfile.mkdtemp(prefix="mh_zip_")
        try:
            zip_path = os.path.join(temp_dir, 'upload.zip')
            with open(zip_path, 'wb') as f:
                f.write(content)
            extract_dir = os.path.join(temp_dir, 'extracted')
            os.makedirs(extract_dir, exist_ok=True)
            safe_extract_zip(zip_path, extract_dir)

            entry = _find_entry(extract_dir)
            if not entry:
                bot.edit_message_text(
                    "❌ ZIP-এ `main.py`, `bot.py`, `app.py`, `index.js` বা `main.js` পাওয়া যায়নি।",
                    message.chat.id, msg.message_id
                )
                return

            # extracted .py/.js স্ক্যান
            if uid != OWNER_ID:
                for root, _, fnames in os.walk(extract_dir):
                    for fn in fnames:
                        if fn.endswith(('.py', '.js')):
                            fp = os.path.join(root, fn)
                            try:
                                with open(fp, 'rb') as fh:
                                    sample = fh.read(4096)
                                bad, rsn = is_suspicious_file(sample, fn)
                                if bad:
                                    raise ValueError(f"{rsn}: {fn}")
                            except Exception as e:
                                raise ValueError(str(e))

            for item in os.listdir(extract_dir):
                src = os.path.join(extract_dir, item)
                dst = os.path.join(folder, item)
                if os.path.exists(dst):
                    if os.path.isdir(dst):
                        shutil.rmtree(dst, ignore_errors=True)
                    else:
                        os.remove(dst)
                shutil.move(src, dst)

            main_filename = entry.replace('\\', '/')
            ftype = 'py' if main_filename.endswith('.py') else 'js'
            full_path = os.path.join(folder, main_filename)
            work_dir  = os.path.dirname(full_path) or folder

            save_user_file(uid, main_filename, ftype)
            bot.edit_message_text(
                f"✅ এক্সট্রাক্ট সম্পন্ন। `{os.path.basename(main_filename)}` রান হচ্ছে…",
                message.chat.id, msg.message_id, parse_mode='Markdown'
            )
            runner = run_script if ftype == 'py' else run_js_script
            Thread(target=runner,
                   args=(full_path, uid, work_dir, main_filename, message),
                   daemon=True).start()
        except Exception as e:
            logger.exception("zip error")
            try: bot.edit_message_text(f"❌ ZIP এরর: {e}",
                                        message.chat.id, msg.message_id)
            except Exception: pass
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
        return

    # ─── .py / .js ───
    try:
        file_path = os.path.join(folder, doc.file_name)
        with open(file_path, 'wb') as f:
            f.write(content)
        save_user_file(uid, doc.file_name, ext[1:])
        bot.edit_message_text(
            f"✅ সেভ হয়েছে। `{doc.file_name}` রান হচ্ছে…",
            message.chat.id, msg.message_id, parse_mode='Markdown'
        )
        runner = run_script if ext == '.py' else run_js_script
        Thread(target=runner,
               args=(file_path, uid, folder, doc.file_name, message),
               daemon=True).start()
    except Exception as e:
        logger.exception("upload error")
        try: bot.edit_message_text(f"❌ এরর: {e}",
                                    message.chat.id, msg.message_id)
        except Exception: pass

# ═══════════════════════════════════════════════════════════════════
#              SEND-COMMAND-TO-PROCESS  /  VIEW LOGS
# ═══════════════════════════════════════════════════════════════════
def _show_running_scripts_for_command(chat_id, user_id):
    with SCRIPT_LOCK:
        items = list(bot_scripts.items())
    running = [
        (k, info) for k, info in items
        if (info['script_owner_id'] == user_id or user_id == OWNER_ID)
        and is_bot_running(info['script_owner_id'], info['file_name'])
    ]
    if not running:
        bot.send_message(chat_id, "❌ কোনো রানিং স্ক্রিপ্ট নেই।")
        return
    m = types.InlineKeyboardMarkup(row_width=1)
    for _, info in running:
        token = uuid.uuid4().hex[:10]
        _pending_cmd_targets[token] = (info['script_owner_id'], info['file_name'])
        label = f"{info['script_owner_id']} → {info['file_name']}"
        m.add(types.InlineKeyboardButton(label, callback_data=f'cmdsel_{token}'))
    bot.send_message(chat_id, "🎯 কোন স্ক্রিপ্টে কমান্ড পাঠাবেন?", reply_markup=m)

def _do_send_command(message, owner, fname):
    if not message.text:
        bot.reply_to(message, "❌ শুধু টেক্সট কমান্ড সাপোর্টেড।")
        return
    key = _script_key(owner, fname)
    with SCRIPT_LOCK:
        info = bot_scripts.get(key)
    if not info:
        bot.reply_to(message, "❌ স্ক্রিপ্ট রানিং নেই।")
        return
    proc = info.get('process')
    if not proc or proc.poll() is not None:
        bot.reply_to(message, "❌ প্রসেস বন্ধ হয়ে গেছে।")
        return
    try:
        proc.stdin.write(message.text + "\n")
        proc.stdin.flush()
        bot.reply_to(message, f"✅ কমান্ড পাঠানো হয়েছে:\n`{message.text}`",
                     parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ পাঠাতে ব্যর্থ: {e}")

def _show_all_logs(chat_id, user_id):
    with STATE_LOCK:
        files = list(user_files.get(user_id, []))
    if not files:
        bot.send_message(chat_id, "❌ কোনো ফাইল নেই।")
        return
    folder = get_user_folder(user_id)
    chunks = []
    for fname, _ in files:
        log_path = _safe_log_path(os.path.join(folder, fname))
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    tail = f.read()[-1200:]
                chunks.append(f"📜 {fname}:\n{tail or '(খালি)'}")
            except Exception:
                pass
    if not chunks:
        bot.send_message(chat_id, "❌ কোনো লগ পাওয়া যায়নি।")
        return
    text = "\n\n".join(chunks)[-LOG_TAIL_BYTES:]
    bot.send_message(chat_id, f"```\n{text}\n```", parse_mode='Markdown')

# ═══════════════════════════════════════════════════════════════════
#                     BROADCAST
# ═══════════════════════════════════════════════════════════════════
def _do_broadcast(message):
    if not message.text:
        bot.reply_to(message, "❌ শুধু টেক্সট সম্প্রচারযোগ্য।")
        return
    with STATE_LOCK:
        users = list(active_users)
    sent, failed = 0, 0
    for u in users:
        try:
            bot.send_message(u, message.text)
            sent += 1
        except Exception:
            failed += 1
        time.sleep(0.04)
    bot.send_message(message.chat.id,
                     f"📢 সম্প্রচার সম্পন্ন\n✅ সফল: {sent}\n❌ ব্যর্থ: {failed}")

# ═══════════════════════════════════════════════════════════════════
#                     CALLBACK HANDLER
# ═══════════════════════════════════════════════════════════════════
@bot.callback_query_handler(func=lambda c: True)
def handle_callbacks(call):
    global bot_locked
    uid  = call.from_user.id          # ✅ আসল ইউজার
    data = call.data

    if bot_locked and uid != OWNER_ID:
        bot.answer_callback_query(call.id, "⚠️ বট লক করা আছে।", show_alert=True)
        return

    chat_id = call.message.chat.id
    msg_id  = call.message.message_id

    try:
        if data == 'check_files':
            try: bot.delete_message(chat_id, msg_id)
            except Exception: pass
            _logic_check_files(chat_id, uid)
            bot.answer_callback_query(call.id)
            return

        if data == 'close_menu':
            try: bot.delete_message(chat_id, msg_id)
            except Exception: pass
            bot.answer_callback_query(call.id)
            return

        if data == 'send_to_process':
            bot.answer_callback_query(call.id)
            _show_running_scripts_for_command(chat_id, uid)
            return

        if data == 'view_all_logs':
            bot.answer_callback_query(call.id)
            _show_all_logs(chat_id, uid)
            return

        if data.startswith('cmdsel_'):
            token = data.split('_', 1)[1]
            target = _pending_cmd_targets.pop(token, None)
            if not target:
                bot.answer_callback_query(call.id, "⌛ মেয়াদোত্তীর্ণ।", show_alert=True)
                return
            owner, fname = target
            if uid != owner and uid != OWNER_ID:
                bot.answer_callback_query(call.id, "⛔ অনুমতি নেই।", show_alert=True)
                return
            bot.answer_callback_query(call.id)
            m = bot.send_message(chat_id,
                                  f"✏️ `{fname}` এ পাঠানোর জন্য টেক্সট লিখুন:",
                                  parse_mode='Markdown')
            bot.register_next_step_handler(m, lambda msg: _do_send_command(msg, owner, fname))
            return

        if data.startswith(('file_', 'start_', 'stop_', 'restart_', 'delete_', 'logs_')):
            parsed = parse_file_cb(data)
            if not parsed:
                bot.answer_callback_query(call.id, "❌ অজানা কমান্ড।", show_alert=True)
                return
            action, owner, fname = parsed

            if uid != owner and uid != OWNER_ID:
                bot.answer_callback_query(call.id, "⛔ অনুমতি নেই।", show_alert=True)
                return

            key   = _script_key(owner, fname)
            folder   = get_user_folder(owner)
            fpath    = os.path.join(folder, fname)
            work_dir = os.path.dirname(fpath) or folder

            # ফাইল মেনু
            if action == 'file':
                running = is_bot_running(owner, fname)
                try:
                    bot.edit_message_text(
                        f"⚙️ প্যানেল: `{fname}`\n"
                        f"স্ট্যাটাস: {'🟢 রানিং' if running else '🔴 বন্ধ'}",
                        chat_id, msg_id,
                        reply_markup=create_control_buttons(owner, fname, running),
                        parse_mode='Markdown'
                    )
                except Exception:
                    pass
                bot.answer_callback_query(call.id)
                return

            # START
            if action == 'start':
                if is_bot_running(owner, fname):
                    bot.answer_callback_query(call.id, "ইতিমধ্যে রানিং!")
                    return
                if not os.path.exists(fpath):
                    bot.answer_callback_query(call.id, "❌ ফাইল পাওয়া যায়নি!", show_alert=True)
                    return
                with STATE_LOCK:
                    entry = next((f for f in user_files.get(owner, []) if f[0] == fname), None)
                ftype = entry[1] if entry else os.path.splitext(fname)[1].lstrip('.')
                bot.answer_callback_query(call.id, "🟡 চালু হচ্ছে…")
                runner = run_script if ftype == 'py' else run_js_script
                Thread(target=runner,
                       args=(fpath, owner, work_dir, fname, call.message),
                       daemon=True).start()
                return

            # STOP
            if action == 'stop':
                stopped = stop_script(key)
                bot.answer_callback_query(
                    call.id, "🔴 থামানো হয়েছে" if stopped else "⚠️ রানিং নেই")
                try:
                    bot.edit_message_text(
                        f"⚙️ প্যানেল: `{fname}` | 🔴 বন্ধ",
                        chat_id, msg_id,
                        reply_markup=create_control_buttons(owner, fname, False),
                        parse_mode='Markdown'
                    )
                except Exception:
                    pass
                return

            # RESTART
            if action == 'restart':
                stop_script(key)
                time.sleep(0.4)
                if not os.path.exists(fpath):
                    bot.answer_callback_query(call.id, "❌ ফাইল নেই!", show_alert=True)
                    return
                with STATE_LOCK:
                    entry = next((f for f in user_files.get(owner, []) if f[0] == fname), None)
                ftype = entry[1] if entry else os.path.splitext(fname)[1].lstrip('.')
                bot.answer_callback_query(call.id, "🔄 রিস্টার্ট হচ্ছে…")
                runner = run_script if ftype == 'py' else run_js_script
                Thread(target=runner,
                       args=(fpath, owner, work_dir, fname, call.message),
                       daemon=True).start()
                return

            # DELETE
            if action == 'delete':
                stop_script(key)
                try:
                    if os.path.exists(fpath):
                        os.remove(fpath)
                except Exception as e:
                    logger.warning(f"delete file warn: {e}")
                remove_user_file_db(owner, fname)
                bot.answer_callback_query(call.id, "🗑️ ডিলিট সম্পন্ন")
                try:
                    bot.edit_message_text(f"🗑️ `{fname}` ডিলিট করা হয়েছে।",
                                            chat_id, msg_id, parse_mode='Markdown')
                except Exception:
                    pass
                return

            # LOGS
            if action == 'logs':
                log_path = _safe_log_path(fpath)
                if os.path.exists(log_path):
                    try:
                        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()[-LOG_TAIL_BYTES:]
                    except Exception as e:
                        content = f"(পড়তে ব্যর্থ: {e})"
                    bot.send_message(chat_id,
                                      f"📜 লগ — `{fname}`\n```\n{content or 'খালি'}\n```",
                                      parse_mode='Markdown')
                else:
                    bot.send_message(chat_id, "❌ লগ ফাইল নেই।")
                bot.answer_callback_query(call.id)
                return

        # ─── Admin ───
        if data == 'admin_broadcast':
            if uid != OWNER_ID:
                bot.answer_callback_query(call.id, "⛔ শুধু মালিক।", show_alert=True)
                return
            bot.answer_callback_query(call.id)
            m = bot.send_message(chat_id, "📢 সম্প্রচার মেসেজ পাঠান:")
            bot.register_next_step_handler(m, _do_broadcast)
            return

        if data == 'admin_lock':
            if uid != OWNER_ID:
                bot.answer_callback_query(call.id, "⛔ শুধু মালিক।", show_alert=True)
                return
            bot_locked = not bot_locked
            bot.answer_callback_query(
                call.id,
                "🔒 বট লক" if bot_locked else "🔓 বট আনলক",
                show_alert=True
            )
            return

        if data == 'admin_run_all':
            if uid != OWNER_ID:
                bot.answer_callback_query(call.id, "⛔ শুধু মালিক।", show_alert=True)
                return
            bot.answer_callback_query(call.id, "🟢 সব স্ক্রিপ্ট রান হচ্ছে…", show_alert=True)
            with STATE_LOCK:
                snapshot = [(u, list(files)) for u, files in user_files.items()]
            for user_id, files in snapshot:
                for fname, ftype in files:
                    if is_bot_running(user_id, fname):
                        continue
                    fpath = os.path.join(get_user_folder(user_id), fname)
                    if not os.path.exists(fpath):
                        continue
                    work_dir = os.path.dirname(fpath) or get_user_folder(user_id)
                    runner = run_script if ftype == 'py' else run_js_script
                    Thread(target=runner,
                           args=(fpath, user_id, work_dir, fname, call.message),
                           daemon=True).start()
                    time.sleep(0.2)
            return

        bot.answer_callback_query(call.id, "❓ অজানা কমান্ড")
    except Exception as e:
        logger.exception("callback error")
        try:
            bot.answer_callback_query(call.id, f"❌ এরর: {str(e)[:100]}", show_alert=True)
        except Exception:
            pass

# ═══════════════════════════════════════════════════════════════════
#                       SHUTDOWN
# ═══════════════════════════════════════════════════════════════════
def _shutdown_cleanup():
    logger.info("🛑 শাটডাউন — সব প্রসেস বন্ধ করা হচ্ছে…")
    with SCRIPT_LOCK:
        items = list(bot_scripts.items())
        bot_scripts.clear()
    for _, info in items:
        try: _cleanup_process_info(info)
        except Exception: pass

atexit.register(_shutdown_cleanup)

def _sigterm_handler(signum, frame):
    _shutdown_cleanup()
    sys.exit(0)

try:
    signal.signal(signal.SIGTERM, _sigterm_handler)
except Exception:
    pass

# ═══════════════════════════════════════════════════════════════════
#                         MAIN
# ═══════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    logger.info("🤖 Marco File Host Bot চালু হচ্ছে…")
    keep_alive()

    # Telegram conflict এড়াতে webhook সরিয়ে ফেলা
    try:
        bot.remove_webhook()
        logger.info("✅ Webhook cleared")
    except Exception as e:
        logger.warning(f"remove_webhook: {e}")

    retry = 5
    while True:
        try:
            try:
                bot.infinity_polling(
                    timeout=60,
                    long_polling_timeout=30,
                    skip_pending=True,
                    allowed_updates=['message', 'callback_query', 'edited_message'],
                )
            except TypeError:
                # পুরোনো pyTelegramBotAPI-এর জন্য ফলব্যাক
                logger.warning("⚠️ infinity_polling params অসমর্থিত — polling fallback")
                bot.polling(non_stop=True, interval=0, timeout=60,
                            long_polling_timeout=30,
                            allowed_updates=['message', 'callback_query', 'edited_message'])
        except KeyboardInterrupt:
            logger.info("🛑 Ctrl+C — বন্ধ করা হচ্ছে…")
            _shutdown_cleanup()
            break
        except Exception as e:
            logger.error(f"⚠️ Polling crash: {e}")
            time.sleep(retry)
            retry = min(retry * 2, 60)
