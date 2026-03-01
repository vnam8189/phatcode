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
    if not db["channels"]: return True
    for channel in db["channels"]:
        try:
            status = bot.get_chat_member(channel, uid_int).status
            if status in ['left', 'kicked']: return False
        except: continue
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
    markup.add("💰 Cộng/Trừ Tiền", "👥 Danh Sách Mem")
    markup.add("🔙 Quay Lại")
    return markup

def cancel_markup():
    return types.ReplyKeyboardMarkup(resize_keyboard=True).add("❌ Hủy Lệnh Admin")

# ==========================================
# 4. XỬ LÝ SỰ KIỆN
# ==========================================
@bot.message_handler(commands=['start'])
def start(message):
    uid = str(message.from_user.id)
    args = message.text.split()
    
    # Đăng ký user mới và xử lý link ref
    if uid not in db["users"]:
        referrer = args[1] if len(args) > 1 and args[1].isdigit() else None
        # Không tự cộng tiền khi /start, chỉ ghi nhận người mời
        db["users"][uid] = {'balance': 0, 'invited_by': referrer, 'refs': 0, 'verified': False}
        save_db()
    
    # Kiểm tra join
    if not is_sub(message.from_user.id):
        list_groups = "\n".join([f"🔹 {c}" for c in db["channels"]])
        msg = f"⚠️ **BẠN BẮT BUỘC PHẢI THAM GIA ĐỦ NHÓM!**\n\n{list_groups}\n\n*Sau khi tham gia, hãy bấm nút xác minh bên dưới.*"
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True).add("✅ Xác Minh Ngay")
        bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "✨ Hệ thống đã sẵn sàng!", reply_markup=main_menu(message.from_user.id))

