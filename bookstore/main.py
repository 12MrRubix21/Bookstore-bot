import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from aiogram.filters import Command
import logging
import sqlite3
import os

API_TOKEN = "TOKEN?"

conn = sqlite3.connect("users.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE,
    username TEXT UNIQUE,
    balance INTEGER DEFAULT 0,
    purchased INTEGER DEFAULT 0,
    purchase_history TEXT DEFAULT ''
)
""")
conn.commit()

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

button1 = KeyboardButton(text="Магазин")
button2 = KeyboardButton(text="История покупок")
button3 = KeyboardButton(text="Профиль")

books = [
    {"name": "Гарри и роллевые игры", "price": 10, "file": "1.pdf"},
    {"name": "Стейси и её трусики", "price": 15, "file": "2.pdf"},
    {"name": "Как единорог, только рог между ног", "price": 20, "file": "3.pdf"},
    {"name": "Как правильно снимать лифчик", "price": 25, "file": "4.pdf"}
]

keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [button1, button2, button3]
    ],
    resize_keyboard=True
)

async def add_user(user_id, username):
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", 
            (user_id, username)
        )
        conn.commit()
    except Exception as e:
        print(f"Ошибка добавления пользователя: {e}")

async def send_book(user_id, book_name, message):
    book = next((b for b in books if b["name"] == book_name), None)
    if not book:
        await message.answer("Файл не найден.")
        return
    file_path = os.path.join("books", book["file"])
    if os.path.exists(file_path):
        await message.answer_document(FSInputFile(file_path))
    else:
        await message.answer("Файл отсутствует на сервере.")
        
async def get_user(user_id):
    cursor.execute("SELECT balance, purchased, purchase_history FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone()

async def add_purchase(user_id, item, cost):
    cursor.execute("SELECT balance, purchase_history FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if result:
        balance, history = result
        if balance >= cost:
            updated_balance = balance - cost
            updated_history = history + f"{item}\n" if history else f"{item}\n"
            cursor.execute(
                "UPDATE users SET balance = ?, purchased = purchased + 1, purchase_history = ? WHERE user_id = ?",
                (updated_balance, updated_history, user_id)
            )
            conn.commit()
            return f"Вы успешно купили '{item}' за {cost} руб. Ваш текущий баланс: {updated_balance} руб."
        else:
            return "Недостаточно средств для покупки."
    else:
        return "Пользователь не найден."
    
@dp.message(Command(commands=["start"]))
async def start_handler(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    await add_user(user_id, username)
    await message.answer("Привет!", reply_markup=keyboard)

@dp.message()
async def button_handler(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    add_user(user_id, username)
    if message.text == "Профиль":
        user_data = await get_user(user_id)
        if user_data:
            balance, purchased, _ = user_data
            await message.answer(f"Ваш профиль:\nБаланс: {balance}\nКуплено товаров: {purchased}")
        else:
            await message.answer("Ваш профиль не найден.")
    elif message.text == "История покупок":
        user_data = await get_user(user_id)
        if user_data:
            _, _, history = user_data
            history = history.strip() if history else "Покупок пока нет."
            await message.answer(f"Ваша история покупок:\n{history}")
            if history != "Покупок пока нет.":
                await message.answer("Напишите название книги из истории, чтобы получить файл.")
        else:
            await message.answer("Ваш профиль не найден.")
    elif message.text == "Магазин":
        book_list = "\n".join([f"{i+1}) {book['name']} - {book['price']} руб." for i, book in enumerate(books)])
        await message.answer(f"Ассортимент книг:\n\n{book_list}\n\nВведите номер книги, чтобы купить её.")

    elif message.text.isdigit():
        book_index = int(message.text) - 1
        if 0 <= book_index < len(books):
            selected_book = books[book_index]
            response = await add_purchase(user_id, selected_book["name"], selected_book["price"])
            await message.answer(response)
            if "успешно купили" in response:
                await send_book(user_id, selected_book["name"], message)
        else:
            await message.answer("Неверный номер книги. Попробуйте ещё раз.")
    else:
        user_data = await get_user(user_id)
        if user_data:
            _, _, history = user_data
            if message.text in history.split("\n"):
                await send_book(user_id, message.text, message)
            else:
                await message.answer("Неизвестная команда. Попробуйте выбрать действие.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
