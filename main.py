import logging
import telebot
from telebot import types
import requests
import os
import json
import time
import threading

# Налаштування логів
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Google Drive константа для изображения
GOOGLE_DRIVE_IMAGE_FILE_ID = "1NQ1NTISffzIxRiMjRO5jYKmt227JjIEU"  # FILE_ID для изображения меню
TEMP_IMAGE_PATH = "menu_image.jpg"  # Временный путь для изображения

# URL для JSON с Gist
PRODUCTS_JSON_URL = "https://gist.githubusercontent.com/Kyryl179/78cb30587280a696559e6d71e1268e32/raw"

# Глобальный словарь товаров
PRODUCTS = {}

# Функция для скачивания файла с Google Drive
def download_google_drive_file(file_id, output_file):
    """Скачивание файла с Google Drive по file_id."""
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    session = requests.Session()
    response = session.get(url, stream=True)

    if "confirm" in response.url:
        confirm_token = response.url.split("confirm=")[1].split("&")[0]
        url = f"https://drive.google.com/uc?export=download&id={file_id}&confirm={confirm_token}"
        response = session.get(url, stream=True)

    if response.status_code == 200:
        with open(output_file, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        logger.info(f"Файл успешно сохранён как {output_file}")
        return True
    else:
        logger.error(f"Ошибка при скачивании файла: {response.status_code}")
        return False

# Функция для загрузки JSON с Gist
def load_products():
    """Загрузка товаров из JSON с Gist."""
    global PRODUCTS
    try:
        response = requests.get(PRODUCTS_JSON_URL)
        if response.status_code == 200:
            PRODUCTS = response.json()
            logger.info("JSON товаров успешно загружен")
            return True
        else:
            logger.error(f"Ошибка при загрузке JSON: {response.status_code}")
            return False
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка парсинга JSON: {e}")
        return False
    except Exception as e:
        logger.error(f"Ошибка при загрузке JSON: {e}")
        return False

# Функция для периодической проверки и обновления товаров
def periodic_product_update():
    """Периодическая проверка и обновление товаров каждые 5 минут."""
    while True:
        logger.info("Проверка обновлений JSON...")
        if load_products():
            logger.info("Товары обновлены автоматически")
        else:
            logger.warning("Не удалось обновить товары")
        time.sleep(300)  # 5 минут (300 секунд)

# Инициализация товаров при запуске
if not load_products():
    logger.error("Не удалось загрузить товары. Бот будет работать без товаров.")

# Запуск фоновой задачи для обновления товаров
threading.Thread(target=periodic_product_update, daemon=True).start()

CATEGORY_NAMES = {
    "liquid": "Рідини",
    "pod": "Поди",
    "disposable": "Одноразки",
    "snus": "Снюс"
}

TOKEN = "8015483044:AAFH7_eaL_ZMjya0hh8DbL2eXtcBnlx6Dc0"
bot = telebot.TeleBot(TOKEN)
logger.info(f"TOKEN: {repr(TOKEN)}")

# Дані користувачів
user_data = {}

def init_user(user_id):
    """Ініціалізація даних користувача."""
    if user_id not in user_data:
        user_data[user_id] = {"last_message_id": None, "current_category": None}

def delete_last_message(user_id, chat_id):
    """Видалення останнього повідомлення користувача."""
    msg_id = user_data[user_id].get("last_message_id")
    if msg_id:
        try:
            bot.delete_message(chat_id, msg_id)
            logger.info(f"Повідомлення {msg_id} видалено для користувача {user_id}")
        except Exception as e:
            logger.warning(f"Не вдалося видалити повідомлення {msg_id}: {e}")
        finally:
            user_data[user_id]["last_message_id"] = None

@bot.message_handler(commands=['start'])
def handle_start(message):
    """Обробка команди /start."""
    user_id = message.from_user.id
    chat_id = message.chat.id
    init_user(user_id)
    delete_last_message(user_id, chat_id)

    if not PRODUCTS:
        msg = bot.send_message(chat_id, "⚠️ Помилка: товари не завантажено. Спробуйте пізніше або зв'яжіться з адміністратором.")
        user_data[user_id]["last_message_id"] = msg.message_id
        logger.warning(f"Користувач {user_id} запустив бота, але товари не завантажено")
        return

    # Створення клавіатури для категорій
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    for key, name in CATEGORY_NAMES.items():
        if key in PRODUCTS:
            keyboard.add(types.InlineKeyboardButton(name, callback_data=f"category_{key}"))

    # Скачивание изображения с Google Drive
    try:
        if download_google_drive_file(GOOGLE_DRIVE_IMAGE_FILE_ID, TEMP_IMAGE_PATH):
            with open(TEMP_IMAGE_PATH, "rb") as img_file:
                msg = bot.send_photo(chat_id, photo=img_file, caption=f"Привіт, {message.from_user.first_name}! Обери категорію:", reply_markup=keyboard)
            os.remove(TEMP_IMAGE_PATH)
            logger.info(f"Временный файл {TEMP_IMAGE_PATH} удалён")
        else:
            raise Exception("Не удалось скачать изображение с Google Drive")
    except Exception as e:
        logger.error(f"Помилка відправки зображення: {e}")
        msg = bot.send_message(chat_id, f"Привіт, {message.from_user.first_name}! Обери категорію (зображення недоступне через помилку):", reply_markup=keyboard)

    # Додаткові інструкції для замовлення та продажу
    instructions = (
        "📦 Для замовлення товару:\n"
        "Напишіть сюди: @managerdydkashop\n\n"
        "💡 Щоб виставити свій под на продаж:\n"
        "Напишіть сюди: @managerdydkashop\n\n"
        "Наш менеджер допоможе вам з оформленням замовлення або розміщенням товару!"
    )
    bot.send_message(chat_id, instructions, parse_mode="Markdown")

    user_data[user_id]["last_message_id"] = msg.message_id
    logger.info(f"Користувач {user_id} запустив бота")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    """Обробка callback-запитів."""
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    init_user(user_id)
    delete_last_message(user_id, chat_id)
    data = call.data

    if data.startswith("category_"):
        category = data.split("_", 1)[1]
        user_data[user_id]["current_category"] = category
        show_products(chat_id, user_id, category)

    elif data.startswith("product_"):
        index = int(data.split("_", 1)[1])
        category = user_data[user_id].get("current_category")
        if category and index < len(PRODUCTS.get(category, [])):
            show_product_details(chat_id, user_id, PRODUCTS[category][index], category)
        else:
            msg = bot.send_message(chat_id, "⚠️ Товар не знайдено. Оберіть категорію ще раз.", reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("⬅ Назад", callback_data="back_to_menu")
            ))
            user_data[user_id]["last_message_id"] = msg.message_id

    elif data == "back_to_menu":
        handle_start(call.message)

    elif data == "back_to_products":
        category = user_data[user_id].get("current_category")
        if category:
            show_products(chat_id, user_id, category)
        else:
            handle_start(call.message)

