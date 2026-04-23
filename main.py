#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NetMorph - MAC & PC Name Changer для Windows
Красивый интерактивный интерфейс с градиентным логотипом
"""

import subprocess
import winreg
import ctypes
import random
import time
import re
import os
import sys
import socket
import threading
import queue
from datetime import datetime
from winotify import Notification, audio

try:
    import inquirer
    MENU_AVAILABLE = True
except ImportError:
    MENU_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════
# ГРАДИЕНТ И ЦВЕТА
# ═══════════════════════════════════════════════════════════════════════════

def enable_ansi():
    """Включаем ANSI-цвета в консоли Windows"""
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

def rgb_to_ansi(r, g, b):
    """Конвертируем RGB в ANSI escape код"""
    return f"\033[38;2;{r};{g};{b}m"

def gradient_text(text, start_color, end_color):
    """Применяем градиент к тексту"""
    lines = text.split('\n')
    result = []
    
    # Считаем все символы (без пробелов и переносов)
    all_chars = ''.join(lines).replace(' ', '')
    total_chars = len(all_chars)
    
    char_index = 0
    for line in lines:
        colored_line = ""
        for char in line:
            if char == ' ':
                colored_line += char
            else:
                if total_chars > 1:
                    factor = char_index / (total_chars - 1)
                else:
                    factor = 0
                
                r = int(start_color[0] + (end_color[0] - start_color[0]) * factor)
                g = int(start_color[1] + (end_color[1] - start_color[1]) * factor)
                b = int(start_color[2] + (end_color[2] - start_color[2]) * factor)
                
                colored_line += rgb_to_ansi(r, g, b) + char
                char_index += 1
        
        result.append(colored_line)
    
    return '\n'.join(result) + "\033[0m"

LOGO = """
███╗   ██╗███████╗████████╗███╗   ███╗ ██████╗ ██████╗ ██████╗ ██╗  ██╗
████╗  ██║██╔════╝╚══██╔══╝████╗ ████║██╔═══██╗██╔══██╗██╔══██╗██║  ██║
██╔██╗ ██║█████╗     ██║   ██╔████╔██║██║   ██║██████╔╝██████╔╝███████║
██║╚██╗██║██╔══╝     ██║   ██║╚██╔╝██║██║   ██║██╔══██╗██╔═══╝ ██╔══██║
██║ ╚████║███████╗   ██║   ██║ ╚═╝ ██║╚██████╔╝██║  ██║██║     ██║  ██║
╚═╝  ╚═══╝╚══════╝   ╚═╝   ╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝ v0.1.0 by CHELOVECHEK
"""

def show_logo():
    """Показываем градиентный логотип"""
    os.system('cls' if os.name == 'nt' else 'clear')
    red = (255, 0, 0)
    blue = (0, 0, 255)
    print(gradient_text(LOGO, red, blue))
    print("\033[90m" + " " * 20 + "MAC & PC Name Changer for Windows\033[0m\n")

# Цветные функции
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
GRAY = "\033[90m"
RESET = "\033[0m"

def green(s): return f"{GREEN}{s}{RESET}"
def red(s): return f"{RED}{s}{RESET}"
def yellow(s): return f"{YELLOW}{s}{RESET}"
def blue(s): return f"{BLUE}{s}{RESET}"
def cyan(s): return f"{CYAN}{s}{RESET}"
def gray(s): return f"{GRAY}{s}{RESET}"

# Префиксы для сообщений
LOG_FILE = "netmorph.log"

def write_log(prefix, msg):
    """Записываем лог в файл"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {prefix} {msg}\n"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except:
        pass

def show_notification(title, message, duration="short"):
    """Показываем Windows уведомление"""
    try:
        toast = Notification(
            app_id="NetMorph",
            title=title,
            msg=message,
            duration=duration,
            icon=None
        )
        toast.set_audio(audio.Default, loop=False)
        toast.show()
    except Exception as e:
        # Если winotify не работает, просто игнорируем
        pass

def info(msg): 
    print(blue(f"[*] {msg}"))
    write_log("[*]", msg)

def error(msg): 
    print(red(f"[E] {msg}"))
    write_log("[E]", msg)

def success(msg): 
    print(green(f"[S] {msg}"))
    write_log("[S]", msg)

def warning(msg):
    print(yellow(f"[!] {msg}"))
    write_log("[!]", msg)

