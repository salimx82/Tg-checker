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

# User data storage
user_data = {}

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
            # Create sessions directory if not exists
            if not os.path.exists("sessions"):
                os.makedirs("sessions")
            
            session_file = f"sessions/{self.user_id}_{phone.replace('+', '')}"
            self.client = TelegramClient(session_file, API_ID, API_HASH)
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
            try:
                await self.client.disconnect()
                self.is_logged_in = False
                self.checked_count = 0
                self.phone = None
                return True, "✅ লগআউট সফল!"
            except:
                pass
        return False, "❌ কোন লগইন একাউন্ট নেই।"

    async def check_numbers(self, numbers: List[str]):
        """Check if numbers have Telegram accounts"""
        if not self.is_logged_in:
            return [], "❌ প্রথমে লগইন করুন।"

        if self.checked_count + len(numbers) > self.check_limit:
            return [], f"❌ লিমিট শেষ! আপনি {self.check_limit}টি নাম্বার চেক করতে পারবেন। নতুন নাম্বার লগইন করুন।"

        results = []
        checked_now = 0
        
        for number in numbers:
            try:
                # Clean phone number
                phone = number.strip().replace(" ", "")
                if not phone:
                    continue
                    
                if phone.startswith('+'):
                    phone = phone[1:]
                
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
                checked_now += 1
                
                # Limit check
                remaining = self.check_limit - self.checked_count
                if remaining <= 0:
                    results.append(f"\n⚠️ লিমিট শেষ! নতুন নাম্বার লগইন করুন।")
                    break
                    
            except Exception as e:
                results.append(f"{number} ❌ (চেক করতে ব্যর্থ)")
        
        status_msg = f"✅ {checked_now}টি নাম্বার চেক করা হয়েছে। বাকি লিমিট: {self.check_limit - self.checked_count}"
        return results, status_msg

# Start command
@bot.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 লগইন", callback_data="login"),
         InlineKeyboardButton("🚪 লগআউট", callback_data="logout")],
        [InlineKeyboardButton("🔍 চেক নাম্বার", callback_data="check"),
         InlineKeyboardButton("📊 স্ট্যাটাস", callback_data="status")],
        [InlineKeyboardButton("ℹ️ সাহায্য", callback_data="help")]
    ])
    
    welcome_text = """
    🎯 **টেলিগ্রাম একাউন্ট চেকার বট**
    
    **ফিচারস:**
    • 📱 ফোন নম্বর দিয়ে লগইন
    • 🚪 একাউন্ট লগআউট
    • 🔍 নাম্বার চেক (ব্যান/খোলা)
    • ⏱️ লিমিট সিস্টেম
    
    **ইনস্ট্রাকশন:**
    1️⃣ প্রথমে 'লগইন' এ ক্লিক করে ফোন নম্বর দিন
    2️⃣ টেলিগ্রাম থেকে কোড পেয়ে তা দিন
    3️⃣ 'চেক নাম্বার' এ ক্লিক করে নাম্বার লিস্ট দিন
    
    **লিমিট:** ⚡ প্রতি লগইনে ১৫০টি নাম্বার চেক করা যাবে
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
            await callback_query.message.edit_text(
                "❌ ইতিমধ্যে লগইন করা আছে!\n"
                "প্রথমে লগআউট করুন।",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🚪 লগআউট", callback_data="logout")],
                    [InlineKeyboardButton("🔙 বাতিল", callback_data="cancel")]
                ])
            )
        else:
            user_data[user_id]["state"] = "waiting_phone"
            await callback_query.message.edit_text(
                "📱 **লগইন করুন**\n\n"
                "আপনার ফোন নম্বর দিন (ইন্টারন্যাশনাল ফরম্যাটে):\n"
                "উদাহরণ:\n"
                "• +8801712345678\n"
                "• +8801812345678\n\n"
                "🔑 টেলিগ্রাম থেকে verification code পাঠানো হবে।",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 বাতিল", callback_data="cancel")]
                ])
            )
    
    elif callback_query.data == "logout":
        success, msg = await user_session.logout()
        await callback_query.message.edit_text(msg)
        user_data[user_id]["state"] = None
    
    elif callback_query.data == "check":
        if not user_session.is_logged_in:
            await callback_query.message.edit_text(
                "❌ প্রথমে লগইন করুন!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📱 লগইন", callback_data="login")],
                    [InlineKeyboardButton("🔙 বাতিল", callback_data="cancel")]
                ])
            )
        else:
            user_data[user_id]["state"] = "waiting_numbers"
            await callback_query.message.edit_text(
                f"🔍 **নাম্বার চেক করুন**\n\n"
                f"নাম্বার লিস্ট দিন (একটি লাইনে একটি নাম্বার):\n\n"
                f"📋 **উদাহরণ:**\n"
                f"+8801712345678\n"
                f"+8801812345678\n"
                f"+8801912345678\n\n"
                f"⚡ **বাকি লিমিট:** {user_session.check_limit - user_session.checked_count}\n"
                f"✅ **স্ট্যাটাস:** লগইন করা\n"
                f"📞 **লগইন নম্বর:** {user_session.phone or 'N/A'}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 বাতিল", callback_data="cancel")]
                ])
            )
    
    elif callback_query.data == "status":
        if user_session.is_logged_in:
            status_text = f"""
