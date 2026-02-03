"""
Прозрачный оверлей для отображения счетчика смертей поверх игры
Использует tkinter с Windows-специфичными настройками для прозрачности
"""

import tkinter as tk
from tkinter import font as tkfont
import threading
from typing import Optional

try:
    import win32gui
    import win32con
    import win32api
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    print("[!] pywin32 не установлен. Запустите: uv sync")

import config


class DeathOverlay:
    """Прозрачный оверлей с счетчиком смертей"""
    
    def __init__(self):
        self.root: Optional[tk.Tk] = None
        self.label: Optional[tk.Label] = None
        self.death_count: int = 0
        self._is_running: bool = False
        self._drag_data = {"x": 0, "y": 0}
    
    def create_window(self):
        """Создать окно оверлея"""
        self.root = tk.Tk()
        
        # Убираем рамку окна
        self.root.overrideredirect(True)
        
        # Устанавливаем окно поверх всех окон
        self.root.attributes('-topmost', True)
        
        # Прозрачный фон (используем специальный цвет как прозрачный)
        transparent_color = '#010101'
        self.root.attributes('-transparentcolor', transparent_color)
        self.root.configure(bg=transparent_color)
        
        # Начальная позиция
        self.root.geometry(f'+{config.OVERLAY_POSITION_X}+{config.OVERLAY_POSITION_Y}')
        
        # Создаем Canvas для текста с обводкой
        self.canvas = tk.Canvas(
            self.root, 
            bg=transparent_color, 
            highlightthickness=0,
            width=400,
            height=60
        )
        self.canvas.pack()
        
        # Создаем текст с "обводкой" (несколько слоев текста)
        self._create_text_with_outline()
        
        # Делаем окно кликабельным для перетаскивания
        self.canvas.bind('<Button-1>', self._start_drag)
        self.canvas.bind('<B1-Motion>', self._drag)
        self.canvas.bind('<Button-3>', self._show_context_menu)
        
        # Применяем Windows-специфичные настройки для прозрачности
        if WIN32_AVAILABLE:
            self._apply_windows_transparency()
        
        self._is_running = True
    
    def _create_text_with_outline(self):
        """Создать текст с обводкой"""
        text = config.DEATH_TEXT_TEMPLATE.format(count=self.death_count)
        
        # Удаляем старый текст
        self.canvas.delete("death_text")
        
        x, y = 10, 30
        outline_width = 2
        
        # Рисуем обводку (черный текст в 8 направлениях)
        for dx in [-outline_width, 0, outline_width]:
            for dy in [-outline_width, 0, outline_width]:
                if dx != 0 or dy != 0:
                    self.canvas.create_text(
                        x + dx, y + dy,
                        text=text,
                        font=(config.OVERLAY_FONT, config.OVERLAY_FONT_SIZE, 'bold'),
                        fill=config.OVERLAY_OUTLINE_COLOR,
                        anchor='w',
                        tags="death_text"
                    )
        
        # Основной белый текст
        self.canvas.create_text(
            x, y,
            text=text,
            font=(config.OVERLAY_FONT, config.OVERLAY_FONT_SIZE, 'bold'),
            fill=config.OVERLAY_TEXT_COLOR,
            anchor='w',
            tags="death_text"
        )
    
    def _apply_windows_transparency(self):
        """Применить Windows-специфичные настройки для кликабельной прозрачности"""
        if not WIN32_AVAILABLE:
            return
            
        try:
            hwnd = win32gui.FindWindow(None, self.root.title())
            if not hwnd:
                # Получаем HWND через tkinter
                hwnd = self.root.winfo_id()
            
            # Получаем текущие стили окна
            styles = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            
            # Добавляем стили для прозрачности и "проходимости" кликов
            # WS_EX_LAYERED - для прозрачности
            # WS_EX_TRANSPARENT - клики проходят сквозь окно (опционально)
            win32gui.SetWindowLong(
                hwnd, 
                win32con.GWL_EXSTYLE, 
                styles | win32con.WS_EX_LAYERED | win32con.WS_EX_TOOLWINDOW
            )
            
            # Устанавливаем прозрачность окна
            # Значение 255 = полностью непрозрачно, 0 = полностью прозрачно
            alpha = int(config.OVERLAY_OPACITY * 255)
            win32gui.SetLayeredWindowAttributes(
                hwnd, 
                0,  # Color key (не используем)
                alpha,  # Alpha
                win32con.LWA_ALPHA
            )
            
        except Exception as e:
            print(f"[!] Ошибка настройки прозрачности Windows: {e}")
    
    def _start_drag(self, event):
        """Начало перетаскивания окна"""
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
    
    def _drag(self, event):
        """Перетаскивание окна"""
        x = self.root.winfo_x() + (event.x - self._drag_data["x"])
        y = self.root.winfo_y() + (event.y - self._drag_data["y"])
        self.root.geometry(f'+{x}+{y}')
    
    def _show_context_menu(self, event):
        """Показать контекстное меню"""
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Сбросить счетчик", command=self._reset_counter)
        menu.add_separator()
        menu.add_command(label="Закрыть", command=self.stop)
        
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
    
    def _reset_counter(self):
        """Сбросить счетчик (только визуально)"""
        self.update_death_count(0)
    
    def update_death_count(self, count: int):
        """Обновить отображаемое количество смертей"""
        self.death_count = count
        
        if self.root and self._is_running:
            # Обновляем в главном потоке tkinter
            self.root.after(0, self._update_text)
    
    def _update_text(self):
        """Обновить текст (вызывается из главного потока)"""
        if self.death_count >= 0:
            self._create_text_with_outline()
        else:
            # Показываем сообщение об ошибке
            self.canvas.delete("death_text")
            self.canvas.create_text(
                10, 30,
                text=config.ERROR_TEXT,
                font=(config.OVERLAY_FONT, config.OVERLAY_FONT_SIZE - 4, 'bold'),
                fill="#FF6B6B",
                anchor='w',
                tags="death_text"
            )
    
    def show_notification(self, message: str, duration_ms: int = 2000):
        """Показать временное уведомление"""
        if not self.root:
            return
            
        # Создаем метку для уведомления
        notification = tk.Label(
            self.root,
            text=message,
            font=(config.OVERLAY_FONT, 14),
            fg="#00FF00",
            bg='#010101'
        )
        notification.place(x=10, y=50)
        
        # Удаляем через указанное время
        self.root.after(duration_ms, notification.destroy)
    
    def run(self):
        """Запустить главный цикл оверлея"""
        if not self.root:
            self.create_window()
        
        self.root.mainloop()
    
    def run_in_thread(self):
        """Запустить оверлей в отдельном потоке"""
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        return thread
    
    def stop(self):
        """Остановить оверлей"""
        self._is_running = False
        if self.root:
            self.root.quit()
            self.root.destroy()
            self.root = None
    
    def is_running(self) -> bool:
        """Проверить, запущен ли оверлей"""
        return self._is_running and self.root is not None


