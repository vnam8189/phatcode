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

MONEY_PER_REF = 10000  # 10k mỗi ref
COST_PER_CODE = 50000  # 50k mới rút được code (5 ref)
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

# ==========================================
# 3. GIAO DIỆN MENU
# ==========================================
def main_menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📊 Thống Kê", "🎁 Rút Giftcode")
    markup.add("🔗 Link Mời (10K/Ref)", "🎮 Link Game") # Ghi rõ 10k ở đây
    if uid in ADMIN_CHINH or uid in ADMIN_PHU:
        markup.add("🛠 Admin Panel")
    return markup

def admin_panel_menu(uid_int):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if uid_int in ADMIN_CHINH:
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
        msg = (f"👋 **CHÀO MỪNG BẠN ĐẾN VỚI BOT NHẬN CODE!**\n\n"
               f"💰 **Chính sách thưởng:**\n"
               f"• Nhận ngay **{MONEY_PER_REF:,}đ** cho mỗi người bạn mời thành công.\n"
               f"• Tích lũy đủ **{COST_PER_CODE:,}đ** (tương đương 5 bạn) để đổi 1 Giftcode.\n\n"
               f"👇 **Để bắt đầu, hãy tham gia các kênh sau:**\n{list_groups}")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True).add("✅ Xác Minh Ngay")
        bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "✨ Hệ thống đã sẵn sàng! Chúc bạn săn được nhiều code.", reply_markup=main_menu(int(uid)))

