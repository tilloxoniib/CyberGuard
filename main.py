import flet as ft
import time
import threading
import asyncio
import os
from config import *
from cleaner_service import CleanerService

def main(page: ft.Page):
    try:
        # --- STORAGE SETUP ---
        # FLET_APP_STORAGE_DATA is specifically for persistent Android storage
        storage_path = os.environ.get("FLET_APP_STORAGE_DATA", ".")
        session_file = os.path.join(storage_path, "mobile_session")
        
        # --- SETUP ---
        page.title = APP_NAME
        page.theme_mode = ft.ThemeMode.DARK
        page.bgcolor = COLOR_BG
        page.padding = 20
        page.window_width = 380 
        page.window_height = 800
        
        cleaner = CleanerService(session_path=session_file)

        # --- STATE ---
        is_logged_in = False
        phone_number = ""

        # --- UI COMPONENTS ---
        
        # 1. Header
        header = ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Image(
                        src="logo.jpg",
                        width=120,
                        height=120,
                        fit="contain",
                    ),
                    shape=ft.BoxShape.CIRCLE,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    bgcolor="black", # Logo foni qora ekanligi uchun
                    border=ft.border.all(1, COLOR_PRIMARY), # Chiroyli oltin hoshiya
                    padding=2
                ),
                ft.Text(
                    "FARG'ONA VILOYATI IIB\nKIBERXAVFSIZLIK BOSHQARMASI\nHIMOYASIDASIZ", 
                    size=16, 
                    weight="bold", 
                    color=COLOR_TEXT, 
                    text_align="center"
                ),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
            alignment=ft.alignment.Alignment(0, 0),
            padding=20,
            bgcolor="black", # Header fonini logo foniga mosladim
            border_radius=10
        )

        # 2. Login View
        t_phone = ft.TextField(label="Telefon raqam", hint_text="+998...", width=250, border_color=COLOR_PRIMARY)
        t_code = ft.TextField(label="SMS Kod", width=150, border_color=COLOR_PRIMARY, visible=False)
        t_password = ft.TextField(label="2FA Parol", width=150, border_color=COLOR_PRIMARY, password=True, visible=False)
        
        btn_action = ft.ElevatedButton(
            "KODNI OLISH", 
            style=ft.ButtonStyle(bgcolor=COLOR_PRIMARY, color="black"),
            width=200
        )
        
        login_column = ft.Column([
            t_phone,
            t_code,
            t_password,
            ft.Container(height=10),
            btn_action
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
        
        login_container = ft.Container(
            content=login_column,
            padding=20,
            bgcolor=COLOR_SURFACE,
            border_radius=10,
            alignment=ft.alignment.Alignment(0, 0),
            visible=True
        )

        # 3. Dashboard View (Hidden initially)
        status_text = ft.Text("HIMOYA FAOL EMAS", size=20, weight="bold", color=COLOR_TEXT_DIM)
        status_container = ft.Container(
            content=status_text,
            alignment=ft.alignment.Alignment(0, 0),
            padding=20,
            border=ft.border.all(2, COLOR_TEXT_DIM),
            border_radius=100,
            width=200,
            height=200,
        )
        
        btn_scan = ft.ElevatedButton(
            "HIMOYAGA OLISH", 
            style=ft.ButtonStyle(bgcolor=COLOR_PRIMARY, color="black"),
            width=200
        )

        dashboard_column = ft.Column([
            status_container,
            ft.Container(height=20),
            ft.Container(content=btn_scan, alignment=ft.alignment.Alignment(0, 0))
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        dashboard_container = ft.Container(
            content=dashboard_column,
            visible=False
        )

        # 4. Logs
        log_column = ft.Column(scroll="auto", expand=True)
        log_container = ft.Container(
            content=log_column,
            bgcolor=COLOR_SURFACE,
            border_radius=10,
            padding=10,
            height=200,
            expand=False
        )

        def add_log(msg):
            t = time.strftime("%H:%M")
            log_column.controls.append(
                ft.Text(f"[{t}] {msg}", size=12, color=COLOR_TEXT_DIM, font_family="monospace")
            )
            page.update()

        cleaner.log_callback = add_log

        # --- LOGIC ---

        def switch_to_dashboard():
            login_container.visible = False
            dashboard_container.visible = True
            
            # Immediately show active state because login starts the service
            if cleaner.is_running:
                btn_scan.text = "HIMOYANI O'CHIRISH"
                btn_scan.style.bgcolor = COLOR_DANGER
                status_text.value = "HIMOYA FAOL"
                status_text.color = COLOR_PRIMARY
                status_container.border = ft.border.all(2, COLOR_PRIMARY)
            
            add_log("Tizimga muvaffaqiyatli kirildi. Himoya yoqildi.")
            page.update()

        # --- STATE ---
        login_step = "phone" # phone, code, password

        def action_click(e):
            nonlocal phone_number, login_step
            if login_step == "phone":
                phone = t_phone.value
                if not phone:
                    add_log("Telefon raqamni kiriting!")
                    return
                
                add_log(f"Kod yuborilmoqda: {phone}...")
                btn_action.disabled = True
                page.update()
                
                # Call synchronous method (runs in background thread inside service)
                success, msg = cleaner.send_code(phone)
                btn_action.disabled = False
                
                if success:
                    if msg == "Allaqachon tizimga kirgan!":
                         cleaner.start() # Start the service
                         switch_to_dashboard()
                         add_log(msg)
                    else:
                        phone_number = phone
                        t_phone.disabled = True
                        t_code.visible = True
                        btn_action.text = "KIRISH" 
                        login_step = "code"
                        add_log("SIZGA TELEGRAMDAN KOD YUBORILDI. SHUNI KIRITING!")
                else:
                    add_log(f"Xatolik: {msg}")
                page.update()

            elif login_step == "code":
                code = t_code.value
                if not code: return
                
                add_log("Tekshirilmoqda...")
                
                paw = t_password.value if t_password.visible else None
                if paw: add_log(f"Parol bilan kirilmoqda...")

                success, msg = cleaner.sign_in(code, password=paw)
                
                if success:
                    switch_to_dashboard()
                elif "password" in msg.lower():
                    if not t_password.visible:
                        t_password.visible = True
                        add_log("⚠️ 2FA Parol kerak. Iltimos parolni yozing.")
                    else:
                        add_log("❌ Parol xato yoki yana so'ralmoqda.")
                        add_log(f"Xatolik tafsiloti: {msg}")
                else:
                    add_log(f"❌ Login xatosi: {msg}")
                page.update()

        # Wrap in simple thread to avoid freezing UI
        def on_action_click_wrapper(e):
            threading.Thread(target=action_click, args=(e,)).start()

        btn_action.on_click = on_action_click_wrapper

        def toggle_protection(e):
            if cleaner.is_running:
                cleaner.stop()
                btn_scan.text = "HIMOYAGA OLISH"
                btn_scan.style.bgcolor = COLOR_PRIMARY
                status_text.value = "HIMOYA FAOL EMAS"
                status_text.color = COLOR_TEXT_DIM
                status_container.border = ft.border.all(2, COLOR_TEXT_DIM)
                add_log("Tizim to'xtatildi.")
            else:
                cleaner.start()
                btn_scan.text = "HIMOYANI O'CHIRISH"
                btn_scan.style.bgcolor = COLOR_DANGER
                status_text.value = "HIMOYA FAOL"
                status_text.color = COLOR_PRIMARY
                status_container.border = ft.border.all(2, COLOR_PRIMARY)
                add_log("Tizim himoyaga o'tdi.")
            page.update()
        
        btn_scan.on_click = toggle_protection

        # --- LAYOUT ---
        page.add(
            ], expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )
        page.update()

        # --- AUTO LOGIN CHECK ---
        def run_auto_login():
            add_log("Tizim tekshirilmoqda...")
            if cleaner.check_auth():
                switch_to_dashboard()
            else:
                add_log("Iltimos, tizimga kiring.")

        threading.Thread(target=run_auto_login, daemon=True).start()
        
        print("UI Loaded")

    except Exception as e:
        print(f"Error: {e}")
        page.add(ft.Text(f"Xatolik: {e}", color="red"))

if __name__ == "__main__":
    ft.app(target=main)
