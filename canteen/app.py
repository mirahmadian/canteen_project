# canteen/app.py

import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import date
from . import db  # ایمپورت شی db از فایل __init__.py
from .models import Employee, Menu, Reservation # ایمپورت مدل‌ها
from .bot_service import process_webhook_request

# --- تنظیمات اپلیکیشن ---
def create_app():
    app = Flask(__name__, template_folder='.')
    
    # تنظیمات پایگاه داده PostgreSQL برای Render
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL').replace('postgres://', 'postgresql://')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # تنظیمات سشن برای احراز هویت
    app.secret_key = os.environ.get('SECRET_KEY', 'your_fallback_secret_key_change_me')
    
    # مقداردهی اولیه SQLAlchemy
    db.init_app(app)
    
    # مقداردهی اولیه Flask-Migrate (اختیاری برای مدیریت دیتابیس)
    migrate = Migrate(app, db)
    
    # --- مسیرهای وب اپلیکیشن ---

    @app.route('/', methods=['GET'])
    def index():
        """صفحه اصلی که به پنل ادمین هدایت می‌کند."""
        return redirect(url_for('admin_login'))

    @app.route('/login', methods=['GET', 'POST'])
    def admin_login():
        """صفحه ورود برای ادمین."""
        if 'admin_logged_in' in session:
            return redirect(url_for('admin_panel'))

        if request.method == 'POST':
            national_id = request.form.get('national_id')
            password = request.form.get('password')

            employee = Employee.query.filter_by(national_id=national_id, is_admin=True).first()
            
            if employee and employee.check_password(password):
                session['admin_logged_in'] = True
                session['admin_id'] = employee.id
                return jsonify({'success': True, 'redirect_url': url_for('admin_panel')})
            else:
                return jsonify({'success': False, 'message': 'کد ملی یا رمز عبور اشتباه است.'})

        return render_template('admin_login.html')

    @app.route('/admin')
    def admin_panel():
        """داشبورد اصلی ادمین."""
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))

        # در این مرحله فقط UI را نمایش می‌دهیم. منطق داده‌ها در مراحل بعد اضافه می‌شود.
        return render_template('admin_panel.html')

    @app.route('/logout')
    def admin_logout():
        """خروج ادمین."""
        session.pop('admin_logged_in', None)
        session.pop('admin_id', None)
        return redirect(url_for('admin_login'))

    # --- مسیر وب‌هوک بله ---

    @app.route('/bale_webhook', methods=['POST'])
    def bale_webhook():
        """دریافت پیام‌های دریافتی از ربات بله."""
        try:
            data = request.json
            if data:
                response_text = process_webhook_request(data)
                return jsonify({"status": "ok", "message": response_text})
            return jsonify({"status": "error", "message": "No data received"}), 400
        except Exception as e:
            app.logger.error(f"Error processing webhook: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    # --- توابع مدیریت دیتابیس ---

    def init_db():
        """ایجاد دیتابیس و اضافه کردن ادمین پیش‌فرض در صورت نبود."""
        with app.app_context():
            db.create_all()
            
            # بررسی وجود ادمین پیش‌فرض (کد ملی 0000000000)
            admin_bale_id = os.environ.get('SUPER_ADMIN_BALE_ID', '1807093505') # شناسه بله واقعی شما
            
            # اگر ادمین با این کد ملی (0000000000) وجود ندارد، ایجادش کن
            if Employee.query.filter_by(national_id='0000000000').first() is None:
                # رمز عبور پیش‌فرض: admin123
                admin_employee = Employee(
                    bale_id=admin_bale_id,
                    national_id='0000000000',
                    name='Super Admin',
                    is_admin=True
                )
                admin_employee.set_password('admin123')
                db.session.add(admin_employee)
                db.session.commit()
                print("--- Super Admin Created ---")
    
    # دیتابیس را در زمان اجرای برنامه ایجاد می‌کند
    init_db()

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)