📊 **বর্তমান স্ট্যাটাস**

📞 লগইন নাম্বার: {user_session.phone or 'N/A'}
✅ চেক করা হয়েছে: {user_session.checked_count}টি
⚡ বাকি লিমিট: {user_session.check_limit - user_session.checked_count}টি
🔓 স্ট্যাটাস: লগইন করা

📈 **ইউজেজ:** {(user_session.checked_count/user_session.check_limit)*100:.1f}%
"""
        else:
            status_text = "❌ কোন লগইন একাউন্ট নেই।\n\n📱 প্রথমে লগইন করুন।"
        
        await callback_query.message.edit_text(
            status_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📱 লগইন", callback_data="login")],
                [InlineKeyboardButton("🔙 মেনু", callback_data="cancel")]
            ])
        )
    
    elif callback_query.data == "help":
        help_text = """
ℹ️ **সাহায্য / নির্দেশনা**

**লগইন প্রক্রিয়া:**
1. 📱 'লগইন' বাটনে ক্লিক করুন
2. আপনার ফোন নম্বর দিন (ইন্টারন্যাশনাল ফরম্যাটে)
3. টেলিগ্রাম থেকে verification code পাবেন
4. সেই code টি দিন

**নাম্বার চেক:**
1. 🔍 'চেক নাম্বার' বাটনে ক্লিক করুন
2. নাম্বার লিস্ট দিন (এক লাইনে একটি)
3. রেজাল্ট পাবেন:
   ✅ = একাউন্ট নেই
   ❌ = একাউন্ট আছে

