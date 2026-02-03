"""
Dark Souls Death Counter
Автоматический счётчик смертей

Детекция по шаблону - ищет картинку "ВЫ ПОГИБЛИ" (death.png) на экране.
"""

import tkinter as tk
import json
import time
import threading
import ctypes
from pathlib import Path

try:
    import mss
    import cv2
    import numpy as np
    SCREEN_OK = True
except ImportError:
    SCREEN_OK = False

try:
    import win32gui
    import win32con
    WIN32_OK = True
except ImportError:
    WIN32_OK = False

SAVE_FILE = Path(__file__).parent / "death_count.json"
TEMPLATE_FILE = Path(__file__).parent / "death.png"


class DeathDetector:
    """Детектор смерти по шаблону изображения"""
    
    def __init__(self):
        self.last_death_time = 0
        self.cooldown = 15.0  # Секунд паузы после смерти
        self.in_cooldown = False  # Флаг кулдауна
        
        # Загружаем шаблон в разных масштабах
        self.templates = []  # Список (template, scale)
        self.debug_mode = True  # Показывать отладку
        self.debug_counter = 0
        self._load_template()
    
    def _load_template(self):
        """Загрузить шаблон изображения смерти в разных масштабах"""
        if not SCREEN_OK:
            return
        
        if not TEMPLATE_FILE.exists():
            print(f"[!] Файл шаблона не найден: {TEMPLATE_FILE}")
            return
        
        try:
            # Загружаем оригинальный шаблон
            template_orig = cv2.imread(str(TEMPLATE_FILE), cv2.IMREAD_GRAYSCALE)
            if template_orig is None:
                print("[!] Не удалось загрузить шаблон")
                return
            
            h, w = template_orig.shape
            print(f"[+] Шаблон загружен: {w}x{h}")
            
            # Создаём шаблоны разных размеров (от 50% до 200%)
            scales = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.4, 1.6, 1.8, 2.0]
            for scale in scales:
                new_w = int(w * scale)
                new_h = int(h * scale)
                if new_w > 10 and new_h > 10:
                    resized = cv2.resize(template_orig, (new_w, new_h), interpolation=cv2.INTER_AREA)
                    self.templates.append((resized, scale))
            
            print(f"[+] Создано {len(self.templates)} масштабов шаблона")
            
        except Exception as e:
            print(f"[!] Ошибка загрузки шаблона: {e}")
    
    def check_screen(self) -> bool:
        """Проверить экран на наличие шаблона смерти"""
        if not SCREEN_OK or not self.templates:
            return False
        
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                width = monitor["width"]
                height = monitor["height"]
                
                # Область поиска - только центр где появляется "ВЫ ПОГИБЛИ"
                # Исключаем верхний UI (здоровье) и нижний UI (предметы, души)
                region = {
                    "left": int(width * 0.25),      # 25% слева
                    "top": int(height * 0.35),      # 35% сверху
                    "width": int(width * 0.5),      # 50% ширины (центр)
                    "height": int(height * 0.20)    # 20% высоты (узкая полоса)
                }
                
                # Делаем скриншот
                screenshot = sct.grab(region)
                
                # Конвертируем в numpy array для OpenCV
                img = np.array(screenshot)
                
                # Конвертируем BGRA -> Grayscale
                gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
                
                best_val = 0
                best_scale = 0
                
                # Пробуем все масштабы шаблона
                for template, scale in self.templates:
                    # Проверяем что шаблон меньше изображения
                    if template.shape[0] > gray.shape[0] or template.shape[1] > gray.shape[1]:
                        continue
                    
                    # Ищем шаблон
                    result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, _ = cv2.minMaxLoc(result)
                    
                    if max_val > best_val:
                        best_val = max_val
                        best_scale = scale
                
                # Отладка - показываем каждые 25 проверок (~5 сек)
                if self.debug_mode:
                    self.debug_counter += 1
                    if self.debug_counter >= 25:
                        self.debug_counter = 0
                        print(f"[DEBUG] Совпадение: {best_val:.1%} (масштаб {best_scale})")
                
                # Порог совпадения (повысил т.к. область теперь точнее)
                threshold = 0.30  # 30%
                
                if best_val >= threshold:
                    print(f"[!] Обнаружена смерть! Совпадение: {best_val:.1%}")
                    return True
                    
        except Exception as e:
            print(f"[!] Ошибка проверки экрана: {e}")
        
        return False
    
    def check_death(self) -> bool:
        """Проверить смерть с простым кулдауном"""
        current_time = time.time()
        time_since_death = current_time - self.last_death_time
        
        # Кулдаун после смерти - игнорируем все проверки
        if self.in_cooldown:
            if time_since_death >= self.cooldown:
                self.in_cooldown = False
                print("[*] Снова слежу за смертями...")
            return False
        
        # Проверяем экран
        if self.check_screen():
            self.last_death_time = current_time
            self.in_cooldown = True
            print(f"[*] Пауза {int(self.cooldown)} сек (надпись на экране)...")
            return True
        
        return False
    
    def stop(self):
        pass


