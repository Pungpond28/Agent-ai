import os
import json
import re
import urllib.parse
import urllib.request
import difflib
import pyautogui
import streamlit as st
from system_tools import launch_command, get_system_stats, check_danger, request_confirmation, SLEEP_CMD

COMMANDS_FILE = "commands.json"

DEFAULT_COMMANDS = {
    "vs code": "start code .",
    "vscode": "start code .",
    "code": "start code .",
    "chrome": "start chrome",
    "browser": "start chrome",
    "google": "start https://www.google.com",
    "claude": "start https://claude.ai",
    "shutdown": "shutdown /s /t 0",
    "notebooklm": "start https://notebooklm.google.com",
    "classroom": "start https://classroom.google.com",
    "youtube": "start https://www.youtube.com",
    "colab": "start https://colab.research.google.com",
    "cmd": "start cmd",
    "terminal": "start wt || start cmd",
    "task manager": "start taskmgr",
    "ram": "STATS",
    "cpu": "STATS"
}

@st.cache_data
def load_fast_commands():
    if os.path.exists(COMMANDS_FILE):
        try:
            with open(COMMANDS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_COMMANDS.copy()

def save_fast_commands(cmds):
    with open(COMMANDS_FILE, "w", encoding="utf-8") as f:
        json.dump(cmds, f, ensure_ascii=False, indent=4)
    st.cache_data.clear()

POWER_COMMANDS = [
    (["พักเครื่อง", "สลีป", "sleep"], SLEEP_CMD, "พักเครื่อง (Sleep)"),
    (["รีสตาร์ท", "รีสตาร์ต", "รีบูต", "restart", "reboot"], "shutdown /r /t 0", "รีสตาร์ทเครื่อง"),
    (["ออกจากระบบ", "ล็อกเอาท์", "ล็อกเอาต์", "sign out", "log off", "logout"], "shutdown /l", "ออกจากระบบ Windows"),
]

def check_and_run_fast_path(user_text: str, session_state):
    text_raw = user_text.strip()
    text_lower = text_raw.lower()
    text_clean = re.sub(r'\s+', ' ', text_lower)

    # 1. Taskbar Shortcuts
    tb_match = re.search(r'(?:taskbar|แท็บ|ลำดับ|แอป|ไอคอน)\s*([1-9])', text_clean)
    if tb_match:
        num = tb_match.group(1)
        pyautogui.hotkey('win', num)
        return f"⚡ **Fast-Path:** สั่งเปิดแอปบน Taskbar ลำดับที่ {num} (Win + {num}) เรียบร้อยครับ!"

    # 2. เล่นเพลง / เปิดคลิป YouTube (ดักจับทุกรูปแบบ: เปิด bnk48, เปิดเพลง..., เล่นเพลง...)
    autoplay_patterns = [
        r'^(?:เปิด|เล่น|ฟัง)\s*(?:เพลง|คลิป)?\s*(.+)$',
        r'^(?:เปิดเพลง|เล่นเพลง|ฟังเพลง|เล่นคลิป|เปิดคลิป)\s*(.+)$'
    ]
    for pattern in autoplay_patterns:
        match = re.match(pattern, text_clean)
        if match:
            query = match.group(1).strip()
            # ตัดคำขยะท้ายประโยคออก
            query = re.sub(r'\s*(?:ให้หน่อย|หน่อย|ให้ที|ที|ครับ|ค่ะ)\s*$', '', query).strip()
            if query and query not in ["google", "chrome", "vs code", "vscode", "code", "youtube", "task manager"]:
                try:
                    encoded_query = urllib.parse.quote(query)
                    search_url = f"https://www.youtube.com/results?search_query={encoded_query}"
                    req = urllib.request.Request(search_url, headers={'User-Agent': 'Mozilla/5.0'})
                    html = urllib.request.urlopen(req, timeout=5).read().decode('utf-8')
                    video_ids = re.findall(r"watch\?v=(\S{11})", html)
                    if video_ids:
                        direct_video_url = f"https://www.youtube.com/watch?v={video_ids[0]}"
                        launch_command(f'start chrome "{direct_video_url}"')
                        return f"🎵 **Fast-Path:** สั่งเปิดเล่นคลิปแรกของ `{query}` บน YouTube ทันทีเรียบร้อยครับ!"
                except Exception:
                    pass
                launch_command(f'start chrome "https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"')
                return f"🎵 **Fast-Path:** สั่งเปิดค้นหาเพลง `{query}` บน YouTube เรียบร้อยครับ!"

    # 3. ค้นหาข่าว / Google
    if "ข่าว" in text_clean or text_clean.startswith("ค้นหา"):
        encoded_query = urllib.parse.quote(text_raw)
        launch_command(f'start chrome "https://www.google.com/search?q={encoded_query}"')
        return f"🌐 **Fast-Path:** สั่งเปิด Google ค้นหา `{text_raw}` เรียบร้อยครับ!"

    # 4. คำสั่งระบบพลังงาน (ปิดเครื่อง/รีสตาร์ท/สลีป -> บังคับถามยืนยัน)
    if len(text_clean) <= 30:
        for words, cmd, label in POWER_COMMANDS:
            if any(w in text_clean for w in words):
                request_confirmation(session_state, [{"kind": "launch", "payload": cmd, "reason": label}])
                return f"⏸️ **รอการยืนยัน:** {label} — กดยืนยันในหน้าต่างที่เด้งขึ้นมาครับ"

    # 5. Fast Keyword Matching (เปิดแอป / เปิดเว็บ)
    fast_cmds = load_fast_commands()
    for key, cmd in fast_cmds.items():
        if key in text_clean:
            if cmd == "STATS":
                return get_system_stats()
            reasons = check_danger(cmd)
            if reasons:
                request_confirmation(session_state, [{"kind": "launch", "payload": cmd, "reason": reasons[0]}])
                return f"⏸️ **รอการยืนยัน:** {reasons[0]} (`{cmd}`) — กดยืนยันในหน้าต่างที่เด้งขึ้นมาครับ"
            launch_command(cmd)
            return f"⚡ **Fast-Path:** สั่งเปิด/ทำงานคำสั่ง `{cmd}` เรียบร้อยครับ!"

    # 6. Smart Fuzzy Matching
    words = text_clean.split()
    for word in words:
        matches = difflib.get_close_matches(word, list(fast_cmds.keys()), n=1, cutoff=0.6)
        if matches:
            matched_key = matches[0]
            cmd = fast_cmds[matched_key]
            if cmd == "STATS":
                return get_system_stats()
            reasons = check_danger(cmd)
            if reasons:
                request_confirmation(session_state, [{"kind": "launch", "payload": cmd, "reason": reasons[0]}])
                return f"⏸️ **รอการยืนยัน:** {reasons[0]} (`{cmd}`) — กดยืนยันในหน้าต่างที่เด้งขึ้นมาครับ"
            launch_command(cmd)
            return f"⚡ **Fast-Path (Fuzzy Match):** เดาจากคำว่า '{word}' -> สั่งเปิด `{matched_key}` เรียบร้อยครับ!"

    return None