import os
import requests
import json
from datetime import date, timedelta
from flask import current_app
from models import db, Employee, DailyMenu, Reservation

# توکن بات (برای موارد اضطراری، اما از app.py منتقل می‌شود)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "321354773:PExaK8QbMFAdMvA-TaOkKh_O87igVJnh38I")

# ==========================================================
# توابع ارسال پیام به API بله
# ==========================================================

def send_message(chat_id, text, api_base_url, reply_markup=None):
    """ارسال پیام به چت مشخص شده با استفاده از آدرس API جدید."""
    
    # === تغییر حیاتی: استفاده از api_base_url جدید ===
    # این خط مشکل NameResolutionError در Render را حل می‌کند.
    url = f"{api_base_url}/sendMessage"
    
    payload = {
        'chat_id': chat_id,
        'text': text,
        'reply_markup': json.dumps(reply_markup) if reply_markup else None
    }
    
    # اگر در محیط لوکال نیستید و با Render کار می‌کنید، نیازی به verify=False نیست. 
    # اما برای رفع مشکلات احتمالی SSL در سرورهای خارجی برای دامنه‌های داخلی، آن را نگه می‌داریم.
    try:
        response = requests.post(url, json=payload, verify=False, timeout=10)
        response.raise_for_status() 
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending message to Bale: {e}")
        return None

def get_phone_keyboard():
    """ایجاد دکمه درخواست شماره تماس."""
    keyboard = {
        'keyboard': [
            [{'text': 'ارسال شماره تماس', 'request_contact': True}]
        ],
        'resize_keyboard': True,
        'one_time_keyboard': True
    }
    return keyboard

def get_main_menu_keyboard():
    """ایجاد کیبورد منوی اصلی."""
    keyboard = {
        'keyboard': [
            [{'text': 'مشاهده منو و رزرو غذا 🍽️'}],
            [{'text': 'مشاهده رزروهای من 🗓️'}],
            [{'text': 'راهنما ❓'}]
        ],
        'resize_keyboard': True,
        'one_time_keyboard': False
    }
    return keyboard

# ==========================================================
# منطق پردازش دستورات
# ==========================================================

def handle_start(chat_id, employee, api_base_url):
    """پاسخ به دستور /start."""
    if employee:
        text = f"سلام {employee.full_name} عزیز! به سیستم رزرو سلف خوش آمدید."
        send_message(chat_id, text, api_base_url, get_main_menu_keyboard())
    else:
        text = "لطفاً برای استفاده از ربات، شماره تلفن خود را از طریق دکمه زیر ارسال کنید."
        send_message(chat_id, text, api_base_url, get_phone_keyboard())

def handle_show_menu(chat_id, employee, api_base_url):
    """نمایش منوی فردا."""
    tomorrow = date.today() + timedelta(days=1)
    menu = DailyMenu.query.filter_by(date=tomorrow).first()

    if menu:
        text = (
            f"**منوی سلف برای فردا ({tomorrow.strftime('%Y/%m/%d')}):**\n\n"
            f"۱. {menu.meal_1}\n"
            f"۲. {menu.meal_2}\n"
            f"۳. {menu.meal_3}\n\n"
            "لطفاً غذای مورد نظر خود را برای رزرو انتخاب کنید."
        )
        
        # کیبورد برای رزرو
        reserve_keyboard = {
            'inline_keyboard': [
                [{'text': menu.meal_1, 'callback_data': f'reserve_1_{tomorrow}'}],
                [{'text': menu.meal_2, 'callback_data': f'reserve_2_{tomorrow}'}],
                [{'text': menu.meal_3, 'callback_data': f'reserve_3_{tomorrow}'}],
            ]
        }
        send_message(chat_id, text, api_base_url, reserve_keyboard)
    else:
        text = "متأسفانه منوی غذای فردا هنوز ثبت نشده است."
        send_message(chat_id, text, api_base_url, get_main_menu_keyboard())

