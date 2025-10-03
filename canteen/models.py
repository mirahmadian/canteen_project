# canteen/models.py

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, time

# این آبجکت db در فایل app.py مقداردهی اولیه خواهد شد
db = SQLAlchemy()

# --- Models ---

class Employee(db.Model):
    """مدل کارمندان شامل ادمین‌ها و کاربران عادی."""
    __tablename__ = 'employees'

    id = db.Column(db.Integer, primary_key=True)
    bale_id = db.Column(db.String(32), unique=True, nullable=False)
    national_id = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(64), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    # اصلاح حیاتی: افزایش طول برای هش‌های scrypt
    password_hash = db.Column(db.String(256), nullable=True) 

    # Relationships
    reservations = db.relationship('Reservation', backref='employee', lazy=True)

    def set_password(self, password):
        """هش کردن و تنظیم رمز عبور."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """بررسی صحت رمز عبور."""
        if not self.password_hash:
            return True
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<Employee {self.national_id}>'

class Menu(db.Model):
    """مدل منوی غذا برای هر روز خاص."""
    __tablename__ = 'menu'
    
    id = db.Column(db.Integer, primary_key=True)
    menu_date = db.Column(db.Date, unique=True, nullable=False)
    meal_name = db.Column(db.String(64), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    is_available = db.Column(db.Boolean, default=True)

    # Relationships
    reservations = db.relationship('Reservation', backref='menu', lazy=True)

    def __repr__(self):
        return f'<Menu {self.menu_date} - {self.meal_name}>'

class Reservation(db.Model):
    """مدل رزرو غذا توسط کارمندان."""
    __tablename__ = 'reservations'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    menu_id = db.Column(db.Integer, db.ForeignKey('menu.id'), nullable=False)
    reservation_date = db.Column(db.Date, default=date.today)
    is_paid = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Reservation {self.employee_id} for Menu {self.menu_id}>'