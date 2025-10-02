from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# ===============================================
# ۱. مدل Employee (کارمند)
# ===============================================
class Employee(db.Model):
    __tablename__ = 'employees'
    
    # ستون‌های اصلی
    id = db.Column(db.Integer, primary_key=True)
    
    # ⬅️ اصلاح کلیدی: افزودن ستون bale_id
    # این ستون برای شناسایی کاربر بله در دیتابیس لازم است.
    bale_id = db.Column(db.String(50), unique=True, nullable=True) 
    
    national_id = db.Column(db.String(10), unique=True, nullable=False)
    phone_number = db.Column(db.String(15), unique=True, nullable=True) # برای اتصال به بله
    full_name = db.Column(db.String(100), nullable=False)
    
    # ستون مورد نیاز برای نقش ادمین
    is_admin = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f"<Employee {self.full_name} ({self.national_id})>"

# ===============================================
# ۲. مدل DailyMenu (منوی روزانه)
# ===============================================
class DailyMenu(db.Model):
    __tablename__ = 'daily_menus'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False)
    meal_1 = db.Column(db.String(100), nullable=False)
    meal_2 = db.Column(db.String(100), nullable=False)
    meal_3 = db.Column(db.String(100), nullable=True)
    
    reservations = db.relationship('Reservation', backref='menu', lazy=True)

    def __repr__(self):
        return f"<DailyMenu {self.date}>"

# ===============================================
# ۳. مدل Reservation (رزرو غذا)
# ===============================================
class Reservation(db.Model):
    __tablename__ = 'reservations'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # کلید خارجی برای کارمند
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    
    # کلید خارجی برای منو (روز)
    menu_id = db.Column(db.Integer, db.ForeignKey('daily_menus.id'), nullable=False)
    
    # انتخاب غذا (1، 2، یا 3)
    selected_meal = db.Column(db.Integer, nullable=False) # 1: meal_1, 2: meal_2, 3: meal_3
    
    reserved_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_cancelled = db.Column(db.Boolean, default=False)

    # تضمین می‌کند که یک کارمند فقط یک بار برای یک روز رزرو کند
    __table_args__ = (
        db.UniqueConstraint('employee_id', 'menu_id', name='_employee_menu_uc'),
    )

    def __repr__(self):
        return f"<Reservation EID:{self.employee_id} MID:{self.menu_id} Meal:{self.selected_meal}>"
