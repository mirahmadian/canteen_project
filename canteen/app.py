from .__init__ import app, db
from .models import Employee, AdminUser, SystemConfig, DailyMenu
from .bot_service import handle_meal_reservation, get_tomorrow_menu_for_display, send_message, show_daily_menu
from flask import request, jsonify
from werkzeug.security import generate_password_hash
import json
from datetime import date, timedelta

# ########## ۱. توابع اولیه راه‌اندازی و داده‌های تستی ##########

def init_db():
    """ایجاد جداول دیتابیس و تعریف ادمین اولیه و متغیرهای سیستمی."""
    # این تابع اکنون فقط مسئول افزودن داده‌های اولیه است، db.create_all خارج از این تابع فراخوانی می‌شود.
    
    # الف) ایجاد ادمین اولیه
    if not AdminUser.query.filter_by(username='superadmin').first():
        # در محیط واقعی، این پسورد باید از متغیرهای محیطی خوانده شود
        hashed_password = generate_password_hash('adminpass', method='pbkdf2:sha256:200000') 
        super_admin = AdminUser(username='superadmin', password_hash=hashed_password, role='SuperAdmin')
        db.session.add(super_admin)
        print("کاربر superadmin ایجاد شد.")
        
    # ب) تعریف متغیرهای سیستمی پیش‌فرض
    default_configs = {
        'RESERVATION_START_HOUR': '18', 'RESERVATION_END_HOUR': '23', 
        'ALARM_HOUR': '18', 'PRINT_START_HOUR': '11', 'PRINT_END_HOUR': '14',
    }
    for key, value in default_configs.items():
        if not SystemConfig.query.filter_by(key=key).first():
            db.session.add(SystemConfig(key=key, value=value))

    # ج) افزودن یک کارمند تستی (شماره تلفن تستی برای احراز هویت در بله)
    test_phone = '09121234567' 
    if not Employee.query.filter_by(phone_number=test_phone).first():
         db.session.add(Employee(national_id='0012345678', phone_number=test_phone, full_name='کارمند تستی'))
         print(f"کارمند تستی با شماره {test_phone} اضافه شد.")

    # د) افزودن منوی تستی برای فردا
    tomorrow = date.today() + timedelta(days=1)
    if not DailyMenu.query.filter_by(date=tomorrow).first():
        db.session.add(DailyMenu(date=tomorrow, meal_1='چلو کباب', meal_2='قورمه سبزی', meal_3='زرشک پلو'))
        print(f"منوی تستی برای {tomorrow} اضافه شد.")
    
    db.session.commit()

# ########## ۲. توابع کمکی و مسیر وب‌هوک ##########

def get_employee_by_chat_id(chat_id):
    """تابع موقت: کارمند تستی را برمی‌گرداند."""
    # در محیط واقعی باید با استفاده از یک جدول چت_آیدی/شماره تلفن این کارمند را پیدا کند
    test_phone = '09121234567' 
    return db.session.query(Employee).filter(Employee.phone_number == test_phone).one_or_none()


@app.route('/bale_webhook', methods=['POST'])
def bale_webhook():
    """نقطه ورود اصلی برای دریافت درخواست‌های سرور بله."""
    update = request.get_json()
    
    # استخراج اطلاعات (message یا callback_query)
    if 'message' in update:
        message = update['message']
        chat_id = message['chat']['id']
        text = message.get('text', '')
    elif 'callback_query' in update:
        query = update['callback_query']
        chat_id = query['message']['chat']['id']
        text = query['data']
    else:
        return jsonify(status="ignored"), 200

    with app.app_context():
        # TODO: در محیط واقعی، ابتدا باید chat_id را به شماره تلفن احراز هویت کنید
        employee = get_employee_by_chat_id(chat_id) 
        if not employee:
            # در محیط واقعی، کاربر باید شماره تلفن خود را ارسال کند تا در جدول employee_chat_id ثبت شود
            send_message(chat_id, "❌ شماره تلفن شما در سیستم یافت نشد. برای تست، لطفاً ابتدا شماره 09121234567 را ارسال کنید.")
            return jsonify(status="OK - Auth required"), 200

        if text in ["/start", "انتخاب غذا"]:
            show_daily_menu(chat_id)
        
        elif text.startswith("MEAL_"):
            meal_name_code = text.replace("MEAL_", "")
            selected_meal_name = meal_name_code.replace('_', ' ').title() 
            response_message = handle_meal_reservation(employee.phone_number, selected_meal_name) 
            send_message(chat_id, response_message)
        
        elif text == "چاپ_فیش":
            send_message(chat_id, "قابلیت چاپ فیش در حال حاضر فعال نیست.")
            
        else:
            send_message(chat_id, "دستور نامعتبر. برای شروع /start را ارسال کنید.")
            
    return jsonify(status="OK"), 200


# ########## ۳. راه‌اندازی دیتابیس هنگام شروع سرور ##########

# این بلوک کد تضمین می‌کند که هنگام اجرای Gunicorn در Render، جداول دیتابیس ساخته شوند
# و داده‌های اولیه (کاربر تستی، منو و...) اضافه شوند.
with app.app_context():
    # ساخت جداول در صورت عدم وجود (اولین بار)
    db.create_all() 
    # افزودن داده‌های اولیه
    init_db()


if __name__ == '__main__':
    # این قسمت فقط برای اجرای محلی روی کامپیوتر شما استفاده می‌شود
    print("\nآماده برای اجرای پروژه به صورت محلی (توسط app.run).")
    app.run(debug=True, port=5000)