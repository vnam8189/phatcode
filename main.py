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
ADMIN_PHU = [6472034224]    

MONEY_PER_REF = 10000  
COST_PER_CODE = 50000  
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
        "game_link": "https://xocdia88.ec"
    }

def save_db():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

db = load_db()
admin_states = {}
bot = telebot.TeleBot(API_TOKEN)

# --- HÀM KIỂM TRA JOIN NHÓM (LUÔN LUÔN CHECK) ---
def is_sub(uid_int):
    for channel in db["channels"]:
        try:
            status = bot.get_chat_member(channel, uid_int).status
            if status in ['left', 'kicked']:
                return False
        except:
            continue # Nếu bot chưa vào nhóm đó thì bỏ qua check nhóm đó
    return True

# ==========================================
# 3. GIAO DIỆN MENU
# ==========================================
def main_menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📊 Thống Kê", "🎁 Rút Giftcode")
    markup.add("🔗 Link Mời (10K/Ref)", "🎮 Link Game")
    if uid in ADMIN_CHINH or uid in ADMIN_PHU:
        markup.add("🛠 Admin Panel")
    return markup

def admin_panel_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📢 Gửi Thông Báo", "📢 Quản Lý Nhóm")
    markup.add("🕹 Đổi Link Game", "➕ Thêm Giftcode")
    markup.add("👥 Danh Sách Mem", "🔙 Quay Lại")
    return markup

def cancel_markup():
    return types.ReplyKeyboardMarkup(resize_keyboard=True).add("❌ Hủy Lệnh Admin")

# ==========================================
# 4. XỬ LÝ SỰ KIỆN
# ==========================================
@bot.message_handler(commands=['start'])
def start(message):
    uid = str(message.from_user.id)
    # Đăng ký user mới
    if uid not in db["users"]:
        args = message.text.split()
        referrer = args[1] if len(args) > 1 and args[1].isdigit() else None
        db["users"][uid] = {'balance': 0, 'invited_by': referrer, 'refs': 0, 'verified': False}
        save_db()
    
    # Kiểm tra join
    if not is_sub(message.from_user.id):
        list_groups = "\n".join([f"🔹 {c}" for c in db["channels"]])
        msg = f"⚠️ **BẠN CHƯA THAM GIA ĐỦ NHÓM!**\n\nĐể sử dụng Bot, bạn bắt buộc phải tham gia:\n{list_groups}\n\n*Sau khi tham gia, hãy bấm nút xác minh bên dưới.*"
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True).add("✅ Xác Minh Ngay")
        bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "✨ Chào mừng bạn quay trở lại!", reply_markup=main_menu(message.from_user.id))