# ═══════════════════════════════════════════════════════════════════════════
# ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА
# ═══════════════════════════════════════════════════════════════════════════

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def relaunch_as_admin():
    """Перезапускаем скрипт с правами администратора"""
    script = os.path.abspath(sys.argv[0])
    params = " ".join([f'"{a}"' for a in sys.argv[1:]])
    try:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{script}" {params}', None, 1
        )
    except Exception as e:
        print(red(f"✗ Ошибка при запросе прав администратора: {e}"))
        input("Нажмите Enter для выхода...")
    sys.exit(0)

# ═══════════════════════════════════════════════════════════════════════════
# РАБОТА С СЕТЕВЫМИ АДАПТЕРАМИ
# ═══════════════════════════════════════════════════════════════════════════

def get_adapters():
    """Возвращает список адаптеров"""
    adapters = []
    encodings = ['cp866', 'cp1251', 'utf-8']
    
    for encoding in encodings:
        try:
            out = subprocess.check_output(
                ["netsh", "interface", "show", "interface"],
                encoding=encoding, errors="replace"
            )
            
            lines = out.splitlines()
            for line in lines[3:]:
                line = line.strip()
                if not line or line.startswith('-'):
                    continue
                    
                parts = [p.strip() for p in re.split(r'\s{2,}', line) if p.strip()]
                
                if len(parts) >= 4:
                    # Формат: Admin State | State | Type | Interface Name
                    admin_state = parts[0].lower()
                    state = parts[1].lower()
                    name = parts[-1]
                    
                    # Проверяем State (второе поле) - это реальный статус подключения
                    is_connected = "connected" in state or "подключен" in state
                    status = "Connected" if is_connected else "Disconnected"
                    
                    if name and len(name) > 1:
                        adapters.append({"name": name, "status": status})
            
            if adapters:
                break
        except:
            continue
    
    return adapters

def choose_adapter():
    """Выбор адаптера через интерактивное меню"""
    adapters = get_adapters()
    
    if not adapters:
        error("Сетевые адаптеры не найдены")
        input("\nНажмите Enter для выхода...")
        sys.exit(1)
    
    print(blue("\nДоступные сетевые адаптеры:"))
    
    if not MENU_AVAILABLE:
        for i, a in enumerate(adapters, 1):
            status = green("[Connected]") if a["status"] == "Connected" else red("[Disconnected]")
            print(f"  {i}. {a['name']} {status}")
        
        while True:
            try:
                choice = int(input("\nВыберите адаптер (номер): "))
                if 1 <= choice <= len(adapters):
                    return adapters[choice - 1]
                error("Неверный номер")
            except ValueError:
                error("Введите число")
            except KeyboardInterrupt:
                sys.exit(0)
    
    # Интерактивное меню с inquirer
    choices = []
    for a in adapters:
        status = green("[Connected]") if a["status"] == "Connected" else red("[Disconnected]")
        choices.append(f"{a['name']} {status}")
    
    questions = [
        inquirer.List('adapter',
                     message="Выберите адаптер (↑↓ Enter)",
                     choices=choices,
                     carousel=True)
    ]
    
    try:
        answers = inquirer.prompt(questions)
        if not answers:
            sys.exit(0)
        
        # Находим выбранный адаптер по имени
        selected_text = answers['adapter']
        for a in adapters:
            if a['name'] in selected_text:
                return a
    except (KeyboardInterrupt, EOFError):
        sys.exit(0)

# ═══════════════════════════════════════════════════════════════════════════
# MAC АДРЕС
# ═══════════════════════════════════════════════════════════════════════════

def generate_random_mac():
    """Генерируем случайный MAC"""
    first_nibble = random.choice("0123456789ABCDEF")
    second_nibble = random.choice("26AE")
    first_byte = first_nibble + second_nibble
    rest = [f"{random.randint(0, 255):02X}" for _ in range(5)]
    return ":".join([first_byte] + rest)

def validate_mac(mac):
    """Валидация MAC адреса"""
    mac = mac.strip().upper()
    pattern = r'^([0-9A-F]{2}:){5}[0-9A-F]{2}$'
    
    if not re.match(pattern, mac):
        return False, "Неверный формат. Используйте XX:XX:XX:XX:XX:XX"
    
    second_char = mac[1]
    if second_char not in "26AE":
        return False, f"Второй символ должен быть 2, 6, A или E. У вас: '{second_char}'"
    
    return True, mac

