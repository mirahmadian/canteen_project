from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# تعریف اپلیکیشن و دیتابیس در هسته
app = Flask(__name__)

# تنظیمات دیتابیس (همان تنظیمات app.py سابق)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///canteen_db.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_strong_secret_key_here' 

db = SQLAlchemy()
db.init_app(app)