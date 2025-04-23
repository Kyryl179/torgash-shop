import os
from flask import Flask
from threading import Thread
import subprocess

app = Flask('')

@app.route('/')
def home():
    return "Бот работает!"

def run_flask():
    # Получаем порт из переменной окружения PORT, по умолчанию 8080
    port = int(os.getenv("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def run_main():
    # Запускаем main.py в отдельном процессе
    subprocess.run(["python", "main.py"])

def keep_alive():
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    main_thread = Thread(target=run_main)
    main_thread.start()

if __name__ == '__main__':
    keep_alive()
