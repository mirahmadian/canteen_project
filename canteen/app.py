import os
from flask import Flask, request, jsonify
from datetime import date, timedelta
import requests
import json
import logging

# تنظیمات لاگ‌گیری برای نمایش اطلاعات
logging.basicConfig(level=logging.INFO)

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
        # db.drop_all() # ⬅️ این خط برای حفظ داده‌ها حذف یا کامنت شده است.
        db.create_all() # ⬅️ ایجاد مجدد جداول (اگر وجود نداشته باشند)
        logging.info("دیتابیس و جداول ایجاد شدند.")

        # ۱. کاربر superadmin (شما) - ⬅️ شناسه بله واقعی شما
        super_admin_bale_id = '1807093505'
        
        # ما فقط در صورتی ادمین را اضافه می‌کنیم که هنوز در دیتابیس نباشد.
        if not Employee.query.filter_by(bale_id=super_admin_bale_id).first():
            super_admin = Employee(
                national_id='1111111111', 
                phone_number='09000000000', 
                full_name='Super Admin', 
                is_admin=True,
                bale_id=super_admin_bale_id 
            )
            db.session.add(super_admin)
            logging.info(f"کاربر superadmin با شناسه بله {super_admin_bale_id} ایجاد شد.")
        
        # ۲. کارمند تستی (که با آن در بله تست می‌کنیم)
        test_employee_bale_id = '22222222' # یک ID غیرواقعی برای تست
        if not Employee.query.filter_by(bale_id=test_employee_bale_id).first():
            test_employee = Employee(
                national_id='0012345678', 
                phone_number='09121234567', 
                full_name='کارمند تستی', 
                bale_id=test_employee_bale_id
            ) 
            db.session.add(test_employee)
            logging.info(f"کارمند تستی با شناسه بله {test_employee_bale_id} اضافه شد.")
        
        # ۳. منوی تستی برای فردا
        tomorrow = date.today() + timedelta(days=1)
        # فقط در صورتی منو را اضافه می‌کنیم که منویی برای فردا وجود نداشته باشد.
        if not DailyMenu.query.filter_by(date=tomorrow).first():
            test_menu = DailyMenu(
                date=tomorrow,
                meal_1='چلو کباب',
                meal_2='قورمه سبزی',
                meal_3='زرشک پلو'
            )
            db.session.add(test_menu)
            logging.info(f"منوی تستی برای {tomorrow} اضافه شد.")
        else:
            logging.info(f"منوی تستی برای {tomorrow} قبلاً وجود دارد.")

        db.session.commit()
        logging.info("داده‌های تستی با موفقیت اضافه شدند.")

# ===============================================
# ۴. مسیرها (Routes)
# ===============================================

@app.route('/')
def home():
    """مسیر اصلی برای بررسی سلامت سرویس."""
    return jsonify({"status": "Bot server is running successfully!", "api_base": BALE_API_BASE_URL}), 200

@app.route('/ping')
def ping():
    """یک پاسخ ساده برای سرویس‌های خارجی که سرور را فعال نگه می‌دارند."""
    return jsonify({"status": "ok", "message": "Pong!"}), 200

@app.route('/webhook', methods=['POST'])
def bale_webhook():
    """نقطه ورود اصلی برای دریافت درخواست‌های سرور بله."""
    update = request.get_json()
    
    # فراخوانی تابع پردازش وب‌هوک و ارسال آدرس API جدید
    # از app_context استفاده می‌کنیم تا دیتابیس در دسترس باشد.
    with app.app_context():
        process_webhook_request(update, BALE_API_BASE_URL)
    
    # بله انتظار پاسخ 200 OK را دارد.
    return jsonify({"status": "ok"}), 200

# ===============================================
# ۵. اجرای اولیه (برای Gunicorn/Render)
# ===============================================
# این بخش مطمئن می‌شود که دیتابیس در زمان راه‌اندازی Gunicorn ایجاد و مقداردهی اولیه شود.
with app.app_context():
    init_db()

# این بخش فقط برای تست محلی است:
if __name__ == '__main__':
    app.run(debug=True, port=5000)
