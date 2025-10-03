# canteen/app.py

import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import date
from . import db  
from .models import Employee, Menu, Reservation 
from .bot_service import process_webhook_request 

# --- تنظیمات اپلیکیشن ---
def create_app():
    """ایجاد و پیکربندی اپلیکیشن Flask."""
    # تعیین پوشه تمپلیت به عنوان پوشه فعلی (canteen)
    app = Flask(__name__, template_folder='.') 
    
    # تنظیمات پایگاه داده PostgreSQL برای Render
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # تنظیمات سشن برای احراز هویت
    app.secret_key = os.environ.get('SECRET_KEY', 'your_fallback_secret_key_change_me')
    
    # مقداردهی اولیه SQLAlchemy
    db.init_app(app)
    
    # مقداردهی اولیه Flask-Migrate 
    migrate = Migrate(app, db)
    
    # --- مسیرهای وب اپلیکیشن ---

    @app.route('/', methods=['GET'])
    def index():
        """صفحه اصلی که به پنل ادمین هدایت می‌کند."""
        if session.get('admin_logged_in'):
            return redirect(url_for('admin_panel'))
        return redirect(url_for('admin_login'))

    @app.route('/login', methods=['GET', 'POST'])
    def admin_login():
        """صفحه ورود برای ادمین."""
        if 'admin_logged_in' in session:
            return redirect(url_for('admin_panel'))

        if request.method == 'POST':
            national_id = request.form.get('national_id')
            password = request.form.get('password')

            # جستجوی کارمند با کد ملی و ادمین بودن
            # از .all() استفاده می کنیم و سپس عنصر اول را می گیریم تا با مشکل کوتیشن در Build Command تداخل نداشته باشد.
            # اگرچه در زمان اجرا این روش کمی متفاوت است اما برای رفع تداخل کوتیشن ها لازم است.
            employee = db.session.execute(
                db.select(Employee).filter_by(national_id=national_id, is_admin=True)
            ).scalar_one_or_none()
            
            # بررسی رمز عبور
            if employee and employee.check_password(password):
                session['admin_logged_in'] = True
                session['admin_id'] = employee.id
                return redirect(url_for('admin_panel'))
            else:
                return render_template('admin_login.html', error='کد ملی یا رمز عبور اشتباه است.')

        return render_template('admin_login.html')

    @app.route('/admin')
    def admin_panel():
        """داشبورد اصلی ادمین."""
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))

        # فرض می کنیم این تمپلیت وجود دارد
        return render_template('admin_panel.html', current_page='dashboard')

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
                response_text = process_webhook_request(data, db) 
                return jsonify({"status": "ok", "message": response_text})
            return jsonify({"status": "error", "message": "No data received"}), 400
        except Exception as e:
            app.logger.error(f"Error processing webhook: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    return app

# این خط توسط Gunicorn استفاده می‌شود:
app = create_app()

# فقط برای اجرای محلی 
if __name__ == '__main__':
    app.run(debug=True)
