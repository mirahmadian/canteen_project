import os
from flask import Flask, request, jsonify
from datetime import date, timedelta
import requests
import json

# ===============================================
# ۱. بخش Imports
# ===============================================

# ⬅️ استفاده از Imports نسبی برای دسترسی به مدل‌ها
from .models import db, Employee, DailyMenu, Reservation 
from .bot_service import process_webhook_request

# ===============================================
# ۲. تنظیمات اولیه
# ===============================================
app = Flask(__name__)

# مسیر دیتابیس (برای Render باید در پوشه ای باشد که قابل نوشتن است)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/canteen.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# توکن و آدرس‌های بات بله
BOT_TOKEN = os.environ.get("BOT_TOKEN", "321354773:PExaK8QbMFAdMvA-TaOkKh_O87igVJnh38I")

# آدرس Webhook که قبلاً به '/webhook' تغییر دادیم
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://canteen-bot-api.onrender.com/webhook")

# آدرس جدید API برای حل مشکل DNS در Render
BALE_API_BASE_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}" 

db.init_app(app) # اتصال SQLAlchemy به برنامه

# ===============================================
# ۳. توابع کمکی و دیتابیس
# ===============================================

def init_db():
    """ایجاد دیتابیس و اضافه کردن داده‌های تستی."""
    with app.app_context():
        # این خط دیتابیس را ایجاد می‌کند (اگر وجود نداشته باشد) و جداول را می‌سازد.
        db.create_all()
        print("دیتابیس و جداول ایجاد شدند.")

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
# ۴. مسیرها (Routes)
# ===============================================

@app.route('/')
def home():
    """مسیر اصلی برای بررسی سلامت سرویس."""
    return jsonify({"status": "Bot server is running successfully!", "api_base": BALE_API_BASE_URL}), 200

# ⬅️ مسیر جدید برای سرویس‌های Keep-Alive
@app.route('/ping')
def ping():
    """یک پاسخ ساده برای سرویس‌های خارجی که سرور را فعال نگه می‌دارند."""
    return jsonify({"status": "ok", "message": "Pong!"}), 200

@app.route('/webhook', methods=['POST'])
def bale_webhook():
    """نقطه ورود اصلی برای دریافت درخواست‌های سرور بله."""
    update = request.get_json()
    
    # فراخوانی تابع پردازش وب‌هوک و ارسال آدرس API جدید
    process_webhook_request(update, BALE_API_BASE_URL)
    
    # بله انتظار پاسخ 200 OK را دارد.
    return jsonify({"status": "ok"}), 200

# ===============================================
# ۵. اجرای اولیه (برای Gunicorn/Render)
# ===============================================
# این بخش مطمئن می‌شود که دیتابیس در زمان راه‌اندازی Gunicorn ایجاد شود.
with app.app_context():
    init_db()

# این بخش فقط برای تست محلی است:
if __name__ == '__main__':
    app.run(debug=True, port=5000)
