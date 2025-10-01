from .__init__ import app, db
from .models import Reservation, Employee, DailyMenu, SystemConfig
from datetime import datetime, time, timedelta, date
import requests
import json

# ########## ۱. تنظیمات حیاتی بات بله ##########
# !!! این توکن را از حساب Bot Father در بله دریافت کرده‌اید:
BOT_TOKEN = "321354773:PExaK8QbMFAdMvA-TaOkKh_O87igVJnh38I" 
BALE_API_URL = "https://bot.tinet.ir/api/v2/" 

# ########## ۲. توابع ارتباطی با API بله ##########

def send_message(chat_id, text, reply_markup=None):
    """ارسال پیام به کاربر در بله"""
    url = f"{BALE_API_URL}{BOT_TOKEN}/sendmessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'reply_markup': reply_markup
    }
    try:
        # ارسال درخواست به API بله با timeout کوتاه
        requests.post(url, json=payload, timeout=5) 
    except requests.exceptions.RequestException as e:
        print(f"Error sending message to Bale: {e}")


# ########## ۳. توابع منطق کسب و کار (Business Logic) ##########

def get_config_value(key):
    """خواندن متغیرهای زمانی از جدول SystemConfig."""
    config = SystemConfig.query.filter_by(key=key).one_or_none()
    if config:
        return config.value
    return None 

def get_tomorrow_menu_for_display():
    """خواندن منوی فردا از دیتابیس برای نمایش به کاربر و ساخت دکمه‌ها."""
    tomorrow = date.today() + timedelta(days=1)
    menu = DailyMenu.query.filter_by(date=tomorrow).one_or_none()
    
    meal_options = {}
    if menu:
        # ساخت دیکشنری {نام غذا: کد callback}
        if menu.meal_1:
             meal_options[menu.meal_1] = f"MEAL_{menu.meal_1.replace(' ', '_').upper()}"
        if menu.meal_2:
             meal_options[menu.meal_2] = f"MEAL_{menu.meal_2.replace(' ', '_').upper()}"
        if menu.meal_3:
             meal_options[menu.meal_3] = f"MEAL_{menu.meal_3.replace(' ', '_').upper()}"
             
    return meal_options

def show_daily_menu(chat_id):
    """نمایش منوی روز بعد با دکمه‌های شیشه‌ای."""
    meal_options = get_tomorrow_menu_for_display()
    
    if not meal_options:
        send_message(chat_id, "❌ متأسفانه منوی غذای فردا هنوز توسط مدیر تعریف نشده است.")
        return

    buttons = []
    for meal, data in meal_options.items():
        buttons.append([{'text': meal, 'callback_data': data}])
    
    markup = json.dumps({'inline_keyboard': buttons})

    send_message(
        chat_id, 
        "لطفاً غذای خود را برای فردا انتخاب کنید:", 
        reply_markup=markup
    )
    

def is_reservation_allowed():
    """بررسی می‌کند آیا در حال حاضر امکان رزرو وجود دارد یا خیر (کنترل زمان و تعطیلی)."""
    
    # خواندن ساعات مجاز رزرو از دیتابیس
    start_hour = int(get_config_value('RESERVATION_START_HOUR') or 18)
    end_hour = int(get_config_value('RESERVATION_END_HOUR') or 23)
    
    now = datetime.now()
    tomorrow = now.date() + timedelta(days=1)
    
    # 1. بررسی ساعت مجاز
    start_time_today = datetime.combine(now.date(), time(start_hour, 0))
    end_time_today = datetime.combine(now.date(), time(end_hour, 0))

    if not (start_time_today <= now <= end_time_today):
        return False, f"زمان مجاز رزرو (از {start_hour}:00 تا {end_hour}:00) به پایان رسیده یا هنوز شروع نشده است."

    # 2. بررسی تعطیلی اضطراری (is_canceled)
    menu_tomorrow = DailyMenu.query.filter_by(date=tomorrow).one_or_none()
    
    if not menu_tomorrow:
        return False, "منوی غذای فردا هنوز توسط مدیر تعریف نشده است."

    if menu_tomorrow.is_canceled:
        return False, "رزرو برای فردا به دلیل تعطیلی اضطراری لغو شده است."

    return True, "مجاز به رزرو هستید."


def handle_meal_reservation(employee_phone: str, selected_meal_name: str) -> str:
    """دریافت رزرو از کارمند و ثبت یا ویرایش آن."""
    
    allowed, reason = is_reservation_allowed()
    if not allowed:
        return f"❌ خطا: {reason}"

    # 1. احراز هویت کارمند با شماره تلفن
    employee = Employee.query.filter_by(phone_number=employee_phone).one_or_none()
    if not employee:
        return "❌ خطا: شماره تلفن شما در سیستم کارمندان یافت نشد."

    # 2. تاریخ رزرو (همیشه فردا)
    tomorrow_date = datetime.now().date() + timedelta(days=1)
    
    # 3. بررسی وجود رزرو قبلی (برای امکان ویرایش)
    existing_reservation = Reservation.query.filter(
        Reservation.employee_id == employee.id,
        Reservation.reservation_date == tomorrow_date
    ).one_or_none()

    if existing_reservation:
        # قابلیت ویرایش
        existing_reservation.selected_meal = selected_meal_name
        existing_reservation.status = 'Reserved' 
        db.session.commit()
        return f"✅ رزرو غذای شما برای فردا با موفقیت به **{selected_meal_name}** **ویرایش** شد."
    else:
        # ثبت رزرو جدید
        new_reservation = Reservation(
            employee_id=employee.id,
            reservation_date=tomorrow_date,
            selected_meal=selected_meal_name
        )
        db.session.add(new_reservation)
        db.session.commit()
        return f"🎉 رزرو غذای شما برای فردا با موفقیت ثبت شد: **{selected_meal_name}**"