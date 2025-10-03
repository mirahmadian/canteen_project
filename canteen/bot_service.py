import json
import logging
from datetime import date, timedelta
import requests
from sqlalchemy.orm.exc import NoResultFound
# توجه: ایمپورت telegram از این خط حذف شد.
from .models import db, Employee, DailyMenu, Reservation 

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
# ۲. توابع کمکی ادمین
# ===============================================

def get_admin_keyboard():
    """کیبورد پنل ادمین."""
    return [
        ['/list_employees', '/add_employee'],
        ['/manage_menu', '/report'],
        ['/settings']
    ]

def send_admin_menu(chat_id, api_base_url):
    """ارسال منوی اصلی ادمین."""
    text = "به پنل مدیریت سامانه رزرو سلف خوش آمدید. لطفاً یکی از گزینه‌ها را انتخاب کنید:"
    keyboard = get_admin_keyboard()
    send_message(chat_id, text, api_base_url, reply_markup=keyboard)

# ===============================================
# ۳. منطق مدیریت کارمندان (جدید)
# ===============================================

def handle_list_employees(chat_id, api_base_url):
    """نمایش لیست تمام کارمندان."""
    employees = Employee.query.all()
    
    if not employees:
        text = "در حال حاضر هیچ کارمندی در سیستم ثبت نشده است."
    else:
        text = "👥 **لیست کارمندان ثبت‌شده:**\n"
        for emp in employees:
            admin_status = "(ادمین)" if emp.is_admin else ""
            bale_id_display = f"ID: `{emp.bale_id}`" if emp.bale_id else "ID: (نامشخص)"
            text += f"- **{emp.full_name}** {admin_status}\n"
            text += f"  کد ملی: {emp.national_id}, تلفن: {emp.phone_number}\n"
            text += f"  {bale_id_display}\n"
        
    send_message(chat_id, text, api_base_url)

def handle_add_employee(chat_id, api_base_url):
    """شروع فرآیند افزودن کارمند جدید (گام ۱)."""
    text = (
        "➕ **افزودن کارمند جدید**\n"
        "لطفاً اطلاعات کارمند را در قالب زیر و در **یک پیام** ارسال کنید:\n\n"
        "`کد ملی | شماره تلفن | نام کامل | شناسه بله (اختیاری)`\n\n"
        "**مثال:** `0012345678 | 09123456789 | علی احمدی | 987654321`"
    )
    send_message(chat_id, text, api_base_url)

def handle_add_employee_data(chat_id, text_data, api_base_url):
    """پردازش داده‌های ورودی برای افزودن کارمند."""
    try:
        parts = [p.strip() for p in text_data.split('|')]
        
        # بررسی حداقل ۳ قسمت (کد ملی، تلفن، نام)
        if len(parts) < 3:
            raise ValueError("ورودی ناقص است. حداقل کد ملی، شماره تلفن و نام کامل لازم است.")
        
        national_id = parts[0]
        phone_number = parts[1]
        full_name = parts[2]
        # شناسه بله اختیاری است
        bale_id = parts[3] if len(parts) > 3 and parts[3] else None

        # اعتبارسنجی ساده
        if not national_id.isdigit() or len(national_id) != 10:
            raise ValueError("کد ملی باید ۱۰ رقم باشد.")
        
        # بررسی وجود کارمند قبلی بر اساس کد ملی
        if Employee.query.filter_by(national_id=national_id).first():
            send_message(chat_id, "⚠️ **خطا:** کارمندی با این کد ملی قبلاً ثبت شده است.", api_base_url)
            return

        # ایجاد کارمند جدید
        new_employee = Employee(
            national_id=national_id,
            phone_number=phone_number,
            full_name=full_name,
            bale_id=bale_id,
            is_admin=False # کارمند جدید به طور پیش‌فرض ادمین نیست
        )
        
        db.session.add(new_employee)
        db.session.commit()

        success_msg = f"✅ **کارمند جدید با موفقیت افزوده شد:**\n"
        success_msg += f"نام: {full_name}\nکد ملی: {national_id}\n"
        if bale_id:
             success_msg += f"شناسه بله: `{bale_id}`"

        send_message(chat_id, success_msg, api_base_url)

    except ValueError as e:
        send_message(chat_id, f"❌ **خطای ورودی:** {e}\nلطفاً دوباره امتحان کنید.", api_base_url)
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding employee: {e}")
        send_message(chat_id, f"❌ **خطای سیستمی:** متاسفانه مشکلی در ذخیره اطلاعات پیش آمد.", api_base_url)


# ===============================================
# ۴. پردازش ورودی و فرمان‌ها
# ===============================================

