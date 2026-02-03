"""
Модуль чтения счетчика смертей из памяти процесса Dark Souls Remastered
Использует pymem для доступа к памяти процесса
"""

import time
import struct
from typing import Optional, Callable
import threading

try:
    import pymem
    import pymem.process
    PYMEM_AVAILABLE = True
except ImportError:
    PYMEM_AVAILABLE = False
    print("[!] pymem не установлен. Запустите: uv sync")

import config


class MemoryReader:
    """Читает данные из памяти процесса Dark Souls Remastered"""
    
    def __init__(self):
        self.pm: Optional[pymem.Pymem] = None
        self.base_address: int = 0
        self.game_data_man: int = 0
        self.connected: bool = False
        self._stop_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
        self._last_death_count: int = 0
        self._callback: Optional[Callable[[int], None]] = None
    
    def connect(self) -> bool:
        """Подключиться к процессу игры"""
        if not PYMEM_AVAILABLE:
            return False
            
        try:
            self.pm = pymem.Pymem(config.PROCESS_NAME)
            self.base_address = self.pm.base_address
            
            # Получаем адрес модуля
            module = pymem.process.module_from_name(
                self.pm.process_handle, 
                config.PROCESS_NAME
            )
            
            if module:
                self.base_address = module.lpBaseOfDll
            
            # Пробуем найти GameDataMan
            self.game_data_man = self._find_game_data_man()
            
            if self.game_data_man:
                self.connected = True
                print(f"[+] Подключено к {config.PROCESS_NAME}")
                print(f"[+] Base address: {hex(self.base_address)}")
                print(f"[+] GameDataMan: {hex(self.game_data_man)}")
                return True
            else:
                print("[!] Не удалось найти GameDataMan")
                return False
                
        except pymem.exception.ProcessNotFound:
            print(f"[!] Процесс {config.PROCESS_NAME} не найден")
            return False
        except Exception as e:
            print(f"[!] Ошибка подключения: {e}")
            return False
    
    def _find_game_data_man(self) -> int:
        """Найти адрес GameDataMan"""
        if not self.pm:
            return 0
            
        try:
            # Метод 1: Используем известный статический offset
            ptr_address = self.base_address + config.GAME_DATA_MAN_OFFSET
            game_data_man = self.pm.read_longlong(ptr_address)
            
            if game_data_man and game_data_man != 0:
                return game_data_man
                
        except Exception as e:
            print(f"[!] Ошибка поиска GameDataMan (метод 1): {e}")
        
        try:
            # Метод 2: Сканирование по AOB сигнатуре
            # Преобразуем AOB в bytes для поиска
            aob_pattern = config.GAME_DATA_MAN_AOB.replace("??", ".")
            aob_bytes = bytes([
                int(b, 16) if b != "." else 0 
                for b in config.GAME_DATA_MAN_AOB.split()
            ])
            
            # Это упрощенный поиск - в реальности нужен pattern scan
            # Для простоты используем статический offset
            
        except Exception as e:
            print(f"[!] Ошибка поиска GameDataMan (метод 2): {e}")
            
        return 0
    
    def read_death_count(self) -> Optional[int]:
        """Прочитать текущее количество смертей"""
        if not self.connected or not self.pm:
            return None
            
        try:
            # Следуем по pointer chain
            current_address = self.game_data_man
            
            for offset in config.DEATH_COUNT_OFFSETS[:-1]:
                current_address = self.pm.read_longlong(current_address + offset)
                if current_address == 0:
                    return None
            
            # Последний offset - читаем int32
            final_offset = config.DEATH_COUNT_OFFSETS[-1]
            death_count = self.pm.read_int(current_address + final_offset)
            
            return death_count
            
        except Exception as e:
            # Игра могла закрыться или память недоступна
            self.connected = False
            return None
    
    def disconnect(self):
        """Отключиться от процесса"""
        self.stop_monitoring()
        if self.pm:
            self.pm.close_process()
            self.pm = None
        self.connected = False
        self.game_data_man = 0
        print("[*] Отключено от процесса")
    
    def start_monitoring(self, callback: Callable[[int], None]):
        """
        Начать мониторинг смертей в отдельном потоке
        
        Args:
            callback: Функция, вызываемая при изменении счетчика смертей
        """
        self._callback = callback
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """Остановить мониторинг"""
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
            self._monitor_thread = None
    
    def _monitor_loop(self):
        """Основной цикл мониторинга"""
        reconnect_delay = 3.0
        
        while not self._stop_event.is_set():
            # Пробуем подключиться если не подключены
            if not self.connected:
                if self.connect():
                    # Читаем начальное значение
                    death_count = self.read_death_count()
                    if death_count is not None:
                        self._last_death_count = death_count
                        if self._callback:
                            self._callback(death_count)
                else:
                    # Ждем перед повторной попыткой
                    self._stop_event.wait(reconnect_delay)
                    continue
            
            # Читаем текущее значение
            death_count = self.read_death_count()
            
            if death_count is not None:
                if death_count != self._last_death_count:
                    self._last_death_count = death_count
                    if self._callback:
                        self._callback(death_count)
            else:
                # Потеряли соединение
                self.connected = False
                if self._callback:
                    self._callback(-1)  # -1 означает потерю соединения
            
            self._stop_event.wait(config.MEMORY_READ_INTERVAL)
    
    def is_game_running(self) -> bool:
        """Проверить, запущена ли игра"""
        if not PYMEM_AVAILABLE:
            return False
            
        try:
            pm = pymem.Pymem(config.PROCESS_NAME)
            pm.close_process()
            return True
        except:
            return False


# Тестирование модуля
if __name__ == "__main__":
    reader = MemoryReader()
    
    def on_death_change(count: int):
        if count >= 0:
            print(f"Смертей: {count}")
        else:
            print("Потеряно соединение с игрой")
    
    print("Ожидание запуска Dark Souls Remastered...")
    reader.start_monitoring(on_death_change)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        reader.stop_monitoring()
        print("\nЗавершение...")