def get_actual_mac(adapter_name):
    """Получаем текущий MAC адаптера"""
    try:
        out = subprocess.check_output(
            ["getmac", "/v", "/fo", "list"],
            encoding="cp866", errors="replace"
        )
        blocks = out.strip().split("\n\n")
        for block in blocks:
            if adapter_name.lower() in block.lower():
                for line in block.splitlines():
                    if "физический" in line.lower() or "physical" in line.lower():
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            raw = parts[1].strip().replace("-", ":").upper()
                            if re.match(r'^([0-9A-F]{2}:){5}[0-9A-F]{2}$', raw):
                                return raw
    except:
        pass
    
    return None

# ═══════════════════════════════════════════════════════════════════════════
# РЕЕСТР
# ═══════════════════════════════════════════════════════════════════════════

NET_CLASS_KEY = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e972-e325-11ce-bfc1-08002be10318}"

def find_adapter_guid_key(adapter_name):
    """Ищем адаптер в реестре"""
    try:
        base = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, NET_CLASS_KEY)
    except Exception as e:
        error(f"Не удалось открыть реестр: {e}")
        return None
    
    info("Поиск адаптера в реестре...")
    
    # Пробуем получить реальное имя драйвера через wmic
    real_name = None
    try:
        out = subprocess.check_output(
            ["wmic", "nic", "where", f"NetConnectionID='{adapter_name}'", "get", "Description"],
            encoding="cp866", errors="replace"
        )
        lines = [line.strip() for line in out.splitlines() if line.strip()]
        if len(lines) >= 2:
            real_name = lines[1]
            info(f"Реальное имя драйвера: {cyan(real_name)}")
    except:
        pass
    
    # Если не получилось через wmic, пробуем PowerShell
    if not real_name:
        try:
            ps_cmd = f'(Get-NetAdapter | Where-Object {{$_.Name -eq "{adapter_name}"}}).DriverDescription'
            out = subprocess.check_output(
                ["powershell", "-Command", ps_cmd],
                encoding="utf-8", errors="replace"
            )
            real_name = out.strip()
            if real_name:
                info(f"Реальное имя драйвера: {cyan(real_name)}")
        except:
            pass
    
    # Используем реальное имя для поиска, если нашли
    search_name = (real_name or adapter_name).lower()
    
    # Ищем в реестре
    candidates = []
    i = 0
    while True:
        try:
            subkey_name = winreg.EnumKey(base, i)
            i += 1
            
            if subkey_name.lower() == "properties":
                continue
            
            try:
                subkey_path = f"{NET_CLASS_KEY}\\{subkey_name}"
                subkey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, subkey_path)
                
                try:
                    desc, _ = winreg.QueryValueEx(subkey, "DriverDesc")
                    desc_lower = desc.lower()
                    
                    # Точное совпадение
                    if search_name == desc_lower:
                        winreg.CloseKey(subkey)
                        winreg.CloseKey(base)
                        success(f"Найден адаптер: {desc}")
                        return subkey_path
                    
                    # Частичное совпадение
                    if search_name in desc_lower or desc_lower in search_name:
                        candidates.append((subkey_path, desc, 2))
                    # Ключевые слова для Wi-Fi
                    elif "беспроводн" in adapter_name.lower() or "wireless" in adapter_name.lower() or "wi-fi" in adapter_name.lower():
                        if any(kw in desc_lower for kw in ["wi-fi", "wifi", "wireless", "802.11", "wlan"]):
                            candidates.append((subkey_path, desc, 1))
                    # Ключевые слова для Ethernet
                    elif "ethernet" in adapter_name.lower():
                        if any(kw in desc_lower for kw in ["ethernet", "realtek", "intel", "lan"]):
                            candidates.append((subkey_path, desc, 1))
                        
                except FileNotFoundError:
                    pass
                
                winreg.CloseKey(subkey)
            except:
                pass
        except OSError:
            break
    
    winreg.CloseKey(base)
    
    # Если нашли кандидатов
    if candidates:
        candidates.sort(key=lambda x: x[2], reverse=True)
        
        # Если только один кандидат с высоким приоритетом - выбираем автоматически
        if len(candidates) == 1 or (candidates[0][2] > candidates[1][2] if len(candidates) > 1 else False):
            success(f"Найден адаптер: {candidates[0][1]}")
            return candidates[0][0]
        
        # Иначе показываем список
        print(yellow(f"\nНайдено несколько похожих адаптеров:"))
        for idx, (path, desc, priority) in enumerate(candidates[:5], 1):
            print(f"  {idx}. {desc}")
        
        while True:
            try:
                choice = input(yellow(f"\nВыберите адаптер (1-{min(5, len(candidates))}) или 0 для отмены: ")).strip()
                choice_num = int(choice)
                
                if choice_num == 0:
                    return None
                    
                if 1 <= choice_num <= min(5, len(candidates)):
                    success(f"Выбран адаптер: {candidates[choice_num - 1][1]}")
                    return candidates[choice_num - 1][0]
                    
                error("Неверный номер")
            except ValueError:
                error("Введите число")
            except KeyboardInterrupt:
                return None
    
    error(f"Адаптер '{adapter_name}' не найден в реестре")
    return None