def show_products(chat_id, user_id, category):
    """Відображення списку товарів у вибраній категорії."""
    if not PRODUCTS or category not in PRODUCTS:
        msg = bot.send_message(chat_id, "⚠️ Товари в цій категорії відсутні.")
        user_data[user_id]["last_message_id"] = msg.message_id
        logger.warning(f"Користувач {user_id} намагався переглянути категорію {category}, але вона порожня")
        return

    keyboard = types.InlineKeyboardMarkup()
    for i, product in enumerate(PRODUCTS.get(category, [])):
        keyboard.add(types.InlineKeyboardButton(product["name"], callback_data=f"product_{i}"))
    keyboard.add(types.InlineKeyboardButton("⬅ Назад", callback_data="back_to_menu"))
    msg = bot.send_message(chat_id, f"Товари в категорії {CATEGORY_NAMES.get(category, category)}:", reply_markup=keyboard)
    user_data[user_id]["last_message_id"] = msg.message_id
    logger.info(f"Користувач {user_id} переглядає категорію {category}")

def show_product_details(chat_id, user_id, product, category):
    """Відображення деталей товару."""
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("⬅ До товарів", callback_data="back_to_products"))
    keyboard.add(types.InlineKeyboardButton("🏠 До меню", callback_data="back_to_menu"))
    text = f"*{product['name']}*\n\n{product['description']}\nЦіна: {product['price']}"
    msg = bot.send_message(chat_id, text=text, reply_markup=keyboard, parse_mode="Markdown")
    user_data[user_id]["last_message_id"] = msg.message_id
    logger.info(f"Користувач {user_id} переглядає товар {product['name']}")

@bot.message_handler(commands=['status'])
def check_status(message):
    """Проверка, работает ли бот."""
    try:
        bot.reply_to(message, "Я активен! 🚀")
        logger.info(f"Користувач {message.from_user.id} проверил статус бота")
    except Exception as e:
        logger.error(f"Ошибка при отправке статуса: {e}")

# Запуск бота с обработкой ошибок
if __name__ == "__main__":
    logger.info("Бот запущен.")
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            logger.error(f"Ошибка во время работы бота: {e}")
            time.sleep(5)  # Задержка 5 секунд
            logger.info("Перезапуск бота...")