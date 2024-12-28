import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from aiogram.filters import Command
from oauth2client.service_account import ServiceAccountCredentials
import gspread
import datetime
import aiohttp
import asyncio

# Telegram API token
API_TOKEN = '7701357624:AAERZa3z5U4qw-8SAqF6iNAuwxKNCVmtD6k'

# Google Sheets settings
SHEET_NAME = 'UserCredentials'  # Jadval nomini tekshiring
CREDENTIALS_FILE = 'credentials.json'

# Google Sheets connection
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1

# Bot initialization
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Google Sheets headers
HEADERS = ['User ID', 'Faollik vaqti', 'Rasmlar', 'Coinlar', 'Status', 'Sayt uchun email', 'Parol']

# Main menu
def main_menu():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='Mening yutuqlarim')],
            [KeyboardButton(text='Jamoa reytingi')],
            [KeyboardButton(text='Qbank', web_app=WebAppInfo(url="https://www.medicospira.com/uworld1/login.php"))]
        ],
        resize_keyboard=True,
    )
    return keyboard

# Start command
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = str(message.from_user.id)
    user_found = False

    records = sheet.get_all_records(expected_headers=HEADERS)
    for record in records:
        if record["User ID"] == user_id:
            user_found = True
            break

    if not user_found:
        sheet.append_row([user_id, "", "", 0, "", "", ""])  # Add new user
        logging.info(f"User added: {user_id}")

    keyboard = main_menu()
    await message.reply("✨ Medstonega xush kelibsiz!", reply_markup=keyboard)

# Handle image and update coins
@dp.message(lambda message: bool(message.photo))
async def handle_image(message: types.Message):
    user_id = str(message.from_user.id)
    file = message.photo[-1].file_id
    today = datetime.datetime.now().strftime('%Y-%m-%d')

    try:
        # Download image
        file_info = await bot.get_file(file)
        file_url = f"https://api.telegram.org/file/bot{API_TOKEN}/{file_info.file_path}"
        file_path = f"./task_images/{user_id}_{today}.jpg"
        os.makedirs('./task_images', exist_ok=True)

        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as response:
                if response.status == 200:
                    with open(file_path, 'wb') as f:
                        f.write(await response.read())
                else:
                    raise Exception("Error downloading image.")

        # Update coins
        records = sheet.get_all_records(expected_headers=HEADERS)
        for index, record in enumerate(records, start=2):
            if record["User ID"] == user_id:
                current_coins = int(record["Coinlar"])
                new_coins = current_coins + 1
                existing_photos = record["Rasmlar"]
                updated_photos = f"{existing_photos},{file_path}" if existing_photos else file_path

                sheet.update_cell(index, 3, updated_photos)  # Update photos
                sheet.update_cell(index, 4, new_coins)  # Update coins
                logging.info(f"Image received and coins updated: {user_id}, {new_coins} coins")
                await message.reply("✅ Image received and coins added!")
                return

        # If user is new
        sheet.append_row([user_id, "", file_path, 1, "", "", ""])  # Start with 1 coin
        logging.info(f"Image received and coins added: {user_id}, 1 coin")
        await message.reply("✅ Image received and coins added!")

    except Exception as e:
        logging.error(f"Error: {str(e)}")
        await message.reply(f"❌ Error: {str(e)}")

# User achievements
@dp.message(lambda message: message.text and message.text.lower() == 'mening yutuqlarim')
async def my_achievements(message: types.Message):
    user_id = str(message.from_user.id)
    total_coins = 0

    records = sheet.get_all_records(expected_headers=HEADERS)
    for record in records:
        if record["User ID"] == user_id:
            total_coins = record["Coinlar"]
            break

    await message.reply(f"🏅 Sizning umumiy coinlaringiz soni: {total_coins}")

# Team ranking
@dp.message(lambda message: message.text.lower() == 'jamoa reytingi')
async def team_ranking(message: types.Message):
    user_coins = {}

    records = sheet.get_all_records(expected_headers=HEADERS)
    for record in records:
        user_id = record.get("User ID", "No User ID")
        coins = record.get("Coinlar", 0)
        user_coins[user_id] = coins

    sorted_users = sorted(user_coins.items(), key=lambda x: x[1], reverse=True)
    message_text = "📊 Jamoa reytingi:\n\n"

    for idx, (user_id, coins) in enumerate(sorted_users, start=1):
        message_text += f"{idx}. {user_id}: {coins} coins\n"

    await message.reply(message_text)

# Qbank button
@dp.message(lambda message: message.text and 'qbank' in message.text.lower())
async def qbank(message: types.Message):
    await message.answer("Testni boshlash uchun:\n🔗 [Bu yerga bosing](https://www.medicospira.com/uworld1/login.php)",
                         parse_mode="Markdown")

# Start bot
async def main():
    print("⚙️ Bot ishga tushirildi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
