from flask import Flask, request, jsonify
from canteen.models import db, Employee, AdminUser, SystemConfig, DailyMenu
from werkzeug.security import generate_password_hash
from canteen.bot_service import handle_meal_reservation, get_tomorrow_menu_for_display, send_message, show_daily_menu
import json
from datetime import datetime, date, timedelta

# ########## ۱. تنظیمات اولیه اپلیکیشن ##########
app = Flask(__name__)
# تنظیم دیتابیس SQLite برای سادگی
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///canteen_db.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_strong_secret_key_here' # حتماً این کلید را تغییر دهید

# اتصال مدل‌های داده به اپلیکیشن
db.init_app(app)

# ########## ۲. توابع اولیه راه‌اندازی ##########

def init_db():
    """ایجاد جداول دیتابیس و تعریف ادمین اولیه و متغیرهای سیستمی."""
    with app.app_context():
        db.create_all()
        
        # الف) ایجاد ادمین اولیه (بند ۳ و ۴)
        if not AdminUser.query.filter_by(username='superadmin').first():
            # رمز عبور 'adminpass' را با متد ایمن هش می‌کنیم
            hashed_password = generate_password_hash('adminpass', method='pbkdf2:sha256:200000') 
            super_admin = AdminUser(username='superadmin', password_hash=hashed_password, role='SuperAdmin')
            db.session.add(super_admin)
            print("کاربر superadmin با رمز 'adminpass' (حتماً آن را تغییر دهید) ایجاد شد.")
            
        # ب) تعریف متغیرهای سیستمی پیش‌فرض (بند ۲)
        default_configs = {
            'RESERVATION_START_HOUR': '18',
            'RESERVATION_END_HOUR': '23',
            'ALARM_HOUR': '18',
            'PRINT_START_HOUR': '11',
            'PRINT_END_HOUR': '14',
        }
        for key, value in default_configs.items():
            if not SystemConfig.query.filter_by(key=key).first():
                config = SystemConfig(key=key, value=value)
                db.session.add(config)

        # ج) افزودن یک کارمند تستی (برای احراز هویت)
        # شماره تلفن خود را که با آن در بله تست می‌کنید، اینجا قرار دهید!
        test_phone = '09121234567' 
        if not Employee.query.filter_by(phone_number=test_phone).first():
             test_employee = Employee(
                national_id='0012345678', 
                phone_number=test_phone, 
                full_name='کارمند تستی'
             )
             db.session.add(test_employee)
             print(f"کارمند تستی با شماره {test_phone} اضافه شد.")

        # د) افزودن منوی تستی برای فردا
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
        
        db.session.commit()

# ########## ۳. توابع کمکی ##########

def get_employee_by_chat_id(chat_id):
    """تابع موقت: در محیط واقعی، باید chat_id را به employee_id نگاشت کنید.
       در حال حاضر، فقط کارمند تستی را برمی‌گرداند."""
    # شماره تلفن کارمند تستی (باید با شماره ثبت شده در init_db یکسان باشد)
    test_phone = '09121234567' 
    return db.session.query(Employee).filter(Employee.phone_number == test_phone).one_or_none()

# ########## ۴. مسیر وب‌هوک بات بله ##########

@app.route('/bale_webhook', methods=['POST'])
def bale_webhook():
    """نقطه ورود اصلی برای دریافت درخواست‌های سرور بله."""
    
    update = request.get_json()
    
    # 1. استخراج اطلاعات اصلی (برای پیام یا callback)
    if 'message' in update:
        message = update['message']
        chat_id = message['chat']['id']
        text = message.get('text', '')
    elif 'callback_query' in update:
        query = update['callback_query']
        chat_id = query['message']['chat']['id']
        text = query['data'] # Callback data از دکمه
    else:
        # اگر نوع به‌روزرسانی پشتیبانی نمی‌شود، نادیده بگیرد
        return jsonify(status="ignored", reason="Not a supported update type"), 200

    # --- منطق پردازش ---
    with app.app_context():
        employee = get_employee_by_chat_id(chat_id)
        if not employee:
            send_message(chat_id, "لطفاً ابتدا شماره تلفن (که در سامانه ثبت شده) را ارسال کنید تا احراز هویت شوید. (شماره: 09121234567)")
            return jsonify(status="OK - Auth required"), 200

        # **مدیریت دستورات اصلی:**
        if text in ["/start", "انتخاب غذا"]:
            show_daily_menu(chat_id)
        
        elif text.startswith("MEAL_"):
            # پردازش انتخاب غذا از دکمه‌های شیشه‌ای
            meal_name_code = text.replace("MEAL_", "")
            selected_meal_name = meal_name_code.replace('_', ' ').title() 
            
            # فراخوانی منطق اصلی رزرو
            response_message = handle_meal_reservation(employee.phone_number, selected_meal_name) 
            send_message(chat_id, response_message)
            
        elif text == "چاپ_فیش":
            # این بخش بعداً پیاده‌سازی می‌شود
            send_message(chat_id, "قابلیت چاپ فیش در حال حاضر فعال نیست.")
            
        else:
            send_message(chat_id, "دستور نامعتبر. برای شروع /start را ارسال کنید.")
            
    return jsonify(status="OK"), 200


# ########## ۵. اجرای اپلیکیشن ##########

if __name__ == '__main__':
    # این تابع، دیتابیس را ایجاد کرده و تنظیمات اولیه و داده‌های تستی را وارد می‌کند.
    init_db() 
    print("\nآماده برای اجرای پروژه.")
    
    # برای اجرای موقت Flask:
    # سرور را روی پورت 5000 اجرا می‌کند
    app.run(debug=True, port=5000)