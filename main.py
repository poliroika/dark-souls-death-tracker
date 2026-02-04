"""
Dark Souls Death Counter
Работает с DSDeaths - читает счётчик из файла DSDeaths.txt

DSDeaths читает death count напрямую из RAM игры и пишет в файл.
Этот скрипт - только оверлей для отображения числа.

https://github.com/quidrex/DSDeaths
"""

import tkinter as tk
import ctypes
import ctypes.wintypes
import time
import threading
from pathlib import Path

# Windows API константы
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x80000
WS_EX_TRANSPARENT = 0x20
WS_EX_TOOLWINDOW = 0x80
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOPMOST = 0x8
LWA_ALPHA = 0x2
LWA_COLORKEY = 0x1
HWND_TOPMOST = -1
SWP_NOMOVE = 0x2
SWP_NOSIZE = 0x1
SWP_NOACTIVATE = 0x10
SWP_SHOWWINDOW = 0x40

# Windows API функции
user32 = ctypes.windll.user32
user32.SetWindowLongW.argtypes = [ctypes.wintypes.HWND, ctypes.c_int, ctypes.c_long]
user32.SetWindowLongW.restype = ctypes.c_long
user32.GetWindowLongW.argtypes = [ctypes.wintypes.HWND, ctypes.c_int]
user32.GetWindowLongW.restype = ctypes.c_long
user32.SetLayeredWindowAttributes.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.COLORREF, ctypes.wintypes.BYTE, ctypes.wintypes.DWORD]
user32.SetLayeredWindowAttributes.restype = ctypes.wintypes.BOOL
user32.SetWindowPos.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
user32.SetWindowPos.restype = ctypes.wintypes.BOOL

# Файл от DSDeaths.exe
SCRIPT_DIR = Path(__file__).parent
DSDEATHS_FILE = SCRIPT_DIR / "DSDeaths.txt"

ALTERNATIVE_PATHS = [
    SCRIPT_DIR / "DSDeaths.txt",
    Path.home() / "Desktop" / "DSDeaths.txt",
    Path("C:/DSDeaths/DSDeaths.txt"),
]


