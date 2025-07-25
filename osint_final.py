
import telebot
import requests
import datetime
import random
import string
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8487753293:AAFpHml9mBYrZC9C_Tb6UqOKuzHU1Ko6zWo"
API_TOKEN = "7020772753:AAOT5EKy"
API_URL = "https://leakosintapi.com/"
ADMIN_USER_ID = 1879424812

bot = telebot.TeleBot(BOT_TOKEN)

access_codes = {}
user_access = set()
bot_active = True
banned_users = set()
cached_reports = {}
last_search_time = {}
SEARCH_COOLDOWN = 15

# ----------- Smallcaps Formatter -----------
def to_smallcaps(text):
    sc_map = {
        'a':'ᴀ','b':'ʙ','c':'ᴄ','d':'ᴅ','e':'ᴇ','f':'ꜰ','g':'ɢ','h':'ʜ','i':'ɪ','j':'ᴊ','k':'ᴋ','l':'ʟ','m':'ᴍ',
        'n':'ɴ','o':'ᴏ','p':'ᴘ','q':'ǫ','r':'ʀ','s':'ꜱ','t':'ᴛ','u':'ᴜ','v':'ᴠ','w':'ᴡ','x':'x','y':'ʏ','z':'ᴢ'
    }
    return ' '.join(["**" + ''.join(sc_map.get(c.lower(), c) for c in word) + "**" for word in text.split()])

# ----------- Utility Functions -----------
def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=random.randint(12, 15)))

def check_access(user_id):
    return user_id in user_access or user_id == ADMIN_USER_ID

# ----------- Start Command -----------
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if user_id in banned_users:
        return
    if not bot_active and user_id != ADMIN_USER_ID:
        bot.send_message(message.chat.id, to_smallcaps("Bot is currently turned off."), parse_mode="Markdown")
        return
    if not check_access(user_id):
        bot.send_message(message.chat.id, to_smallcaps("Please enter your access code."), parse_mode="Markdown")
        return
    bot.send_message(message.chat.id, to_smallcaps("Welcome! Use") + " /search " + to_smallcaps("to begin."), parse_mode="Markdown")

# ----------- Access Code Plain Message -----------
@bot.message_handler(func=lambda m: not m.text.startswith('/') and not check_access(m.from_user.id))
def handle_access_code(message):
    code = message.text.strip().upper()
    if code in access_codes and datetime.datetime.now() < access_codes[code]:
        user_access.add(message.from_user.id)
        bot.send_message(message.chat.id, to_smallcaps("Access granted. You can now use") + " /search", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, to_smallcaps("Invalid or expired access code."), parse_mode="Markdown")

# ----------- Search Command -----------
@bot.message_handler(commands=['search'])
def search(message):
    user_id = message.from_user.id
    if user_id in banned_users:
        return
    if not check_access(user_id):
        bot.send_message(message.chat.id, to_smallcaps("Please enter your access code."), parse_mode="Markdown")
        return
    now = datetime.datetime.now()
    if user_id in last_search_time and (now - last_search_time[user_id]).total_seconds() < SEARCH_COOLDOWN:
        wait_time = int(SEARCH_COOLDOWN - (now - last_search_time[user_id]).total_seconds())
        bot.send_message(message.chat.id, to_smallcaps(f"Please wait {wait_time} seconds before next search."), parse_mode="Markdown")
        return

    msg = bot.send_message(message.chat.id, to_smallcaps("Send the number/email to search:"), parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_query)