**লিমিট:**
• প্রতি লগইনে ১৫০টি নাম্বার চেক করতে পারবেন
• লিমিট শেষ হলে নতুন নাম্বার দিয়ে লগইন করুন
• লগআউট করলে সেশন রিসেট হবে
"""
        await callback_query.message.edit_text(
            help_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 মেনু", callback_data="cancel")]
            ])
        )
    
    elif callback_query.data == "cancel":
        # Back to main menu
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📱 লগইন", callback_data="login"),
             InlineKeyboardButton("🚪 লগআউট", callback_data="logout")],
            [InlineKeyboardButton("🔍 চেক নাম্বার", callback_data="check"),
             InlineKeyboardButton("📊 স্ট্যাটাস", callback_data="status")]
        ])
        await callback_query.message.edit_text(
            "🎯 **মূল মেনু**\n\nকি করতে চান?",
            reply_markup=keyboard
        )
    
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
        
        # Processing message
        processing_msg = await message.reply_text("📱 কোড পাঠানো হচ্ছে...")
        
        success, msg = await user_session.send_code(phone)
        
        await processing_msg.delete()
        
        if success:
            await message.reply_text(
                f"✅ {msg}\n\n"
                f"📞 আপনার নম্বর: {phone}\n\n"
                f"🔑 **টেলিগ্রাম থেকে পাঠানো কোডটি দিন:**",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 বাতিল", callback_data="cancel")]
                ])
            )
        else:
            await message.reply_text(
                msg,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📱 আবার চেষ্টা করুন", callback_data="login")],
                    [InlineKeyboardButton("🔙 বাতিল", callback_data="cancel")]
                ])
            )
            user_data[user_id]["state"] = None
    
    elif state == "waiting_code":
        code = message.text.strip()
        
        # Processing message
        processing_msg = await message.reply_text("🔐 লগইন করা হচ্ছে...")
        
        success, msg = await user_session.login(code)
        
        await processing_msg.delete()
        
        if success:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 নাম্বার চেক করুন", callback_data="check")],
                [InlineKeyboardButton("📊 স্ট্যাটাস দেখুন", callback_data="status")]
            ])
            await message.reply_text(
                f"🎉 {msg}\n\n"
                f"📞 লগইন নম্বর: {user_session.phone}\n"
                f"⚡ বাকি লিমিট: {user_session.check_limit}\n\n"
                f"এখন আপনি নাম্বার চেক করতে পারেন।",
                reply_markup=keyboard
            )
        else:
            await message.reply_text(
                f"❌ {msg}\n\n"
                f"আবার চেষ্টা করুন।",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📱 আবার চেষ্টা করুন", callback_data="login")],
                    [InlineKeyboardButton("🔙 বাতিল", callback_data="cancel")]
                ])
            )
        
        user_data[user_id]["state"] = None
    
    elif state == "waiting_numbers":
        numbers_text = message.text.strip()
        numbers = [n.strip() for n in numbers_text.split('\n') if n.strip()]
        
        if not numbers:
            await message.reply_text(
                "❌ ভুল ইনপুট।\n\n"
                "একটি লাইনে একটি নাম্বার দিন।\n\n"
                "📋 **উদাহরণ:**\n"
                "+8801712345678\n"
                "+8801812345678",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 আবার চেষ্টা করুন", callback_data="check")],
                    [InlineKeyboardButton("🔙 বাতিল", callback_data="cancel")]
                ])
            )
            return
        
        # Limit check
        if user_session.checked_count + len(numbers) > user_session.check_limit:
            await message.reply_text(
                f"❌ লিমিট শেষ!\n\n"
                f"আপনি {user_session.check_limit}টি নাম্বার চেক করতে পারবেন।\n"
                f"ইতিমধ্যে চেক করেছেন: {user_session.checked_count}টি\n\n"
                f"নতুন নাম্বার দিয়ে লগইন করুন।",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🚪 লগআউট", callback_data="logout")],
                    [InlineKeyboardButton("📱 নতুন লগইন", callback_data="login")]
                ])
            )
            user_data[user_id]["state"] = None
            return
        
        # Processing message
        processing_msg = await message.reply_text(
            f"🔄 চেক করা হচ্ছে...\n\n"
            f"📊 মোট নাম্বার: {len(numbers)}টি\n"
            f"⏳ দয়া করে অপেক্ষা করুন..."
        )
        
        # Check numbers
        results, status_msg = await user_session.check_numbers(numbers)
        
        # Format results
        result_text = "📋 **চেক রেজাল্ট:**\n\n"
        result_text += "\n".join(results[:50])  # প্রথম ৫০টি দেখাবে
        
        # যদি ৫০টির বেশি হয়
        if len(results) > 50:
            result_text += f"\n\n... এবং আরও {len(results) - 50}টি ফলাফল"
        
        result_text += f"\n\n{status_msg}"
        
        # Send results
        await processing_msg.delete()
        
        if len(result_text) > 4000:
            # Split long message
            parts = [result_text[i:i+4000] for i in range(0, len(result_text), 4000)]
            for i, part in enumerate(parts):
                if i == 0:
                    await message.reply_text(part)
                else:
                    await message.reply_text(f"(চলছে...)\n\n{part}")
        else:
            await message.reply_text(result_text)
        
        # Show menu after checking
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 আরও চেক করুন", callback_data="check")],
            [InlineKeyboardButton("📊 স্ট্যাটাস", callback_data="status")],
            [InlineKeyboardButton("🚪 লগআউট", callback_data="logout")]
        ])
        await message.reply_text("আপনি কি আরও নাম্বার চেক করতে চান?", reply_markup=keyboard)
        
        user_data[user_id]["state"] = None
    
    else:
        await message.reply_text(
            "🤔 আমি বুঝতে পারিনি।\n\n"
            "/start কমান্ড দিন বা নিচের মেনু থেকে অপশন সিলেক্ট করুন।",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 মেনু", callback_data="cancel")]
            ])
        )

async def main():
    # Create sessions directory
    if not os.path.exists("sessions"):
        os.makedirs("sessions")
        print("✅ 'sessions' directory created")
    
    print("🚀 বট শুরু হচ্ছে...")
    
    try:
        await bot.start()
        me = await bot.get_me()
        print(f"✅ বট চালু হয়েছে!")
        print(f"🤖 বট ইউজারনেম: @{me.username}")
        print(f"🆔 বট আইডি: {me.id}")
        print(f"⚡ লিমিট: {CHECK_LIMIT} নাম্বার/লগইন")
        print("📞 বট প্রস্তুত! /start কমান্ড দিয়ে শুরু করুন")
        
        # Keep the bot running
        await asyncio.Event().wait()
        
    except Exception as e:
        print(f"❌ ত্রুটি: {e}")
    finally:
        await bot.stop()
        print("👋 বট বন্ধ হচ্ছে...")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 বট বন্ধ হচ্ছে...")
    except Exception as e:
        print(f"❌ মেইন ত্রুটি: {e}")
