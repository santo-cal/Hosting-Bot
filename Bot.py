# -*- coding: utf-8 -*-
import telebot
import subprocess
import os
import zipfile
import tempfile
import shutil
from telebot import types
import time
from datetime import datetime
import psutil
import sqlite3
import logging
import threading
import re
import sys
import atexit

# --- Flask Keep Alive ---
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "আমি মার্কো ফাইল হোস্ট (I'am Marco File Host)"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    print("ফ্লাস্ক কিপ-অ্যালাইভ (Flask Keep-Alive) সার্ভার চালু হয়েছে।")
# --- End Flask Keep Alive ---

# --- Configuration ---
TOKEN = '9115784893:AAGCwR20a3maDEF9TL5o5O5FmyGUtwbf3lM'

# ⚠️ নিচে আপনার আসল টেলিগ্রাম ইউজার আইডি দিন
OWNER_ID = 7010177964  

YOUR_USERNAME = '@santobhai_dm'
UPDATE_CHANNEL = 'https://t.me/MohabbatBd'

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_BOTS_DIR = os.path.join(BASE_DIR, 'upload_bots')
IROTECH_DIR = os.path.join(BASE_DIR, 'inf')
DATABASE_PATH = os.path.join(IROTECH_DIR, 'bot_data.db')

FREE_USER_LIMIT = 5 # ফ্রি ইউজার কয়টি ফাইল রাখতে পারবে

os.makedirs(UPLOAD_BOTS_DIR, exist_ok=True)
os.makedirs(IROTECH_DIR, exist_ok=True)

bot = telebot.TeleBot(TOKEN)

bot_scripts = {}
user_files = {}
active_users = set()
bot_locked = False

MALWARE_SIGNATURES = [b'MZ', b'\x7fELF', b'\xfe\xed\xfa', b'\xce\xfa\xed\xfe', b'PK', b'Rar!']
ENCRYPTED_FILE_INDICATORS = [b'openssl', b'encrypted', b'cipher', b'AES', b'DES', b'RSA', b'GPG', b'PGP']
SUSPICIOUS_KEYWORDS = [b'ransomware', b'trojan', b'virus', b'malware', b'backdoor', b'exploit', b'payload', b'botnet', b'keylogger', b'rootkit']

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Command Button Layouts ---
COMMAND_BUTTONS_LAYOUT_USER = [
    ["📤 ফাইল আপলোড", "📂 আমার ফাইলসমূহ"],
    ["⚡ বট স্পিড", "📊 পরিসংখ্যান"],
    ["📤 কমান্ড পাঠান", "📢 আপডেট চ্যানেল"],
    ["ℹ️ হেল্প ও নিয়মাবলী", "📞  সহায়তা নিন"]
]

COMMAND_BUTTONS_LAYOUT_OWNER = [
    ["📤 ফাইল আপলোড", "📂 আমার ফাইলসমূহ"],
    ["⚡ বট স্পিড", "📊 পরিসংখ্যান"],
    ["📤 কমান্ড পাঠান", "👑 অ্যাডমিন প্যানেল"], 
    ["ℹ️ হেল্প ও নিয়মাবলী", "📞  সহায়তা নিন"]
]