# ----------- Query Handler -----------
# ----------- Query Handler -----------
def process_query(message):
    user_id = message.from_user.id
    query = message.text.strip()
    clean = query.replace(" ", "").replace("-", "")
    if clean in ["8303617383", "+918303617383", "9415005184", "+919415005184"]:
        bot.send_message(message.chat.id, to_smallcaps("Loda lelo"), parse_mode="Markdown")
        return

    last_search_time[user_id] = datetime.datetime.now()
    bot.send_message(message.chat.id, to_smallcaps("Searching..."), parse_mode="Markdown")

    data = {"token": API_TOKEN, "request": query, "limit": 100, "lang": "en"}
    try:
        res = requests.post(API_URL, json=data).json()
        if "List" not in res:
            bot.send_message(message.chat.id, to_smallcaps("No data found."), parse_mode="Markdown")
            return
        
        pages = []
        for db, content in res["List"].items():
            section = []
            # Add database name as header
            section.append(f"<b>🔍 {db}</b>\n")
            
            # Skip the generic InfoLeak text about HiTeckGroop
            if "InfoLeak" in content and not content["InfoLeak"].startswith("At the beginning of 2025"):
                section.append(f"{content['InfoLeak']}\n\n")
            
            # Process Data section
            if "Data" in content:
                for item in content["Data"]:
                    for k, v in item.items():
                        # Format each field with proper spacing
                        if k.lower() in ['phone', 'phone2', 'phone3']:
                            section.append(f"<b>📱 {k}:</b> {v}\n")
                        elif k.lower() in ['fullname', 'fathername']:
                            section.append(f"<b>👤 {k}:</b> {v}\n")
                        elif k.lower() == 'docnumber':
                            section.append(f"<b>🆔 {k}:</b> {v}\n")
                        elif k.lower() == 'region':
                            section.append(f"<b>📍 {k}:</b> {v}\n")
                        elif k.lower().startswith('address'):
                            section.append(f"<b>🏠 {k}:</b> {v}\n")
                        else:
                            section.append(f"<b>{k}:</b> {v}\n")
                    section.append("\n")  # Add extra line between records
            
            # Combine all sections
            text_block = "".join(section).strip()
            
            # Handle large blocks
            if len(text_block) > 3500:
                text_block = text_block[:3500] + "...\n\nSome data is omitted."
            
            pages.append(text_block)
        
        cached_reports[str(message.message_id)] = pages
        markup = make_keyboard(message.message_id, 0, len(pages))
        bot.send_message(message.chat.id, pages[0], parse_mode="HTML", reply_markup=markup)
    except Exception as e:
        print(f"Error: {e}")
        bot.send_message(message.chat.id, to_smallcaps("API error occurred."), parse_mode="Markdown")

# ----------- Pagination -----------
def make_keyboard(query_id, page, total):
    markup = InlineKeyboardMarkup()
    if total > 1:
        markup.add(
            InlineKeyboardButton("⬅️", callback_data=f"page {query_id} {page-1}"),
            InlineKeyboardButton(f"{page+1}/{total}", callback_data="noop"),
            InlineKeyboardButton("➡️", callback_data=f"page {query_id} {page+1}")
        )
    return markup

@bot.callback_query_handler(func=lambda call: call.data.startswith("page "))
def change_page(call):
    _, query_id, page = call.data.split()
    page = int(page)
    report = cached_reports.get(query_id)
    if not report:
        return
    page %= len(report)
    markup = make_keyboard(query_id, page, len(report))
    bot.edit_message_text(report[page], call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)

# ----------- Admin Commands -----------
@bot.message_handler(commands=['gen_code'])
def gen_code(message):
    if message.from_user.id != ADMIN_USER_ID:
        return
    try:
        mins = int(message.text.split()[1])
        code = generate_code()
        access_codes[code] = datetime.datetime.now() + datetime.timedelta(minutes=mins)
        bot.send_message(
            message.chat.id,
            f"<b>Access Code:</b> <code>{code}</code>\n<b>Valid for:</b> <code>{mins}</code> minutes",
            parse_mode="HTML"
        )
    except:
        bot.send_message(
            message.chat.id,
            "<b>Usage:</b> <code>/gen_code 15</code>",
            parse_mode="HTML"
        )

@bot.message_handler(commands=['ban'])
def ban(message):
    if message.from_user.id == ADMIN_USER_ID:
        try:
            uid = int(message.text.split()[1])
            banned_users.add(uid)
            bot.send_message(message.chat.id, to_smallcaps("User banned."), parse_mode="Markdown")
        except:
            bot.send_message(message.chat.id, to_smallcaps("Usage: /ban user_id"), parse_mode="Markdown")

@bot.message_handler(commands=['unban'])
def unban(message):
    if message.from_user.id == ADMIN_USER_ID:
        try:
            uid = int(message.text.split()[1])
            banned_users.discard(uid)
            bot.send_message(message.chat.id, to_smallcaps("User unbanned."), parse_mode="Markdown")
        except:
            bot.send_message(message.chat.id, to_smallcaps("Usage: /unban user_id"), parse_mode="Markdown")

@bot.message_handler(commands=['toggle'])
def toggle(message):
    global bot_active
    if message.from_user.id == ADMIN_USER_ID:
        bot_active = not bot_active
        status = "ON" if bot_active else "OFF"
        bot.send_message(message.chat.id, to_smallcaps(f"Bot is now {status}"), parse_mode="Markdown")

print("🤖 Bot is running...")
bot.polling()
