import os
import asyncio
from typing import Dict, List
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from telethon.sync import TelegramClient
from telethon.errors import PhoneNumberInvalidError, PhoneCodeInvalidError, PhoneCodeExpiredError, SessionPasswordNeededError

# লোড environment variables
load_dotenv()

# Configuration
API_ID = int(os.getenv("API_ID", "34902375"))
API_HASH = os.getenv("API_HASH", "647f67ecffd70ffc19ad3fadcf57f82e")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8445518269:AAGc3zUsWs1QJ1x3gnEaTcj4pBfkgJgLVUo")
SESSION_NAME = os.getenv("SESSION_NAME", "telegram_checker")
CHECK_LIMIT = int(os.getenv("CHECK_LIMIT", "150"))

# Pyrogram বট ক্লায়েন্ট
bot = Client(
    "checker_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# User data storage (In production, use database)
user_data = {}
user_sessions = {}

class UserSession:
    def __init__(self, user_id):
        self.user_id = user_id
        self.phone = None
        self.phone_code_hash = None
        self.client = None
        self.is_logged_in = False
        self.checked_count = 0
        self.check_limit = CHECK_LIMIT

    async def send_code(self, phone: str):
        """Send verification code to phone"""
        try:
            self.client = TelegramClient(f"sessions/{self.user_id}_{phone}", API_ID, API_HASH)
            await self.client.connect()
            
            sent_code = await self.client.send_code_request(phone)
            self.phone = phone
            self.phone_code_hash = sent_code.phone_code_hash
            return True, "✅ কোড পাঠানো হয়েছে। কোডটি দিন।"
        except PhoneNumberInvalidError:
            return False, "❌ ভুল ফোন নম্বর।"
        except Exception as e:
            return False, f"❌ ত্রুটি: {str(e)}"

    async def login(self, code: str):
        """Login with verification code"""
        try:
            await self.client.sign_in(
                phone=self.phone,
                code=code,
                phone_code_hash=self.phone_code_hash
            )
            self.is_logged_in = True
            return True, "✅ লগইন সফল!"
        except PhoneCodeInvalidError:
            return False, "❌ ভুল কোড।"
        except PhoneCodeExpiredError:
            return False, "❌ কোডের মেয়াদ শেষ। আবার চেষ্টা করুন।"
        except SessionPasswordNeededError:
            return False, "❌ টু-ফ্যাক্টর পাসওয়ার্ড লাগবে।"
        except Exception as e:
            return False, f"❌ ত্রুটি: {str(e)}"

    async def logout(self):
        """Logout from session"""
        if self.client and self.is_logged_in:
            await self.client.disconnect()
            self.is_logged_in = False
            self.checked_count = 0
            return True, "✅ লগআউট সফল!"
        return False, "❌ কোন লগইন একাউন্ট নেই।"

    async def check_numbers(self, numbers: List[str]):
        """Check if numbers have Telegram accounts"""
        if not self.is_logged_in:
            return [], "❌ প্রথমে লগইন করুন।"

        if self.checked_count + len(numbers) > self.check_limit:
            return [], f"❌ লিমিট শেষ! আপনি {self.check_limit}টি নাম্বার চেক করতে পারবেন। নতুন নাম্বার লগইন করুন।"

        results = []
        for number in numbers:
            try:
                # Clean phone number
                phone = number.strip().replace(" ", "").replace("+", "")
                if not phone.isdigit():
                    results.append(f"{number} ❌ (ভুল ফরম্যাট)")
                    continue
                
                # Check if user exists
                try:
                    user = await self.client.get_entity(phone)
                    if user:
                        results.append(f"{number} ❌ (একাউন্ট আছে)")
                    else:
                        results.append(f"{number} ✅ (একাউন্ট নেই)")
                except:
                    results.append(f"{number} ✅ (একাউন্ট নেই)")
                
                self.checked_count += 1
                
                # Limit check
                remaining = self.check_limit - self.checked_count
                if remaining <= 0:
                    results.append(f"\n⚠️ লিমিট শেষ! নতুন নাম্বার লগইন করুন।")
                    break
                    
            except Exception as e:
                results.append(f"{number} ❌ (চেক করতে ব্যর্থ)")
        
        return results, f"চেক করা হয়েছে। বাকি লিমিট: {self.check_limit - self.checked_count}"

# Start command
@bot.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 লগইন", callback_data="login"),
         InlineKeyboardButton("🚪 লগআউট", callback_data="logout")],
        [InlineKeyboardButton("🔍 চেক নাম্বার", callback_data="check"),
         InlineKeyboardButton("📊 স্ট্যাটাস", callback_data="status")]
    ])
    
    welcome_text = """
    🎯 **টেলিগ্রাম একাউন্ট চেকার বট**
    
    **ফিচারস:**
    • ফোন নম্বর দিয়ে লগইন
    • একাউন্ট লগআউট
    • নাম্বার চেক (ব্যান/খোলা)
    • লিমিট সিস্টেম
    
    **ইনস্ট্রাকশন:**
    1. প্রথমে 'লগইন' এ ক্লিক করে ফোন নম্বর দিন
    2. টেলিগ্রাম থেকে কোড পেয়ে তা দিন
    3. 'চেক নাম্বার' এ ক্লিক করে নাম্বার লিস্ট দিন
    
    **লিমিট:** প্রতি লগইনে ১৫০টি নাম্বার চেক করা যাবে
    """
    
    await message.reply_text(welcome_text, reply_markup=keyboard)

