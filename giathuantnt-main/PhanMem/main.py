"""Khởi chạy ứng dụng: python main.py"""
import Core.database
from GUI.gui import App
from Core import database
if __name__ == "__main__":
    database.init_db()
    App().mainloop()