class DeathOverlay:
    """Прозрачный оверлей со счётчиком смертей"""
    
    def __init__(self):
        self.deaths = 0
        self.root = None
        self.canvas = None
        self.running = False
        self.hwnd = None
        self.dsdeaths_path = None
        self.drag_enabled = True
        self._find_dsdeaths_file()
    
    def _find_dsdeaths_file(self):
        """Найти файл DSDeaths.txt"""
        for path in ALTERNATIVE_PATHS:
            if path.exists():
                self.dsdeaths_path = path
                print(f"[+] Найден DSDeaths.txt: {path}")
                return
        
        self.dsdeaths_path = DSDEATHS_FILE
        print(f"[*] Жду создания файла: {self.dsdeaths_path}")
    
    def read_deaths(self) -> int:
        """Прочитать число смертей из DSDeaths.txt"""
        try:
            if self.dsdeaths_path and self.dsdeaths_path.exists():
                text = self.dsdeaths_path.read_text(encoding='utf-8').strip()
                if text.isdigit():
                    return int(text)
        except:
            pass
        return self.deaths
    
    def monitor_loop(self):
        """Мониторинг файла DSDeaths.txt"""
        last_deaths = -1
        
        while self.running:
            current = self.read_deaths()
            
            if current != last_deaths:
                last_deaths = current
                
                if current > self.deaths:
                    print(f"[!] ВЫ ПОГИБЛИ! Смертей: {current}")
                
                self.deaths = current
                self.update_display()
            
            time.sleep(0.5)
    
    def update_display(self):
        """Обновить отображение"""
        if self.root and self.canvas:
            self.root.after(0, self._redraw)
    
    def _redraw(self):
        """Перерисовать счётчик"""
        self.canvas.delete("all")
        text = f"☠ {self.deaths}"
        x, y = 10, 25
        
        # Тень
        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                if dx or dy:
                    self.canvas.create_text(
                        x + dx, y + dy, 
                        text=text,
                        font=('Arial', 28, 'bold'), 
                        fill='#000000', 
                        anchor='w'
                    )
        
        # Красный текст
        self.canvas.create_text(
            x, y, 
            text=text,
            font=('Arial', 28, 'bold'), 
            fill='#C41E3A', 
            anchor='w'
        )
    
    def _get_hwnd(self):
        """Получить HWND окна"""
        if self.hwnd:
            return self.hwnd
        
        try:
            self.root.update_idletasks()
            hwnd = user32.GetParent(self.root.winfo_id())
            if hwnd == 0:
                hwnd = self.root.winfo_id()
            self.hwnd = hwnd
        except:
            self.hwnd = self.root.winfo_id()
        
        return self.hwnd
    
    def create_overlay(self):
        """Создать прозрачное окно"""
        self.root = tk.Tk()
        self.root.title("Deaths")
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-transparentcolor', '#010101')
        self.root.configure(bg='#010101')
        self.root.geometry('180x50+50+50')
        
        self.canvas = tk.Canvas(
            self.root, 
            bg='#010101', 
            highlightthickness=0,
            width=180, 
            height=50
        )
        self.canvas.pack()
        self._redraw()
        
        # Перетаскивание ЛКМ
        self._drag = {"x": 0, "y": 0}
        self.canvas.bind('<Button-1>', self._start_drag)
        self.canvas.bind('<B1-Motion>', self._do_drag)
        
        # ПКМ - переключить режим "сквозь окно"
        self.canvas.bind('<Button-3>', self._toggle_clickthrough)
        
        # Настройка окна
        self.root.after(100, self._setup_win)
    
    def _start_drag(self, e):
        if self.drag_enabled:
            self._drag.update({"x": e.x, "y": e.y})
    
    def _do_drag(self, e):
        """Обработка перетаскивания"""
        if not self.drag_enabled:
            return
        x = self.root.winfo_x() + e.x - self._drag["x"]
        y = self.root.winfo_y() + e.y - self._drag["y"]
        self.root.geometry(f'+{x}+{y}')
    
    def _toggle_clickthrough(self, e=None):
        """Переключить режим прозрачности для кликов"""
        hwnd = self._get_hwnd()
        ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        
        if ex_style & WS_EX_TRANSPARENT:
            # Убираем прозрачность - можно перетаскивать
            new_style = ex_style & ~WS_EX_TRANSPARENT
            self.drag_enabled = True
            print("[*] Режим: можно перетаскивать (ЛКМ)")
        else:
            # Добавляем прозрачность - клики проходят сквозь
            new_style = ex_style | WS_EX_TRANSPARENT
            self.drag_enabled = False
            print("[*] Режим: клики проходят сквозь окно")
        
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)
    
    def _setup_win(self):
        """Настроить окно для работы поверх игр"""
        try:
            hwnd = self._get_hwnd()
            
            # Получаем текущие стили
            ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            
            # Устанавливаем стили для оверлея
            new_style = (
                ex_style | 
                WS_EX_LAYERED |      # Для прозрачности
                WS_EX_TOOLWINDOW |   # Не показывать в таскбаре
                WS_EX_NOACTIVATE |   # Не забирать фокус
                WS_EX_TOPMOST        # Поверх всех
            )
            
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)
            
            # Прозрачность по цвету (чёрный фон прозрачный)
            # 0x010101 = RGB(1, 1, 1) - наш прозрачный цвет
            user32.SetLayeredWindowAttributes(hwnd, 0x010101, 0, LWA_COLORKEY)
            
            # Принудительно поверх
            user32.SetWindowPos(
                hwnd, 
                HWND_TOPMOST,
                0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
            )
            
            print("[+] Оверлей готов")
            print()
            print("[*] ЛКМ = перетащить, ПКМ = режим 'сквозь окно'")
            print()
        except Exception as e:
            print(f"[!] Ошибка настройки: {e}")
        
        # Агрессивно поддерживаем поверх (каждые 16мс ~ 60fps)
        self.root.after(16, self._keep_top)
    
    def _keep_top(self):
        """Агрессивно поддерживать окно поверх"""
        if not self.root or not self.running:
            return
        
        try:
            hwnd = self._get_hwnd()
            
            # Принудительно ставим поверх
            user32.SetWindowPos(
                hwnd,
                HWND_TOPMOST,
                0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
            )
        except:
            pass
        
        # Повторяем каждые 16мс
        self.root.after(16, self._keep_top)
    
    def run(self):
        """Запуск оверлея"""
        print()
        print("=" * 55)
        print("   DARK SOULS DEATH COUNTER")
        print("   Powered by DSDeaths")
        print("=" * 55)
        print()
        print("   ╔══════════════════════════════════════════════╗")
        print("   ║  ВАЖНО: Для работы оверлея поверх игры      ║")
        print("   ║  включите BORDERLESS WINDOWED режим!        ║")
        print("   ║                                              ║")
        print("   ║  Dark Souls Remastered:                      ║")
        print("   ║  Settings → Screen Mode → BORDERLESS WINDOW  ║")
        print("   ╚══════════════════════════════════════════════╝")
        print()
        print(f"   Файл счётчика: {self.dsdeaths_path}")
        print()
        print("=" * 55)
        print()
        
        # Читаем начальное значение
        self.deaths = self.read_deaths()
        print(f"[*] Текущий счётчик: {self.deaths}")
        print("[*] Мониторю файл DSDeaths.txt...")
        
        self.running = True
        
        # Поток мониторинга
        thread = threading.Thread(target=self.monitor_loop, daemon=True)
        thread.start()
        
        # Создаём оверлей
        self.create_overlay()
        
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False


def main():
    overlay = DeathOverlay()
    overlay.run()


if __name__ == "__main__":
    main()