def set_mac_in_registry(subkey_path, mac_no_sep):
    """Записываем MAC в реестр"""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, subkey_path,
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, "NetworkAddress", 0, winreg.REG_SZ, mac_no_sep)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        error(f"Ошибка записи в реестр: {e}")
        return False

# ═══════════════════════════════════════════════════════════════════════════
# УПРАВЛЕНИЕ АДАПТЕРОМ
# ═══════════════════════════════════════════════════════════════════════════

def disable_adapter(name):
    """Отключаем адаптер"""
    result = subprocess.run(
        ["netsh", "interface", "set", "interface", name, "admin=disable"],
        capture_output=True
    )
    return result.returncode == 0

def enable_adapter(name):
    """Включаем адаптер"""
    result = subprocess.run(
        ["netsh", "interface", "set", "interface", name, "admin=enable"],
        capture_output=True
    )
    return result.returncode == 0

def renew_ip():
    """Обновляем IP"""
    subprocess.run(["ipconfig", "/release"], capture_output=True)
    subprocess.run(["ipconfig", "/renew"], capture_output=True)

def get_adapter_status(name):
    """Возвращает статус адаптера: Connected / Disconnected / Unknown"""
    adapters = get_adapters()
    for a in adapters:
        if a["name"].lower() == name.lower():
            return a["status"]
    return "Unknown"

def toggle_adapter(adapter_name):
    """Включает или отключает адаптер"""
    current_status = get_adapter_status(adapter_name)
    
    if current_status == "Connected":
        info(f'Отключение адаптера "{adapter_name}"...')
        if disable_adapter(adapter_name):
            time.sleep(2)
            new_status = get_adapter_status(adapter_name)
            if new_status == "Disconnected":
                success("Адаптер отключен")
                return True
            else:
                error("Не удалось отключить адаптер")
                return False
        else:
            error("Не удалось отключить адаптер")
            return False
    else:
        info(f'Включение адаптера "{adapter_name}"...')
        if enable_adapter(adapter_name):
            time.sleep(2)
            new_status = get_adapter_status(adapter_name)
            if new_status == "Connected":
                success("Адаптер включен")
                return True
            else:
                error("Не удалось включить адаптер")
                return False
        else:
            error("Не удалось включить адаптер")
            return False

# ═══════════════════════════════════════════════════════════════════════════
# АВТОМАТИЧЕСКАЯ СМЕНА ПРИ ПОТЕРЕ СОЕДИНЕНИЯ
# ═══════════════════════════════════════════════════════════════════════════

# Глобальные переменные для потока мониторинга
monitor_thread = None
monitor_stop_event = threading.Event()
monitor_active = False
monitor_callback_queue = None

def ping_check(host="8.8.8.8", timeout=1):
    """Проверяем доступность хоста через ping"""
    try:
        result = subprocess.run(
            ["ping", "-n", "1", "-w", str(timeout * 1000), host],
            capture_output=True,
            timeout=timeout + 1
        )
        return result.returncode == 0
    except:
        return False

