import os
import logging
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from .bot_service import process_webhook_request
# توجه: تمام منطق مربوط به مدل‌ها در models.py است.
from .models import db, Employee, DailyMenu, Reservation 

# ===============================================
# ۱. تنظیمات اولیه Flask
# ===============================================

app = Flask(__name__)

# تنظیمات دیتابیس: استفاده از SQLite در محیط توسعه و متغیر محیطی در محیط Production
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///canteen.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_key_very_secret_123')

# تنظیمات لاگینگ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===============================================
# ۲. پیکربندی دیتابیس و مدل‌ها
# ===============================================

db.init_app(app)

# 🔔 شناسه بله ادمین اصلی
# این مقدار باید توسط متغیر محیطی تنظیم شود یا به صورت دستی با شناسه بله واقعی شما جایگزین شود.
SUPER_ADMIN_BALE_ID = os.environ.get('SUPER_ADMIN_BALE_ID', '1807093505')

def init_db():
    """ایجاد دیتابیس و اضافه کردن کاربر ادمین اصلی در صورت عدم وجود."""
    with app.app_context():
        # اگر دیتابیس وجود ندارد، آن را ایجاد کن.
        if not os.path.exists('canteen.db') and app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite'):
             logger.info("Initializing SQLite database.")
        
        # در صورت استفاده از دیتابیس خارجی، این خط جدول‌ها را ایجاد می‌کند.
        db.create_all()

        # بررسی وجود ادمین اصلی (با استفاده از یک کد ملی ثابت برای شناسایی)
        super_admin_national_id = '0000000000' 
        admin_employee = Employee.query.filter_by(national_id=super_admin_national_id).first()
        
        if not admin_employee:
            logger.info("Creating Super Admin user...")
            # رمز عبور پیش‌فرض: 'admin123'
            admin_employee = Employee(
                national_id=super_admin_national_id,
                phone_number='09120000000',
                full_name='مدیر اصلی سیستم',
                bale_id=SUPER_ADMIN_BALE_ID, # شناسه بله واقعی شما
                is_admin=True,
                password_hash=generate_password_hash(os.environ.get('ADMIN_PASSWORD', 'admin123')) # رمز عبور برای ورود به وب
            )
            db.session.add(admin_employee)
            db.session.commit()
            logger.info("Super Admin user created successfully.")
        else:
            # اطمینان از به روز بودن شناسه بله و نقش ادمین
            if admin_employee.bale_id != SUPER_ADMIN_BALE_ID:
                 admin_employee.bale_id = SUPER_ADMIN_BALE_ID
                 db.session.commit()
            if not admin_employee.is_admin:
                 admin_employee.is_admin = True
                 db.session.commit()

init_db()

# ===============================================
# ۳. مسیرهای وب (پنل ادمین)
# ===============================================

@app.route('/')
def index():
    """صفحه خوش آمدگویی یا هدایت به ادمین."""
    return redirect(url_for('admin_login'))

@app.route('/login', methods=['GET', 'POST'])
def admin_login():
    """صفحه ورود ادمین."""
    if 'admin_logged_in' in session:
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        national_id = request.form.get('national_id')
        password = request.form.get('password')
        
        employee = Employee.query.filter_by(national_id=national_id, is_admin=True).first()

        if employee and check_password_hash(employee.password_hash, password):
            session['admin_logged_in'] = True
            session['admin_id'] = employee.id
            session['admin_name'] = employee.full_name
            return redirect(url_for('admin_dashboard'))
        else:
            error = "کد ملی یا رمز عبور اشتباه است."
            return render_template('admin_login.html', error=error) 

    return render_template('admin_login.html')

@app.route('/admin')
def admin_dashboard():
    """پنل اصلی ادمین (نیازمند احراز هویت)."""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    # اینجا admin_panel.html را رندر می‌کنیم
    return render_template('admin_panel.html', admin_name=session.get('admin_name', 'مدیر'))


@app.route('/logout')
def admin_logout():
    """خروج از پنل ادمین."""
    session.pop('admin_logged_in', None)
    session.pop('admin_id', None)
    session.pop('admin_name', None)
    return redirect(url_for('admin_login'))

# ===============================================
# ۴. مسیر وب‌هوک (ربات بله)
# ===============================================

@app.route('/webhook', methods=['POST'])
def webhook():
    """دریافت به‌روزرسانی‌ها از API بله."""
    if request.method == 'POST':
        update = request.get_json()
        
        # 🔔 آدرس Base API بله برای ارسال پاسخ
        # این مقدار باید از متغیر محیطی BALE_API_BASE_URL تامین شود
        bale_api_base_url = os.environ.get('BALE_API_BASE_URL')
        
        if not bale_api_base_url:
            logger.error("BALE_API_BASE_URL environment variable is not set.")
            return jsonify({'status': 'error', 'message': 'API base URL missing'}), 500

        # پردازش درخواست در bot_service
        process_webhook_request(update, bale_api_base_url)
        
        return jsonify({'status': 'ok'})
    return 'Method Not Allowed', 405

if __name__ == '__main__':
    # این فقط برای تست محلی است و در Render استفاده نمی‌شود.
    app.run(debug=True)