# --- Database Setup ---
def init_db():
    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS user_files (user_id INTEGER, file_name TEXT, file_type TEXT, PRIMARY KEY (user_id, file_name))''')
        c.execute('''CREATE TABLE IF NOT EXISTS active_users (user_id INTEGER PRIMARY KEY)''')
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"❌ ডাটাবেস তৈরিতে এরর: {e}")

def load_data():
    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('SELECT user_id, file_name, file_type FROM user_files')
        for user_id, file_name, file_type in c.fetchall():
            if user_id not in user_files: user_files[user_id] = []
            user_files[user_id].append((file_name, file_type))
        c.execute('SELECT user_id FROM active_users')
        active_users.update(user_id for (user_id,) in c.fetchall())
        conn.close()
    except Exception as e:
        logger.error(f"❌ ডাটা লোড করতে এরর: {e}")

init_db(); load_data()

# --- Malware Detection ---
def is_suspicious_file(file_content, file_name):
    file_lower = file_name.lower()
    suspicious_extensions = ['.exe', '.dll', '.bat', '.cmd', '.scr', '.com', '.pif', '.msi', '.apk', '.iso', '.img']
    if any(file_lower.endswith(ext) for ext in suspicious_extensions): return True, f"সন্দেহজনক ফাইল এক্সটেনশন: {file_name}"
    for signature in MALWARE_SIGNATURES:
        if file_content.startswith(signature): return True, f"ম্যালওয়্যার সিগনেচার পাওয়া গেছে"
    file_sample = file_content[:min(len(file_content), 4096)]
    for indicator in ENCRYPTED_FILE_INDICATORS:
        if indicator in file_sample: return True, f"এনক্রিপ্টেড ফাইল ইন্ডিকেটর পাওয়া গেছে"
    sample_text = file_sample.decode('utf-8', errors='ignore').lower()
    for keyword in SUSPICIOUS_KEYWORDS:
        if keyword.decode('utf-8').lower() in sample_text: return True, f"সন্দেহজনক কিওয়ার্ড পাওয়া গেছে"
    return False, "ফাইলটি নিরাপদ মনে হচ্ছে"

def scan_file_for_malware(file_content, file_name, user_id):
    if user_id == OWNER_ID: return True, "মালিক সিকিউরিটি চেক বাইপাস করেছেন"
    is_suspicious, reason = is_suspicious_file(file_content, file_name)
    if is_suspicious: return False, f"সিকিউরিটি ভায়োলেশন: {reason}"
    return True, "ফাইলটি নিরাপদ"

# --- Helper Functions ---
def get_user_folder(user_id):
    user_folder = os.path.join(UPLOAD_BOTS_DIR, str(user_id))
    os.makedirs(user_folder, exist_ok=True)
    return user_folder

def get_user_file_limit(user_id):
    return float('inf') if user_id == OWNER_ID else FREE_USER_LIMIT

def get_user_file_count(user_id): 
    return len(user_files.get(user_id, []))

def is_bot_running(script_owner_id, file_name):
    script_key = f"{script_owner_id}_{file_name}"
    script_info = bot_scripts.get(script_key)
    if script_info and script_info.get('process'):
        try:
            proc = psutil.Process(script_info['process'].pid)
            if proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE: return True
        except Exception: pass
    if script_key in bot_scripts: del bot_scripts[script_key]
    return False

def kill_process_tree(process_info):
    try:
        process = process_info.get('process')
        if process and hasattr(process, 'pid'):
            parent = psutil.Process(process.pid)
            children = parent.children(recursive=True)
            for child in children: child.kill()
            parent.kill()
    except Exception: pass

# --- Automatic Package Installation & Script Running ---
TELEGRAM_MODULES = {'telebot': 'pyTelegramBotAPI', 'telegram': 'python-telegram-bot', 'aiogram': 'aiogram', 'pyrogram': 'pyrogram', 'requests': 'requests', 'psutil': 'psutil'}

def attempt_install_pip(module_name, message):
    package_name = TELEGRAM_MODULES.get(module_name.lower(), module_name)
    try:
        bot.reply_to(message, f"🐍 `{module_name}` ইনস্টল করা হচ্ছে...", parse_mode='Markdown')
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', package_name], capture_output=True, text=True)
        return result.returncode == 0
    except: return False

def attempt_install_npm(module_name, user_folder, message):
    try:
        bot.reply_to(message, f"🟠 `{module_name}` ইনস্টল করা হচ্ছে...", parse_mode='Markdown')
        result = subprocess.run(['npm', 'install', module_name], capture_output=True, text=True, cwd=user_folder)
        return result.returncode == 0
    except: return False

def run_script(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt=1):
    if attempt > 2: return
    script_key = f"{script_owner_id}_{file_name}"
    try:
        if not os.path.exists(script_path): remove_user_file_db(script_owner_id, file_name); return

        if attempt == 1:
            check_proc = subprocess.Popen([sys.executable, script_path], cwd=user_folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = check_proc.communicate(timeout=5)
            if check_proc.returncode != 0 and stderr:
                match_py = re.search(r"ModuleNotFoundError: No module named '(.+?)'", stderr)
                if match_py and attempt_install_pip(match_py.group(1).strip().strip("'\""), message_obj_for_reply):
                    bot.reply_to(message_obj_for_reply, f"🔄 আবার রান করার চেষ্টা করা হচ্ছে...")
                    threading.Thread(target=run_script, args=(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt + 1)).start()
                    return
                else: bot.reply_to(message_obj_for_reply, f"❌ এরর: {stderr[:200]}..."); return

        log_file = open(os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log"), 'w', encoding='utf-8')
        process = subprocess.Popen([sys.executable, script_path], cwd=user_folder, stdout=log_file, stderr=log_file, stdin=subprocess.PIPE, encoding='utf-8')
        bot_scripts[script_key] = {'process': process, 'log_file': log_file, 'file_name': file_name, 'script_owner_id': script_owner_id}
        bot.reply_to(message_obj_for_reply, f"✅ পাইথন স্ক্রিপ্ট '{file_name}' চালু হয়েছে!")
    except Exception as e:
        bot.reply_to(message_obj_for_reply, f"❌ এরর: {str(e)}")

def run_js_script(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt=1):
    if attempt > 2: return
    script_key = f"{script_owner_id}_{file_name}"
    try:
        if not os.path.exists(script_path): remove_user_file_db(script_owner_id, file_name); return

        if attempt == 1:
            check_proc = subprocess.Popen(['node', script_path], cwd=user_folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = check_proc.communicate(timeout=5)
            if check_proc.returncode != 0 and stderr:
                match_js = re.search(r"Cannot find module '(.+?)'", stderr)
                if match_js and attempt_install_npm(match_js.group(1).strip().strip("'\""), user_folder, message_obj_for_reply):
                    bot.reply_to(message_obj_for_reply, f"🔄 আবার রান করার চেষ্টা করা হচ্ছে...")
                    threading.Thread(target=run_js_script, args=(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt + 1)).start()
                    return
                else: bot.reply_to(message_obj_for_reply, f"❌ এরর: {stderr[:200]}..."); return

        log_file = open(os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log"), 'w', encoding='utf-8')
        process = subprocess.Popen(['node', script_path], cwd=user_folder, stdout=log_file, stderr=log_file, stdin=subprocess.PIPE, encoding='utf-8')
        bot_scripts[script_key] = {'process': process, 'log_file': log_file, 'file_name': file_name, 'script_owner_id': script_owner_id}
        bot.reply_to(message_obj_for_reply, f"✅ জেএস স্ক্রিপ্ট '{file_name}' চালু হয়েছে!")
    except Exception as e:
        bot.reply_to(message_obj_for_reply, f"❌ এরর: {str(e)}")

# --- Database Operations ---
DB_LOCK = threading.Lock() 

def save_user_file(user_id, file_name, file_type='py'):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO user_files (user_id, file_name, file_type) VALUES (?, ?, ?)', (user_id, file_name, file_type))
        conn.commit(); conn.close()
        if user_id not in user_files: user_files[user_id] = []
        user_files[user_id] = [(fn, ft) for fn, ft in user_files[user_id] if fn != file_name]
        user_files[user_id].append((file_name, file_type))

def remove_user_file_db(user_id, file_name):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('DELETE FROM user_files WHERE user_id = ? AND file_name = ?', (user_id, file_name))
        conn.commit(); conn.close()
        if user_id in user_files:
            user_files[user_id] = [f for f in user_files[user_id] if f[0] != file_name]

def add_active_user(user_id):
    active_users.add(user_id) 
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('INSERT OR IGNORE INTO active_users (user_id) VALUES (?)', (user_id,))
        conn.commit(); conn.close()

# --- Menus ---
def create_main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    layout = COMMAND_BUTTONS_LAYOUT_OWNER if user_id == OWNER_ID else COMMAND_BUTTONS_LAYOUT_USER
    for row in layout: markup.add(*[types.KeyboardButton(t) for t in row])
    return markup

def create_control_buttons(script_owner_id, file_name, is_running=True):
    markup = types.InlineKeyboardMarkup(row_width=2)
    if is_running:
        markup.row(types.InlineKeyboardButton("🔴 থামান (Stop)", callback_data=f'stop_{script_owner_id}_{file_name}'),
                   types.InlineKeyboardButton("🔄 রিস্টার্ট", callback_data=f'restart_{script_owner_id}_{file_name}'))
    else:
        markup.row(types.InlineKeyboardButton("🟢 চালু করুন (Start)", callback_data=f'start_{script_owner_id}_{file_name}'))
    markup.row(types.InlineKeyboardButton("🗑️ ডিলিট", callback_data=f'delete_{script_owner_id}_{file_name}'),
               types.InlineKeyboardButton("📜 লগ (Logs)", callback_data=f'logs_{script_owner_id}_{file_name}'))
    markup.add(types.InlineKeyboardButton("🔙 ফাইল মেনুতে ফেরত", callback_data='check_files'))
    return markup

def create_admin_panel():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📢 সম্প্রচার (Broadcast)", callback_data='admin_broadcast'),
        types.InlineKeyboardButton("🔒 বট লক/আনলক", callback_data='admin_lock'),
        types.InlineKeyboardButton("🟢 সব কোড একসাথে রান", callback_data='admin_run_all'),
        types.InlineKeyboardButton("🔙 মেনু বন্ধ করুন", callback_data='close_menu')
    )
    return markup

def create_send_command_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton('📝 প্রসেসে কমান্ড পাঠান', callback_data='send_to_process'),
               types.InlineKeyboardButton('🔍 সব লগ দেখুন', callback_data='view_all_logs'),
               types.InlineKeyboardButton('🔙 মেনু বন্ধ করুন', callback_data='close_menu'))
    return markup

# --- Core Logic Functions ---
def _logic_send_welcome(message):
    user_id = message.from_user.id
    if bot_locked and user_id != OWNER_ID: bot.send_message(message.chat.id, "⚠️ বট লক করা আছে।"); return

    if user_id not in active_users:
        add_active_user(user_id)
        try: bot.send_message(OWNER_ID, f"🎉 নতুন ইউজার: {message.from_user.first_name} (`{user_id}`)", parse_mode='Markdown')
        except: pass

    user_status = "👑 মালিক (Owner)" if user_id == OWNER_ID else "🆓 ফ্রি ইউজার"
    limit_str = "আনলিমিটেড" if user_id == OWNER_ID else str(FREE_USER_LIMIT)
    
    msg = f"〽️ স্বাগতম, {message.from_user.first_name}!\n\n🆔 আইডি: `{user_id}`\n🔰 স্ট্যাটাস: {user_status}\n📁 ফাইল: {get_user_file_count(user_id)} / {limit_str}\n\n🤖 পাইথন বা জেএস কোড রান করুন সহজেই।"
    bot.send_message(message.chat.id, msg, reply_markup=create_main_menu(user_id), parse_mode='Markdown')

def _logic_upload_file(message):
    user_id = message.from_user.id
    if bot_locked and user_id != OWNER_ID: bot.reply_to(message, "⚠️ বট লক করা আছে।"); return
    if get_user_file_count(user_id) >= get_user_file_limit(user_id): bot.reply_to(message, "⚠️ লিমিট শেষ। আগে ফাইল ডিলিট করুন।"); return
    bot.reply_to(message, "📤 আপনার `.py`, `.js`, অথবা `.zip` প্রজেক্ট ফাইল পাঠান।")

def _logic_check_files(message):
    user_id = message.from_user.id
    user_files_list = user_files.get(user_id, [])
    if not user_files_list: bot.reply_to(message, "📂 আপনার কোনো ফাইল নেই।"); return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for file_name, file_type in sorted(user_files_list):
        status = "🟢" if is_bot_running(user_id, file_name) else "🔴"
        markup.add(types.InlineKeyboardButton(f"{status} {file_name}", callback_data=f'file_{user_id}_{file_name}'))
    bot.reply_to(message, "📂 আপনার ফাইলসমূহ:", reply_markup=markup)

def _logic_bot_speed(message):
    start = time.time()
    msg = bot.reply_to(message, "🏃 চেক করা হচ্ছে...")
    bot.edit_message_text(f"⚡ রেসপন্স: {round((time.time() - start) * 1000, 2)} ms\n🚦 স্ট্যাটাস: {'🔒 লকড' if bot_locked else '🔓 আনলকড'}", message.chat.id, msg.message_id)

def _logic_statistics(message):
    user_id = message.from_user.id
    total_files = sum(len(f) for f in user_files.values())
    running = sum(1 for k, v in bot_scripts.items() if is_bot_running(v['script_owner_id'], v['file_name']))
    my_running = sum(1 for k, v in bot_scripts.items() if v['script_owner_id'] == user_id and is_bot_running(user_id, v['file_name']))
    bot.reply_to(message, f"📊 পরিসংখ্যান:\n👥 ইউজার: {len(active_users)}\n📂 মোট ফাইল: {total_files}\n🟢 মোট রানিং: {running}\n🤖 আপনার রানিং: {my_running}")

@bot.message_handler(commands=['start', 'help'])
def cmd_start(message): _logic_send_welcome(message)

BUTTONS_LOGIC = {
    "📤 ফাইল আপলোড": _logic_upload_file,
    "📂 আমার ফাইলসমূহ": _logic_check_files,
    "⚡ বট স্পিড": _logic_bot_speed,
    "📊 পরিসংখ্যান": _logic_statistics,
    "📤 কমান্ড পাঠান": lambda m: bot.reply_to(m, "অপশন সিলেক্ট করুন:", reply_markup=create_send_command_menu()),
    "📢 আপডেট চ্যানেল": lambda m: bot.reply_to(m, "চ্যানেলে যুক্ত হোন:", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('📢 চ্যানেল', url=UPDATE_CHANNEL))),
    "ℹ️ হেল্প ও নিয়মাবলী": lambda m: bot.reply_to(m, "ফাইল পাঠান এবং ক্লিক করে রান করুন।"),
    "📞  সহায়তা নিন": lambda m: bot.reply_to(m, "সাপোর্ট:", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('📞 যোগাযোগ', url=f'https://t.me/{YOUR_USERNAME[1:]}'))),
    "👑 অ্যাডমিন প্যানেল": lambda m: bot.reply_to(m, "👑 প্যানেল:", reply_markup=create_admin_panel()) if m.from_user.id == OWNER_ID else None
}

@bot.message_handler(func=lambda message: message.text in BUTTONS_LOGIC)
def handle_text(message): 
    func = BUTTONS_LOGIC[message.text]
    if func: func(message)

@bot.message_handler(content_types=['document'])
def handle_doc(message):
    user_id = message.from_user.id
    if bot_locked and user_id != OWNER_ID: bot.reply_to(message, "⚠️ বট লক করা আছে।"); return
    if get_user_file_count(user_id) >= get_user_file_limit(user_id): bot.reply_to(message, "⚠️ লিমিট শেষ।"); return
    
    doc = message.document
    if doc.file_size > 20 * 1024 * 1024: bot.reply_to(message, "⚠️ ফাইল 20MB এর বড়।"); return
    ext = os.path.splitext(doc.file_name)[1].lower()
    if ext not in ['.py', '.js', '.zip']: bot.reply_to(message, "⚠️ শুধু .py, .js, .zip গ্রহণযোগ্য।"); return

    msg = bot.reply_to(message, f"⏳ প্রসেস হচ্ছে...")
    try:
        content = bot.download_file(bot.get_file(doc.file_id).file_path)
        if user_id != OWNER_ID:
            safe, reason = scan_file_for_malware(content, doc.file_name, user_id)
            if not safe: bot.edit_message_text(f"🚨 সিকিউরিটি অ্যালার্ট: {reason}", message.chat.id, msg.message_id); return
        
        folder = get_user_folder(user_id)
        if ext == '.zip':
            # Handle ZIP Simple
            temp_dir = tempfile.mkdtemp()
            zip_path = os.path.join(temp_dir, 'temp.zip')
            with open(zip_path, 'wb') as f: f.write(content)
            with zipfile.ZipFile(zip_path, 'r') as z: z.extractall(temp_dir)
            
            main_script = None; f_type = None
            files = os.listdir(temp_dir)
            for p in ['main.py', 'bot.py', 'app.py', 'index.js', 'main.js']:
                if p in files: 
                    main_script = p; f_type = 'py' if p.endswith('.py') else 'js'; break
            if not main_script: bot.edit_message_text("❌ জিপে main.py বা index.js পাওয়া যায়নি।", message.chat.id, msg.message_id); return
            
            for item in files:
                if item != 'temp.zip': shutil.move(os.path.join(temp_dir, item), os.path.join(folder, item))
            
            save_user_file(user_id, main_script, f_type)
            bot.edit_message_text(f"✅ এক্সট্রাক্ট সম্পন্ন। রান হচ্ছে...", message.chat.id, msg.message_id)
            if f_type == 'py': threading.Thread(target=run_script, args=(os.path.join(folder, main_script), user_id, folder, main_script, message)).start()
            else: threading.Thread(target=run_js_script, args=(os.path.join(folder, main_script), user_id, folder, main_script, message)).start()
        else:
            file_path = os.path.join(folder, doc.file_name)
            with open(file_path, 'wb') as f: f.write(content)
            save_user_file(user_id, doc.file_name, ext[1:])
            bot.edit_message_text(f"✅ সেভ হয়েছে। রান হচ্ছে...", message.chat.id, msg.message_id)
            if ext == '.py': threading.Thread(target=run_script, args=(file_path, user_id, folder, doc.file_name, message)).start()
            else: threading.Thread(target=run_js_script, args=(file_path, user_id, folder, doc.file_name, message)).start()
    except Exception as e: bot.edit_message_text(f"❌ এরর: {e}", message.chat.id, msg.message_id)

# --- Callbacks ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = call.from_user.id; data = call.data
    if bot_locked and uid != OWNER_ID: bot.answer_callback_query(call.id, "⚠️ বট লক।", show_alert=True); return
    try:
        if data == 'check_files': _logic_check_files(call.message); bot.delete_message(call.message.chat.id, call.message.message_id)
        elif data == 'close_menu': bot.delete_message(call.message.chat.id, call.message.message_id)
        
        # File Control
        elif data.startswith('file_'):
            _, owner_str, fname = data.split('_', 2); owner = int(owner_str)
            if uid != owner and uid != OWNER_ID: return
            is_run = is_bot_running(owner, fname)
            bot.edit_message_text(f"⚙️ প্যানেল: `{fname}`\nস্ট্যাটাস: {'🟢 রানিং' if is_run else '🔴 বন্ধ'}", call.message.chat.id, call.message.message_id, reply_markup=create_control_buttons(owner, fname, is_run), parse_mode='Markdown')
        
        elif data.startswith('start_'):
            _, owner_str, fname = data.split('_', 2); owner = int(owner_str)
            if uid != owner and uid != OWNER_ID: return
            f_info = next((f for f in user_files.get(owner, []) if f[0] == fname), None)
            path = os.path.join(get_user_folder(owner), fname)
            if f_info and os.path.exists(path):
                bot.answer_callback_query(call.id, "চালু হচ্ছে...")
                if f_info[1] == 'py': threading.Thread(target=run_script, args=(path, owner, get_user_folder(owner), fname, call.message)).start()
                else: threading.Thread(target=run_js_script, args=(path, owner, get_user_folder(owner), fname, call.message)).start()
                time.sleep(1.5)
                bot.edit_message_text(f"⚙️ প্যানেল: `{fname}` | 🟢 রানিং", call.message.chat.id, call.message.message_id, reply_markup=create_control_buttons(owner, fname, True))
        
        elif data.startswith('stop_'):
            _, owner_str, fname = data.split('_', 2); owner = int(owner_str)
            if uid != owner and uid != OWNER_ID: return
            if f"{owner}_{fname}" in bot_scripts: kill_process_tree(bot_scripts[f"{owner}_{fname}"]); del bot_scripts[f"{owner}_{fname}"]
            bot.edit_message_text(f"⚙️ প্যানেল: `{fname}` | 🔴 বন্ধ", call.message.chat.id, call.message.message_id, reply_markup=create_control_buttons(owner, fname, False))
            
        elif data.startswith('delete_'):
            _, owner_str, fname = data.split('_', 2); owner = int(owner_str)
            if uid != owner and uid != OWNER_ID: return
            if f"{owner}_{fname}" in bot_scripts: kill_process_tree(bot_scripts[f"{owner}_{fname}"]); del bot_scripts[f"{owner}_{fname}"]
            folder = get_user_folder(owner)
            if os.path.exists(os.path.join(folder, fname)): os.remove(os.path.join(folder, fname))
            remove_user_file_db(owner, fname)
            bot.edit_message_text(f"🗑️ `{fname}` ডিলিট করা হয়েছে!", call.message.chat.id, call.message.message_id)
            
        elif data.startswith('logs_'):
            _, owner_str, fname = data.split('_', 2); owner = int(owner_str)
            log_path = os.path.join(get_user_folder(owner), f"{os.path.splitext(fname)[0]}.log")
            if os.path.exists(log_path):
                with open(log_path, 'r') as f: content = f.read()[-4000:]
                bot.send_message(call.message.chat.id, f"📜 লগ:\n```\n{content or 'খালি'}\n```", parse_mode='Markdown')

        # Admin Panel Logic
        elif data == 'admin_broadcast' and uid == OWNER_ID:
            msg = bot.send_message(call.message.chat.id, "📢 মেসেজটি লিখে পাঠান:")
            bot.register_next_step_handler(msg, lambda m: bot.send_message(m.chat.id, f"✅ {len(active_users)} জনকে পাঠানো হলো!") and [bot.send_message(u, m.text) for u in active_users])
        elif data == 'admin_lock' and uid == OWNER_ID:
            global bot_locked; bot_locked = not bot_locked
            bot.answer_callback_query(call.id, f"বট {'লক' if bot_locked else 'আনলক'} হয়েছে!", show_alert=True)
        elif data == 'admin_run_all' and uid == OWNER_ID:
            bot.answer_callback_query(call.id, "সবার স্ক্রিপ্ট রান করা হচ্ছে...", show_alert=True)
            for u, files in user_files.items():
                for fn, ft in files:
                    if not is_bot_running(u, fn):
                        p = os.path.join(get_user_folder(u), fn)
                        if os.path.exists(p):
                            threading.Thread(target=run_script if ft=='py' else run_js_script, args=(p, u, get_user_folder(u), fn, call.message)).start()
        
    except Exception as e: bot.answer_callback_query(call.id, "এরর!")

def cleanup():
    for key in list(bot_scripts.keys()): kill_process_tree(bot_scripts[key])
atexit.register(cleanup)

if __name__ == '__main__':
    logger.info("🤖 সিম্পল বট চালু হচ্ছে...")
    keep_alive()
    bot.infinity_polling()
