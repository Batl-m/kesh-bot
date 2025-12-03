import asyncio
import logging
import sqlite3
import sys
import math
import io
import time
import os
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BufferedInputFile,
    URLInputFile,
    FSInputFile
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
import qrcode

# ================= КОНФИГУРАЦИЯ =================
BOT_TOKEN = "USER_BOT_TOKEN_HERE" # Токен БОТА покупателя

DEFAULT_PHOTO = "https://cdn-icons-png.flaticon.com/512/2203/2203183.png"
DB_FILE = "kokshe_prices.db" 
PHOTOS_DIR = "product_photos" 

# ================= ЛОКАЛИЗАЦИЯ (RU / KK) =================
STRINGS = {
    "ru": {
        "welcome": "👋 Я помогу найти продукты со скидками 70-95% в Кокшетау.\n\nДля начала выберите язык / Тілді таңдаңыз:",
        "send_geo": "📍 Отправить мое местоположение",
        "btn_my_location": "📍 Мое местоположение", 
        "geo_request": "Чтобы найти магазины, укажите свое местоположение (через меню).",
        "menu_title": "🛒 Главное меню",
        "btn_shops": "🏪 Магазины рядом",
        "btn_my_bookings": "📦 Мои брони",
        "btn_radius": "⚙️ Радиус",
        "btn_lang": "🇰🇿/🇷🇺 Язык",
        "btn_restart": "🔄 Перезапустить",
        "no_geo": "Сначала отправьте геопозицию или выберите город!",
        "dist_km": "км",
        "dist_m": "м",
        "items_count": "товаров",
        "select_shop": "Выберите магазин (Радиус: {radius} м):",
        "shop_empty": "В этом магазине пока нет товаров со скидкой.",
        "book_btn": "Забронировать",
        "booked_ok": "✅ Успешно! Покажите QR-код на кассе.",
        "booked_limit": "❌ У вас уже 10 активных броней.",
        "booked_fail": "Товар уже забрали, недостаточно количества или срок истек.",
        "booking_info": "Магазин: {shop}\nТовар: {product}\nЦена: {price} ₸\nГоден до: {time}",
        "my_bookings_empty": "У вас нет активных броней.",
        "active_bookings": "Выберите бронь, чтобы открыть QR-код:",
        "lang_changed": "Язык изменен на Русский 🇷🇺",
        "radius_select": "Выберите радиус поиска магазинов:",
        "radius_set": "✅ Радиус поиска установлен: {km} км",
        "qr_caption": "<b>{product}</b>\nКол-во: {qty} шт.\nИтого: {total_price} ₸\nМагазин: {shop}\nБронь до: {valid_until}\n\n<i>Покажите кассиру этот код</i>",
        "loc_option_share": "📡 Поделиться геопозицией",
        "loc_option_city": "🏙 Выбрать город",
        "choose_loc_method": "Выберите способ указания местоположения:",
        "choose_city": "Выберите город из списка:",
        "city_set": "✅ Выбран город: {city}. Геопозиция установлена в центр города.",
        "btn_back": "⬅️ Назад",
        "city_kokshe": "Кокшетау",
        "city_astana": "Астана",
        "cancel_book_btn": "❌ Отменить бронь",
        "map_shop_btn": "🗺 Показать магазин на карте",
        "booking_cancelled": "✅ Бронь отменена. Товар снова доступен для бронирования.",
        "restarted": "🔄 Бот перезапущен.",
        "qr_sold_status": "<b>СТАТУС: ПРОДАНО!</b>", 
        "qr_cancelled_status": "<b>СТАТУС: ОТМЕНЕНО!</b>",
        "qr_active_status": "<b>СТАТУС: АКТИВНО</b>",
        "available_qty": "Доступно: {qty} шт.",
        "select_qty_title": "🔢 <b>Сколько штук вы хотите забронировать?</b>",
        "btn_more_shops": "Ещё магазины (показать дальше)" # НОВАЯ КНОПКА
    },
    "kk": {
        "welcome": "Сәлем! 👋 Мен Көкшетауда 70-95% жеңілдікпен өнімдерді табуға көмектесемін.",
        "send_geo": "📍 Менің орналасқан жерім",
        "btn_my_location": "📍 Менің орналасқан жерім",
        "geo_request": "Дүкендерді табу үшін орналасқан жеріңізді көрсетіңіз.",
        "menu_title": "🛒 Басты мәзір",
        "btn_shops": "🏪 Жақын дүкендер",
        "btn_my_bookings": "📦 Менің брондарым",
        "btn_radius": "⚙️ Радиус",
        "btn_lang": "🇰🇿/🇷🇺 Тіл",
        "btn_restart": "🔄 Қайта қосу",
        "no_geo": "Алдымен геолокацияны жіберіңіз немесе қаланы таңдаңыз!",
        "dist_km": "км",
        "dist_m": "м",
        "items_count": "тауар",
        "select_shop": "Дүкенді таңдаңыз (Радиус: {radius} м):",
        "shop_empty": "Бұл дүкенде әзірге жеңілдікпен тауарлар жоқ.",
        "book_btn": "Брондау",
        "booked_ok": "✅ Сәтті! QR-кодты кассада көрсетіңіз.",
        "booked_limit": "❌ Сізде 10 белсенді бронь бар.",
        "booked_fail": "Тауар алынып қойған немесе мерзімі өткен.",
        "booking_info": "Дүкен: {shop}\nТауар: {product}\nБағасы: {price} ₸\nДейін жарамды: {time}",
        "my_bookings_empty": "Сізде белсенді броньдар жоқ.",
        "active_bookings": "QR-кодты ашу үшін броньды таңдаңыз:",
        "lang_changed": "Тіл Қазақшаға ауыстырылды 🇰🇿",
        "radius_select": "Дүкендерді іздеу радиусын таңдаңыз:",
        "radius_set": "✅ Іздеу радиусы орнатылды: {km} км",
        "qr_caption": "<b>{product}</b>\nСаны: {qty} дана.\nБарлығы: {total_price} ₸\nДүкен: {shop}\nБронь уақыты: {valid_until}\n\n<i>Кассирге көрсетіңіз</i>",
        "loc_option_share": "📡 Геолокациямен бөлісу",
        "loc_option_city": "🏙 Қаланы таңдау",
        "choose_loc_method": "Орналасқан жерді көрсету әдісін таңдаңыз:",
        "choose_city": "Тізімнен қаланы таңдаңыз:",
        "city_set": "✅ Қала таңдалды: {city}. Геолокация жаңартылды.",
        "btn_back": "⬅️ Артқа",
        "city_kokshe": "Көкшетау",
        "city_astana": "Астана",
        "cancel_book_btn": "❌ Брондауды болдырмау",
        "map_shop_btn": "🗺 Дүкенді картадан көрсету",
        "booking_cancelled": "✅ Брондау болдырылды. Өнім қайта брондауға қол жетімді.",
        "restarted": "🔄 Бот қайта іске қосылды.",
        "qr_sold_status": "<b>МӘРТЕБЕСІ: САТЫЛДЫ!</b>",
        "qr_cancelled_status": "<b>МӘРТЕБЕСІ: БОЛДЫРЫЛДЫ!</b>",
        "qr_active_status": "<b>МӘРТЕБЕСІ: БЕЛСЕНДІ</b>",
        "available_qty": "Қолжетімді: {qty} дана.",
        "select_qty_title": "🔢 <b>Қанша дана брондағыңыз келеді?</b>",
        "btn_more_shops": "Көбірек дүкендер (әрі қарай көрсету)" # НОВАЯ КНОПКА
    }
}

