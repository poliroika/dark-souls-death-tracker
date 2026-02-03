"""
Dark Souls Death Counter
Автоматический счётчик смертей

Методы детекции:
1. Экран - ищет красный текст "Вы погибли"
2. Звук - слушает характерный звук смерти
"""

import tkinter as tk
import json
import time
import threading
from pathlib import Path

try:
    import mss
    from PIL import Image
    SCREEN_OK = True
except ImportError:
    SCREEN_OK = False

try:
    import sounddevice as sd
    import numpy as np
    SOUND_OK = True
except ImportError:
    SOUND_OK = False

try:
    import win32gui
    import win32con
    WIN32_OK = True
except ImportError:
    WIN32_OK = False

SAVE_FILE = Path(__file__).parent / "death_count.json"


class DeathDetector:
    """Детектор смерти по экрану и звуку"""
    
    def __init__(self):
        self.last_death_time = 0
        self.cooldown = 4.0  # Секунд между смертями
        
        # Для звука
        self.audio_buffer = []
        self.sound_threshold = 0.15  # Порог громкости
        self.loud_duration = 0
        self.stream = None
        
        if SOUND_OK:
            self._start_audio()
    
    def _start_audio(self):
        """Запустить захват аудио"""
        try:
            def audio_callback(indata, frames, time_info, status):
                # Вычисляем громкость
                volume = np.sqrt(np.mean(indata**2))
                self.audio_buffer.append(volume)
                if len(self.audio_buffer) > 30:
                    self.audio_buffer.pop(0)
            
            self.stream = sd.InputStream(
                channels=1,
                samplerate=22050,
                blocksize=1024,
                callback=audio_callback
            )
            self.stream.start()
            print("[+] Аудио захват запущен")
        except Exception as e:
            print(f"[!] Не удалось запустить аудио: {e}")
            self.stream = None
    
    def check_sound(self) -> bool:
        """Проверить был ли громкий звук (смерть)"""
        if not self.audio_buffer:
            return False
        
        current_volume = np.mean(self.audio_buffer[-5:]) if len(self.audio_buffer) >= 5 else 0
        avg_volume = np.mean(self.audio_buffer) if self.audio_buffer else 0
        
        # Если текущая громкость значительно выше средней
        if current_volume > avg_volume * 2.5 and current_volume > self.sound_threshold:
            self.loud_duration += 1
            # Нужно несколько фреймов подряд громкого звука
            if self.loud_duration >= 3:
                self.loud_duration = 0
                return True
        else:
            self.loud_duration = 0
        
        return False
    
    def check_screen(self) -> bool:
        """Проверить экран на надпись смерти"""
        if not SCREEN_OK:
            return False
        
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                width = monitor["width"]
                height = monitor["height"]
                
                # Центр экрана где появляется "Вы погибли"
                region = {
                    "left": width // 4,
                    "top": height // 3,
                    "width": width // 2,
                    "height": height // 4
                }
                
                screenshot = sct.grab(region)
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                
                # Считаем красные пиксели
                red_count = 0
                dark_red_count = 0
                total = 0
                
                pixels = img.load()
                for x in range(0, img.width, 4):
                    for y in range(0, img.height, 4):
                        r, g, b = pixels[x, y]
                        total += 1
                        
                        # Красный текст: R высокий, G и B низкие
                        # Расширенный диапазон для разных версий
                        if r > 100 and g < 60 and b < 60 and r > g + 60 and r > b + 60:
                            red_count += 1
                        
                        # Тёмно-красный (некоторые версии)
                        if 80 < r < 180 and g < 40 and b < 40:
                            dark_red_count += 1
                
                # Если много красного - смерть
                red_ratio = (red_count + dark_red_count) / total if total > 0 else 0
                
                if red_ratio > 0.008:  # 0.8% красных пикселей
                    return True
                    
        except:
            pass
        
        return False
    
    def check_death(self) -> bool:
        """Проверить смерть любым методом"""
        if time.time() - self.last_death_time < self.cooldown:
            return False
        
        # Проверяем экран
        if self.check_screen():
            self.last_death_time = time.time()
            return True
        
        # Проверяем звук
        if SOUND_OK and self.check_sound():
            self.last_death_time = time.time()
            return True
        
        return False
    
    def stop(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()


class DeathCounter:
    def __init__(self):
        self.deaths = 0
        self.root = None
        self.running = False
        self.detector = DeathDetector()
        self.load()
    
    def load(self):
        try:
            if SAVE_FILE.exists():
                with open(SAVE_FILE, 'r') as f:
                    self.deaths = json.load(f).get('deaths', 0)
        except:
            pass
    
    def save(self):
        try:
            with open(SAVE_FILE, 'w') as f:
                json.dump({'deaths': self.deaths}, f)
        except:
            pass
    
    def add_death(self):
        self.deaths += 1
        self.save()
        self.update_display()
        print(f"[!] ВЫ ПОГИБЛИ! Смертей: {self.deaths}")
    
    def update_display(self):
        if self.root and self.canvas:
            self.root.after(0, self._redraw)
    
    def _redraw(self):
        self.canvas.delete("all")
        text = f"Смертей: {self.deaths}"
        x, y = 10, 25
        
        for dx in [-2, 0, 2]:
            for dy in [-2, 0, 2]:
                if dx or dy:
                    self.canvas.create_text(x+dx, y+dy, text=text,
                        font=('Arial', 24, 'bold'), fill='#000000', anchor='w')
        
        self.canvas.create_text(x, y, text=text,
            font=('Arial', 24, 'bold'), fill='#FFFFFF', anchor='w')
    
    def detection_loop(self):
        while self.running:
            if self.detector.check_death():
                self.add_death()
            time.sleep(0.2)
    
    def create_overlay(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-transparentcolor', '#010101')
        self.root.configure(bg='#010101')
        self.root.geometry('+50+50')
        
        self.canvas = tk.Canvas(self.root, bg='#010101', highlightthickness=0,
                                width=300, height=50)
        self.canvas.pack()
        self._redraw()
        
        self._drag = {"x": 0, "y": 0}
        self.canvas.bind('<Button-1>', lambda e: self._drag.update({"x": e.x, "y": e.y}))
        self.canvas.bind('<B1-Motion>', self._do_drag)
        self.canvas.bind('<Button-3>', self._reset)
        
        if WIN32_OK:
            self.root.after(100, self._setup_win)
            self.root.after(500, self._keep_top)
    
    def _do_drag(self, e):
        self.root.geometry(f'+{self.root.winfo_x() + e.x - self._drag["x"]}+{self.root.winfo_y() + e.y - self._drag["y"]}')
    
    def _reset(self, e=None):
        self.deaths = 0
        self.save()
        self.update_display()
        print("[*] Сброс")
    
    def _setup_win(self):
        try:
            hwnd = int(self.root.winfo_id())
            styles = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                styles | win32con.WS_EX_LAYERED | win32con.WS_EX_TOOLWINDOW | win32con.WS_EX_NOACTIVATE)
            win32gui.SetLayeredWindowAttributes(hwnd, 0, 230, win32con.LWA_ALPHA)
        except:
            pass
    
    def _keep_top(self):
        if self.root and self.running:
            try:
                hwnd = int(self.root.winfo_id())
                win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)
            except:
                pass
            self.root.after(300, self._keep_top)
    
    def run(self):
        print()
        print("=" * 50)
        print("   DARK SOULS DEATH COUNTER")
        print("=" * 50)
        print()
        print(f"   Смертей: {self.deaths}")
        print()
        print("   Детекция: экран + звук")
        print("   ПКМ на счётчике = сброс")
        print("   Ctrl+C = выход")
        print()
        print("=" * 50)
        print()
        
        if not SCREEN_OK:
            print("[!] mss/pillow не установлены")
        if not SOUND_OK:
            print("[!] sounddevice/numpy не установлены")
        
        if not SCREEN_OK and not SOUND_OK:
            print("[!] Запустите: uv sync")
            return
        
        print("[*] Слежу за смертями...")
        print()
        
        self.running = True
        
        thread = threading.Thread(target=self.detection_loop, daemon=True)
        thread.start()
        
        self.create_overlay()
        
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            self.detector.stop()


def main():
    counter = DeathCounter()
    counter.run()


if __name__ == "__main__":
    main()