def handle_admin_commands(chat_id, command, text, api_base_url):
    """مدیریت فرمان‌های خاص ادمین."""
    if command == '/admin_menu':
        send_admin_menu(chat_id, api_base_url)
    elif command == '/list_employees':
        handle_list_employees(chat_id, api_base_url)
    elif command == '/add_employee':
        handle_add_employee(chat_id, api_base_url)
    else:
        # اگر فرمان ادمین دیگری به صورت متنی (غیر از فرمان‌های کیبورد) باشد،
        # مثلاً اطلاعات کارمند پس از /add_employee
        if '|' in text:
            # فعلاً فرض می‌کنیم هر متنی که شامل '|' باشد، داده کارمند است.
            # در آینده با استفاده از "State" می‌توان این بخش را دقیق‌تر کرد.
            handle_add_employee_data(chat_id, text, api_base_url)
        else:
             send_admin_menu(chat_id, api_base_url)


def handle_text_message(chat_id, text, employee, api_base_url):
    """مدیریت پیام‌های متنی غیرفرمانی."""
    
    # اگر کاربر ادمین است، ابتدا ببینیم آیا ورودی مربوط به فرآیند ادمین است یا خیر.
    if employee and employee.is_admin:
        # فعلاً فرض می‌کنیم اگر متن ورودی دارای '|' بود، ورودی داده کارمند است.
        if '|' in text:
            handle_add_employee_data(chat_id, text, api_base_url)
            return
        
    # اگر کاربر عادی است یا ادمین نبود
    welcome_message = (
        f"👋 سلام {employee.full_name} عزیز!\n"
        "شما به سامانه رزرو غذای سلف خوش آمدید.\n"
        "فعلاً فقط می‌توانید با دستورات زیر کار کنید:\n"
        "/menu - برای مشاهده منوی روز و رزرو غذا"
    )
    send_message(chat_id, welcome_message, api_base_url)


def handle_start_command(chat_id, employee, api_base_url):
    """مدیریت فرمان /start."""
    
    if employee:
        # کاربر ثبت شده است
        if employee.is_admin:
             send_admin_menu(chat_id, api_base_url)
        else:
            # کاربر عادی
            welcome_message = (
                f"👋 سلام {employee.full_name} عزیز!\n"
                "شما به سامانه رزرو غذای سلف خوش آمدید.\n"
                "از دستور /menu برای رزرو غذا استفاده کنید."
            )
            send_message(chat_id, welcome_message, api_base_url)
    else:
        # کاربر ثبت نشده است - درخواست تماس با مدیر
        # (قبلاً شناسه بله در اینجا لاگ می‌شد، الان مستقیماً به کاربر نشان می‌دهیم)
        contact_message = (
            "به ربات رزرو غذای سلف خوش آمدید.\n"
            "برای فعال‌سازی حساب کاربری خود، لطفاً با مدیر سیستم تماس بگیرید.\n"
            f"شناسه بله شما: `{chat_id}`"
        )
        send_message(chat_id, contact_message, api_base_url)


def process_webhook_request(update, api_base_url):
    """تابع اصلی پردازش به‌روزرسانی‌های بله."""
    
    if 'message' not in update:
        # اگر به‌روزرسانی پیام نیست (مثلاً CallBackQuery)، نادیده بگیرید
        return

    message = update['message']
    chat_id = message['chat']['id']
    user_id = message['from']['id'] 
    
    # اگر پیام متنی نیست، نادیده بگیرید
    if 'text' not in message:
        return

    text = message['text'].strip()
    logger.info(f"Received message from user {user_id} in chat {chat_id}: {text}")

    # ۱. جستجوی کارمند
    employee = Employee.query.filter_by(bale_id=user_id).first()
    
    # ۲. پردازش فرمان‌ها
    if text.startswith('/'):
        command = text.split()[0]
        
        if command == '/start':
            handle_start_command(chat_id, employee, api_base_url)
            return
        
        # اگر کاربر ادمین است و فرمان ادمین ارسال کرده است
        if employee and employee.is_admin:
            # تمام فرمان‌های ادمین در اینجا مدیریت می‌شوند
            handle_admin_commands(chat_id, command, text, api_base_url)
            return

    # ۳. اگر فرمان ادمین نیست یا کاربر ادمین نیست، به پردازش متن می‌رویم
    if employee and not text.startswith('/'):
        handle_text_message(chat_id, text, employee, api_base_url)
    elif not employee and not text.startswith('/'):
        # کاربر ناشناس و پیام متنی
        handle_start_command(chat_id, employee, api_base_url) # دوباره پیام خوش‌آمدگویی را نشان دهید
