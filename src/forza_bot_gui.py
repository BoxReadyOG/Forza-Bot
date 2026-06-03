import tkinter as tk
from tkinter import scrolledtext
from tkinter import ttk
import threading
import time
import ctypes
import cv2
import numpy as np
import pytesseract
from mss import mss
import keyboard
import os
import sys
import json
import random
import urllib.request

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- Tesseract Pfad (Dynamisch für PyInstaller) ---
tess_path = get_resource_path(r"Tesseract-OCR\tesseract.exe")
if os.path.exists(tess_path):
    pytesseract.pytesseract.tesseract_cmd = tess_path
    os.environ["TESSDATA_PREFIX"] = get_resource_path(r"Tesseract-OCR\tessdata")
else:
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# --- DirectInput Scancodes für Forza ---
DIK_W = 0x11

# --- Setup ctypes für Low-Level Keyboard Hooks ---
SendInput = ctypes.windll.user32.SendInput

PUL = ctypes.POINTER(ctypes.c_ulong)
class KeyBdInput(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]
class HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong),
                ("wParamL", ctypes.c_short),
                ("wParamH", ctypes.c_ushort)]
class MouseInput(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]
class Input_I(ctypes.Union):
    _fields_ = [("ki", KeyBdInput),
                ("mi", MouseInput),
                ("hi", HardwareInput)]
class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong),
                ("ii", Input_I)]

def press_key(hexKeyCode):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput( 0, hexKeyCode, 0x0008, 0, ctypes.pointer(extra) )
    x = Input( ctypes.c_ulong(1), ii_ )
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

def release_key(hexKeyCode):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput( 0, hexKeyCode, 0x0008 | 0x0002, 0, ctypes.pointer(extra) )
    x = Input( ctypes.c_ulong(1), ii_ )
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

DIK_X = 0x2D
DIK_RETURN = 0x1C
DIK_A = 0x1E
DIK_D = 0x20

