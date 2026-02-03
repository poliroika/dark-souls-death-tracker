"""
Конфигурация счетчика смертей Dark Souls Remastered
"""

# === Настройки процесса игры ===
PROCESS_NAME = "DarkSoulsRemastered.exe"

# === Pointer chain для death count ===
# Base: GameDataMan
# Путь: GameDataMan -> PlayerGameData -> DeathCount
# Эти offset'ы для Dark Souls Remastered (Steam версия)
GAME_DATA_MAN_AOB = "48 8B 05 ?? ?? ?? ?? 48 85 C0 74 05 48 8B 40 58"  # AOB сигнатура
GAME_DATA_MAN_OFFSET = 0x1C8A530  # Статический offset (может отличаться между версиями)

# Pointer chain от GameDataMan до DeathCount
DEATH_COUNT_OFFSETS = [0x98, 0x5C]  # GameDataMan -> +0x98 -> +0x5C = Death Count

# === Настройки Overlay ===
OVERLAY_FONT = "Arial"
OVERLAY_FONT_SIZE = 28
OVERLAY_TEXT_COLOR = "#FFFFFF"  # Белый
OVERLAY_OUTLINE_COLOR = "#000000"  # Черная обводка
OVERLAY_POSITION_X = 50  # Отступ слева
OVERLAY_POSITION_Y = 50  # Отступ сверху
OVERLAY_OPACITY = 0.85  # Прозрачность (0.0 - 1.0)

# === Настройки обновления ===
UPDATE_INTERVAL_MS = 500  # Интервал обновления счетчика (миллисекунды)
MEMORY_READ_INTERVAL = 0.3  # Интервал чтения памяти (секунды)

# === Текст ===
DEATH_TEXT_TEMPLATE = "Смертей: {count}"
ERROR_TEXT = "Ожидание игры..."
