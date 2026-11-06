import os
import sys
import io
import subprocess
import threading
import ctypes
import pyautogui
import psutil
import pyperclip
import re
import streamlit as st

try:
    import screen_brightness_control as sbc
except ImportError:
    sbc = None

SLEEP_CMD = "rundll32.exe powrprof.dll,SetSuspendState 0,1,0"

DANGEROUS_RULES = [
    (r"\bshutdown(\.exe)?\b", "ปิดเครื่อง / รีสตาร์ท / ออกจากระบบ"),
    (r"setsuspendstate|powrprof", "พักเครื่อง (Sleep / Hibernate)"),
    (r"\b(logoff|poweroff|restart-computer|stop-computer)\b", "ปิดเครื่อง / ออกจากระบบ"),
    (r"\b(del|erase|rd|rmdir|rm|remove-item)\b", "ลบไฟล์หรือโฟลเดอร์"),
    (r"\bformat(\.com)?\s+[a-z]:|\bdiskpart\b|\bcipher\b\s+/w", "ฟอร์แมต/ล้างข้อมูลในไดรฟ์"),
    (r"\b(taskkill|stop-process)\b", "บังคับปิดโปรแกรม"),
    (r"\breg(\.exe)?\s+(add|delete|import)\b|\bbcdedit\b|\bvssadmin\b|\bnet\s+user\b|\bschtasks\b", "แก้ค่าระบบ Windows"),
    (r"\bsc(\.exe)?\s+(stop|delete|config)\b", "หยุด/ลบ/แก้ไข Service"),
    (r"-enc(odedcommand)?\b", "คำสั่ง PowerShell แบบเข้ารหัส"),
]

DANGEROUS_HOTKEYS = [{"alt", "f4"}, {"ctrl", "alt", "delete"}, {"ctrl", "alt", "del"},
                     {"shift", "delete"}, {"shift", "del"}, {"ctrl", "shift", "delete"}]

BLOCKED_MSG = "BLOCKED: ผู้ใช้ต้องกดยืนยันเองก่อน คำสั่งนี้ยังไม่ถูกรัน ห้ามลองซ้ำหรือหาทางอ้อมอื่น ให้แจ้งผู้ใช้ว่ากำลังรอยืนยัน"

SCREEN_WIDTH, SCREEN_HEIGHT = pyautogui.size()

def run_bg(fn, *args, **kwargs):
    """รันฟังก์ชันใน Thread แยกทันทีเพื่อไม่ให้ UI หน่วง"""
    threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True).start()

def run_system_command(command: str):
    try:
        res = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=15)
        return res.stdout or res.stderr or "Success"
    except Exception as e:
        return str(e)

def _visible_windows():
    user32 = ctypes.windll.user32
    found = {}
    enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def _cb(hwnd, _):
        try:
            if user32.IsWindowVisible(hwnd) and not user32.GetWindow(hwnd, 4):
                length = user32.GetWindowTextLengthW(hwnd)
                ex_style = user32.GetWindowLongW(hwnd, -20)
                if length > 0 and not (ex_style & 0x80):
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    found[hwnd] = buf.value
        except Exception:
            pass
        return True

    user32.EnumWindows(enum_proc(_cb), 0)
    return found

def _bring_to_front(hwnd):
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    fg = user32.GetForegroundWindow()
    cur_tid = kernel32.GetCurrentThreadId()
    fg_tid = user32.GetWindowThreadProcessId(fg, None)
    attached = False
    try:
        if fg_tid and fg_tid != cur_tid:
            attached = bool(user32.AttachThreadInput(cur_tid, fg_tid, True))
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, 9)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
    finally:
        if attached:
            user32.AttachThreadInput(cur_tid, fg_tid, False)

FOCUS_HINTS = {"code": "Visual Studio Code", "chrome": "Chrome", "taskmgr": "Task Manager"}

def _focus_new_window(before_hwnds, command):
    import time
    try:
        tokens = command.lower().replace('"', " ").split()
        if tokens and tokens[0] == "start":
            tokens = tokens[1:]
        hint = FOCUS_HINTS.get(tokens[0]) if tokens else None
        start = time.time()
        while time.time() - start < 2:
            time.sleep(0.2)
            now = _visible_windows()
            new = [h for h in now if h not in before_hwnds]
            if new:
                time.sleep(0.1)
                _bring_to_front(new[-1])
                return
            if hint and time.time() - start > 1.0:
                match = [h for h, title in now.items() if hint.lower() in title.lower()]
                if match:
                    _bring_to_front(match[0])
                    return
    except Exception:
        pass

