import os
import asyncio
import threading
import concurrent.futures
from telethon import TelegramClient, events
from config import *

class CleanerService:
    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.client = None
        self.phone = None
        self.loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(target=self._start_background_loop, daemon=True)
        self.loop_thread.start()
        self.is_running = False

    def _start_background_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)
        else:
            print(f"[SERVICE] {message}")

    def _run_coroutine(self, coro):
        """Runs a coroutine in the background loop and waits for result."""
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result()

    def send_code(self, phone):
        """Thread-safe method to request login code."""
        return self._run_coroutine(self._send_code_async(phone))

    async def _send_code_async(self, phone):
        self.phone = phone
        try:
            if not self.client:
                self.client = TelegramClient('mobile_session', API_ID, API_HASH, loop=self.loop)
            
            if not self.client.is_connected():
                await self.client.connect()
            
            # Check if already authorized
            if await self.client.is_user_authorized():
                self.is_running = True
                self.loop.create_task(self._monitor_messages()) # Ensure handlers are attached!
                return True, "Allaqachon tizimga kirgan!"

            await self.client.send_code_request(phone)
            return True, "Kod yuborildi."
        except Exception as e:
            return False, str(e)

    def sign_in(self, code, password=None):
        """Thread-safe method to sign in."""
        return self._run_coroutine(self._sign_in_async(code, password))

    async def _sign_in_async(self, code, password=None):
        try:
            # If password is provided, we try to use it.
            # Telethon's sign_in can handle all args, but sometimes splitting them is safer 
            # if we are already in 'password needed' state.
            if password:
                try:
                    await self.client.sign_in(password=password)
                except Exception:
                    # If that fails (maybe completely new session), try full sign-in
                    await self.client.sign_in(self.phone, code, password=password)
            else:
                await self.client.sign_in(self.phone, code)

            self.is_running = True
            # Start background monitoring task
            self.loop.create_task(self._monitor_messages())
            
            user = await self.client.get_me()
            return True, f"Xush kelibsiz, {user.first_name}!"
        except Exception as e:
            return False, str(e)

    async def _monitor_messages(self):
        self.log("👀 Kuzatuv boshlandi...")
        @self.client.on(events.NewMessage)
        async def handler(event):
            if not self.is_running: return
            if event.message.file:
                file_name = event.message.file.name
                if file_name:
                    ext = os.path.splitext(file_name)[1].lower()
                    if ext in BLOCKED_EXTENSIONS:
                        self.log(f"🚨 XAVFLI FAYL: {file_name}")
                        try:
                            await event.delete()
                            self.log(f"♻️ O'CHIRILDI: {file_name}")
                        except Exception as e:
                            self.log(f"❌ Xatolik: {e}")
        
        # Keep the client running (though run_forever handles the loop, we need to ensure client isn't GC'd)
        # Telethon's run_until_disconnected is blocking, we shouldn't use it here if we want to do other things.
        # But since we are in run_forever, events will just process.
        pass

    def start(self):
        self.is_running = True
        self.log("🛡 Himoya tizimi ishga tushdi...")

    def stop(self):
        self.is_running = False
        self.log("🛑 Himoya to'xtatildi.")