class DeathCounter:
    def __init__(self):
        self.deaths = 0
        self.root = None
        self.running = False
        self.detector = DeathDetector()
        self.hwnd = None
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
        text = f"☠ {self.deaths}"
        x, y = 10, 25
        
        # Тень для читаемости
        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                if dx or dy:
                    self.canvas.create_text(x+dx, y+dy, text=text,
                        font=('Arial', 28, 'bold'), fill='#000000', anchor='w')
        
        # Красный текст как в игре
        self.canvas.create_text(x, y, text=text,
            font=('Arial', 28, 'bold'), fill='#C41E3A', anchor='w')
    
    def detection_loop(self):
        while self.running:
            if self.detector.check_death():
                self.add_death()
            time.sleep(0.2)
    
    def _get_hwnd(self):
        """Получить правильный HWND окна Tk"""
        if self.hwnd:
            return self.hwnd
        
        # Tk использует вложенные окна, нужен родительский HWND
        try:
            # Метод 1: через wm frame
            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            if hwnd == 0:
                hwnd = self.root.winfo_id()
            self.hwnd = hwnd
        except:
            self.hwnd = self.root.winfo_id()
        
        return self.hwnd
    
    def create_overlay(self):
        self.root = tk.Tk()
        self.root.title("Deaths")
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-transparentcolor', '#010101')
        self.root.configure(bg='#010101')
        self.root.geometry('180x50+50+50')
        
        self.canvas = tk.Canvas(self.root, bg='#010101', highlightthickness=0,
                                width=180, height=50)
        self.canvas.pack()
        self._redraw()
        
        self._drag = {"x": 0, "y": 0}
        self.canvas.bind('<Button-1>', lambda e: self._drag.update({"x": e.x, "y": e.y}))
        self.canvas.bind('<B1-Motion>', self._do_drag)
        self.canvas.bind('<Button-3>', self._reset)
        
        # Настройка после отрисовки первого кадра
        self.root.after(100, self._setup_win)
    
    def _do_drag(self, e):
        self.root.geometry(f'+{self.root.winfo_x() + e.x - self._drag["x"]}+{self.root.winfo_y() + e.y - self._drag["y"]}')
    
    def _reset(self, e=None):
        self.deaths = 0
        self.save()
        self.update_display()
        print("[*] Сброс счётчика")
    
    def _setup_win(self):
        """Настроить окно для работы поверх полноэкранных игр"""
        if not WIN32_OK:
            self.root.after(100, self._keep_top_simple)
            return
        
        try:
            hwnd = self._get_hwnd()
            
            # Получаем текущие стили
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            
            # Добавляем стили:
            # WS_EX_LAYERED - для прозрачности
            # WS_EX_TOOLWINDOW - не показывать в таскбаре
            # WS_EX_NOACTIVATE - не забирать фокус
            # WS_EX_TOPMOST - поверх всех окон
            new_style = (ex_style | 
                        win32con.WS_EX_LAYERED | 
                        win32con.WS_EX_TOOLWINDOW | 
                        win32con.WS_EX_NOACTIVATE |
                        win32con.WS_EX_TOPMOST)
            
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, new_style)
            
            # Устанавливаем прозрачность
            win32gui.SetLayeredWindowAttributes(hwnd, 0, 245, win32con.LWA_ALPHA)
            
            # Принудительно ставим поверх
            win32gui.SetWindowPos(
                hwnd, 
                win32con.HWND_TOPMOST,
                0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW
            )
            
            print("[+] Окно настроено для работы поверх игр")
        except Exception as e:
            print(f"[!] Ошибка настройки окна: {e}")
        
        # Запускаем цикл поддержания поверх
        self.root.after(100, self._keep_top)
    
    def _keep_top_simple(self):
        """Простой метод поддержания поверх (без win32)"""
        if self.root and self.running:
            try:
                self.root.attributes('-topmost', True)
                self.root.lift()
            except:
                pass
            self.root.after(50, self._keep_top_simple)
    
    def _keep_top(self):
        """Агрессивно поддерживать окно поверх игры"""
        if not self.root or not self.running:
            return
        
        try:
            hwnd = self._get_hwnd()
            
            # Ставим окно поверх без изменения фокуса
            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_TOPMOST,
                0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
            )
        except:
            pass
        
        # Проверяем каждые 50мс (20 раз в секунду)
        self.root.after(50, self._keep_top)
    
    def run(self):
        print()
        print("=" * 50)
        print("   DARK SOULS DEATH COUNTER")
        print("=" * 50)
        print()
        print(f"   Смертей: {self.deaths}")
        print()
        print("   Детекция: по шаблону (death.png)")
        print("   ПКМ на счётчике = сброс")
        print("   Ctrl+C = выход")
        print()
        print("=" * 50)
        print()
        
        if not SCREEN_OK:
            print("[!] Зависимости не установлены - запустите: uv sync")
            return
        
        if not self.detector.templates:
            print("[!] Файл death.png не найден! Положите его рядом с main.py")
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
