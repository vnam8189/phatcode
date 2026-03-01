import telebot
from telebot import types
from flask import Flask
from threading import Thread
import os, json

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG
# ==========================================
API_TOKEN = '8281748233:AAFCVhG3-LBvG_wAli70gRLbfSCOf7fzqTA'
ADMIN_CHINH = [7816353760]  
ADMIN_PHU = [1]    

# --- CẬP NHẬT TẠI ĐÂY ---
MONEY_PER_REF = 10000  # Mời 1 bạn nhận 10k
COST_PER_CODE = 50000  # 5 bạn (50k) mới đủ rút 1 code (Bạn có thể chỉnh lại số này)
# -----------------------

DB_FILE = "database.json"

# ==========================================
# 2. XỬ LÝ DATABASE
# ==========================================
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "users": {}, 
        "codes": [],
        "channels": ['@kiemtienonline48h'],
        "game_link": "https://betvip.ceo/"
    }

def save_db():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

db = load_db()
admin_states = {}
bot = telebot.TeleBot(API_TOKEN)

# ==========================================
# 3. GIAO DIỆN MENU
# ==========================================
def main_menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📊 Thống Kê", "🎁 Rút Giftcode")
    markup.add("🔗 Link Mời", "🎮 Link Game")
    if uid in ADMIN_CHINH or uid in ADMIN_PHU:
        markup.add("🛠 Admin Panel")
    return markup

def admin_panel_menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if uid in ADMIN_CHINH:
        markup.add("📢 Gửi Thông Báo", "📢 Quản Lý Nhóm")
        markup.add("🕹 Đổi Link Game", "➕ Thêm Giftcode")
    markup.add("👥 Danh Sách Mem", "🔙 Quay Lại")
    return markup

# ==========================================
# 4. XỬ LÝ SỰ KIỆN
# ==========================================
@bot.message_handler(commands=['start'])
def start(message):
    uid = str(message.from_user.id)
    if uid not in db["users"]:
        args = message.text.split()
        referrer = args[1] if len(args) > 1 and args[1].isdigit() else None
        db["users"][uid] = {'balance': 0, 'invited_by': referrer, 'refs': 0, 'verified': False}
        save_db()
    
    if not db["users"][uid]['verified']:
        list_groups = "\n".join([f"🔹 {c}" for c in db["channels"]])
        msg = f"👋 **Chào mừng bạn!**\n\nĐể sử dụng Bot, bạn cần tham gia nhóm để xác minh:\n{list_groups}"
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True).add("✅ Xác Minh Ngay")
        bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "✨ Hệ thống đã sẵn sàng!", reply_markup=main_menu(int(uid)))

@bot.message_handler(func=lambda msg: True)
def handle_all(message):
    uid_int = message.from_user.id
    uid = str(uid_int)
    text = message.text
    state = admin_states.get(uid_int)

    # --- XỬ LÝ ADMIN STATES ---
    if state == "WAIT_GAME_LINK" and uid_int in ADMIN_CHINH:
        db["game_link"] = text
        save_db()
        admin_states.pop(uid_int)
        return bot.send_message(uid_int, f"✅ Đã cập nhật Link Game: {text}", reply_markup=admin_panel_menu(uid_int))

    if state == "WAIT_ADD_CODE" and uid_int in ADMIN_CHINH:
        new_codes = [c.strip() for c in text.split('\n') if c.strip()]
        db["codes"].extend(new_codes)
        save_db()
        admin_states.pop(uid_int)
        return bot.send_message(uid_int, f"✅ Đã thêm {len(new_codes)} code vào kho.", reply_markup=admin_panel_menu(uid_int))

    if state == "WAIT_BROADCAST" and uid_int in ADMIN_CHINH:
        admin_states.pop(uid_int)
        for u in db["users"].keys():
            try: bot.send_message(u, f"📢 **THÔNG BÁO:**\n\n{text}", parse_mode="Markdown")
            except: pass
        return bot.send_message(uid_int, "✅ Đã gửi thông báo thành công!", reply_markup=admin_panel_menu(uid_int))

    # --- XỬ LÝ NÚT BẤM ---
    if text == "✅ Xác Minh Ngay":
        for channel in db["channels"]:
            try:
                status = bot.get_chat_member(channel, uid_int).status
                if status in ['left', 'kicked']:
                    return bot.reply_to(message, f"❌ Bạn chưa gia nhập nhóm: {channel}")
            except: pass
        
        if not db["users"][uid]['verified']:
            db["users"][uid]['verified'] = True
            ref_id = db["users"][uid].get('invited_by')
            if ref_id and str(ref_id) in db["users"]:
                db["users"][str(ref_id)]['balance'] += MONEY_PER_REF
                db["users"][str(ref_id)]['refs'] += 1
                try: bot.send_message(ref_id, f"🎉 Bạn nhận được **{MONEY_PER_REF:,}đ** từ việc mời bạn bè!", parse_mode="Markdown")
                except: pass
            save_db()
        bot.send_message(uid_int, "✅ Xác minh thành công!", reply_markup=main_menu(uid_int))

    elif text == "📊 Thống Kê":
        u = db["users"].get(uid, {'balance': 0, 'refs': 0})
        bot.send_message(uid_int, f"👤 **TÀI KHOẢN**\n💰 Số dư: **{u['balance']:,}đ**\n👫 Đã mời: `{u['refs']}` bạn", parse_mode="Markdown")

    elif text == "🎮 Link Game":
        bot.send_message(uid_int, f"🎮 **LINK GAME:** {db.get('game_link')}")

    elif text == "🎁 Rút Giftcode":
        u = db["users"].get(uid)
        if u['balance'] < COST_PER_CODE: 
            con_thieu = COST_PER_CODE - u['balance']
            return bot.send_message(uid_int, f"❌ Số dư không đủ!\nBạn cần thêm **{con_thieu:,}đ** nữa để rút code (Tương ứng mời thêm {int(con_thieu/MONEY_PER_REF)} bạn).", parse_mode="Markdown")
        if not db["codes"]: 
            return bot.send_message(uid_int, "📭 Kho code hiện đang trống!")
        
        code = db["codes"].pop(0)
        u['balance'] -= COST_PER_CODE
        save_db()
        bot.send_message(uid_int, f"🎁 Chúc mừng! Giftcode của bạn là: `{code}`", parse_mode="Markdown")

    elif text == "🔗 Link Mời":
        link = f"https://t.me/{bot.get_me().username}?start={uid}"
        bot.send_message(uid_int, f"🔗 **Link mời của bạn:**\n`{link}`\n\n💰 Mỗi lượt mời thành công nhận: **{MONEY_PER_REF:,}đ**.")

    elif text == "🛠 Admin Panel" and (uid_int in ADMIN_CHINH or uid_int in ADMIN_PHU):
        bot.send_message(uid_int, "Cài đặt hệ thống:", reply_markup=admin_panel_menu(uid_int))

    elif text == "🔙 Quay Lại": 
        bot.send_message(uid_int, "Menu chính", reply_markup=main_menu(uid_int))

# ==========================================
# 5. RUN BOT
# ==========================================
app = Flask('')
@app.route('/')
def home(): return "Bot Live"

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    bot.infinity_polling()
      