def launch_command(command: str):
    try:
        before = set(_visible_windows()) if os.name == "nt" else set()
        subprocess.Popen(command, shell=True, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if os.name == "nt":
            threading.Thread(target=_focus_new_window, args=(before, command), daemon=True).start()
        return "Success"
    except Exception as e:
        return str(e)

def click_screen(x: int, y: int):
    pyautogui.click(x, y)
    return f"Clicked at ({x}, {y})"

def type_text(text: str, press_enter: bool = False):
    pyautogui.write(text, interval=0.02)
    if press_enter:
        pyautogui.press('enter')
    return f"Typed: {text}"

def press_hotkey(keys: str):
    key_list = [k.strip() for k in keys.split(',')]
    pyautogui.hotkey(*key_list)
    return f"HotKey: {keys}"

def exec_python_code(code: str):
    try:
        temp_file = "temp_script.py"
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(code)
        res = subprocess.run([sys.executable, temp_file], capture_output=True, text=True, timeout=30)
        output = res.stdout or res.stderr or "Executed with no output."
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return output.strip()
    except Exception as e:
        return f"Execution Error: {str(e)}"

def get_system_stats():
    cpu_usage = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory()
    return f"📊 CPU: {cpu_usage}% | RAM: {ram.percent}% ({ram.used // (1024**2)}MB / {ram.total // (1024**2)}MB)"

def read_clipboard():
    try:
        return pyperclip.paste()
    except Exception as e:
        return f"Error clipboard: {str(e)}"

# ---------- FAST WIN32 VOLUME CONTROL (0 DELAY) ----------
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF

def _send_vk(vk_code):
    if os.name == "nt":
        ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
        ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)
    else:
        if vk_code == VK_VOLUME_UP:
            pyautogui.press("volumeup")
        elif vk_code == VK_VOLUME_DOWN:
            pyautogui.press("volumedown")
        else:
            pyautogui.press("volumemute")

def change_volume(action: str):
    """ปรับเสียงแบบยิง Keycode ตรงเข้า Win32 API ไม่หน่วง"""
    if action == "up":
        _send_vk(VK_VOLUME_UP)
    elif action == "down":
        _send_vk(VK_VOLUME_DOWN)
    elif action == "mute":
        _send_vk(VK_VOLUME_MUTE)

# ---------- UNIVERSAL BRIGHTNESS CONTROL ----------
def get_brightness_level() -> int:
    """ดึงระดับความสว่างหน้าจอปัจจุบัน (%)"""
    if sbc:
        try:
            curr = sbc.get_brightness()
            if isinstance(curr, list) and len(curr) > 0:
                return int(curr[0])
            elif isinstance(curr, int):
                return curr
        except Exception:
            pass
    return 50

def _adjust_brightness_work(delta: int):
    if sbc:
        try:
            curr = sbc.get_brightness()
            if isinstance(curr, list) and len(curr) > 0:
                curr = curr[0]
            elif not isinstance(curr, int):
                curr = 50
            new_val = max(0, min(100, curr + delta))
            sbc.set_brightness(new_val)
            return new_val
        except Exception:
            pass

    op = "+" if delta > 0 else "-"
    val = abs(delta)
    cmd = (
        'powershell -Command "$b = (Get-CimInstance -Namespace root/Wmi -ClassName WmiMonitorBrightness).CurrentBrightness; '
        f'(Get-CimInstance -Namespace root/Wmi -ClassName WmiMonitorBrightnessMethods).WmiSetBrightness(1, [math]::min(100, [math]::max(0, $b {op} {val})))"'
    )
    subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return 50

def change_brightness(delta: int) -> int:
    """ปรับแสงและคืนค่า % ความสว่างใหม่"""
    curr = get_brightness_level()
    new_val = max(0, min(100, curr + delta))
    if sbc:
        try:
            sbc.set_brightness(new_val)
            return new_val
        except Exception:
            pass
    _adjust_brightness_work(delta)
    return new_val