def connection_monitor(adapter_name, callback_queue):
    """Мониторинг соединения в отдельном потоке"""
    consecutive_failures = 0
    check_interval = 1  # Проверяем каждую секунду
    last_status = None
    
    while not monitor_stop_event.is_set():
        is_online = ping_check()
        
        if is_online:
            if last_status == False:
                # Соединение восстановлено
                write_log("[S]", "Соединение восстановлено")
            consecutive_failures = 0
            last_status = True
        else:
            if last_status == True or last_status is None:
                # Соединение потеряно
                write_log("[!]", "Соединение потеряно - начало отсчета")
            
            consecutive_failures += 1
            
            # Если 5 секунд нет соединения
            if consecutive_failures >= 5:
                write_log("[!]", f"Соединение отсутствует {consecutive_failures} секунд - запуск автосмены")
                callback_queue.put(('connection_lost', adapter_name))
                # Сбрасываем счетчик
                consecutive_failures = 0
                last_status = None
            
            last_status = False
        
        time.sleep(check_interval)

def start_connection_monitor(adapter_name):
    """Запускаем мониторинг соединения"""
    global monitor_thread, monitor_active, monitor_callback_queue
    
    if monitor_active:
        info("Мониторинг уже запущен")
        return monitor_callback_queue
    
    monitor_stop_event.clear()
    monitor_callback_queue = queue.Queue()
    
    monitor_thread = threading.Thread(
        target=connection_monitor,
        args=(adapter_name, monitor_callback_queue),
        daemon=True
    )
    monitor_thread.start()
    monitor_active = True
    
    success("Мониторинг соединения запущен")
    info("При потере соединения на 5+ секунд MAC и имя ПК будут изменены автоматически")
    write_log("[S]", f"Мониторинг соединения запущен для адаптера: {adapter_name}")
    
    return monitor_callback_queue

def stop_connection_monitor():
    """Останавливаем мониторинг соединения"""
    global monitor_active
    
    if not monitor_active:
        return
    
    monitor_stop_event.set()
    if monitor_thread:
        monitor_thread.join(timeout=2)
    
    monitor_active = False
    info("Мониторинг соединения остановлен")
    write_log("[*]", "Мониторинг соединения остановлен")

def auto_change_on_disconnect(adapter_name):
    """Автоматически меняем MAC и имя при потере соединения"""
    print("\n" + yellow("=" * 70))
    print(yellow("[!] ОБНАРУЖЕНА ПОТЕРЯ СОЕДИНЕНИЯ!"))
    print(yellow("=" * 70))
    write_log("[!]", "═══ ОБНАРУЖЕНА ПОТЕРЯ СОЕДИНЕНИЯ - АВТОСМЕНА ═══")
    
    # Останавливаем мониторинг перед сменой
    info("Остановка мониторинга...")
    stop_connection_monitor()
    
    max_attempts = 3
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        
        # Генерируем новые данные
        new_mac = generate_random_mac()
        new_hostname = generate_random_hostname()
        
        info(f"Попытка {attempt}/{max_attempts}")
        info(f"Новый MAC: {cyan(new_mac)}")
        info(f"Новое имя ПК: {cyan(new_hostname)}")
        write_log("[*]", f"Попытка {attempt}: MAC={new_mac}, Имя ПК={new_hostname}")
        
        # Меняем MAC
        mac_changed = change_mac(adapter_name, new_mac)
        if mac_changed:
            success("MAC успешно изменен")
            show_notification("NetMorph - MAC изменен", f"Новый MAC: {new_mac}")
        else:
            error("Не удалось изменить MAC")
            show_notification("NetMorph - Ошибка", "Не удалось изменить MAC адрес")
        
        # Меняем имя компьютера
        hostname_changed = change_hostname(new_hostname)
        if hostname_changed:
            success("Имя компьютера успешно изменено")
            show_notification("NetMorph - Имя ПК изменено", f"Новое имя: {new_hostname}")
        else:
            error("Не удалось изменить имя компьютера")
        
        # Ждем 10 секунд и проверяем соединение
        info("Ожидание 10 секунд для проверки соединения...")
        time.sleep(10)
        
        # Проверяем соединение
        info("Проверка соединения...")
        connection_restored = False
        for i in range(5):
            if ping_check():
                connection_restored = True
                break
            time.sleep(1)
        
        if connection_restored:
            success("Соединение восстановлено!")
            write_log("[S]", f"═══ АВТОСМЕНА УСПЕШНА: MAC={new_mac}, Имя ПК={new_hostname} ═══")
            show_notification("NetMorph - Успех!", "Соединение восстановлено")
            print(yellow("=" * 70) + "\n")
            
            # Перезапускаем мониторинг
            info("Перезапуск мониторинга...")
            start_connection_monitor(adapter_name)
            return
        else:
            warning(f"Соединение не восстановлено. Попытка {attempt}/{max_attempts}")
            write_log("[!]", f"Соединение не восстановлено после попытки {attempt}")
            
            if attempt < max_attempts:
                info("Повторная смена MAC адреса...")
    
    # Если все попытки исчерпаны
    error(f"Не удалось восстановить соединение после {max_attempts} попыток")
    write_log("[E]", f"Соединение не восстановлено после {max_attempts} попыток")
    show_notification("NetMorph - Внимание", f"Соединение не восстановлено после {max_attempts} попыток")
    print(yellow("=" * 70) + "\n")
    
    # Перезапускаем мониторинг даже если не удалось
    info("Перезапуск мониторинга...")
    start_connection_monitor(adapter_name)