@bot.message_handler(func=lambda msg: True)
def handle_all(message):
    uid_int = message.from_user.id
    uid = str(uid_int)
    text = message.text
    state = admin_states.get(uid_int)

    # 1. HỦY LỆNH ADMIN
    if text == "❌ Hủy Lệnh Admin":
        admin_states.pop(uid_int, None)
        return bot.send_message(uid_int, "Trạng thái đã được reset.", reply_markup=admin_panel_menu())

    # 2. XỬ LÝ TRẠNG THÁI ADMIN NGHIÊM NGẶT
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
            db["channels"].append(text)
            save_db(); admin_states.pop(uid_int)
            return bot.send_message(uid_int, f"✅ Đã thêm nhóm {text}", reply_markup=admin_panel_menu())

        # CHỨC NĂNG CỘNG/TRỪ TIỀN ADMIN
        if state == "WAIT_BALANCE_CMD":
            try:
                # Định dạng: ID | số_tiền
                target_id, amount = text.split('|')
                target_id = target_id.strip()
                amount = int(amount.strip())
                
                if target_id in db["users"]:
                    db["users"][target_id]['balance'] += amount
                    save_db()
                    bot.send_message(uid_int, f"✅ Đã cộng/trừ {amount}đ cho user {target_id}.\nSố dư mới: {db['users'][target_id]['balance']}đ")
                    try: bot.send_message(target_id, f"💰 **TÀI KHOẢN CẬP NHẬT:** {amount}đ (Từ Admin)")
                    except: pass
                else:
                    bot.send_message(uid_int, "❌ Không tìm thấy ID user này.")
            except:
                bot.send_message(uid_int, "❌ Định dạng sai. Vui lòng nhập: `ID_USER | Số_Tiền` (Số tiền âm để trừ)", parse_mode="Markdown", reply_markup=cancel_markup())
            
            if text != "❌ Hủy Lệnh Admin": admin_states.pop(uid_int, None)
            return

    # 3. KIỂM TRA JOIN NHÓM (CHẶN NGƯỜI DÙNG)
    if not is_sub(uid_int):
        if text != "✅ Xác Minh Ngay":
            return start(message)

    # 4. NÚT BẤM
    if text == "✅ Xác Minh Ngay":
        if is_sub(uid_int):
            if not db["users"][uid]['verified']:
                db["users"][uid]['verified'] = True
                
                # CỘNG TIỀN NGHIÊM NGẶT TẠI ĐÂY
                ref_id = db["users"][uid].get('invited_by')
                if ref_id and str(ref_id) in db["users"] and str(ref_id) != uid:
                    db["users"][str(ref_id)]['balance'] += MONEY_PER_REF
                    db["users"][str(ref_id)]['refs'] += 1
                    save_db()
                    try: 
                        bot.send_message(ref_id, f"🎉 **TÀI KHOẢN +10.000đ**!\nUser {uid} đã xác minh thành công.", parse_mode="Markdown")
                    except: pass
                save_db()
            bot.send_message(uid_int, "✅ Xác minh thành công!", reply_markup=main_menu(uid_int))
        else:
            bot.send_message(uid_int, "❌ Bạn vẫn chưa join đủ nhóm! Hãy kiểm tra lại.")

    elif text == "📊 Thống Kê":
        u = db["users"].get(uid)
        bot.send_message(uid_int, f"👤 **TÀI KHOẢN**\n💰 Số dư: **{u['balance']:,}đ**\n👫 Đã mời: `{u['refs']}`\n🎁 Rút code tại: {COST_PER_CODE:,}đ", parse_mode="Markdown")

    elif text == "🎮 Link Game":
        bot.send_message(uid_int, f"🎮 **LINK GAME:** {db.get('game_link')}")

    elif text == "🎁 Rút Giftcode":
        u = db["users"].get(uid)
        if u['balance'] < COST_PER_CODE:
            return bot.send_message(uid_int, f"❌ Không đủ {COST_PER_CODE:,}đ (Cần mời thêm {int((COST_PER_CODE-u['balance'])/MONEY_PER_REF)} bạn)")
        if not db["codes"]: return bot.send_message(uid_int, "📭 Hết code!")
        code = db["codes"].pop(0)
        u['balance'] -= COST_PER_CODE
        save_db()
        bot.send_message(uid_int, f"🎁 Code của bạn: `{code}`", parse_mode="Markdown")

    elif text == "🔗 Link Mời (10K/Ref)":
        link = f"https://t.me/{bot.get_me().username}?start={uid}"
        bot.send_message(uid_int, f"💰 **1 REF = {MONEY_PER_REF:,}đ**\n\nLink của bạn:\n`{link}`\n\n*Tiền chỉ được cộng khi bạn bè xác minh thành công.*", parse_mode="Markdown")

    # --- ADMIN CONTROL ---
    elif text == "🛠 Admin Panel" and (uid_int in ADMIN_CHINH or uid_int in ADMIN_PHU):
        bot.send_message(uid_int, "🛠 Hệ thống quản trị:", reply_markup=admin_panel_menu())

    elif text == "🕹 Đổi Link Game" and uid_int in ADMIN_CHINH:
        admin_states[uid_int] = "WAIT_GAME_LINK"
        bot.send_message(uid_int, "Nhập Link Game mới:", reply_markup=cancel_markup())

    elif text == "➕ Thêm Giftcode" and uid_int in ADMIN_CHINH:
        admin_states[uid_int] = "WAIT_ADD_CODE"
        bot.send_message(uid_int, "Nhập code (mỗi dòng 1 cái):", reply_markup=cancel_markup())

    elif text == "📢 Gửi Thông Báo" and uid_int in ADMIN_CHINH:
        admin_states[uid_int] = "WAIT_BROADCAST"
        bot.send_message(uid_int, "Nhập nội dung:", reply_markup=cancel_markup())

    elif text == "📢 Quản Lý Nhóm" and uid_int in ADMIN_CHINH:
        msg = "📝 **Nhóm:**\n" + "\n".join(db["channels"])
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("➕ Thêm Nhóm Check", "🧹 Xóa Hết Nhóm")
        markup.add("🛠 Admin Panel")
        bot.send_message(uid_int, msg, reply_markup=markup, parse_mode="Markdown")

    elif text == "➕ Thêm Nhóm Check" and uid_int in ADMIN_CHINH:
        admin_states[uid_int] = "WAIT_ADD_GROUP"
        bot.send_message(uid_int, "Nhập Username (@tennhom):", reply_markup=cancel_markup())

    elif text == "🧹 Xóa Hết Nhóm" and uid_int in ADMIN_CHINH:
        db["channels"] = []
        save_db(); bot.send_message(uid_int, "✅ Đã xóa!", reply_markup=admin_panel_menu())

    elif text == "💰 Cộng/Trừ Tiền" and uid_int in ADMIN_CHINH:
        admin_states[uid_int] = "WAIT_BALANCE_CMD"
        bot.send_message(uid_int, "Nhập theo định dạng:\n`ID_USER | Số_Tiền`\n\nVí dụ để trừ 10k: `1234567 | -10000`", parse_mode="Markdown", reply_markup=cancel_markup())

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
            
