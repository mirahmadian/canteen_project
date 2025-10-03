import json
import logging
from datetime import date, timedelta
import requests
from .models import db, Employee, Menu, Reservation 

# تنظیمات اولیه
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ===============================================
# ۱. توابع ارسال پیام
# ===============================================

def send_message(chat_id, text, api_base_url, reply_markup=None):
    """تابع کمکی برای ارسال پیام به بله."""
    url = f"{api_base_url}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown'
    }
    if reply_markup:
        # ساختار دکمه‌ها برای بله کمی متفاوت است
        payload['reply_markup'] = json.dumps({
            'keyboard': reply_markup,
            'resize_keyboard': True,
            'one_time_keyboard': True
        })
    
    try:
        # InsecureRequestWarning را نادیده می‌گیریم، چون tapi.bale.ai گواهی‌نامه معتبری دارد اما urllib3 گاهی خطا می‌دهد.
        response = requests.post(url, json=payload, verify=False) 
        response.raise_for_status() # برای تشخیص خطاهای HTTP
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending message to chat {chat_id}: {e}")
        return None
    
    return response.json()

# ===============================================
# ۲. توابع کمکی ربات
# ===============================================

def get_user_keyboard():
    """کیبورد کاربر عادی."""
    return [
        ['/menu', '/reserve_info'],
    ]

def send_user_menu(chat_id, api_base_url):
    """ارسال منوی اصلی کاربر عادی."""
    text = "🗓️ **منوی امروز و رزرو**\nلطفاً از دستور /menu برای مشاهده منو و رزرو غذا استفاده کنید."
    keyboard = get_user_keyboard()
    send_message(chat_id, text, api_base_url, reply_markup=keyboard)


def handle_admin_panel_access(chat_id, api_base_url):
    """هدایت ادمین به پنل وب."""
    admin_url = f"{api_base_url.replace('/bot', '')}/admin"
    text = (
        "👑 **پنل مدیریت سامانه**\n"
        "برای مدیریت کاربران، منو و مشاهده گزارشات، لطفاً از پنل وب استفاده کنید:\n\n"
        f"[ورود به پنل ادمین]({admin_url})\n\n"
        "دستورات مدیریت در محیط ربات غیرفعال شده‌اند."
    )
    send_message(chat_id, text, api_base_url)


# ===============================================
# ۳. پردازش ورودی و فرمان‌ها
# ===============================================

def process_webhook_request(update, api_base_url):
    """تابع اصلی پردازش به‌روزرسانی‌های بله."""
    
    if 'message' not in update or 'text' not in update['message']:
        return

    message = update['message']
    chat_id = message['chat']['id']
    user_id = message['from']['id'] 
    text = message['text'].strip()
    logger.info(f"Received message from user {user_id} in chat {chat_id}: {text}")

    # ۱. جستجوی کارمند
    employee = Employee.query.filter_by(bale_id=user_id).first()
    
    # ۲. پردازش فرمان‌ها
    if text.startswith('/'):
        command = text.split()[0]
        
        if command == '/start' or command == '/menu':
            if employee and employee.is_admin:
                handle_admin_panel_access(chat_id, api_base_url)
            elif employee:
                send_user_menu(chat_id, api_base_url)
            else:
                contact_message = (
                    "به ربات رزرو غذای سلف خوش آمدید.\n"
                    "برای فعال‌سازی حساب کاربری خود، لطفاً با مدیر سیستم تماس بگیرید.\n"
                    f"شناسه بله شما: `{chat_id}`"
                )
                send_message(chat_id, contact_message, api_base_url)
            return

        # اگر ادمین هر فرمان دیگری (مثل admin_menu قبلی) را بفرستد، او را به پنل وب هدایت می‌کنیم
        if employee and employee.is_admin:
            handle_admin_panel_access(chat_id, api_base_url)
            return

    # ۳. اگر پیام متنی عادی است:
    if employee and not text.startswith('/'):
        # در اینجا می‌توانید منطق مربوط به رزرو (فاز بعدی) را اضافه کنید
        send_user_menu(chat_id, api_base_url)
    elif not employee and not text.startswith('/'):
        # کاربر ناشناس و پیام متنی
        contact_message = (
            "لطفاً با /start شروع کنید یا برای فعال‌سازی با مدیر تماس بگیرید.\n"
            f"شناسه بله شما: `{chat_id}`"
        )
        send_message(chat_id, contact_message, api_base_url)
