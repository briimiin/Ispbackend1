import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "yoursecretkey")
    SQLALCHEMY_DATABASE_URI = 'sqlite:///isp.db'  # Use SQLite for local testing, replace with production DB URI
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "yourjwtsecret")