def check_danger(command: str):
    c = (command or "").lower().strip()
    if re.fullmatch(r"shutdown(\.exe)?\s+/a", c):
        return []
    reasons = []
    for pattern, reason in DANGEROUS_RULES:
        if re.search(pattern, c) and reason not in reasons:
            reasons.append(reason)
    return reasons

def is_dangerous_hotkey(keys: str) -> bool:
    pressed = {k.strip().lower() for k in re.split(r"[,+]", keys or "") if k.strip()}
    return any(h <= pressed for h in DANGEROUS_HOTKEYS)

def request_confirmation(st_session_state, items):
    pending = st_session_state.get("pending_confirm") or []
    for it in items:
        if not any(p["kind"] == it["kind"] and p["payload"] == it["payload"] for p in pending):
            pending.append(it)
    st_session_state.pending_confirm = pending

def execute_confirmed(item):
    if item["kind"] == "python":
        return exec_python_code(item["payload"])
    if item["kind"] == "cmd":
        return run_system_command(item["payload"])
    return launch_command(item["payload"])

@st.dialog("⚠️ ยืนยันก่อนดำเนินการ")
def confirm_dialog(items):
    st.warning("คำสั่งต่อไปนี้อาจกระทบเครื่องหรือข้อมูลของคุณ ตรวจให้แน่ใจก่อนกดยืนยัน (ปิดหน้าต่างนี้ = ยกเลิก)")
    for it in items:
        st.markdown(f"**{it['reason']}**")
        st.code(it["payload"], language="python" if it["kind"] == "python" else "bat")
    col_yes, col_no = st.columns(2)
    if col_yes.button("✅ ยืนยัน ทำเลย", key="cf_yes", use_container_width=True):
        outputs = []
        for it in items:
            out = str(execute_confirmed(it))
            outputs.append(f"- {it['reason']}: `{it['payload'][:80]}` → {out[:120]}")
        st.session_state.messages.append({"role": "assistant", "content": "✅ ยืนยันแล้ว ดำเนินการให้ครับ\n" + "\n".join(outputs)})
        st.rerun()
    if col_no.button("❌ ยกเลิก", key="cf_no", use_container_width=True):
        st.session_state.messages.append({"role": "assistant", "content": "🚫 ยกเลิกคำสั่งอันตรายแล้วครับ ไม่มีอะไรถูกรัน"})
        st.rerun()

def capture_desktop():
    img = pyautogui.screenshot()
    if img.mode != 'RGB':
        img = img.convert('RGB')
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=70)
    return buf.getvalue()

def capture_desktop_scaled(max_width=1280):
    img = pyautogui.screenshot()
    if img.mode != 'RGB':
        img = img.convert('RGB')
    scale = 1.0
    if img.width > max_width:
        scale = img.width / max_width
        img = img.resize((max_width, max(1, round(img.height / scale))))
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=70)
    return buf.getvalue(), scale, img.size

def _named(name):
    def deco(fn):
        fn.__name__ = name
        fn.__qualname__ = name
        return fn
    return deco

@_named("run_system_command")
def run_system_command_tool(command: str):
    reasons = check_danger(command)
    if reasons:
        return BLOCKED_MSG
    return run_system_command(command)

@_named("exec_python_code")
def exec_python_code_tool(code: str):
    reasons = check_danger(code)
    if reasons:
        return BLOCKED_MSG
    return exec_python_code(code)

@_named("type_text")
def type_text_tool(text: str, press_enter: bool = False):
    if check_danger(text):
        return "BLOCKED: ไม่อนุญาตให้พิมพ์คำสั่งอันตราย"
    return type_text(text, press_enter)

@_named("press_hotkey")
def press_hotkey_tool(keys: str):
    if is_dangerous_hotkey(keys):
        return "BLOCKED: คีย์ลัดนี้อันตราย ไม่อนุญาต"
    return press_hotkey(keys.replace("+", ","))

tools_list = [click_screen, type_text_tool, press_hotkey_tool, run_system_command_tool,
              exec_python_code_tool, get_system_stats, read_clipboard]
tools_map = {fn.__name__: fn for fn in tools_list}