# Добавлен четвертый элемент: onPro (1 = включен, 0 = выключен)
SHOPS_DATA = [
    ("Arbat Market", 53.2814, 69.3785, 1), 
    ("Союз Центр", 53.2839, 69.3748, 1), 
    ("INMART Южный", 53.2690, 69.3842, 0), # НЕ onPro
    ("Союз Сарыарка", 53.2951, 69.3921, 1), 
    ("Galmart", 53.2811, 69.4045, 0), # НЕ onPro
    ("SMALL Центр", 53.2832, 69.3777, 1), 
    ("Анвар", 53.2865, 69.3689, 1), 
    ("Центральный рынок", 53.2820, 69.3823, 0), # НЕ onPro
    ("Kiwi", 53.303554, 69.391613, 1) 
]

CITIES_COORDS = {
    "kokshe": (53.2832, 69.3777),
    "astana": (51.1694, 71.4491)
}

# ================= РАБОТА С БД =================
class Database:
    def __init__(self, db_file=DB_FILE):
        self.connection = sqlite3.connect(db_file)
        self.cursor = self.connection.cursor()
        self.create_tables()
        self.seed_shops()

    def create_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                lang TEXT DEFAULT 'ru',
                lat REAL,
                lon REAL,
                radius INTEGER DEFAULT 5000
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS shops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                lat REAL,
                lon REAL,
                secret_key TEXT,
                owner_id INTEGER,
                onPro INTEGER DEFAULT 0 -- НОВАЯ КОЛОНКА
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shop_id INTEGER,
                name TEXT,
                old_price INTEGER,
                new_price INTEGER,
                expiry_time TEXT,
                photo_file_id TEXT,
                active BOOLEAN DEFAULT 1,
                quantity INTEGER DEFAULT 1, 
                FOREIGN KEY(shop_id) REFERENCES shops(id)
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                product_id INTEGER,
                valid_until TEXT,
                status TEXT DEFAULT 'active',
                booked_quantity INTEGER DEFAULT 1,
                sale_date TEXT
            )
        """)
        
        # Проверка и добавление колонки booked_quantity в bookings
        try:
            self.cursor.execute("SELECT booked_quantity FROM bookings LIMIT 1")
        except sqlite3.OperationalError:
            try:
                self.cursor.execute("ALTER TABLE bookings ADD COLUMN booked_quantity INTEGER DEFAULT 1")
                self.connection.commit()
            except: pass
            
        # Проверка и добавление колонки onPro в shops (для существующих баз)
        try:
            self.cursor.execute("SELECT onPro FROM shops LIMIT 1")
        except sqlite3.OperationalError:
            try:
                self.cursor.execute("ALTER TABLE shops ADD COLUMN onPro INTEGER DEFAULT 0")
                self.connection.commit()
            except: pass
            
        self.connection.commit()

    def seed_shops(self):
        res = self.cursor.execute("SELECT count(*) FROM shops").fetchone()
        if res[0] == 0:
            print("База пуста, добавляем магазины и тестовые товары...")
            # Теперь вставляем 4 значения, включая onPro
            for name, lat, lon, onpro_status in SHOPS_DATA:
                self.cursor.execute("INSERT INTO shops (name, lat, lon, onPro) VALUES (?, ?, ?, ?)", (name, lat, lon, onpro_status))
            
            first_shop_id = self.cursor.execute("SELECT id FROM shops LIMIT 1").fetchone()[0]
            future_date = datetime.now() + timedelta(days=2)
            formatted_date = future_date.strftime("%d.%m.%Y %H:%M")
            
            dummy_products = [
                (first_shop_id, "Хлеб Бородинский", 200, 50, formatted_date, None, 1, 5),
                (first_shop_id, "Молоко 3.2%", 450, 100, formatted_date, None, 1, 3),
            ]
            # Внимание: dummy_products имеет 8 полей, 7ой индекс - active, 8ой - quantity
            self.cursor.executemany("INSERT INTO products (shop_id, name, old_price, new_price, expiry_time, photo_file_id, active, quantity) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", dummy_products)
            self.connection.commit()

    def get_user(self, user_id):
        return self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()

    def add_or_update_user(self, user_id, lat=None, lon=None, lang=None, radius=None):
        user = self.get_user(user_id)
        if not user:
            self.cursor.execute("INSERT INTO users (user_id, lang, lat, lon, radius) VALUES (?, ?, ?, ?, 5000)", 
                                (user_id, 'ru', lat, lon))
        else:
            if lat is not None: self.cursor.execute("UPDATE users SET lat=?, lon=? WHERE user_id=?", (lat, lon, user_id))
            if lang is not None: self.cursor.execute("UPDATE users SET lang=? WHERE user_id=?", (lang, user_id))
            if radius is not None: self.cursor.execute("UPDATE users SET radius=? WHERE user_id=?", (radius, user_id))
        self.connection.commit()

    def get_shops(self):
        # ИЗМЕНЕНИЕ: Добавлен фильтр WHERE onPro = 1
        return self.cursor.execute("SELECT * FROM shops WHERE onPro = 1").fetchall()
        
    def get_shop(self, shop_id):
        # Магазины можно получать по ID, независимо от статуса onPro, 
        # чтобы получать данные для броней или карты.
        return self.cursor.execute("SELECT * FROM shops WHERE id = ?", (shop_id,)).fetchone()

    def check_products_expiry(self):
        active_products = self.cursor.execute("SELECT id, expiry_time FROM products WHERE active=1").fetchall()
        now = datetime.now()
        
        for prod in active_products:
            prod_id, expiry_str = prod
            try:
                expiry_dt = datetime.strptime(expiry_str, "%d.%m.%Y %H:%M")
                if now > expiry_dt:
                    self.cursor.execute("UPDATE products SET active=0 WHERE id=?", (prod_id,))
            except ValueError:
                pass
        self.connection.commit()

    def get_products(self, shop_id):
        self.check_products_expiry()
        # Выбираем только активные товары с количеством > 0
        return self.cursor.execute("SELECT * FROM products WHERE shop_id=? AND active=1 AND quantity > 0", (shop_id,)).fetchall()
    
    def get_product(self, prod_id):
        # Возвращает текущее состояние товара, включая его количество
        return self.cursor.execute("SELECT * FROM products WHERE id=?", (prod_id,)).fetchone()

    def count_active_bookings(self, user_id):
        now = datetime.now().isoformat()
        
        expired_bookings = self.cursor.execute("""
            SELECT id, product_id, booked_quantity FROM bookings 
            WHERE valid_until < ? AND status='active'
        """, (now,)).fetchall()

        self.cursor.execute("UPDATE bookings SET status='expired' WHERE valid_until < ? AND status='active'", (now,))
        
        for booking_id, prod_id, booked_qty in expired_bookings:
            qty_to_return = booked_qty if booked_qty else 1
            self.cursor.execute("UPDATE products SET quantity = quantity + ? WHERE id=?", (qty_to_return, prod_id)) 
            # Активируем товар, если количество стало > 0 после возврата
            self.cursor.execute("UPDATE products SET active = 1 WHERE id=? AND quantity > 0", (prod_id,))
            
        self.connection.commit()
        return self.cursor.execute("SELECT count(*) FROM bookings WHERE user_id=? AND status='active'", (user_id,)).fetchone()[0]

    def create_booking(self, user_id, product_id, quantity_to_book=1):
        prod = self.get_product(product_id)
        if not prod or prod[7] == 0 or prod[8] < quantity_to_book:
            return None, None
            
        try:
            expiry_dt = datetime.strptime(prod[5], "%d.%m.%Y %H:%M")
            if datetime.now() > expiry_dt:
                self.cursor.execute("UPDATE products SET active=0 WHERE id=?", (product_id,))
                self.connection.commit()
                return None, None
        except:
            pass

        import uuid
        booking_id = str(uuid.uuid4())[:8]
        valid_until = (datetime.now() + timedelta(minutes=35)).isoformat()
        
        try:
            self.cursor.execute("INSERT INTO bookings (id, user_id, product_id, valid_until, booked_quantity) VALUES (?, ?, ?, ?, ?)",
                                (booking_id, user_id, prod[0], valid_until, quantity_to_book))
            
            # Уменьшаем количество
            self.cursor.execute("UPDATE products SET quantity = quantity - ? WHERE id=?", (quantity_to_book, prod[0]))
            
            # Деактивируем товар, только если количество стало <= 0
            self.cursor.execute("UPDATE products SET active = 0 WHERE id=? AND quantity <= 0", (prod[0],))
            
            self.connection.commit()
            return booking_id, valid_until
        except Exception as e:
            print(f"Booking Error: {e}")
            return None, None
            
    def cancel_booking(self, booking_id):
        self.cursor.execute("SELECT product_id, booked_quantity FROM bookings WHERE id=? AND status='active'", (booking_id,))
        result = self.cursor.fetchone()
        
        if not result:
            return False, None
            
        product_id = result[0]
        qty_to_return = result[1] if result[1] else 1
        
        self.cursor.execute("UPDATE bookings SET status='cancelled' WHERE id=? AND status='active'", (booking_id,))
        
        # Возвращаем количество
        self.cursor.execute("UPDATE products SET quantity = quantity + ? WHERE id=?", (qty_to_return, product_id))
        
        # Активируем товар (так как количество гарантированно > 0)
        self.cursor.execute("UPDATE products SET active = 1 WHERE id=?", (product_id,))
        
        self.connection.commit()
        return True, product_id

    def get_user_bookings(self, user_id):
        query = """
            SELECT b.id, s.name, p.name, p.new_price, b.valid_until, p.id, b.status, b.booked_quantity
            FROM bookings b
            JOIN products p ON b.product_id = p.id
            JOIN shops s ON p.shop_id = s.id
            WHERE b.user_id = ? AND b.status = 'active'
        """
        return self.cursor.execute(query, (user_id,)).fetchall()
    
    def get_booking_details(self, booking_id):
        query = """
            SELECT b.id, s.name, p.name, p.new_price, b.valid_until, b.status, b.booked_quantity
            FROM bookings b
            JOIN products p ON b.product_id = p.id
            JOIN shops s ON p.shop_id = s.id
            WHERE b.id = ?
        """
        return self.cursor.execute(query, (booking_id,)).fetchone()

db = Database()
dp = Dispatcher()
bot = Bot(token=BOT_TOKEN)

# ================= СТЕЙТ-МАШИНА =================
class BookingState(StatesGroup):
    # Состояние для ожидания выбора количества, 
    # в FSMContext хранится ID сообщения для последующего обновления.
    waiting_for_qty = State()

# ================= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =================
def get_distance(lat1, lon1, lat2, lon2):
    R = 6371e3
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def generate_qr(data):
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    bio = io.BytesIO()
    img.save(bio)
    bio.seek(0)
    return bio

def get_text(user_id, key, **kwargs):
    user = db.get_user(user_id)
    lang = user[1] if user else 'ru'
    text = STRINGS[lang].get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text

async def update_product_card(bot: Bot, chat_id: int, message_id: int, prod_id: int, user_id: int):
    """
    Обновляет существующую карточку товара после бронирования (или отмены).
    Удаляет сообщение, если количество стало <= 0.
    """
    prod = db.get_product(prod_id)
    
    if not prod or prod[8] <= 0:
        # Товар закончился, удаляем карточку
        try: await bot.delete_message(chat_id, message_id)
        except Exception as e: print(f"Failed to delete message: {e}")
        return

    shop_details = db.get_shop(prod[1])
    shop_name = shop_details[1] if shop_details else "Магазин"
    quantity = prod[8]
    discount = int(((prod[3] - prod[4]) / prod[3]) * 100)
    
    # Формируем новое описание товара
    caption = (
        f"🏪 <b>{shop_name}</b>\n"
        f"🍞 <b>{prod[2]}</b>\n"
        f"❌ <s>{prod[3]} ₸</s> ➡️ <b>{prod[4]} ₸</b> (-{discount}%)\n"
        f"⏰ Годен до: <b>{prod[5]}</b>\n\n"
        f"{get_text(user_id, 'available_qty', qty=quantity)}"
    )
    
    # Формируем новую клавиатуру
    kb = InlineKeyboardBuilder()
    kb.button(text=get_text(user_id, 'map_shop_btn'), callback_data=f"mapshop_{prod[1]}")
    kb.button(text=f"🛒 {get_text(user_id, 'book_btn')}", callback_data=f"book_{prod[0]}")
    kb.adjust(1)
    
    try:
        # Редактируем подпись и клавиатуру
        await bot.edit_message_caption(
            chat_id=chat_id,
            message_id=message_id,
            caption=caption,
            parse_mode="HTML",
            reply_markup=kb.as_markup()
        )
    except Exception as e:
        # Может возникнуть, если сообщение слишком старое или было изменено ранее
        print(f"Error updating product card (message {message_id}): {e}")


async def display_shops_page(chat_id: int, user_id: int, page: int = 0, message_id: int = None):
    """
    Отображает список магазинов с пагинацией и сортировкой.
    ВНИМАНИЕ: Использует db.get_shops(), которая теперь возвращает ТОЛЬКО магазины onPro.
    """
    user = db.get_user(user_id)
    user_lat, user_lon = user[2], user[3]
    user_radius = user[4] if user[4] else 5000 
    
    db.check_products_expiry()

    # db.get_shops() возвращает только onPro магазины
    shops = db.get_shops()
    shops_with_dist = []
    
    for shop in shops:
        dist = get_distance(user_lat, user_lon, shop[2], shop[3])
        if dist <= user_radius:
            prods = db.get_products(shop[0])
            shops_with_dist.append((shop, dist, len(prods))) # (shop_tuple, distance, product_count)
            
    # 1. Сортировка и группировка:
    # Группа 1: Магазины с товарами, сортировка по расстоянию (ASC)
    shops_with_items = sorted([s for s in shops_with_dist if s[2] > 0], key=lambda x: x[1])
    # Группа 2: Магазины без товаров, сортировка по расстоянию (ASC)
    shops_without_items = sorted([s for s in shops_with_dist if s[2] == 0], key=lambda x: x[1])
    
    # Объединяем: сначала с товарами, потом без
    sorted_shops = shops_with_items + shops_without_items
    
    # 2. Логика пагинации
    PAGE_SIZE = 10
    start_index = page * PAGE_SIZE
    end_index = start_index + PAGE_SIZE
    
    shops_to_display = sorted_shops[start_index:end_index]
    total_shops = len(sorted_shops)

    if not sorted_shops and page == 0:
        # Если нет магазинов вообще
        await bot.send_message(chat_id, f"В радиусе {user_radius/1000} км магазинов не найдено.")
        return

    # 3. Построение клавиатуры
    builder = InlineKeyboardBuilder()
    
    for shop, dist, p_count in shops_to_display:
        dist_str = f"{dist/1000:.1f} {get_text(user_id, 'dist_km')}" if dist > 1000 else f"{int(dist)} {get_text(user_id, 'dist_m')}"
        
        # Добавляем эмодзи для лучшего UX: 🛒 если есть товары, 🚫 если нет
        emoji = "🛒 " if p_count > 0 else "🚫 "
        btn_text = f"{emoji}{shop[1]} (~{dist_str}) | {p_count} шт."
        
        builder.button(text=btn_text, callback_data=f"shop_{shop[0]}")
    
    builder.adjust(1)

    # 4. Добавление кнопки "Ещё магазины"
    if total_shops > end_index:
        builder.row(InlineKeyboardButton(text=get_text(user_id, 'btn_more_shops'), callback_data=f"next_shops_page_{page + 1}"))
    
    # 5. Отправка / Редактирование
    message_text = get_text(user_id, "select_shop", radius=int(user_radius))

    if message_id:
        # Если это колбэк, редактируем клавиатуру
        try:
            await bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=builder.as_markup()
            )
        except Exception as e:
            # Если сообщение не может быть отредактировано (например, слишком старое)
            await bot.send_message(chat_id, message_text, reply_markup=builder.as_markup())
    else:
        # Отправляем новое сообщение
        await bot.send_message(chat_id, message_text, reply_markup=builder.as_markup())


# ================= КЛАВИАТУРЫ =================
def main_kb(user_id):
# ... (Клавиатуры без изменений) ...
    lang_btn = KeyboardButton(text=get_text(user_id, "btn_lang"))
    location_btn = KeyboardButton(text=get_text(user_id, "btn_my_location"))
    shops_btn = KeyboardButton(text=get_text(user_id, "btn_shops"))
    book_btn = KeyboardButton(text=get_text(user_id, "btn_my_bookings"))
    radius_btn = KeyboardButton(text=get_text(user_id, "btn_radius"))
    restart_btn = KeyboardButton(text=get_text(user_id, "btn_restart"))
    
    return ReplyKeyboardMarkup(
        keyboard=[
            [shops_btn, book_btn], 
            [radius_btn, location_btn], 
            [lang_btn, restart_btn]
        ],
        resize_keyboard=True
    )

def location_choice_kb(user_id):
    btn1 = KeyboardButton(text=get_text(user_id, "loc_option_share"), request_location=True)
    btn3 = KeyboardButton(text=get_text(user_id, "loc_option_city"))
    btn_back = KeyboardButton(text=get_text(user_id, "btn_back"))
    
    return ReplyKeyboardMarkup(
        keyboard=[[btn1], [btn3], [btn_back]],
        resize_keyboard=True
    )

def cities_kb(user_id):
    btn_k = KeyboardButton(text=get_text(user_id, "city_kokshe"))
    btn_a = KeyboardButton(text=get_text(user_id, "city_astana"))
    btn_back = KeyboardButton(text=get_text(user_id, "btn_back"))
    
    return ReplyKeyboardMarkup(
        keyboard=[[btn_k, btn_a], [btn_back]],
        resize_keyboard=True
    )

def lang_inline():
    builder = InlineKeyboardBuilder()
    builder.button(text="Русский 🇷🇺", callback_data="set_lang_ru")
    builder.button(text="Қазақша 🇰🇿", callback_data="set_lang_kk")
    return builder.as_markup()

def radius_inline():
    builder = InlineKeyboardBuilder()
    for r in [1, 3, 5, 10, 50]:
        builder.button(text=f"{r} км", callback_data=f"set_radius_{r}")
    builder.adjust(3)
    return builder.as_markup()

def qty_selection_inline(prod_id, max_qty, user_id):
    builder = InlineKeyboardBuilder()
    limit = min(max_qty, 10)
    for i in range(1, limit + 1):
        builder.button(text=str(i), callback_data=f"confirm_book_{prod_id}_{i}")
    builder.adjust(5) 
    # Кнопка НАЗАД для отмены выбора количества
    builder.row(InlineKeyboardButton(text=get_text(user_id, "btn_back"), callback_data=f"back_booking_{prod_id}"))
    return builder.as_markup()

# ================= ХЕНДЛЕРЫ =================

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
# ... (Хендлер cmd_start без изменений) ...
    db.add_or_update_user(message.from_user.id)
    await message.answer(STRINGS['ru']['welcome'], reply_markup=lang_inline())

@dp.message(F.text.in_([STRINGS['ru']['btn_restart'], STRINGS['kk']['btn_restart']]))
async def restart_bot(message: types.Message):
# ... (Хендлер restart_bot без изменений) ...
    await message.answer(get_text(message.from_user.id, "restarted"))
    await cmd_start(message)

@dp.callback_query(F.data.startswith("set_lang_"))
async def set_language(callback: types.CallbackQuery):
# ... (Хендлер set_language без изменений) ...
    lang = callback.data.split("_")[-1]
    db.add_or_update_user(callback.from_user.id, lang=lang)
    await callback.message.delete()
    await callback.message.answer(get_text(callback.from_user.id, "lang_changed"), 
                                  reply_markup=main_kb(callback.from_user.id))
    await callback.message.answer(get_text(callback.from_user.id, "geo_request"))

@dp.message(F.text.in_(['🇰🇿/🇷🇺 Язык', '🇰🇿/🇷🇺 Тіл']))
async def change_lang_btn(message: types.Message):
# ... (Хендлер change_lang_btn без изменений) ...
    current_user = db.get_user(message.from_user.id)
    current_lang = current_user[1]
    new_lang = 'kk' if current_lang == 'ru' else 'ru'
    db.add_or_update_user(message.from_user.id, lang=new_lang)
    await message.answer(get_text(message.from_user.id, "lang_changed"), 
                         reply_markup=main_kb(message.from_user.id))

# --- ЛОГИКА ГЕОЛОКАЦИИ ---
@dp.message(F.text.in_([STRINGS['ru']['btn_my_location'], STRINGS['kk']['btn_my_location']]))
async def open_location_menu(message: types.Message):
# ... (Хендлер open_location_menu без изменений) ...
    await message.answer(get_text(message.from_user.id, "choose_loc_method"), 
                         reply_markup=location_choice_kb(message.from_user.id))

@dp.message(F.text.in_([STRINGS['ru']['loc_option_city'], STRINGS['kk']['loc_option_city']]))
async def open_cities_list(message: types.Message):
# ... (Хендлер open_cities_list без изменений) ...
    await message.answer(get_text(message.from_user.id, "choose_city"), 
                         reply_markup=cities_kb(message.from_user.id))

@dp.message(F.text.in_([STRINGS['ru']['city_kokshe'], STRINGS['kk']['city_kokshe']]))
async def set_city_kokshe(message: types.Message):
# ... (Хендлер set_city_kokshe без изменений) ...
    lat, lon = CITIES_COORDS["kokshe"]
    db.add_or_update_user(message.from_user.id, lat=lat, lon=lon)
    await message.answer(get_text(message.from_user.id, "city_set", city=message.text), 
                         reply_markup=main_kb(message.from_user.id))

@dp.message(F.text.in_([STRINGS['ru']['city_astana'], STRINGS['kk']['city_astana']]))
async def set_city_astana(message: types.Message):
# ... (Хендлер set_city_astana без изменений) ...
    lat, lon = CITIES_COORDS["astana"]
    db.add_or_update_user(message.from_user.id, lat=lat, lon=lon)
    await message.answer(get_text(message.from_user.id, "city_set", city=message.text), 
                         reply_markup=main_kb(message.from_user.id))

@dp.message(F.text.in_([STRINGS['ru']['btn_back'], STRINGS['kk']['btn_back']]))
async def back_to_main(message: types.Message):
# ... (Хендлер back_to_main без изменений) ...
    await message.answer(get_text(message.from_user.id, "menu_title"), 
                         reply_markup=main_kb(message.from_user.id))

@dp.message(F.location)
async def handle_location(message: types.Message):
# ... (Хендлер handle_location без изменений) ...
    lat = message.location.latitude
    lon = message.location.longitude
    db.add_or_update_user(message.from_user.id, lat=lat, lon=lon)
    await message.answer("📍 OK!", reply_markup=main_kb(message.from_user.id))

# --- НАСТРОЙКИ РАДИУСА ---
@dp.message(F.text.in_([STRINGS['ru']['btn_radius'], STRINGS['kk']['btn_radius']]))
async def radius_menu(message: types.Message):
# ... (Хендлер radius_menu без изменений) ...
    await message.answer(get_text(message.from_user.id, "radius_select"), reply_markup=radius_inline())

@dp.callback_query(F.data.startswith("set_radius_"))
async def set_radius_callback(callback: types.CallbackQuery):
# ... (Хендлер set_radius_callback без изменений) ...
    km = int(callback.data.split("_")[-1])
    meters = km * 1000
    db.add_or_update_user(callback.from_user.id, radius=meters)
    await callback.answer(get_text(callback.from_user.id, "radius_set", km=km), show_alert=True)
    await callback.message.delete()

# --- МАГАЗИНЫ И ТОВАРЫ ---
@dp.message(F.text.in_([STRINGS['ru']['btn_shops'], STRINGS['kk']['btn_shops']]))
async def show_shops_nearby(message: types.Message):
    user = db.get_user(message.from_user.id)
    if not user or not user[2]: 
        await message.answer(get_text(message.from_user.id, "no_geo"))
        return

    # Вызываем новую функцию для отображения первой страницы магазинов
    await display_shops_page(message.chat.id, message.from_user.id, page=0)


@dp.callback_query(F.data.startswith("next_shops_page_"))
async def next_shops_page_callback(callback: types.CallbackQuery):
    """
    Обрабатывает нажатие кнопки "Ещё магазины" и отображает следующую страницу.
    """
    try:
        page = int(callback.data.split("_")[-1])
        # Передаем message_id для редактирования существующего сообщения (обновления клавиатуры)
        await display_shops_page(callback.message.chat.id, callback.from_user.id, page=page, message_id=callback.message.message_id)
        await callback.answer()
    except Exception as e:
        print(f"Error in next_shops_page_callback: {e}")
        await callback.answer("Ошибка при загрузке следующей страницы.", show_alert=True)


@dp.callback_query(F.data.startswith("shop_"))
async def show_products(callback: types.CallbackQuery):
# ... (Хендлер show_products без изменений) ...
    shop_id = int(callback.data.split("_")[1])
    products = db.get_products(shop_id)
    shop_details = db.get_shop(shop_id)
    shop_name = shop_details[1] if shop_details else "Магазин"
    
    if not products:
        await callback.answer(get_text(callback.from_user.id, "shop_empty"), show_alert=True)
        return

    # Удаляем сообщение со списком магазинов
    await callback.message.delete()
    
    for prod in products:
        quantity = prod[8]
        discount = int(((prod[3] - prod[4]) / prod[3]) * 100)
        
        caption = (
            f"🏪 <b>{shop_name}</b>\n"
            f"🍞 <b>{prod[2]}</b>\n"
            f"❌ <s>{prod[3]} ₸</s> ➡️ <b>{prod[4]} ₸</b> (-{discount}%)\n"
            f"⏰ Годен до: <b>{prod[5]}</b>\n\n"
            f"{get_text(callback.from_user.id, 'available_qty', qty=quantity)}"
        )
        
        kb = InlineKeyboardBuilder()
        kb.button(text=get_text(callback.from_user.id, 'map_shop_btn'), callback_data=f"mapshop_{shop_id}")
        kb.button(text=f"🛒 {get_text(callback.from_user.id, 'book_btn')}", callback_data=f"book_{prod[0]}")
        kb.adjust(1)
        
        photo = URLInputFile(DEFAULT_PHOTO)
        if prod[6] and os.path.exists(prod[6]):
            photo = FSInputFile(prod[6])
        
        await callback.message.answer_photo(
            photo=photo,
            caption=caption,
            parse_mode="HTML",
            reply_markup=kb.as_markup()
        )

@dp.callback_query(F.data.startswith("mapshop_"))
async def show_shop_on_map_callback(callback: types.CallbackQuery):
# ... (Хендлер show_shop_on_map_callback без изменений) ...
    shop_id = int(callback.data.split("_")[1])
    shop_details = db.get_shop(shop_id)
    if shop_details:
        await callback.message.answer_venue(shop_details[2], shop_details[3], shop_details[1], "Kokshetau")
        await callback.answer()
    else:
        await callback.answer("Магазин не найден", show_alert=True)

# --- ЛОГИКА БРОНИРОВАНИЯ ---

@dp.callback_query(F.data.startswith("book_"))
async def book_product(callback: types.CallbackQuery, state: FSMContext):
# ... (Хендлер book_product без изменений) ...
    user_id = callback.from_user.id
    prod_id = int(callback.data.split("_")[1])
    
    active_count = db.count_active_bookings(user_id)
    if active_count >= 10:
        await callback.answer(get_text(user_id, "booked_limit"), show_alert=True)
        return

    prod = db.get_product(prod_id)
    if not prod or prod[7] == 0 or prod[8] <= 0:
        await callback.answer(get_text(user_id, "booked_fail"), show_alert=True)
        try: await callback.message.delete()
        except: pass
        return

    # Сохраняем ID сообщения с карточкой товара для последующего редактирования
    await state.update_data(
        original_message_id=callback.message.message_id, 
        prod_id=prod_id
    )

    if prod[8] > 1:
        # Изменяем сообщение на выбор количества (сохраняем message_id)
        new_caption = callback.message.caption + "\n\n" + get_text(user_id, "select_qty_title")
        await callback.message.edit_caption(
            caption=new_caption,
            parse_mode="HTML",
            reply_markup=qty_selection_inline(prod_id, prod[8], user_id)
        )
        await callback.answer()
        await state.set_state(BookingState.waiting_for_qty)
    else:
        # Только 1 шт., прямое бронирование.
        await callback.answer(get_text(user_id, "booked_ok"), show_alert=True)
        
        # message_to_update_id = callback.message.message_id
        await process_booking_final(callback.message, user_id, prod_id, 1, callback.message.message_id)
        await state.clear()

# Хендлер для кнопки "Назад" при выборе количества (возвращает исходную карточку)
@dp.callback_query(F.data.startswith("back_booking_"), BookingState.waiting_for_qty)
async def back_booking_callback(callback: types.CallbackQuery, state: FSMContext):
# ... (Хендлер back_booking_callback без изменений) ...
    prod_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    original_message_id = data.get('original_message_id')
    
    # Восстанавливаем оригинальную карточку товара с актуальными данными
    await update_product_card(bot, callback.message.chat.id, original_message_id, prod_id, callback.from_user.id)
    await callback.answer()
    await state.clear()

@dp.callback_query(F.data.startswith("confirm_book_"), BookingState.waiting_for_qty)
async def confirm_booking_qty(callback: types.CallbackQuery, state: FSMContext):
# ... (Хендлер confirm_booking_qty без изменений) ...
    parts = callback.data.split("_")
    prod_id = int(parts[2])
    qty = int(parts[3])
    
    data = await state.get_data()
    original_message_id = data.get('original_message_id')
    
    await callback.answer(get_text(callback.from_user.id, "booked_ok"), show_alert=True)
    
    # 1. Process booking and send QR code
    # Передаем ID сообщения, которое нужно обновить (оригинальная карточка товара)
    await process_booking_final(callback.message, callback.from_user.id, prod_id, qty, original_message_id)
    
    await state.clear()


async def process_booking_final(message_obj, user_id, prod_id, qty, message_to_update_id):
# ... (Функция process_booking_final без изменений) ...
    booking_id, valid_until_iso = db.create_booking(user_id, prod_id, qty)
    
    if not booking_id:
        await message_obj.answer("Ошибка бронирования (возможно, товар только что забрали).")
        return

    # Обновляем оригинальную карточку товара, чтобы показать новый остаток
    await update_product_card(bot, message_obj.chat.id, message_to_update_id, prod_id, user_id)
    
    # Отправляем QR код как новое сообщение, что обеспечит скролл к нему
    await send_booking_qr(message_obj, user_id, booking_id, is_new_message=True)

async def send_booking_qr(message_obj, user_id, booking_id, is_new_message=False):
# ... (Функция send_booking_qr без изменений) ...
    details = db.get_booking_details(booking_id) 
    if not details:
        await message_obj.answer("Ошибка: бронь не найдена.")
        return

    booking_status = details[5]
    booked_qty = details[6] if details[6] else 1
    total_price = details[3] * booked_qty
    
    qr_data = f"KESHKOKSHE:{booking_id}"
    qr_img_io = generate_qr(qr_data)
    valid_time = datetime.fromisoformat(details[4]).strftime("%H:%M")
    
    caption_text = get_text(user_id, "qr_caption", 
                            product=details[2], 
                            shop=details[1], 
                            price=details[3], 
                            total_price=total_price,
                            qty=booked_qty,
                            valid_until=valid_time)
                            
    if booking_status == 'sold':
        caption_text += "\n\n" + get_text(user_id, "qr_sold_status")
    elif booking_status == 'cancelled':
        caption_text += "\n\n" + get_text(user_id, "qr_cancelled_status")
    elif booking_status == 'expired':
        caption_text += "\n\n" + get_text(user_id, "qr_cancelled_status")
    else: 
        caption_text += "\n\n" + get_text(user_id, "qr_active_status")

    kb = InlineKeyboardBuilder()
    
    if booking_status == 'active':
        kb.button(text=get_text(user_id, "cancel_book_btn"), callback_data=f"cancel_{booking_id}")
    
    reply_markup = kb.as_markup() if kb.buttons else None
        
    if is_new_message:
        # Отправляем НОВОЕ сообщение (для скролла)
        await message_obj.answer_photo(
            photo=BufferedInputFile(qr_img_io.read(), filename="qr.png"),
            caption=caption_text,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    else:
        # Редактируем существующее сообщение (для 'Мои брони' и отмены)
        await bot.edit_message_caption(
            chat_id=message_obj.chat.id,
            message_id=message_obj.message_id,
            caption=caption_text,
            parse_mode="HTML",
            reply_markup=reply_markup
        )


@dp.callback_query(F.data.startswith("cancel_"))
async def cancel_booking_callback(callback: types.CallbackQuery):
# ... (Хендлер cancel_booking_callback без изменений) ...
    booking_id = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    details = db.get_booking_details(booking_id)
    if details and details[5] != 'active':
        await callback.answer("❌ Эту бронь нельзя отменить, так как она уже неактивна.", show_alert=True)
        # Просто обновляем статус в текущем сообщении
        await send_booking_qr(callback.message, user_id, booking_id, is_new_message=False) 
        return
    
    success, prod_id = db.cancel_booking(booking_id)
    if success:
        await callback.answer(get_text(user_id, "booking_cancelled"), show_alert=True)
        # Обновляем сообщение с QR-кодом (статус "Отменено")
        await send_booking_qr(callback.message, user_id, booking_id, is_new_message=False) 
        
    else:
        await callback.answer("Ошибка: бронь не найдена или неактивна.", show_alert=True)

@dp.message(F.text.in_([STRINGS['ru']['btn_my_bookings'], STRINGS['kk']['btn_my_bookings']]))
async def my_bookings(message: types.Message):
# ... (Хендлер my_bookings без изменений) ...
    db.count_active_bookings(message.from_user.id) 
    bookings = db.get_user_bookings(message.from_user.id)
    
    if not bookings:
        await message.answer(get_text(message.from_user.id, "my_bookings_empty"))
        return

    await message.answer(get_text(message.from_user.id, "active_bookings"))
    builder = InlineKeyboardBuilder()
    
    for b in bookings:
        time_left = datetime.fromisoformat(b[4]).strftime("%H:%M")
        qty = b[7] if b[7] else 1
        total = b[3] * qty
        btn_text = f"{b[2]} ({qty} шт.) | {total}₸ | ⏳{time_left}"
        builder.button(text=btn_text, callback_data=f"show_qr_{b[0]}")
    builder.adjust(1)
    await message.answer("👇", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("show_qr_"))
async def show_qr_callback(callback: types.CallbackQuery):
# ... (Хендлер show_qr_callback без изменений) ...
    parts = callback.data.split("_")
    if len(parts) >= 3:
        booking_id = parts[2]
    else:
        await callback.answer("Ошибка данных", show_alert=True)
        return
        
    # Удаляем сообщение со списком броней перед показом QR
    try: await callback.message.delete()
    except: pass
    
    # Отправляем QR как новое сообщение, что обеспечит скролл к нему
    await send_booking_qr(callback.message, callback.from_user.id, booking_id, is_new_message=True)
    await callback.answer()

async def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    print("Bot started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")