# Callback query handler
@bot.on_callback_query()
async def callback_handler(client: Client, callback_query):
    user_id = callback_query.from_user.id
    
    if user_id not in user_data:
        user_data[user_id] = {"state": None, "session": UserSession(user_id)}
    
    user_session = user_data[user_id]["session"]
    
    if callback_query.data == "login":
        if user_session.is_logged_in:
            await callback_query.message.edit_text("❌ ইতিমধ্যে লগইন করা আছে! প্রথমে লগআউট করুন।")
        else:
            user_data[user_id]["state"] = "waiting_phone"
            await callback_query.message.edit_text("📱 **লগইন করুন**\n\nআপনার ফোন নম্বর দিন (ইন্টারন্যাশনাল ফরম্যাটে):\nউদাহরণ: +8801712345678")
    
    elif callback_query.data == "logout":
        success, msg = await user_session.logout()
        await callback_query.message.edit_text(msg)
        user_data[user_id]["state"] = None
    
    elif callback_query.data == "check":
        if not user_session.is_logged_in:
            await callback_query.message.edit_text("❌ প্রথমে লগইন করুন!")
        else:
            user_data[user_id]["state"] = "waiting_numbers"
            await callback_query.message.edit_text(
                f"🔍 **নাম্বার চেক করুন**\n\n"
                f"নাম্বার লিস্ট দিন (একটি লাইনে একটি নাম্বার):\n"
                f"উদাহরণ:\n"
                f"+8801712345678\n"
                f"+8801812345678\n"
                f"+8801912345678\n\n"
                f"বাকি লিমিট: {user_session.check_limit - user_session.checked_count}"
            )
    
    elif callback_query.data == "status":
        if user_session.is_logged_in:
            status_text = f"""
            📊 **বর্তমান স্ট্যাটাস**
            
            • লগইন নাম্বার: {user_session.phone or 'N/A'}
            • চেক করা হয়েছে: {user_session.checked_count}
            • বাকি লিমিট: {user_session.check_limit - user_session.checked_count}
            • স্ট্যাটাস: ✅ লগইন করা
            """
        else:
            status_text = "❌ কোন লগইন একাউন্ট নেই। প্রথমে লগইন করুন।"
        
        await callback_query.message.edit_text(status_text)
    
    await callback_query.answer()

# Message handler
@bot.on_message(filters.text & ~filters.command("start"))
async def handle_messages(client: Client, message: Message):
    user_id = message.from_user.id
    
    if user_id not in user_data:
        user_data[user_id] = {"state": None, "session": UserSession(user_id)}
    
    state = user_data[user_id]["state"]
    user_session = user_data[user_id]["session"]
    
    if state == "waiting_phone":
        phone = message.text.strip()
        user_data[user_id]["state"] = "waiting_code"
        
        success, msg = await user_session.send_code(phone)
        if success:
            await message.reply_text(f"{msg}\n\nআপনার ফোনে পাঠানো কোডটি দিন:")
        else:
            await message.reply_text(msg)
            user_data[user_id]["state"] = None
    
    elif state == "waiting_code":
        code = message.text.strip()
        success, msg = await user_session.login(code)
        
        if success:
            await message.reply_text(f"{msg}\n\nএখন আপনি নাম্বার চেক করতে পারেন।")
        else:
            await message.reply_text(msg)
        
        user_data[user_id]["state"] = None
    
    elif state == "waiting_numbers":
        numbers_text = message.text.strip()
        numbers = [n.strip() for n in numbers_text.split('\n') if n.strip()]
        
        if not numbers:
            await message.reply_text("❌ ভুল ইনপুট। আবার চেষ্টা করুন।")
            return
        
        # Limit check
        if user_session.checked_count + len(numbers) > user_session.check_limit:
            await message.reply_text(
                f"❌ লিমিট শেষ! আপনি {user_session.check_limit}টি নাম্বার চেক করতে পারবেন।\n"
                f"নতুন নাম্বার লগইন করুন।"
            )
            user_data[user_id]["state"] = None
            return
        
        # Processing message
        processing_msg = await message.reply_text("🔄 চেক করা হচ্ছে... দয়া করে অপেক্ষা করুন")
        
        # Check numbers
        results, status_msg = await user_session.check_numbers(numbers)
        
        # Format results
        result_text = "📋 **চেক রেজাল্ট:**\n\n"
        result_text += "\n".join(results)
        result_text += f"\n\n{status_msg}"
        
        # Send results (split if too long)
        if len(result_text) > 4000:
            parts = [result_text[i:i+4000] for i in range(0, len(result_text), 4000)]
            for part in parts:
                await message.reply_text(part)
        else:
            await processing_msg.delete()
            await message.reply_text(result_text)
        
        user_data[user_id]["state"] = None
    
    else:
        await message.reply_text(
            "❓ কমান্ড বুঝতে পারিনি।\n"
            "/start লিখুন বা মেনু থেকে অপশন সিলেক্ট করুন।"
        )

async def main():
    # Create sessions directory
    if not os.path.exists("sessions"):
        os.makedirs("sessions")
    
    print("🤖 বট শুরু হচ্ছে...")
    await bot.start()
    print("✅ বট চালু হয়েছে!")
    
    # Get bot info
    me = await bot.get_me()
    print(f"Bot username: @{me.username}")
    
    # Keep running
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 বট বন্ধ হচ্ছে...")
