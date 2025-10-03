# setup_db.py
# این اسکریپت وظیفه ساخت جداول دیتابیس و درج کارمند ادمین را بر عهده دارد.
import os
import sys

# اطمینان از اینکه پایتون می تواند ماژول های محلی را پیدا کند
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    # وارد کردن ماژول ها از داخل پوشه canteen
    from canteen.app import create_app
    from canteen.models import Employee, db

    app = create_app()
    
    # اجرای دستورات در App Context
    with app.app_context():
        print("Creating all database tables...")
        db.create_all()
        print("Database tables created successfully.")

        # بررسی و درج ادمین پیش فرض
        admin_id = "0000000000"
        admin_employee = db.session.execute(
            db.select(Employee).filter_by(national_id=admin_id)
        ).scalar_one_or_none()
        
        if not admin_employee:
            print(f"Adding default admin: {admin_id}")
            admin_employee = Employee(
                bale_id='1807093505', 
                national_id=admin_id, 
                name='Super Admin', 
                is_admin=True
            )
            admin_employee.set_password('admin123')
            db.session.add(admin_employee)
            db.session.commit()
            print("Default admin added successfully.")
        else:
            print("Default admin already exists.")

except Exception as e:
    print(f"--- FATAL DB SETUP ERROR ---")
    print(f"Error: {e}")
    sys.exit(1)
