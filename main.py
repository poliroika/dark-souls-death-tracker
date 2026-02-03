"""
Dark Souls Remastered Death Tracker
Счетчик смертей в реальном времени с прозрачным оверлеем

Запуск: python main.py [--minimal]

Требует запуска от администратора для чтения памяти процесса игры.
"""

import sys
import argparse
from typing import Optional

import config
from overlay import create_overlay, DeathOverlay, WIN32_AVAILABLE

try:
    from memory_reader import MemoryReader, PYMEM_AVAILABLE
except ImportError:
    PYMEM_AVAILABLE = False
    MemoryReader = None


class DeathTracker:
    """Главный класс приложения"""
    
    def __init__(self, use_minimal: bool = False):
        self.use_minimal = use_minimal
        self.overlay: Optional[DeathOverlay] = None
        self.memory_reader: Optional[MemoryReader] = None
        self._current_deaths: int = 0
    
    def _on_death_count_changed(self, count: int):
        """Callback при изменении счетчика смертей"""
        if count >= 0:
            if count > self._current_deaths:
                diff = count - self._current_deaths
                print(f"[!] +{diff} смерть(ей)! Всего: {count}")
            elif count < self._current_deaths:
                print(f"[*] Счетчик изменился: {count}")
            
            self._current_deaths = count
        else:
            print("[!] Потеряно соединение с игрой...")
        
        if self.overlay:
            self.overlay.update_death_count(count)
    
    def _print_banner(self):
        """Вывести приветственный баннер"""
        banner = """
╔═══════════════════════════════════════════════════════════╗
║     DARK SOULS REMASTERED - DEATH TRACKER                 ║
║                                                           ║
║     Отслеживание смертей в реальном времени               ║
╚═══════════════════════════════════════════════════════════╝
"""
        print(banner)
        print("[*] Режим: Чтение памяти процесса")
        print()
        print("[*] Управление оверлеем:")
        print("    - Левая кнопка мыши: перетаскивание")
        print("    - Правая кнопка мыши: меню / закрыть")
        print()
        print("[*] Нажмите Ctrl+C для выхода")
        print("-" * 60)
    
    def start(self):
        """Запустить трекер"""
        self._print_banner()
        
        if not PYMEM_AVAILABLE or MemoryReader is None:
            print("[!] ОШИБКА: pymem не установлен!")
            print("[*] Установите: uv sync")
            return
        
        # Создаем оверлей
        print("[*] Создание оверлея...")
        self.overlay = create_overlay(use_minimal=self.use_minimal)
        
        # Запускаем чтение памяти
        print("[*] Запуск чтения памяти...")
        self.memory_reader = MemoryReader()
        self.memory_reader.start_monitoring(self._on_death_count_changed)
        
        print("[*] Ожидание запуска Dark Souls Remastered...")
        print("[+] Оверлей запущен!")
        print()
        
        try:
            self.overlay.run()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
    
    def stop(self):
        """Остановить трекер"""
        print("\n[*] Завершение работы...")
        
        if self.memory_reader:
            self.memory_reader.stop_monitoring()
            self.memory_reader.disconnect()
        
        if self.overlay:
            self.overlay.stop()
        
        print("[*] До встречи, Chosen Undead!")


def check_dependencies():
    """Проверить наличие зависимостей"""
    print("=== Проверка зависимостей ===")
    
    ok = True
    
    if not PYMEM_AVAILABLE:
        print("[✗] pymem - НЕ УСТАНОВЛЕН")
        ok = False
    else:
        print("[✓] pymem")
    
    if not WIN32_AVAILABLE:
        print("[✗] pywin32 - НЕ УСТАНОВЛЕН (оверлей будет упрощённым)")
    else:
        print("[✓] pywin32")
    
    print()
    
    if not ok:
        print("[!] Установите зависимости: uv sync")
        return False
    
    return True


def main():
    """Точка входа"""
    parser = argparse.ArgumentParser(
        description='Dark Souls Remastered Death Tracker',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  uv run python main.py              # Стандартный запуск
  uv run python main.py --minimal    # Упрощённый оверлей
  uv run python main.py --check      # Проверить зависимости

ВАЖНО: Запускайте от имени администратора!
"""
    )
    
    parser.add_argument(
        '--minimal', '-m',
        action='store_true',
        help='Использовать упрощённый оверлей'
    )
    
    parser.add_argument(
        '--check', '-c',
        action='store_true',
        help='Проверить зависимости и выйти'
    )
    
    args = parser.parse_args()
    
    if not check_dependencies():
        return 1
    
    if args.check:
        print("[*] Проверка завершена")
        return 0
    
    tracker = DeathTracker(use_minimal=args.minimal)
    
    try:
        tracker.start()
    except KeyboardInterrupt:
        tracker.stop()
    except Exception as e:
        print(f"[!] Ошибка: {e}")
        tracker.stop()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
