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
SHEET_NAME = 'User Credentials'
CREDENTIALS_FILE = 'credentials.json'

# Google Sheets connection
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1

# Bot initialization
bot = Bot(token=API_TOKEN)
dp = Dispatcher()


# Main menu
def main_menu():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='Mening yutuqlarim')],
            [KeyboardButton(text='Jamoa reytingi')],
            [KeyboardButton(text='Qbank', web_app=WebAppInfo(url="https://www.medicospira.com/uworld1/login.php"))],
            [KeyboardButton(text='Sizning emailingiz')]  # Email tugmasi qo'shildi
        ],
        resize_keyboard=True,
    )
    return keyboard


# Start command
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = str(message.from_user.id)
    username = message.from_user.username or "No username"
    user_found = False

    headers = sheet.row_values(1)
    records = sheet.get_all_records()
    for record in records:
        if str(record.get("Username")) == username:  # Username asosida tekshirilyapti
            user_found = True
            break

    if not user_found:
        empty_row = {header: "" for header in headers}
        empty_row["Username"] = username
        empty_row["Coinlar"] = 0
        empty_row["Email"] = ""  # Email maydoni qo'shildi
        empty_row["Parol"] = ""  # Parol maydoni qo'shildi
        sheet.append_row([empty_row.get(header, "") for header in headers])  # Yangi foydalanuvchi qo'shish
        logging.info(f"User added: {user_id}, Username: {username}")

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
        headers = sheet.row_values(1)
        records = sheet.get_all_records()
        for index, record in enumerate(records, start=2):
            if record["Username"] == message.from_user.username:
                current_coins = int(record["Coinlar"])
                new_coins = current_coins + 1
                existing_photos = record.get("Rasmlar", "")
                updated_photos = f"{existing_photos},{file_path}" if existing_photos else file_path

                sheet.update_cell(index, headers.index("Rasmlar") + 1, updated_photos)  # Update photos
                sheet.update_cell(index, headers.index("Coinlar") + 1, new_coins)  # Update coins
                logging.info(f"Image received and coins updated: {user_id}, {new_coins} coins")
                await message.reply("✅ Hisobot qabul qilindi va 1 ta coin qo'shildi!")
                return

        # If user is new
        empty_row = {header: "" for header in headers}
        empty_row["Username"] = message.from_user.username
        empty_row["Rasmlar"] = file_path
        empty_row["Coinlar"] = 1
        sheet.append_row([empty_row.get(header, "") for header in headers])  # Start with 1 coin
        logging.info(f"Image received and coins added: {user_id}, 1 coin")
        await message.reply("✅ Hisobot qabul qilindi va 1 ta coin qo'shildi!")

    except Exception as e:
        logging.error(f"Error: {str(e)}")
        await message.reply(f"❌ Error: {str(e)}")


# User achievements
@dp.message(lambda message: message.text and message.text.lower() == 'mening yutuqlarim')
async def my_achievements(message: types.Message):
    user_id = str(message.from_user.id)
    total_coins = 0

    headers = sheet.row_values(1)
    records = sheet.get_all_records()
    for record in records:
        if record["Username"] == message.from_user.username:
            total_coins = record["Coinlar"]
            break

    await message.reply(f"🏅 Sizning umumiy coinlaringiz soni: {total_coins}")


# Team ranking
@dp.message(lambda message: message.text.lower() == 'jamoa reytingi')
async def team_ranking(message: types.Message):
    user_coins = {}

    headers = sheet.row_values(1)
    records = sheet.get_all_records()
    for record in records:
        username = record.get("Username", "No User ID")
        coins = record.get("Coinlar", 0)
        user_coins[username] = coins

    sorted_users = sorted(user_coins.items(), key=lambda x: x[1], reverse=True)
    message_text = "📊 Jamoa reytingi:\n\n"

    for idx, (username, coins) in enumerate(sorted_users, start=1):
        message_text += f"{idx}. {username}: {coins} coins\n"

    await message.reply(message_text)


# Show email and password for user based on Username
@dp.message(lambda message: message.text.lower() == 'sizning emailingiz')
async def show_email(message: types.Message):
    username = message.from_user.username or "No username"  # Ensure username exists
    email = "Email not provided"
    password = "Password not provided"

    headers = sheet.row_values(1)  # Fetch headers
    logging.info(f"Headers in the sheet: {headers}")  # Debugging headers
    records = sheet.get_all_records()  # Fetch all records

    # Loop through the records and check for matching username
    for record in records:
        logging.info(f"Checking record: {record}")  # Debugging individual records
        if record.get("Username") == username:  # Compare Username column
            email = record.get("Email", "Email not provided")  # Get Email from column E
            password = record.get("Password", "Password not provided")  # Get Password from column F
            break  # Exit loop once matching username is found

    # Respond with the email and password if found
    logging.info(f"Sending email and password to {username}: Email: {email}, Password: {password}")
    await message.reply(f"📧 Sizning email manzilingiz: {email}\n🔐 Parolingiz: {password}")


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
