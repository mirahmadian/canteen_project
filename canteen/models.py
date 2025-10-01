from .__init__ import db
from datetime import datetime, date
from sqlalchemy.schema import UniqueConstraint

class Employee(db.Model):
    """جدول کارمندان و پرسنل."""
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    national_id = db.Column(db.String(10), unique=True, nullable=False) # کدملی: شناسه اصلی
    phone_number = db.Column(db.String(11), unique=True, nullable=False) # شماره تلفن: برای احراز هویت بله
    full_name = db.Column(db.String(100))
    unit = db.Column(db.String(50)) # محل خدمت
    is_manager = db.Column(db.Boolean, default=False) # آیا این شخص مدیر است؟
    
    reservations = db.relationship("Reservation", back_populates="employee")

class AdminUser(db.Model):
    """جدول کاربران ادمین پنل (مدیران سیستم، اپراتورها)."""
    __tablename__ = 'admin_users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='Operator') # SuperAdmin, Operator
    
    assigned_managers = db.relationship("ManagerAssignment", foreign_keys='ManagerAssignment.admin_id', back_populates="admin_user")

class DailyMenu(db.Model):
    """جدول منوی غذای روزانه."""
    __tablename__ = 'daily_menu'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False)
    meal_1 = db.Column(db.String(100), nullable=False)
    meal_2 = db.Column(db.String(100))
    meal_3 = db.Column(db.String(100))
    is_canceled = db.Column(db.Boolean, default=False) # لغو اضطراری/تعطیلی

class Reservation(db.Model):
    """جدول رزروهای غذا توسط کارمندان."""
    __tablename__ = 'reservations'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    
    reservation_date = db.Column(db.Date, nullable=False) 
    selected_meal = db.Column(db.String(100), nullable=False) 
    
    # وضعیت: Reserved, Print_Attempt, Served/Printed
    status = db.Column(db.String(20), default='Reserved') 
    print_attempts = db.Column(db.Integer, default=0) # کنترل سوءاستفاده
    
    employee = db.relationship("Employee", back_populates="reservations")
    
    __table_args__ = (
        # تضمین می‌کند که هر کارمند فقط یک رزرو برای یک تاریخ خاص داشته باشد.
        UniqueConstraint('employee_id', 'reservation_date', name='uq_employee_date'),
    )

class ManagerAssignment(db.Model):
    """تخصیص مدیران به یک اپراتور/آبدارچی خاص."""
    __tablename__ = 'manager_assignment'
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin_users.id'), nullable=False) # آبدارچی/اپراتور
    manager_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False) # مدیر تحت پوشش
    
    admin_user = db.relationship("AdminUser", foreign_keys=[admin_id])
    manager = db.relationship("Employee", foreign_keys=[manager_id])

class SystemConfig(db.Model):
    """جدول متغیرهای سیستمی قابل تنظیم توسط ادمین."""
    __tablename__ = 'system_config'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False) # مثال: RESERVATION_END_HOUR
    value = db.Column(db.String(50))
    
    
class Holiday(db.Model):
    """جدول روزهای تعطیل ثبت شده."""
    __tablename__ = 'holidays'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False)
    description = db.Column(db.String(100))