def handle_callback_query(chat_id, employee, callback_data, api_base_url):
    """مدیریت دکمه‌های شیشه‌ای (رزرو)."""
    if not employee:
        text = "لطفاً ابتدا احراز هویت کنید."
        return send_message(chat_id, text, api_base_url, get_phone_keyboard())

    try:
        action, meal_index, date_str = callback_data.split('_')
        reserve_date = date.fromisoformat(date_str)
        meal_index = int(meal_index)
    except ValueError:
        return send_message(chat_id, "اطلاعات رزرو نامعتبر است.", api_base_url)

    if action == 'reserve':
        # بررسی اینکه آیا قبلا رزرو شده است
        existing_reservation = Reservation.query.filter_by(employee_id=employee.id, reservation_date=reserve_date).first()
        if existing_reservation:
            text = "شما قبلاً غذای خود را برای این تاریخ رزرو کرده‌اید. فقط یک رزرو در روز مجاز است."
            return send_message(chat_id, text, api_base_url)

        menu = DailyMenu.query.filter_by(date=reserve_date).first()
        if not menu:
             text = "منوی این روز در دسترس نیست."
             return send_message(chat_id, text, api_base_url)

        # انتخاب نام غذا بر اساس ایندکس
        meal_name = getattr(menu, f'meal_{meal_index}', 'نامشخص')

        new_reservation = Reservation(
            employee_id=employee.id,
            reservation_date=reserve_date,
            meal_name=meal_name
        )
        db.session.add(new_reservation)
        db.session.commit()

        text = f"✅ رزرو شما برای **{meal_name}** در تاریخ **{date_str}** با موفقیت ثبت شد."
        send_message(chat_id, text, api_base_url, get_main_menu_keyboard())


# ==========================================================
# تابع اصلی پردازش وب‌هوک
# ==========================================================

# === تغییر حیاتی: تابع باید دو آرگومان را بپذیرد ===
def process_webhook_request(update, api_base_url):
    """دریافت و پردازش درخواست وب‌هوک از بله."""
    with current_app.app_context():
        # ۱. استخراج اطلاعات اولیه
        if 'message' in update:
            message = update['message']
            chat_id = message['chat']['id']
            user_id = message['from']['id']
            
            # پیدا کردن کارمند در دیتابیس
            employee = Employee.query.filter_by(bale_id=user_id).first()

            # ۲. مدیریت پیام‌های متنی
            if 'text' in message:
                text = message['text'].strip()

                if text == '/start':
                    handle_start(chat_id, employee, api_base_url)
                elif text == 'مشاهده منو و رزرو غذا 🍽️':
                    if employee:
                        handle_show_menu(chat_id, employee, api_base_url)
                    else:
                        handle_start(chat_id, employee, api_base_url)
                elif text == 'مشاهده رزروهای من 🗓️':
                    # منطق مشاهده رزروها (در این مثال حذف شده است)
                    send_message(chat_id, "این قابلیت در حال توسعه است.", api_base_url, get_main_menu_keyboard())
                else:
                    send_message(chat_id, "متوجه نشدم. از منوی اصلی استفاده کنید.", api_base_url, get_main_menu_keyboard())

            # ۳. مدیریت درخواست شماره تماس (Contact Request)
            elif 'contact' in message:
                contact = message['contact']
                phone_number_raw = contact.get('phone_number')
                
                # تمیز کردن شماره: حذف کد کشور (+98 یا 98) و فقط شماره 09xx
                if phone_number_raw and phone_number_raw.startswith('+98'):
                    phone_number = '0' + phone_number_raw[3:]
                elif phone_number_raw and phone_number_raw.startswith('98'):
                    phone_number = '0' + phone_number_raw[2:]
                else:
                    phone_number = phone_number_raw # اگر با 09 شروع شده باشد

                employee = Employee.query.filter_by(phone_number=phone_number).first()
                
                if employee:
                    # احراز هویت موفق: ذخیره bale_id و خوش‌آمدگویی
                    employee.bale_id = user_id
                    db.session.commit()
                    text = f"احراز هویت شما با شماره {phone_number} تأیید شد. به سیستم رزرو سلف خوش آمدید."
                    handle_start(chat_id, employee, api_base_url)
                else:
                    # احراز هویت ناموفق
                    text = f"شماره {phone_number} در سیستم کارمندی ثبت نشده است. لطفاً با ادمین تماس بگیرید."
                    send_message(chat_id, text, api_base_url)

        # ۴. مدیریت Callback Query (رزرو)
        elif 'callback_query' in update:
            callback_query = update['callback_query']
            chat_id = callback_query['message']['chat']['id']
            user_id = callback_query['from']['id']
            callback_data = callback_query['data']
            
            employee = Employee.query.filter_by(bale_id=user_id).first()
            
            if employee:
                handle_callback_query(chat_id, employee, callback_data, api_base_url)
            else:
                 send_message(chat_id, "لطفاً برای انجام رزرو ابتدا احراز هویت کنید.", api_base_url, get_phone_keyboard())

    return True