# ═══════════════════════════════════════════════════════════════════════════
# СМЕНА MAC
# ═══════════════════════════════════════════════════════════════════════════

def change_mac(adapter_name, new_mac):
    """Полный цикл смены MAC"""
    mac_no_sep = new_mac.replace(":", "")
    
    info(f'Отключение адаптера "{adapter_name}"...')
    if not disable_adapter(adapter_name):
        error("Не удалось отключить адаптер")
        return False
    
    time.sleep(2)
    
    subkey_path = find_adapter_guid_key(adapter_name)
    if not subkey_path:
        error("Адаптер не найден в реестре")
        enable_adapter(adapter_name)
        return False
    
    info(f"Запись MAC {new_mac} в реестр...")
    if not set_mac_in_registry(subkey_path, mac_no_sep):
        enable_adapter(adapter_name)
        return False
    
    time.sleep(1)
    
    info("Включение адаптера...")
    enable_adapter(adapter_name)
    time.sleep(3)
    
    info("Обновление IP...")
    renew_ip()
    time.sleep(2)
    
    info("Проверка MAC...")
    actual_mac = get_actual_mac(adapter_name)
    
    if actual_mac and actual_mac.upper() == new_mac.upper():
        success(f"MAC изменен на {cyan(actual_mac)}")
        write_log("[S]", f"MAC адрес изменен: {adapter_name} -> {actual_mac}")
        show_notification("NetMorph", f"MAC изменен на {actual_mac}")
        return True
    else:
        display = actual_mac if actual_mac else "не удалось определить"
        error(f"MAC не изменился. Текущий: {display}")
        write_log("[E]", f"Ошибка смены MAC адреса на {adapter_name}. Текущий: {display}")
        return False

# ═══════════════════════════════════════════════════════════════════════════
# ИМЯ КОМПЬЮТЕРА
# ═══════════════════════════════════════════════════════════════════════════

def generate_random_hostname():
    """Генерируем случайное имя"""
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    suffix = "".join(random.choices(chars, k=6))
    return f"PC-{suffix}"

def validate_hostname(name):
    """Валидация имени компьютера"""
    if not re.match(r'^[A-Za-z0-9\-]{3,15}$', name):
        return False, "Имя должно содержать только латиницу, цифры и дефис (3-15 символов)"
    return True, name.upper()

