"""Khởi chạy ứng dụng: python main.py"""
import database
from gui import App

if __name__ == "__main__":
    database.init_db()
    App().mainloop()
