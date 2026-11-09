"""Khởi chạy ứng dụng: python main.py"""
import Data.database as database
from GUI.gui import App

if __name__ == "__main__":
    database.init_db()
    App().mainloop()
