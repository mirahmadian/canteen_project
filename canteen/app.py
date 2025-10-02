import os
from flask import Flask, request, jsonify
from datetime import date, timedelta
import requests
import json
# مطمئن شوید که فایل‌های models و bot_service در این مسیر قابل دسترسی هستند
from models import db, Employee, DailyMenu, Reservation 
from bot_service import process_webhook_request

# ===============================================
# ۱. تنظیمات اولیه
# ===============================================
app = Flask(__name__)

# مسیر دیتابیس (برای Render باید در پوشه ای باشد که قابل نوشتن است)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/canteen.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# توکن و آدرس‌های بات بله
BOT_TOKEN = os.environ.get("BOT_TOKEN", "321354773:PExaK8QbMFAdMvA-TaOkKh_O87igVJnh38I")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://canteen-bot-api.onrender.com/bale_webhook")

# === FIX: آدرس جدید API برای حل مشکل DNS در Render ===
# این آدرس به جای 'https://bot.tinet.ir/api/v2/' استفاده می‌شود تا خطای DNS حل شود.
BALE_API_BASE_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}" 

db.init_app(app)

# ===============================================
# ۲. توابع کمکی و دیتابیس
# ===============================================

def init_db():
    """ایجاد دیتابیس و اضافه کردن داده‌های تستی."""
    with app.app_context():
        db.create_all()
        print("دیتابیس ایجاد شد.")

        # ۱. کاربر superadmin (تست)
        super_admin_phone = '09000000000'
        if not Employee.query.filter_by(phone_number=super_admin_phone).first():
            super_admin = Employee(national_id='1111111111', phone_number=super_admin_phone, full_name='Super Admin', is_admin=True)
            db.session.add(super_admin)
            print("کاربر superadmin ایجاد شد.")
        
        # ۲. کارمند تستی (که با آن در بله تست می‌کنیم)
        test_employee_phone = '09121234567'
        if not Employee.query.filter_by(phone_number=test_employee_phone).first():
             test_employee = Employee(national_id='0012345678', phone_number=test_employee_phone, full_name='کارمند تستی')
             db.session.add(test_employee)
             print(f"کارمند تستی با شماره {test_employee_phone} اضافه شد.")
        
        # ۳. منوی تستی برای فردا
        tomorrow = date.today() + timedelta(days=1)
        if not DailyMenu.query.filter_by(date=tomorrow).first():
            test_menu = DailyMenu(
                date=tomorrow,
                meal_1='چلو کباب',
                meal_2='قورمه سبزی',
                meal_3='زرشک پلو'
            )
            db.session.add(test_menu)
            print(f"منوی تستی برای {tomorrow} اضافه شد.")
        else:
             print(f"منوی تستی برای {tomorrow} قبلاً وجود دارد.")

        db.session.commit()
        print("داده‌های تستی با موفقیت اضافه شدند.")

# ===============================================
# ۳. مسیرها (Routes)
# ===============================================

@app.route('/')
def home():
    """مسیر اصلی برای بررسی سلامت سرویس و اطمینان از اجرای init_db."""
    init_db() 
    return jsonify({"status": "Bot server is running successfully!", "api_base": BALE_API_BASE_URL})

@app.route('/bale_webhook', methods=['POST'])
def bale_webhook():
    """نقطه ورود اصلی برای دریافت درخواست‌های سرور بله."""
    update = request.get_json()
    
    # فراخوانی تابع پردازش وب‌هوک و ارسال آدرس API جدید
    # توجه: باید تابع process_webhook_request در bot_service.py را نیز به‌روز کنید
    process_webhook_request(update, BALE_API_BASE_URL)
    
    # بله انتظار پاسخ 200 OK را دارد.
    return jsonify({"status": "ok"}), 200

# ===============================================
# ۴. اجرای اپلیکیشن (برای Gunicorn/Render)
# ===============================================
# این بخش در Render توسط gunicorn اجرا می‌شود:
# gunicorn canteen.app:app

# این بخش فقط برای تست محلی است:
if __name__ == '__main__':
    init_db() 
    app.run(debug=True, port=5000)