def change_hostname(new_name):
    """Меняем имя компьютера"""
    keys = [
        (r"SYSTEM\CurrentControlSet\Control\ComputerName\ComputerName", "ComputerName"),
        (r"SYSTEM\CurrentControlSet\Control\ComputerName\ActiveComputerName", "ComputerName"),
        (r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters", "Hostname"),
        (r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters", "NV Hostname"),
    ]
    
    success_flag = True
    for key_path, value_name in keys:
        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE, key_path,
                0, winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, new_name)
            winreg.CloseKey(key)
        except Exception as e:
            error(f"Ошибка записи {key_path}: {e}")
            success_flag = False
    
    if success_flag:
        success(f"Имя компьютера изменено на {cyan(new_name)}")
        write_log("[S]", f"Имя компьютера изменено на: {new_name}")
        show_notification("NetMorph", f"Имя ПК изменено на {new_name}")
        print(yellow("[!] Требуется перезагрузка!"))
        write_log("[!]", "Требуется перезагрузка для применения изменений")
    else:
        error("Не все ключи реестра обновлены")
        write_log("[E]", "Ошибка изменения имени компьютера")
    
    return success_flag

def get_current_hostname():
    """Текущее имя компьютера"""
    return os.environ.get("COMPUTERNAME", socket.gethostname())

# ═══════════════════════════════════════════════════════════════════════════
# ГЛАВНОЕ МЕНЮ
# ═══════════════════════════════════════════════════════════════════════════

def show_info(adapter):
    """Показываем текущую информацию"""
    current_mac = get_actual_mac(adapter["name"]) or "Не удалось определить"
    current_host = get_current_hostname()
    
    print("\n" + gray("═" * 70))
    print(cyan("Адаптер:") + f" {adapter['name']}")
    print(cyan("MAC:") + f" {green(current_mac)}")
    print(cyan("Имя ПК:") + f" {green(current_host)}")
    print(gray("═" * 70) + "\n")

def main_menu(adapter):
    """Главное меню"""
    show_logo()
    show_info(adapter)
    
    menu_items = [
        "Сменить MAC (вручную)",
        "Сменить MAC (случайный)",
        "Сменить имя ПК (вручную)",
        "Сменить имя ПК (случайное)",
        "Включить/Отключить адаптер",
        "Автосмена при потере соединения",
        "Показать текущие данные",
        "Выбрать другой адаптер",
        "Выход"
    ]
    
    if not MENU_AVAILABLE:
        for i, item in enumerate(menu_items, 1):
            print(f"  {i}. {item}")
        
        try:
            choice = input("\nВыберите пункт меню: ").strip()
            return int(choice) - 1 if choice.isdigit() else None
        except (ValueError, KeyboardInterrupt):
            return None
    
    questions = [
        inquirer.List('action',
                     message="Выберите действие (↑↓ Enter)",
                     choices=menu_items,
                     carousel=True)
    ]
    
    try:
        answers = inquirer.prompt(questions)
        if not answers:
            return None
        return menu_items.index(answers['action'])
    except (KeyboardInterrupt, EOFError):
        return None

# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    enable_ansi()
    
    # Логируем запуск программы
    write_log("[*]", "=" * 50)
    write_log("[*]", "NetMorph v0.1.0 запущен")
    
    if not is_admin():
        show_logo()
        print(yellow("⚠ Требуются права администратора"))
        print(blue("ℹ После подтверждения UAC откроется новое окно\n"))
        write_log("[!]", "Запуск без прав администратора - запрос UAC")
        input("Нажмите Enter для запроса прав администратора...")
        relaunch_as_admin()
        return
    
    show_logo()
    success("Запущено с правами администратора\n")
    write_log("[S]", "Программа запущена с правами администратора")
    
    adapter = choose_adapter()
    success(f'Выбран адаптер: {adapter["name"]}')
    write_log("[*]", f"Выбран адаптер: {adapter['name']}")
    
    while True:
        # Обновляем статус адаптера перед показом меню
        adapter["status"] = get_adapter_status(adapter["name"])
        choice = main_menu(adapter)
        
        if choice is None:
            print(yellow("\n[!] Выход из программы"))
            break
        
        elif choice == 0:  # MAC вручную
            show_logo()
            while True:
                raw = input("Введите новый MAC (XX:XX:XX:XX:XX:XX): ").strip()
                ok, result = validate_mac(raw)
                if ok:
                    change_mac(adapter["name"], result)
                    break
                else:
                    error(result)
            print(gray("\nНажмите Enter для выхода в меню..."))
            input()
        
        elif choice == 1:  # MAC случайный
            show_logo()
            new_mac = generate_random_mac()
            info(f"Сгенерирован MAC: {cyan(new_mac)}")
            change_mac(adapter["name"], new_mac)
            print(gray("\nНажмите Enter для выхода в меню..."))
            input()
        
        elif choice == 2:  # Имя вручную
            show_logo()
            while True:
                raw = input("Введите новое имя ПК (латиница, цифры, дефис, 3-15 символов): ").strip()
                ok, result = validate_hostname(raw)
                if ok:
                    change_hostname(result)
                    break
                else:
                    error(result)
            print(gray("\nНажмите Enter для выхода в меню..."))
            input()
        
        elif choice == 3:  # Имя случайное
            show_logo()
            new_name = generate_random_hostname()
            info(f"Сгенерировано имя: {cyan(new_name)}")
            change_hostname(new_name)
            print(gray("\nНажмите Enter для выхода в меню..."))
            input()
        
        elif choice == 4:  # Включить/Отключить адаптер
            show_logo()
            toggle_adapter(adapter["name"])
            print(gray("\nНажмите Enter для выхода в меню..."))
            input()
        
        elif choice == 5:  # Автосмена при потере соединения
            show_logo()
            try:
                if not monitor_active:
                    start_connection_monitor(adapter["name"])
                    
                    # Показываем логи в реальном времени
                    print(gray("\n" + "=" * 70))
                    print(cyan("РЕЖИМ МОНИТОРИНГА - Логи в реальном времени"))
                    print(gray("=" * 70))
                    print(yellow("\nНажмите Ctrl+C для выхода в меню\n"))
                    
                    try:
                        last_log_size = 0
                        while monitor_active:
                            # Проверяем события от монитора
                            if monitor_callback_queue:
                                try:
                                    while not monitor_callback_queue.empty():
                                        event, data = monitor_callback_queue.get_nowait()
                                        if event == 'connection_lost':
                                            auto_change_on_disconnect(data)
                                except queue.Empty:
                                    pass
                            
                            # Показываем новые строки из лога
                            try:
                                if os.path.exists(LOG_FILE):
                                    with open(LOG_FILE, "r", encoding="utf-8") as f:
                                        lines = f.readlines()
                                        if len(lines) > last_log_size:
                                            for line in lines[last_log_size:]:
                                                # Парсим и красиво выводим
                                                if "[*]" in line:
                                                    print(blue(line.strip()))
                                                elif "[S]" in line:
                                                    print(green(line.strip()))
                                                elif "[E]" in line:
                                                    print(red(line.strip()))
                                                elif "[!]" in line:
                                                    print(yellow(line.strip()))
                                                else:
                                                    print(gray(line.strip()))
                                            last_log_size = len(lines)
                            except:
                                pass
                            
                            time.sleep(0.5)
                    except KeyboardInterrupt:
                        print(yellow("\n\n[!] Выход из режима мониторинга"))
                        print(gray("Мониторинг продолжает работать в фоне\n"))
                        input("Нажмите Enter для выхода в меню...")
                else:
                    stop_connection_monitor()
                    success("Мониторинг остановлен")
                    print(gray("\nНажмите Enter для выхода в меню..."))
                    input()
            except Exception as e:
                error(f"Ошибка при запуске мониторинга: {e}")
                import traceback
                traceback.print_exc()
                print(gray("\nНажмите Enter для выхода в меню..."))
                input()
        
        elif choice == 6:  # Показать данные
            show_logo()
            show_info(adapter)
            
            # Показываем статус мониторинга
            if monitor_active:
                print(green("[S] Мониторинг соединения: АКТИВЕН"))
            else:
                print(gray("Мониторинг соединения: отключен"))
            
            print(gray("\nНажмите Enter для выхода в меню..."))
            input()
        
        elif choice == 7:  # Выбрать другой адаптер
            show_logo()
            # Останавливаем мониторинг при смене адаптера
            if monitor_active:
                stop_connection_monitor()
            success("Запущено с правами администратора\n")
            adapter = choose_adapter()
            success(f'Выбран адаптер: {adapter["name"]}')
        
        elif choice == 8:  # Выход
            if monitor_active:
                stop_connection_monitor()
            print(yellow("\n[!] Выход из программы"))
            break
        
        # Проверяем события от монитора
        if monitor_active and monitor_callback_queue:
            try:
                while not monitor_callback_queue.empty():
                    event, data = monitor_callback_queue.get_nowait()
                    if event == 'connection_lost':
                        auto_change_on_disconnect(data)
            except queue.Empty:
                pass

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(yellow("\n\n[!] Программа прервана пользователем"))
        if monitor_active:
            stop_connection_monitor()
        input("\nНажмите Enter для выхода...")
    except Exception as e:
        print("\n" + red("=" * 70))
        print(red("[E] КРИТИЧЕСКАЯ ОШИБКА"))
        print(red("=" * 70))
        print(red(f"\nОшибка: {str(e)}"))
        print(red(f"Тип: {type(e).__name__}"))
        
        print(yellow("\n--- Подробная информация ---"))
        import traceback
        traceback.print_exc()
        
        print(red("\n" + "=" * 70))
        print(yellow("\nЕсли ошибка повторяется, создайте Issue на GitHub"))
        print(yellow("с описанием проблемы и этим логом ошибки."))
        
        if monitor_active:
            try:
                stop_connection_monitor()
            except:
                pass
        
        input("\nНажмите Enter для выхода...")
