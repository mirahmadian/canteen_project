import requests
from flask import Flask
from datetime import date, timedelta
from .models import db, Employee, DailyMenu, Reservation

# ===============================================
# ۱. توابع ارتباط با API بله
# ===============================================

def send_message(chat_id, text, api_base_url):
    """ارسال پیام به چت مشخص شده با استفاده از API بله."""
    url = f"{api_base_url}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text
    }
    try:
        # NOTE: Bale API expects text/markdown or similar content type
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending message to Bale: {e}")
        return None

def send_photo(chat_id, photo_url, caption, api_base_url):
    """ارسال عکس به چت مشخص شده."""
    url = f"{api_base_url}/sendPhoto"
    payload = {
        'chat_id': chat_id,
        'photo': photo_url,
        'caption': caption
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending photo to Bale: {e}")
        return None

# ===============================================
# ۲. توابع کمکی دیتابیس
# ===============================================

def get_employee_by_bale_id(bale_id):
    """بازیابی کارمند بر اساس شناسه بله (bale_id)."""
    # در اینجا از ستون جدید bale_id استفاده می‌شود
    return Employee.query.filter_by(bale_id=bale_id).first()

def get_current_menu():
    """دریافت منوی فردا برای رزرو."""
    tomorrow = date.today() + timedelta(days=1)
    return DailyMenu.query.filter_by(date=tomorrow).first()

# ===============================================
# ۳. منطق بات برای دستورات اصلی
# ===============================================

def handle_start_command(chat_id, user_id, api_base_url):
    """پاسخ به فرمان /start و خوش آمدگویی."""
    
    # ۱. کاربر را بر اساس bale_id پیدا یا ثبت کنید
    employee = get_employee_by_bale_id(user_id)

    if not employee:
        # اگر کاربر در Employee ثبت نشده است، یک پیام خوش‌آمدگویی و دستورالعمل ورود ارسال کنید.
        # ⬅️ خط جدید برای چاپ شناسه بله در لاگ‌ها
        print(f"--- LOGGING NEW BALE ID: {user_id} ---")
        
        # NOTE: در یک سیستم واقعی، باید با شماره ملی یا کد کارمندی احراز هویت شوند.
        welcome_message = (
            "به ربات رزرو غذای سلف خوش آمدید.\n"
            "برای فعال‌سازی حساب کاربری خود، لطفاً با مدیر سیستم تماس بگیرید.\n"
            "شناسه بله شما: `{user_id}`"
        ).format(user_id=user_id)
        send_message(chat_id, welcome_message, api_base_url)
        return

    # ۲. اگر کاربر ادمین است، گزینه‌های مدیریتی را هم اضافه کنید
    if employee.is_admin:
        admin_info = "شما مدیر سیستم هستید. می‌توانید از دستور /admin_menu استفاده کنید."
    else:
        admin_info = ""

    # ۳. ارسال منوی اصلی
    menu = get_current_menu()
    if menu:
        menu_text = (
            f"✅ خوش آمدید، {employee.full_name}!\n"
            f"منوی غذای فردا ({menu.date.strftime('%Y/%m/%d')}) آماده رزرو است:\n\n"
            f"۱. {menu.meal_1}\n"
            f"۲. {menu.meal_2}\n"
            f"۳. {menu.meal_3 or '---'}\n\n"
            "برای رزرو، یکی از اعداد (1، 2 یا 3) را ارسال کنید."
        )
    else:
        menu_text = "❌ منوی غذای فردا هنوز توسط مدیر تعریف نشده است."

    final_message = f"{menu_text}\n\n{admin_info}"
    send_message(chat_id, final_message, api_base_url)

# ===============================================
# ۴. منطق پنل ادمین
# ===============================================

def handle_admin_menu(chat_id, employee, api_base_url):
    """نمایش پنل ادمین برای کاربران مجاز."""
    if not employee or not employee.is_admin:
        send_message(chat_id, "❌ شما دسترسی مدیر سیستم را ندارید.", api_base_url)
        return

    admin_menu = (
        "⚙️ **پنل مدیریت سیستم (مدیر)**\n\n"
        "لطفاً عملیات مورد نظر خود را انتخاب کنید:\n\n"
        "**مدیریت کاربران:**\n"
        "/add_employee - افزودن کارمند جدید\n"
        "/list_employees - مشاهده لیست کارمندان\n\n"
        "**مدیریت منو و رزرو:**\n"
        "/set_menu - تعریف/ویرایش منوی روزانه\n"
        "/get_report - گزارش رزروهای ثبت شده\n\n"
        "**تنظیمات سیستم:**\n"
        "/set_time - تنظیم زمان یادآوری و پایان سفارش‌گیری (در حال حاضر ثابت است)"
    )
    send_message(chat_id, admin_menu, api_base_url)


def handle_add_employee_step1(chat_id, api_base_url):
    """شروع فرایند افزودن کارمند جدید."""
    send_message(chat_id, "لطفاً اطلاعات کارمند جدید را در یک خط و به ترتیب زیر وارد کنید:\n\n"
                          "**شماره ملی، نام و نام خانوادگی، شماره تلفن، شناسه بله**\n\n"
                          "مثال: `0012345678، علی محمدی، 09123456789، 12345678`", api_base_url)

# NOTE: برای ساده‌سازی، منطق کامل "افزودن کارمند" به خاطر نیاز به حفظ State کاربر (که Flask بدون Context مشکل دارد) در اینجا پیاده‌سازی نشده است.
# ما در اینجا فقط یک تابع نمونه برای پردازش پیام‌های ورودی ایجاد می‌کنیم.


def handle_text_message(chat_id, user_id, text, api_base_url):
    """پردازش پیام‌های متنی عادی، رزرو غذا یا تکمیل افزودن کارمند."""
    employee = get_employee_by_bale_id(user_id)

    if not employee:
        # اگر کاربر ثبت نشده است، کاری انجام ندهید.
        send_message(chat_id, "لطفاً برای فعال‌سازی ابتدا /start را ارسال کنید.", api_base_url)
        return

    text = text.strip()
    
    # 1. مدیریت رزرو
    if text.isdigit() and 1 <= int(text) <= 3:
        # منطق رزرو باید اینجا پیاده‌سازی شود
        send_message(chat_id, f"✅ رزرو غذای شماره {text} برای شما ثبت شد.", api_base_url)
        return

    # 2. مدیریت ادمین (در این مرحله ساده‌سازی شده است)
    if employee.is_admin and text.startswith("ادمین اضافه کن:"):
        # این یک منطق Placeholder برای افزودن کارمند است
        send_message(chat_id, "درخواست ادمین پردازش شد.", api_base_url)
        return

    # 3. پاسخ پیش‌فرض
    send_message(chat_id, "پیام شما دریافت شد. لطفاً یکی از دستورات اصلی (/start) یا شماره غذا را ارسال کنید.", api_base_url)


# ===============================================
# ۵. تابع اصلی پردازش وب‌هوک
# ===============================================

def process_webhook_request(update, api_base_url):
    """تابع اصلی که درخواست‌های Webhook را پردازش می‌کند."""
    try:
        # استخراج اطلاعات پیام
        message = update.get('message')
        if not message:
            return

        chat_id = message['chat']['id']
        user_id = message['from']['id']
        text = message.get('text', '')
        
        # ⬅️ اولین بار که کاربر پیام می‌دهد، bale_id او در دیتابیس نیست.
        # ابتدا بررسی می‌کنیم که آیا این کاربر در دیتابیس ما ثبت شده است یا خیر.
        employee = get_employee_by_bale_id(user_id)
        
        if text.startswith('/start'):
            handle_start_command(chat_id, user_id, api_base_url)
        elif text.startswith('/admin_menu'):
            handle_admin_menu(chat_id, employee, api_base_url)
        elif text.startswith('/add_employee'):
            # اگر ادمین است، مرحله اول افزودن کارمند را شروع کنید.
            if employee and employee.is_admin:
                handle_add_employee_step1(chat_id, api_base_url)
            else:
                send_message(chat_id, "❌ شما دسترسی لازم را برای اجرای این فرمان ندارید.", api_base_url)
        else:
            # اگر فرمان خاصی نبود، آن را به عنوان پیام متنی عادی (رزرو یا ورودی ادمین) پردازش کنید.
            handle_text_message(chat_id, user_id, text, api_base_url)

    except Exception as e:
        print(f"An error occurred during webhook processing: {e}")