class MinimalOverlay:
    """
    Минималистичный оверлей без pywin32
    Менее функциональный, но работает без дополнительных зависимостей
    """
    
    def __init__(self):
        self.root: Optional[tk.Tk] = None
        self.death_count: int = 0
        self._is_running: bool = False
    
    def create_window(self):
        """Создать простое окно"""
        self.root = tk.Tk()
        self.root.title("Death Counter")
        
        # Убираем рамку
        self.root.overrideredirect(True)
        
        # Поверх всех окон
        self.root.attributes('-topmost', True)
        
        # Полупрозрачность (работает на Windows)
        self.root.attributes('-alpha', config.OVERLAY_OPACITY)
        
        # Темный фон
        self.root.configure(bg='#1a1a1a')
        
        # Позиция
        self.root.geometry(f'300x50+{config.OVERLAY_POSITION_X}+{config.OVERLAY_POSITION_Y}')
        
        # Текст
        self.label = tk.Label(
            self.root,
            text=config.DEATH_TEXT_TEMPLATE.format(count=self.death_count),
            font=(config.OVERLAY_FONT, config.OVERLAY_FONT_SIZE, 'bold'),
            fg=config.OVERLAY_TEXT_COLOR,
            bg='#1a1a1a',
            padx=10,
            pady=5
        )
        self.label.pack(fill='both', expand=True)
        
        # Перетаскивание
        self.label.bind('<Button-1>', self._start_drag)
        self.label.bind('<B1-Motion>', self._drag)
        self.label.bind('<Button-3>', lambda e: self.stop())
        
        self._drag_data = {"x": 0, "y": 0}
        self._is_running = True
    
    def _start_drag(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
    
    def _drag(self, event):
        x = self.root.winfo_x() + (event.x - self._drag_data["x"])
        y = self.root.winfo_y() + (event.y - self._drag_data["y"])
        self.root.geometry(f'+{x}+{y}')
    
    def update_death_count(self, count: int):
        """Обновить счетчик"""
        self.death_count = count
        if self.root and self.label:
            if count >= 0:
                text = config.DEATH_TEXT_TEMPLATE.format(count=count)
            else:
                text = config.ERROR_TEXT
            self.root.after(0, lambda: self.label.config(text=text))
    
    def run(self):
        if not self.root:
            self.create_window()
        self.root.mainloop()
    
    def run_in_thread(self):
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        return thread
    
    def stop(self):
        self._is_running = False
        if self.root:
            self.root.quit()
            self.root.destroy()
            self.root = None
    
    def is_running(self) -> bool:
        return self._is_running


def create_overlay(use_minimal: bool = False) -> DeathOverlay:
    """
    Создать подходящий оверлей
    
    Args:
        use_minimal: Использовать минималистичный оверлей без pywin32
    """
    if use_minimal or not WIN32_AVAILABLE:
        return MinimalOverlay()
    return DeathOverlay()


# Тестирование модуля
if __name__ == "__main__":
    import time
    
    print("=== Тест оверлея ===")
    print("Перетаскивайте левой кнопкой мыши")
    print("Правая кнопка - закрыть")
    
    overlay = create_overlay()
    overlay.create_window()
    
    # Симуляция обновления счетчика
    def simulate_deaths():
        count = 0
        while overlay.is_running():
            time.sleep(2)
            count += 1
            overlay.update_death_count(count)
            print(f"Обновлено: {count}")
    
    import threading
    sim_thread = threading.Thread(target=simulate_deaths, daemon=True)
    sim_thread.start()
    
    overlay.run()