def parse_screen(sct, lang, regions):
    tess_config_11 = '--psm 11 -l rus+eng' if lang == "Русский" else '--psm 11'
    tess_config_6 = '--psm 6 -l rus+eng' if lang == "Русский" else '--psm 6'

    # 1. Post-Race Screen (Höchste Priorität)
    img_rest = np.array(sct.grab(regions["leaderboard"]))
    gray_rest = cv2.cvtColor(img_rest, cv2.COLOR_BGRA2GRAY)
    gray_rest = cv2.resize(gray_rest, (0,0), fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
    _, thresh_rest = cv2.threshold(gray_rest, 150, 255, cv2.THRESH_BINARY)
    try:
        text_rest = pytesseract.image_to_string(thresh_rest, config=tess_config_11).lower()
        if lang == "Deutsch":
            kw_rest = ["fahrer", "auto", "klasse", "skill", "points"]
        elif lang == "Français":
            kw_rest = ["pilote", "voiture", "classe", "points"]
        elif lang == "Español":
            kw_rest = ["piloto", "coche", "auto", "clase", "puntos"]
        elif lang == "Italiano":
            kw_rest = ["pilota", "auto", "classe", "punti"]
        elif lang == "Português":
            kw_rest = ["piloto", "carro", "classe", "pontos"]
        elif lang == "Polski":
            kw_rest = ["kierowca", "auto", "klasa", "punkty"]
        elif lang == "Nederlands":
            kw_rest = ["coureur", "auto", "klasse", "punten"]
        elif lang == "Türkçe":
            kw_rest = ["surucu", "sürücü", "arac", "araç", "araba", "sinif", "sınıf", "puan"]
        elif lang == "Русский":
            kw_rest = ["водитель", "игрок", "гонщик", "авто", "автомобиль", "класс", "очки"]
        else: # Default: English
            kw_rest = ["driver", "car", "class", "skill", "points"]
            
        if any(w in text_rest for w in kw_rest):
            return "POST_RACE"
    except: pass
    
    # 2. Pre-Race Menu
    img_menu = np.array(sct.grab(regions["menu"]))
    gray_menu = cv2.cvtColor(img_menu, cv2.COLOR_BGRA2GRAY)
    _, thresh_menu = cv2.threshold(gray_menu, 150, 255, cv2.THRESH_BINARY)
    try:
        text_menu = pytesseract.image_to_string(thresh_menu, config=tess_config_6).lower()
        if lang == "Deutsch":
            if "renn-event" in text_menu or "renn event" in text_menu:
                return "PRE_RACE"
        elif lang == "Français":
            if "course" in text_menu or "evenement" in text_menu or "événement" in text_menu:
                return "PRE_RACE"
        elif lang == "Español":
            if "carrera" in text_menu or "evento" in text_menu:
                return "PRE_RACE"
        elif lang == "Italiano":
            if "gara" in text_menu or "evento" in text_menu:
                return "PRE_RACE"
        elif lang == "Português":
            if "corrida" in text_menu or "evento" in text_menu:
                return "PRE_RACE"
        elif lang == "Polski":
            if "wyscig" in text_menu or "wyścig" in text_menu or "wydarzenie" in text_menu:
                return "PRE_RACE"
        elif lang == "Nederlands":
            if "race" in text_menu or "evenement" in text_menu:
                return "PRE_RACE"
        elif lang == "Türkçe":
            if "yaris" in text_menu or "yarış" in text_menu or "etkinlik" in text_menu:
                return "PRE_RACE"
        elif lang == "Русский":
            if "гонка" in text_menu or "заезд" in text_menu or "событие" in text_menu or "начат" in text_menu:
                return "PRE_RACE"
        else: # Default: English
            if "race event" in text_menu or "start race" in text_menu or "race" in text_menu:
                return "PRE_RACE"
    except: pass

    # 3. ANNA/LINK scannen (Nur als Lebenszeichen/Keepalive für den Failsafe)
    img_drive = np.array(sct.grab(regions["drive"]))
    gray_drive = cv2.cvtColor(img_drive, cv2.COLOR_BGRA2GRAY)
    gray_drive = cv2.resize(gray_drive, (0,0), fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
    _, thresh_drive = cv2.threshold(gray_drive, 130, 255, cv2.THRESH_BINARY)
    try:
        text_drive = pytesseract.image_to_string(thresh_drive, config=tess_config_11).lower()
        if any(word in text_drive for word in ["anna", "link", "анна", "линк"]):
            return "DRIVING_ANNA"
    except: pass
        
    return "UNKNOWN"

def tap_key(hexKeyCode, duration=0.1):
    # Humanization: add randomized jitter between -0.05 and +0.08 seconds
    jitter_duration = duration + random.uniform(-0.05, 0.08)
    if jitter_duration < 0.05: jitter_duration = 0.05
    press_key(hexKeyCode)
    time.sleep(jitter_duration)
    release_key(hexKeyCode)

TRANSLATIONS = {
    "Deutsch": {
        "status_ready": "BEREIT", "status_running": "LÄUFT", "status_stopped": "GESTOPPT", "laps": "Runden",
        "lang_lbl": "Sprache:", "log_changed": "[*] Sprache auf Deutsch geändert", "log_start": "[*] Bot gestartet...",
        "log_stop": "[*] Bot manuell gestoppt.", "log_gas": "[+] Gebe Gas", "log_lap": "[*] RUNDE {lap} BEENDET!",
        "log_new_event": "[*] Starte neues Event...", "log_fallback": "[+] Fallback (ANNA): Gebe Gas!", "log_failsafe": "[-] Failsafe: Neustart erzwungen",
        "log_tab_in": "[*] Bitte innerhalb 5 sec ins spiel tabben !!",
        "log_auto_stop": "✅ AUTO-STOP: Ziel von {target} Runden erreicht. Bot beendet sich."
    },
    "English": {
        "status_ready": "READY", "status_running": "RUNNING", "status_stopped": "STOPPED", "laps": "Laps",
        "lang_lbl": "Language:", "log_changed": "[*] Language changed to English", "log_start": "[*] Bot started...",
        "log_stop": "[*] Bot stopped manually.", "log_gas": "[+] Accelerating", "log_lap": "[*] LAP {lap} FINISHED!",
        "log_new_event": "[*] Starting new event...", "log_fallback": "[+] Fallback (ANNA): Accelerating!", "log_failsafe": "[-] Failsafe: Forced restart",
        "log_tab_in": "[*] Please tab into the game within 5 seconds!",
        "log_auto_stop": "✅ AUTO-STOP: Target of {target} laps reached. Bot is exiting."
    },
    "Français": {
        "status_ready": "PRÊT", "status_running": "EN COURS", "status_stopped": "ARRÊTÉ", "laps": "Tours",
        "lang_lbl": "Langue:", "log_changed": "[*] Langue changée en Français", "log_start": "[*] Bot démarré...",
        "log_stop": "[*] Bot arrêté manuellement.", "log_gas": "[+] Accélération", "log_lap": "[*] TOUR {lap} TERMINÉ!",
        "log_new_event": "[*] Démarrage d'un nouvel événement...", "log_fallback": "[+] Fallback (ANNA): Accélération!", "log_failsafe": "[-] Failsafe: Redémarrage forcé",
        "log_tab_in": "[*] Veuillez retourner au jeu dans les 5 secondes!",
        "log_auto_stop": "✅ AUTO-STOP: Objectif de {target} tours atteint. Arrêt du bot."
    },
    "Español": {
        "status_ready": "LISTO", "status_running": "EN MARCHA", "status_stopped": "DETENIDO", "laps": "Vueltas",
        "lang_lbl": "Idioma:", "log_changed": "[*] Idioma cambiado a Español", "log_start": "[*] Bot iniciado...",
        "log_stop": "[*] Bot detenido manualmente.", "log_gas": "[+] Acelerando", "log_lap": "[*] VUELTA {lap} TERMINADA!",
        "log_new_event": "[*] Iniciando nuevo evento...", "log_fallback": "[+] Fallback (ANNA): Acelerando!", "log_failsafe": "[-] Failsafe: Reinicio forzado",
        "log_tab_in": "[*] ¡Por favor, vuelve al juego en 5 segundos!",
        "log_auto_stop": "✅ AUTO-STOP: Meta de {target} vueltas alcanzada. El bot se detiene."
    },
    "Italiano": {
        "status_ready": "PRONTO", "status_running": "IN ESECUZIONE", "status_stopped": "FERMATO", "laps": "Giri",
        "lang_lbl": "Lingua:", "log_changed": "[*] Lingua cambiata in Italiano", "log_start": "[*] Bot avviato...",
        "log_stop": "[*] Bot fermato manualmente.", "log_gas": "[+] Accelerando", "log_lap": "[*] GIRO {lap} COMPLETATO!",
        "log_new_event": "[*] Avvio nuovo evento...", "log_fallback": "[+] Fallback (ANNA): Accelerando!", "log_failsafe": "[-] Failsafe: Riavvio forzato",
        "log_tab_in": "[*] Torna al gioco entro 5 secondi!",
        "log_auto_stop": "✅ AUTO-STOP: Obiettivo di {target} giri raggiunto. Il bot si ferma."
    },
    "Português": {
        "status_ready": "PRONTO", "status_running": "EM EXECUÇÃO", "status_stopped": "PARADO", "laps": "Voltas",
        "lang_lbl": "Idioma:", "log_changed": "[*] Idioma alterado para Português", "log_start": "[*] Bot iniciado...",
        "log_stop": "[*] Bot parado manualmente.", "log_gas": "[+] Acelerando", "log_lap": "[*] VOLTA {lap} CONCLUÍDA!",
        "log_new_event": "[*] Iniciando novo evento...", "log_fallback": "[+] Fallback (ANNA): Acelerando!", "log_failsafe": "[-] Failsafe: Reinício forçado",
        "log_tab_in": "[*] Volte ao jogo em 5 segundos!",
        "log_auto_stop": "✅ AUTO-STOP: Alvo de {target} voltas atingido. Bot finalizando."
    },
    "Polski": {
        "status_ready": "GOTOWY", "status_running": "DZIAŁA", "status_stopped": "ZATRZYMANY", "laps": "Okrążenia",
        "lang_lbl": "Język:", "log_changed": "[*] Język zmieniony na Polski", "log_start": "[*] Bot uruchomiony...",
        "log_stop": "[*] Bot zatrzymany ręcznie.", "log_gas": "[+] Przyspieszanie", "log_lap": "[*] OKRĄŻENIE {lap} ZAKOŃCZONE!",
        "log_new_event": "[*] Rozpoczynanie nowego wydarzenia...", "log_fallback": "[+] Fallback (ANNA): Przyspieszanie!", "log_failsafe": "[-] Failsafe: Wymuszony restart",
        "log_tab_in": "[*] Wróć do gry w ciągu 5 sekund!",
        "log_auto_stop": "✅ AUTO-STOP: Cel {target} okrążeń osiągnięty. Bot kończy pracę."
    },
    "Nederlands": {
        "status_ready": "KLAAR", "status_running": "ACTIEF", "status_stopped": "GESTOPT", "laps": "Rondes",
        "lang_lbl": "Taal:", "log_changed": "[*] Taal gewijzigd naar Nederlands", "log_start": "[*] Bot gestart...",
        "log_stop": "[*] Bot handmatig gestopt.", "log_gas": "[+] Gas geven", "log_lap": "[*] RONDE {lap} VOLTOOID!",
        "log_new_event": "[*] Nieuw evenement starten...", "log_fallback": "[+] Fallback (ANNA): Gas geven!", "log_failsafe": "[-] Failsafe: Geforceerde herstart",
        "log_tab_in": "[*] Ga binnen 5 seconden terug naar de game!",
        "log_auto_stop": "✅ AUTO-STOP: Doel van {target} rondes bereikt. Bot stopt."
    },
    "Türkçe": {
        "status_ready": "HAZIR", "status_running": "ÇALIŞIYOR", "status_stopped": "DURDURULDU", "laps": "Turlar",
        "lang_lbl": "Dil:", "log_changed": "[*] Dil Türkçe olarak değiştirildi", "log_start": "[*] Bot başlatıldı...",
        "log_stop": "[*] Bot manuel olarak durduruldu.", "log_gas": "[+] Hızlanıyor", "log_lap": "[*] TUR {lap} TAMAMLANDI!",
        "log_new_event": "[*] Yeni etkinlik başlatılıyor...", "log_fallback": "[+] Fallback (ANNA): Hızlanıyor!", "log_failsafe": "[-] Failsafe: Zorunlu yeniden başlatma",
        "log_tab_in": "[*] Lütfen 5 saniye içinde oyuna dönün!",
        "log_auto_stop": "✅ AUTO-STOP: {target} tur hedefine ulaşıldı. Bot kapatılıyor."
    },
    "Русский": {
        "status_ready": "ГОТОВ", "status_running": "В ИГРЕ", "status_stopped": "ОСТАНОВЛЕН", "laps": "Круги",
        "lang_lbl": "Язык:", "log_changed": "[*] Язык изменен на Русский", "log_start": "[*] Бот запущен...",
        "log_stop": "[*] Бот остановлен вручную.", "log_gas": "[+] Газ", "log_lap": "[*] КРУГ {lap} ЗАВЕРШЕН!",
        "log_new_event": "[*] Запуск нового события...", "log_fallback": "[+] Fallback (ANNA): Газ!", "log_failsafe": "[-] Failsafe: Принудительный перезапуск",
        "log_tab_in": "[*] Вернитесь в игру в течение 5 секунд!",
        "log_auto_stop": "✅ AUTO-STOP: Цель из {target} кругов достигнута. Бот завершает работу."
    }
}

# --- GUI ---
class ForzaBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Forza Working Bot")
        self.root.geometry("550x450")
        self.root.configure(bg="#f0f0f0")
        self.root.attributes("-topmost", True)
        
        # Load Config
        self.config_path = "config.json"
        self.config = {"webhook_url": "", "target_laps": 0, "shutdown_on_finish": False}
        self.load_config()
        
        # UI Elements
        self.title_lbl = tk.Label(root, text="Forza Working Bot", font=("Arial", 22, "bold"), bg="#f0f0f0")
        self.title_lbl.pack(pady=(15, 5))
        
        self.status_lbl = tk.Label(root, text="BEREIT", font=("Arial", 16, "bold"), fg="green", bg="#f0f0f0")
        self.status_lbl.pack(pady=(0, 5))
        
        # Language Dropdown
        lang_frame = tk.Frame(root, bg="#f0f0f0")
        lang_frame.pack(pady=5)
        self.lang_lbl = tk.Label(lang_frame, text="Sprache / Language: ", font=("Arial", 10), bg="#f0f0f0")
        self.lang_lbl.pack(side=tk.LEFT)
        self.lang_var = tk.StringVar(value="English")
        self.lang_cb = ttk.Combobox(lang_frame, textvariable=self.lang_var, values=list(TRANSLATIONS.keys()), state="readonly", width=10, font=("Arial", 10))
        self.lang_cb.pack(side=tk.LEFT)
        self.lang_cb.bind("<<ComboboxSelected>>", self.on_lang_change)
        
        self.laps_lbl = tk.Label(root, text="Runden: 0", font=("Arial", 18, "bold"), bg="#f0f0f0")
        self.laps_lbl.pack(pady=(5, 10))
        
        # Buttons Frame
        btn_frame = tk.Frame(root, bg="#f0f0f0")
        btn_frame.pack(pady=5)
        
        self.btn_start = tk.Button(btn_frame, text="▶ START", width=12, font=("Arial", 10), command=self.start_bot)
        self.btn_start.pack(side=tk.LEFT, padx=5)
        
        self.btn_stop = tk.Button(btn_frame, text="⏹ STOP", width=12, font=("Arial", 10), state=tk.DISABLED, command=self.stop_bot)
        self.btn_stop.pack(side=tk.LEFT, padx=5)
        
        self.btn_settings = tk.Button(btn_frame, text="Settings ⚙️", width=15, font=("Arial", 10), command=self.open_settings)
        self.btn_settings.pack(side=tk.LEFT, padx=5)
        
        # Log Box
        self.log_box = scrolledtext.ScrolledText(root, width=65, height=10, font=("Consolas", 9))
        self.log_box.pack(pady=15, padx=20)
        
        self.running = False
        self.bot_thread = None
        self.drive_thread = None
        self.laps = 0
        self.driving_enabled = False

        self.on_lang_change()

    def load_config(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.config.update(json.load(f))
        except: pass

    def save_config(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
        except: pass

    def open_settings(self):
        top = tk.Toplevel(self.root)
        top.title("Settings")
        top.geometry("400x250")
        top.attributes("-topmost", True)
        
        tk.Label(top, text="Discord Webhook URL:").pack(pady=(10, 0))
        webhook_entry = tk.Entry(top, width=50)
        webhook_entry.pack(pady=5)
        webhook_entry.insert(0, self.config.get("webhook_url", ""))
        
        tk.Label(top, text="Auto-Stop after X Laps (0 = Infinite):").pack(pady=(10, 0))
        laps_entry = tk.Entry(top, width=10)
        laps_entry.pack(pady=5)
        laps_entry.insert(0, str(self.config.get("target_laps", 0)))
        
        shutdown_var = tk.BooleanVar(value=self.config.get("shutdown_on_finish", False))
        tk.Checkbutton(top, text="Shutdown PC after Auto-Stop", variable=shutdown_var).pack(pady=5)
        
        def save_and_close():
            self.config["webhook_url"] = webhook_entry.get().strip()
            try:
                self.config["target_laps"] = int(laps_entry.get().strip())
            except:
                self.config["target_laps"] = 0
            self.config["shutdown_on_finish"] = shutdown_var.get()
            self.save_config()
            top.destroy()
            
        tk.Button(top, text="Save", command=save_and_close).pack(pady=10)

    def send_webhook(self, message):
        url = self.config.get("webhook_url", "")
        if not url.startswith("http"): return
        
        def _send():
            try:
                data = json.dumps({"content": message}).encode('utf-8')
                req = urllib.request.Request(url, data=data, headers={'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/json'})
                urllib.request.urlopen(req, timeout=5)
            except Exception as e:
                self.root.after(0, self.log, f"[-] Webhook Fehler: {e}")
        threading.Thread(target=_send, daemon=True).start()

    def on_lang_change(self, event=None):
        lang = self.lang_var.get()
        t = TRANSLATIONS.get(lang, TRANSLATIONS["English"])
        
        if self.running:
            self.status_lbl.config(text=t["status_running"])
        else:
            self.status_lbl.config(text=t["status_ready"])
            
        self.laps_lbl.config(text=f"{t['laps']}: {self.laps}")
        self.lang_lbl.config(text=t["lang_lbl"])
        self.log(t["log_changed"])

    def log(self, message):
        self.log_box.insert(tk.END, message + "\n")
        self.log_box.see(tk.END)

    def start_bot(self):
        if self.running: return
        self.running = True
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        lang = self.lang_var.get()
        t = TRANSLATIONS.get(lang, TRANSLATIONS["English"])
        self.status_lbl.config(text=t["status_running"], fg="blue")
        self.log(t["log_start"])
        self.log(t["log_tab_in"])
        
        # 5 Sekunden Delay bevor die Threads wirklich loslegen
        self.start_timer = self.root.after(5000, self._launch_threads)
        
    def _launch_threads(self):
        if not self.running: return
        self.bot_thread = threading.Thread(target=self.bot_loop, daemon=True)
        self.bot_thread.start()
        
        self.drive_thread = threading.Thread(target=self.drive_macro_loop, daemon=True)
        self.drive_thread.start()

    def stop_bot(self):
        if not self.running: return
        self.running = False
        
        # Falls während der 5 Sekunden gestoppt wurde, Timer abbrechen
        if hasattr(self, 'start_timer'):
            self.root.after_cancel(self.start_timer)
            
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        lang = self.lang_var.get()
        t = TRANSLATIONS.get(lang, TRANSLATIONS["English"])
        self.status_lbl.config(text=t["status_stopped"], fg="red")
        self.log(t["log_stop"])
        self.driving_enabled = False
        release_key(DIK_W)
        release_key(DIK_A)
        release_key(DIK_D)

    def drive_macro_loop(self):
        while self.running:
            if self.driving_enabled:
                # Gas geben
                press_key(DIK_W)
                
                # Links lenken (angepasst für weniger Aufschaukeln)
                press_key(DIK_A)
                time.sleep(0.08)
                release_key(DIK_A)
                
                # Halte Gas für ca 0.8 Sekunden
                for _ in range(8):
                    if not self.driving_enabled: break
                    time.sleep(0.1)
                
                if not self.driving_enabled: continue
                
                # Rechts lenken (angepasst für weniger Aufschaukeln)
                press_key(DIK_D)
                time.sleep(0.08)
                release_key(DIK_D)
                
                # Halte Gas für weitere ca 0.8 Sekunden (insgesamt Gas: ~1.7s)
                for _ in range(8):
                    if not self.driving_enabled: break
                    time.sleep(0.1)
                    
                if not self.driving_enabled: continue
                
                # Gas loslassen ("und dann wieder ned" - Bot langsamer machen)
                release_key(DIK_W)
                
                # Rollen lassen für 1.5 Sekunden
                for _ in range(15):
                    if not self.driving_enabled: break
                    time.sleep(0.1)
            else:
                time.sleep(0.1)

    def enable_driving(self):
        if self.running:
            lang = self.lang_var.get()
            t = TRANSLATIONS.get(lang, TRANSLATIONS["English"])
            self.log(t["log_gas"])
            self.driving_enabled = True

    def bot_loop(self):
        last_action_time = 0
        missed_time_frames = 0
        try:
            with mss() as sct:
                self.driving_enabled = False
                
                # Dynamische Auflösungsskalierung (Basis 1920x1080)
                monitor = sct.monitors[1]
                w = monitor["width"]
                h = monitor["height"]
                scale_x = w / 1920.0
                scale_y = h / 1080.0
                
                regions = {
                    "leaderboard": {"top": int(150 * scale_y), "left": int(150 * scale_x), "width": int(600 * scale_x), "height": int(200 * scale_y)},
                    "menu": {"top": int(400 * scale_y), "left": int(0 * scale_x), "width": int(800 * scale_x), "height": int(600 * scale_y)},
                    "drive": {"top": int(700 * scale_y), "left": int(0 * scale_x), "width": int(600 * scale_x), "height": int(380 * scale_y)}
                }
                
                self.root.after(0, self.log, f"[*] Auflösung: {w}x{h} (Scaling X:{scale_x:.2f} Y:{scale_y:.2f})")
                
                while self.running:
                    if keyboard.is_pressed('q'):
                        self.root.after(0, self.stop_bot)
                        break
                        
                    # State erkennen
                    lang = self.lang_var.get()
                    t = TRANSLATIONS.get(lang, TRANSLATIONS["English"])
                    state = parse_screen(sct, lang, regions)
                    current_time = time.time()
                    
                    # Cooldown von 5 Sekunden
                    cooldown_active = (current_time - last_action_time) < 5.0
                    
                    if state == "POST_RACE" and not cooldown_active:
                        if self.driving_enabled:
                            self.driving_enabled = False
                            release_key(DIK_W)
                            
                        self.laps += 1
                        laps_text = f"{t['laps']}: {self.laps}"
                        self.root.after(0, self.laps_lbl.config, {"text": laps_text})
                        log_msg = t["log_lap"].format(lap=self.laps)
                        self.root.after(0, self.log, log_msg)
                        
                        # Webhook & Target Farming Logic
                        self.send_webhook(log_msg)
                        
                        target = self.config.get("target_laps", 0)
                        if target > 0 and self.laps >= target:
                            stop_msg = t["log_auto_stop"].format(target=target)
                            self.root.after(0, self.log, stop_msg)
                            self.send_webhook(stop_msg)
                            self.root.after(0, self.stop_bot)
                            if self.config.get("shutdown_on_finish", False):
                                self.root.after(0, self.log, "[*] PC wird in 60 Sekunden heruntergefahren...")
                                os.system("shutdown /s /t 60")
                            break
                        
                        tap_key(DIK_X, 0.2)
                        time.sleep(random.uniform(0.15, 0.35))
                        tap_key(DIK_RETURN, 0.2)
                        
                        last_action_time = time.time()
                        missed_time_frames = 0
                        
                    elif state == "PRE_RACE" and not cooldown_active:
                        if self.driving_enabled:
                            self.driving_enabled = False
                            release_key(DIK_W)
                            
                        self.root.after(0, self.log, t["log_new_event"])
                        tap_key(DIK_RETURN, 0.2)
                        
                        last_action_time = time.time()
                        missed_time_frames = 0
                        
                        self.root.after(3500, self.enable_driving)
                        
                    elif state == "DRIVING_ANNA":
                        missed_time_frames = 0
                        if not self.driving_enabled:
                            self.root.after(0, self.log, t["log_fallback"])
                            self.driving_enabled = True
                    else:
                        # UNKNOWN State (Ladescreen, Countdown, Übergänge)
                        if self.driving_enabled:
                            missed_time_frames += 1
                            if missed_time_frames > 100: # 20 Sekunden (100 * 0.2s) Toleranz für Ladescreens
                                self.root.after(0, self.log, t["log_failsafe"])
                                self.driving_enabled = False
                                release_key(DIK_W)
                                
                                self.laps += 1
                                laps_text = f"{t['laps']}: {self.laps} (Failsafe)"
                                self.root.after(0, self.laps_lbl.config, {"text": laps_text})
                                
                                # Blind Restart Failsafe
                                tap_key(DIK_X, 0.2)
                                time.sleep(random.uniform(0.4, 0.7))
                                tap_key(DIK_RETURN, 0.2)
                                
                                last_action_time = time.time()
                                missed_time_frames = 0
                            
                    time.sleep(0.2)
                    
        except Exception as e:
            self.root.after(0, self.log, f"[-] Fehler: {e}")
            self.root.after(0, self.stop_bot)
            
        self.driving_enabled = False
        release_key(DIK_W)
        release_key(DIK_A)
        release_key(DIK_D)

if __name__ == "__main__":
    root = tk.Tk()
    app = ForzaBotGUI(root)
    root.mainloop()