@bot.message_handler(func=lambda msg: True)
def handle_all(message):
    uid_int = message.from_user.id
    uid = str(uid_int)
    text = message.text
    state = admin_states.get(uid_int)

    # 1. KIỂM TRA HỦY LỆNH ADMIN
    if text == "❌ Hủy Lệnh Admin":
        admin_states.pop(uid_int, None)
        return bot.send_message(uid_int, "Trạng thái đã được reset.", reply_markup=admin_panel_menu())

    # 2. XỬ LÝ CÁC TRẠNG THÁI ADMIN (Chỉ dành cho ADMIN)
    if uid_int in ADMIN_CHINH or uid_int in ADMIN_PHU:
        if state == "WAIT_GAME_LINK":
            db["game_link"] = text
            save_db(); admin_states.pop(uid_int)
            return bot.send_message(uid_int, "✅ Link Game đã cập nhật!", reply_markup=admin_panel_menu())
            
        if state == "WAIT_ADD_CODE":
            new_codes = [c.strip() for c in text.split('\n') if c.strip()]
            db["codes"].extend(new_codes)
            save_db(); admin_states.pop(uid_int)
            return bot.send_message(uid_int, f"✅ Đã thêm {len(new_codes)} code!", reply_markup=admin_panel_menu())

        if state == "WAIT_BROADCAST":
            admin_states.pop(uid_int)
            bot.send_message(uid_int, "⏳ Đang gửi...")
            for u in db["users"].keys():
                try: bot.send_message(u, f"📢 **THÔNG BÁO:**\n\n{text}", parse_mode="Markdown")
                except: pass
            return bot.send_message(uid_int, "✅ Đã gửi xong!", reply_markup=admin_panel_menu())

        if state == "WAIT_ADD_GROUP":
            if not text.startswith("@"): 
                return bot.send_message(uid_int, "❌ Username phải bắt đầu bằng @", reply_markup=cancel_markup())
            db["channels"].append(text)
            save_db(); admin_states.pop(uid_int)
            return bot.send_message(uid_int, f"✅ Đã thêm nhóm {text}", reply_markup=admin_panel_menu())

    # 3. KIỂM TRA JOIN NHÓM BẮT BUỘC (Đối với mọi người dùng)
    if not is_sub(uid_int):
        # Nếu đang bấm nút xác minh thì không hiện cảnh báo này để tránh lặp
        if text != "✅ Xác Minh Ngay":
            return start(message)

    # 4. XỬ LÝ NÚT BẤM NGƯỜI DÙNG & MENU ADMIN
    if text == "✅ Xác Minh Ngay":
        if is_sub(uid_int):
            if not db["users"][uid]['verified']:
                db["users"][uid]['verified'] = True
                ref_id = db["users"][uid].get('invited_by')
                if ref_id and str(ref_id) in db["users"]:
                    db["users"][str(ref_id)]['balance'] += MONEY_PER_REF
                    db["users"][str(ref_id)]['refs'] += 1
                    try: bot.send_message(ref_id, f"🎁 **+10.000đ**! Bạn bè đã xác minh thành công.")
                    except: pass
                save_db()
            bot.send_message(uid_int, "✅ Xác minh thành công!", reply_markup=main_menu(uid_int))
        else:
            bot.answer_callback_query(message.id, "❌ Bạn vẫn chưa join đủ nhóm!", show_alert=True)
            bot.send_message(uid_int, "Vui lòng kiểm tra lại các nhóm ở tin nhắn phía trên.")

    elif text == "📊 Thống Kê":
        u = db["users"].get(uid)
        bot.send_message(uid_int, f"👤 **TÀI KHOẢN**\n💰 Số dư: **{u['balance']:,}đ**\n👫 Đã mời: `{u['refs']}`\n🎁 Rút code tại: 50.000đ", parse_mode="Markdown")

    elif text == "🎮 Link Game":
        bot.send_message(uid_int, f"🎮 **LINK GAME:** {db.get('game_link')}")

    elif text == "🎁 Rút Giftcode":
        u = db["users"].get(uid)
        if u['balance'] < COST_PER_CODE:
            return bot.send_message(uid_int, f"❌ Không đủ 50.000đ (Cần mời thêm {int((COST_PER_CODE-u['balance'])/10000)} bạn)")
        if not db["codes"]: return bot.send_message(uid_int, "📭 Hết code!")
        code = db["codes"].pop(0)
        u['balance'] -= COST_PER_CODE
        save_db()
        bot.send_message(uid_int, f"🎁 Code của bạn: `{code}`", parse_mode="Markdown")

    elif text == "🔗 Link Mời (10K/Ref)":
        link = f"https://t.me/{bot.get_me().username}?start={uid}"
        bot.send_message(uid_int, f"💰 **1 REF = 10.000đ**\n\nLink của bạn:\n`{link}`", parse_mode="Markdown")

    # --- ĐIỀU KHIỂN ADMIN ---
    elif text == "🛠 Admin Panel" and (uid_int in ADMIN_CHINH or uid_int in ADMIN_PHU):
        bot.send_message(uid_int, "🛠 Hệ thống quản trị:", reply_markup=admin_panel_menu())

    elif text == "🕹 Đổi Link Game" and uid_int in ADMIN_CHINH:
        admin_states[uid_int] = "WAIT_GAME_LINK"
        bot.send_message(uid_int, "Nhập Link Game mới:", reply_markup=cancel_markup())

    elif text == "➕ Thêm Giftcode" and uid_int in ADMIN_CHINH:
        admin_states[uid_int] = "WAIT_ADD_CODE"
        bot.send_message(uid_int, "Nhập danh sách code (mỗi dòng 1 cái):", reply_markup=cancel_markup())

    elif text == "📢 Gửi Thông Báo" and uid_int in ADMIN_CHINH:
        admin_states[uid_int] = "WAIT_BROADCAST"
        bot.send_message(uid_int, "Nhập nội dung thông báo:", reply_markup=cancel_markup())

    elif text == "📢 Quản Lý Nhóm" and uid_int in ADMIN_CHINH:
        msg = "📝 **Các nhóm hiện tại:**\n" + "\n".join(db["channels"])
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("➕ Thêm Nhóm Check", "🧹 Xóa Hết Nhóm")
        markup.add("🛠 Admin Panel")
        bot.send_message(uid_int, msg, reply_markup=markup, parse_mode="Markdown")

    elif text == "➕ Thêm Nhóm Check" and uid_int in ADMIN_CHINH:
        admin_states[uid_int] = "WAIT_ADD_GROUP"
        bot.send_message(uid_int, "Nhập Username nhóm (VD: @tennhom):", reply_markup=cancel_markup())

    elif text == "🧹 Xóa Hết Nhóm" and uid_int in ADMIN_CHINH:
        db["channels"] = []
        save_db()
        bot.send_message(uid_int, "✅ Đã xóa sạch danh sách nhóm check!", reply_markup=admin_panel_menu())

    elif text == "👥 Danh Sách Mem":
        bot.send_message(uid_int, f"👥 Tổng: `{len(db['users'])}` mem.")

    elif text == "🔙 Quay Lại":
        bot.send_message(uid_int, "Menu chính", reply_markup=main_menu(uid_int))

# ==========================================
# 5. CHẠY SERVER
# ==========================================
app = Flask('')
@app.route('/')
def home(): return "Bot Live"

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    bot.infinity_polling()
    
