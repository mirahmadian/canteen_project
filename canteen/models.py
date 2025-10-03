# canteen/models.py

from . import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# مدل کارمند (Employee)
# شامل مشخصات کارمند و منطق احراز هویت برای ادمین
class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    bale_id = db.Column(db.String(20), unique=True, nullable=False, index=True) # شناسه بله کاربر
    national_id = db.Column(db.String(10), unique=True, nullable=True, index=True) # کد ملی (برای ورود ادمین)
    name = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    # فیلد ذخیره رمز عبور هش شده (فقط برای ادمین)
    password_hash = db.Column(db.String(128), nullable=True) 
    
    # ارتباط با رزروها
    reservations = db.relationship('Reservation', backref='employee', lazy=True)

    def set_password(self, password):
        """هش کردن و ذخیره رمز عبور ادمین"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """بررسی رمز عبور وارد شده با رمز هش شده"""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<Employee {self.name} - Bale ID: {self.bale_id}>'

# مدل منوی غذا (Menu)
# برای تعریف غذاهای قابل رزرو در یک تاریخ خاص
class Menu(db.Model):
    __tablename__ = 'menus'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True, index=True) # تاریخ منو
    meal_name = db.Column(db.String(100), nullable=False) # نام غذا
    price = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # ارتباط با رزروها
    reservations = db.relationship('Reservation', backref='menu', lazy=True)

    def __repr__(self):
        return f'<Menu {self.meal_name} on {self.date}>'

# مدل رزرو غذا (Reservation)
# برای ثبت رزروهای انجام شده توسط کارمندان
class Reservation(db.Model):
    __tablename__ = 'reservations'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False, index=True)
    menu_id = db.Column(db.Integer, db.ForeignKey('menus.id'), nullable=False, index=True)
    reservation_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # اطمینان از اینکه هر کارمند برای هر منو فقط یک بار رزرو کند
    __table_args__ = (db.UniqueConstraint('employee_id', 'menu_id', name='_employee_menu_uc'),)

    def __repr__(self):
        return f'<Reservation by {self.employee_id} for Menu {self.menu_id}>'