@bot.message_handler(func=lambda msg: True)
def handle_all(message):
    uid_int = message.from_user.id
    uid = str(uid_int)
    text = message.text
    state = admin_states.get(uid_int)

    # --- XỬ LÝ ADMIN STATES (Lệnh điều khiển của Boss) ---
    if state == "WAIT_GAME_LINK" and uid_int in ADMIN_CHINH:
        db["game_link"] = text
        save_db()
        admin_states.pop(uid_int)
        return bot.send_message(uid_int, f"✅ Đã cập nhật Link Game mới thành công!", reply_markup=admin_panel_menu(uid_int))

    if state == "WAIT_ADD_CODE" and uid_int in ADMIN_CHINH:
        new_codes = [c.strip() for c in text.split('\n') if c.strip()]
        db["codes"].extend(new_codes)
        save_db()
        admin_states.pop(uid_int)
        return bot.send_message(uid_int, f"✅ Đã thêm {len(new_codes)} code vào kho.\n📦 Tổng code hiện có: {len(db['codes'])}", reply_markup=admin_panel_menu(uid_int))

    if state == "WAIT_BROADCAST" and uid_int in ADMIN_CHINH:
        admin_states.pop(uid_int)
        bot.send_message(uid_int, "⏳ Đang gửi thông báo cho toàn bộ người dùng...")
        for u in db["users"].keys():
            try: bot.send_message(u, f"📢 **THÔNG BÁO TỪ ADMIN:**\n\n{text}", parse_mode="Markdown")
            except: pass
        return bot.send_message(uid_int, "✅ Đã gửi thông báo hoàn tất!", reply_markup=admin_panel_menu(uid_int))

    # --- XỬ LÝ NÚT BẤM CHO NGƯỜI DÙNG ---
    if text == "✅ Xác Minh Ngay":
        for channel in db["channels"]:
            try:
                status = bot.get_chat_member(channel, uid_int).status
                if status in ['left', 'kicked']:
                    return bot.reply_to(message, f"❌ Bạn chưa tham gia kênh {channel}. Hãy tham gia rồi bấm lại nút này nhé!")
            except: pass
        
        if not db["users"][uid]['verified']:
            db["users"][uid]['verified'] = True
            ref_id = db["users"][uid].get('invited_by')
            if ref_id and str(ref_id) in db["users"]:
                db["users"][str(ref_id)]['balance'] += MONEY_PER_REF
                db["users"][str(ref_id)]['refs'] += 1
                try: bot.send_message(ref_id, f"🎉 **Chúc mừng!** Bạn nhận được +{MONEY_PER_REF:,}đ vì đã mời 1 người bạn mới.", parse_mode="Markdown")
                except: pass
            save_db()
        bot.send_message(uid_int, "✅ Xác minh thành công! Bạn có thể bắt đầu kiếm tiền.", reply_markup=main_menu(uid_int))

    elif text == "📊 Thống Kê":
        u = db["users"].get(uid, {'balance': 0, 'refs': 0})
        bot.send_message(uid_int, f"👤 **TÀI KHOẢN CỦA BẠN**\n\n💰 Số dư: **{u['balance']:,} VNĐ**\n👫 Đã mời: `{u['refs']}` bạn bè\n🎁 Tiến độ rút code: `{u['balance']}/{COST_PER_CODE}`", parse_mode="Markdown")

    elif text == "🎮 Link Game":
        bot.send_message(uid_int, f"🎮 **LINK GAME CHÍNH THỨC:**\n👉 {db.get('game_link')}\n\n*Đăng ký và nạp ngay để nhận ưu đãi!*", parse_mode="Markdown")

    elif text == "🎁 Rút Giftcode":
        u = db["users"].get(uid)
        if u['balance'] < COST_PER_CODE: 
            con_thieu = COST_PER_CODE - u['balance']
            ban_can_them = int(con_thieu / MONEY_PER_REF)
            return bot.send_message(uid_int, f"⚠️ **KHÔNG ĐỦ SỐ DƯ**\n\nBạn cần thêm **{con_thieu:,}đ** nữa.\n🔥 Hãy mời thêm **{ban_can_them}** bạn bè để đủ điều kiện rút code!", parse_mode="Markdown")
        
        if not db["codes"]: 
            return bot.send_message(uid_int, "📭 **KHO CODE TẠM HẾT**\nAdmin đang cập nhật thêm code mới, bạn vui lòng quay lại sau ít phút nhé!")
        
        code = db["codes"].pop(0)
        u['balance'] -= COST_PER_CODE
        save_db()
        bot.send_message(uid_int, f"🎉 **RÚT CODE THÀNH CÔNG!**\n\n🎁 Giftcode của bạn: `{code}`\n\n💡 Hãy nạp ngay vào game để sử dụng.", parse_mode="Markdown")

    elif text == "🔗 Link Mời (10K/Ref)":
        link = f"https://t.me/{bot.get_me().username}?start={uid}"
        bot.send_message(uid_int, f"🚀 **KIẾM TIỀN THẬT DỄ DÀNG**\n\n1️⃣ Gửi link này cho bạn bè.\n2️⃣ Khi bạn bè bấm /start và tham gia nhóm.\n3️⃣ Bạn nhận ngay **{MONEY_PER_REF:,}đ** vào tài khoản.\n\n🔗 Link của bạn:\n`{link}`", parse_mode="Markdown")

    # --- ADMIN CONTROL ---
    elif text == "🛠 Admin Panel" and (uid_int in ADMIN_CHINH or uid_int in ADMIN_PHU):
        bot.send_message(uid_int, f"🛠 **BẢNG ĐIỀU KHIỂN QUẢN TRỊ**\n\n📦 Code trong kho: {len(db['codes'])}\n👥 Tổng thành viên: {len(db['users'])}", reply_markup=admin_panel_menu(uid_int))

    elif text == "🕹 Đổi Link Game" and uid_int in ADMIN_CHINH:
        admin_states[uid_int] = "WAIT_GAME_LINK"
        bot.send_message(uid_int, "✏️ Nhập Link Game mới bạn muốn hiển thị cho người dùng:", reply_markup=types.ReplyKeyboardRemove())

    elif text == "➕ Thêm Giftcode" and uid_int in ADMIN_CHINH:
        admin_states[uid_int] = "WAIT_ADD_CODE"
        bot.send_message(uid_int, "✏️ Nhập danh sách Code mới (Mỗi dòng 1 code):", reply_markup=types.ReplyKeyboardRemove())

    elif text == "📢 Gửi Thông Báo" and uid_int in ADMIN_CHINH:
        admin_states[uid_int] = "WAIT_BROADCAST"
        bot.send_message(uid_int, "✏️ Nhập nội dung cần gửi đến TẤT CẢ thành viên:", reply_markup=types.ReplyKeyboardRemove())

    elif text == "👥 Danh Sách Mem":
        bot.send_message(uid_int, f"👥 Tổng số thành viên đã sử dụng bot: `{len(db['users'])}` người.")

    elif text == "🔙 Quay Lại": 
        bot.send_message(uid_int, "Đã quay lại Menu chính.", reply_markup=main_menu(uid_int))

# ==========================================
# 5. CHẠY SERVER (TƯƠNG THÍCH RENDER)
# ==========================================
app = Flask('')
@app.route('/')
def home(): return "Bot Live Status: OK"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    print("🚀 BOT ĐÃ SẴN SÀNG CHẠY TRÊN RENDER!")
    bot.infinity_polling()
    
