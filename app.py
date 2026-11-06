import sys
import asyncio
import queue
import threading

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import os
import re
import io
import pyautogui
import psutil
import streamlit as st
from PIL import Image, ImageGrab

from styles import inject_custom_css
from system_tools import (
    run_bg, change_volume, change_brightness, get_brightness_level, launch_command,
    run_system_command, read_clipboard, confirm_dialog, SLEEP_CMD,
    request_confirmation, SCREEN_WIDTH, SCREEN_HEIGHT
)
from fast_path import load_fast_commands, save_fast_commands, check_and_run_fast_path
from ai_engine import (
    client, is_offline, ollama_list_models, listen_from_mic, listen_continuously,
    get_youtube_transcript, generate_handoff_summary, llm_text,
    run_ollama_agent, run_gemini_agent
)

st.set_page_config(page_title="Gemini OS Center", page_icon="⚡", layout="wide")

_ver = tuple(int(x) for x in re.findall(r"\d+", st.__version__)[:2])
if _ver < (1, 39):
    st.error(f"⚠️ Streamlit เวอร์ชัน {st.__version__} เก่าเกินไป ต้องเป็น 1.39 ขึ้นไป\n\n"
             "เปิดเทอร์มินัลแล้วรัน: `python -m pip install -U streamlit` จากนั้นรันแอปใหม่")
    st.stop()

inject_custom_css()

# Header Title Section
st.markdown("""
<div class="header-container">
    <div class="main-title"><span class="glow-bolt">⚡</span>Gemini <span class="gradient-text">Fast OS</span> & Workspace Center</div>
    <div class="main-subtitle">ระบบควบคุม Windows ความเร็วสูง (Modularized Edition) | หน้าจอ: {} x {}{}</div>
</div>
""".format(SCREEN_WIDTH, SCREEN_HEIGHT,
           " | 🔒 โหมดส่วนตัว (AI ในเครื่อง)" if st.session_state.get("offline_mode") else ""), unsafe_allow_html=True)

# ==================== SIDEBAR MENU ====================

with st.sidebar:
    st.markdown("""
    <div class="sidebar-card-header">
        <div class="icon-box">🔒</div>
        <div>
            <div class="header-text-title">โหมดส่วนตัว / ออฟไลน์</div>
            <div class="header-text-sub">Local AI via Ollama</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    _voice_thread = st.session_state.get("_continuous_voice_thread")
    _voice_mode_locked = bool(_voice_thread and _voice_thread.is_alive())
    st.toggle("ใช้ AI ในเครื่อง (ไม่ส่งขึ้นอินเทอร์เน็ต)", key="offline_mode",
              disabled=_voice_mode_locked)
    if _voice_mode_locked:
        st.caption("หยุดฟังต่อเนื่องก่อนจึงเปลี่ยนโหมด AI ได้")
    if st.session_state.get("offline_mode"):
        _models, _err = ollama_list_models()
        if _err:
            st.error(_err)
        elif not _models:
            st.warning("ยังไม่มีโมเดลใน Ollama")
        else:
            if st.session_state.get("ollama_model") not in _models:
                st.session_state.ollama_model = _models[0]
            st.selectbox("โมเดลที่ใช้", _models, key="ollama_model")
            st.checkbox("ให้โมเดลเห็นหน้าจอ", key="ollama_vision")
            st.caption("🔒 ประมวลผลในเครื่อง ไมค์ใช้ Whisper")
    else:
        st.caption("☁️ ตอนนี้ใช้ Gemini" + ("" if client else " — ⚠️ ยังไม่ได้ตั้ง GEMINI_API_KEY"))

    st.markdown("---")

    st.markdown("""
    <div class="sidebar-card-header">
        <div class="icon-box">⚙️</div>
        <div>
            <div class="header-text-title">จัดการคำสั่งด่วน</div>
            <div class="header-text-sub">Fast-Path JSON Manager</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    fast_cmds = load_fast_commands()
    with st.expander("➕ เพิ่ม / ลบ คำสั่งเปิดโปรแกรม-เว็บ"):
        new_key = st.text_input("คำสั่งสั่งพูด", key="new_k")
        new_cmd = st.text_input("คำสั่งเครื่อง", key="new_c")
        if st.button("💾 บันทึกคำสั่งใหม่", use_container_width=True):
            if new_key and new_cmd:
                fast_cmds[new_key.strip().lower()] = new_cmd.strip()
                save_fast_commands(fast_cmds)
                st.toast(f"บันทึกคำสั่ง '{new_key}' สำเร็จ!")
                st.rerun()

        st.markdown("---")
        del_key = st.selectbox("เลือกคำสั่งที่ต้องการลบ", list(fast_cmds.keys()))
        if st.button("🗑️ ลบคำสั่งนี้", use_container_width=True):
            if del_key in fast_cmds:
                del fast_cmds[del_key]
                save_fast_commands(fast_cmds)
                st.toast(f"ลบคำสั่ง '{del_key}' เรียบร้อยแล้ว!")
                st.rerun()

    st.markdown("---")

    # Card 3: Quick Shortcuts
    st.markdown("""
    <div class="sidebar-card-header">
        <div class="icon-box">⚡</div>
        <div>
            <div class="header-text-title">ทางลัดควบคุม & เปิดโปรแกรม</div>
            <div class="header-text-sub">Quick Action Launchers</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.caption("🔊 ควบคุมระดับเสียง")
    col_v1, col_v2, col_v3 = st.columns(3)
    with col_v1:
        if st.button("🔉 ลด", use_container_width=True, help="ลดเสียง"):
            change_volume("down")
    with col_v2:
        if st.button("🔇 ปิด", use_container_width=True, help="เปิด/ปิดเสียง"):
            change_volume("mute")
    with col_v3:
        if st.button("🔊 เพิ่ม", use_container_width=True, help="เพิ่มเสียง"):
            change_volume("up")

    st.caption("☀️ ปรับความสว่างหน้าจอ")
    if "brightness_val" not in st.session_state:
        st.session_state.brightness_val = get_brightness_level()

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button("🔆 ลด (-10%)", use_container_width=True):
            st.session_state.brightness_val = change_brightness(-10)
            st.rerun()
    with col_b2:
        if st.button("☀️ เพิ่ม (+10%)", use_container_width=True):
            st.session_state.brightness_val = change_brightness(10)
            st.rerun()

    b_val = st.session_state.brightness_val
    st.markdown(f"**ระดับแสงปัจจุบัน:** <span style='color:var(--accent-cyan); font-weight:700;'>{b_val}%</span>", unsafe_allow_html=True)
    st.progress(b_val / 100)

    st.caption("🚀 เปิดโปรแกรม / เว็บไซต์")
    col_app1, col_app2 = st.columns(2)
    with col_app1:
        if st.button("💻 VS Code", use_container_width=True):
            launch_command("start code .")
        if st.button("🎵 YouTube", use_container_width=True):
            launch_command("start https://www.youtube.com")
    with col_app2:
        if st.button("🌐 Chrome", use_container_width=True):
            launch_command("start chrome")
        if st.button("🟡 Colab", use_container_width=True):
            launch_command("start https://colab.research.google.com")
            st.toast("เปิด Google Colab เรียบร้อย!")

    st.caption("⚡ สั่งงานระบบพลังงาน")
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        if st.button("🌙 Sleep", use_container_width=True):
            request_confirmation(st.session_state, [{"kind": "launch", "payload": SLEEP_CMD, "reason": "พักเครื่อง (Sleep)"}])
            st.rerun()
    with col_p2:
        if st.button("🔄 Restart", use_container_width=True):
            request_confirmation(st.session_state, [{"kind": "launch", "payload": "shutdown /r /t 0", "reason": "รีสตาร์ทเครื่อง"}])
            st.rerun()
    with col_p3:
        if st.button("🛑 Off", use_container_width=True, help="ปิดเครื่อง"):
            request_confirmation(st.session_state, [{"kind": "launch", "payload": "shutdown /s /t 0", "reason": "ปิดเครื่อง"}])
            st.rerun()

    st.markdown("---")

    st.markdown("""
    <div class="sidebar-card-header">
        <div class="icon-box">📊</div>
        <div>
            <div class="header-text-title">สถานะเครื่องปัจจุบัน</div>
            <div class="header-text-sub">Real-Time Performance</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    cpu_val = psutil.cpu_percent()
    ram_val = psutil.virtual_memory().percent

    cpu_color = "var(--danger)" if cpu_val > 90 else ("var(--warning)" if cpu_val > 70 else "var(--accent-cyan)")
    ram_color = "var(--danger)" if ram_val > 90 else ("var(--warning)" if ram_val > 70 else "var(--accent-cyan)")

    st.markdown(f"**CPU Usage:** <span style='color:{cpu_color}; font-weight:700;'>{cpu_val}%</span>", unsafe_allow_html=True)
    st.progress(cpu_val / 100)

    st.markdown(f"**RAM Usage:** <span style='color:{ram_color}; font-weight:700;'>{ram_val}%</span>", unsafe_allow_html=True)
    st.progress(ram_val / 100)

    st.markdown("---")

    st.markdown("""
    <div class="sidebar-card-header">
        <div class="icon-box">📌</div>
        <div>
            <div class="header-text-title">Handoff & Clipboard</div>
            <div class="header-text-sub">Context Transfer Tools</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("📋 ดึงข้อความ Clipboard", use_container_width=True):
        clip_txt = read_clipboard()
        st.info(f"Clipboard: {clip_txt[:80]}...")
        st.session_state.pending_prompt = f"แปลหรือวิเคราะห์ข้อความจาก Clipboard นี้: {clip_txt}"

    if st.button("🔄 สร้าง Handoff Summary", use_container_width=True):
        if "messages" in st.session_state and st.session_state.messages:
            st.session_state.handoff_result = generate_handoff_summary(st.session_state.messages)

    if "handoff_result" in st.session_state:
        st.code(st.session_state.handoff_result, language="markdown")

    if st.button("🗑️ ล้างประวัติแชท", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ==================== MAIN CHAT INTERFACE ====================

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ==================== BOTTOM BAR ====================

MIC_LISTENING_CSS = """
<style>
    @keyframes micPulse {
        0%   { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.65); }
        70%  { box-shadow: 0 0 0 14px rgba(239, 68, 68, 0); }
        100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
    }
    .st-key-mic_btn button {
        background: rgba(239, 68, 68, 0.22) !important;
        color: var(--danger) !important;
        animation: micPulse 1.2s infinite !important;
    }
</style>
"""

with st.container(key="attach_btn"):
    with st.popover("+", help="แนบรูปภาพ / ดึงรูปจาก Clipboard"):
        st.caption("📎 แนบรูปให้ Gemini ดูพร้อมคำสั่งถัดไป")
        if st.button("📋 ดึงรูปจาก Clipboard ทันที", use_container_width=True, key="btn_clip_img"):
            try:
                clipboard_img = ImageGrab.grabclipboard()
                if isinstance(clipboard_img, Image.Image):
                    buf = io.BytesIO()
                    if clipboard_img.mode != 'RGB':
                        clipboard_img = clipboard_img.convert('RGB')
                    clipboard_img.save(buf, format='JPEG', quality=70)
                    st.session_state.pending_image = buf.getvalue()
                    st.toast("ดึงรูปภาพจาก Clipboard เรียบร้อย!")
                    st.rerun()
                else:
                    st.warning("⚠️ ไม่พบรูปภาพใน Clipboard")
            except Exception as e:
                st.error(f"❌ ดึงรูปไม่สำเร็จ: {str(e)}")
        uploaded_file = st.file_uploader("หรืออัปโหลดรูปภาพที่นี่", type=["png", "jpg", "jpeg"], label_visibility="collapsed",
                                         key=f"img_upload_{st.session_state.get('uploader_n', 0)}")
        if uploaded_file:
            st.session_state.pending_image = uploaded_file.getvalue()
            st.toast("แนบไฟล์รูปเรียบร้อยแล้ว!")

if st.session_state.get("pending_image"):
    st.markdown("""
    <style>
        .st-key-attach_btn button { position: relative !important; }
        .st-key-attach_btn button::after {
            content: ""; position: absolute; top: 3px; right: 3px;
            width: 10px; height: 10px; border-radius: 50%;
            background: var(--accent-cyan);
            box-shadow: 0 0 8px var(--accent-cyan);
        }
    </style>
    """, unsafe_allow_html=True)

if "_continuous_voice_pending" not in st.session_state:
    st.session_state["_continuous_voice_pending"] = []

_voice_thread = st.session_state.get("_continuous_voice_thread")
_voice_thread_alive = bool(_voice_thread and _voice_thread.is_alive())

with st.container(key="mic_btn"):
    mic_clicked = st.button(
        " ", key="btn_mic", icon=":material/mic:", help="กดแล้วพูดสั่งงาน",
        disabled=_voice_thread_alive
    )

voice_start_col, voice_stop_col = st.columns(2)
with voice_start_col:
    start_continuous_voice = st.button(
        "🎙️ เริ่มฟังต่อเนื่อง", key="btn_voice_start", use_container_width=True,
        disabled=_voice_thread_alive
    )
with voice_stop_col:
    stop_continuous_voice = st.button(
        "⏹️ หยุดฟัง", key="btn_voice_stop", use_container_width=True,
        disabled=not _voice_thread_alive
    )

if start_continuous_voice:
    _old_thread = st.session_state.get("_continuous_voice_thread")
    _old_stop = st.session_state.get("_continuous_voice_stop")
    if _old_thread and _old_thread.is_alive() and _old_stop:
        _old_stop.set()
        _old_thread.join(timeout=10)
    if _old_thread and _old_thread.is_alive():
        st.error("ไมค์เดิมยังหยุดไม่เสร็จ กรุณารอสักครู่แล้วลองเริ่มใหม่")
    else:
        _voice_queue = queue.Queue()
        _voice_stop = threading.Event()
        _voice_worker = threading.Thread(
            target=listen_continuously,
            args=(_voice_stop, _voice_queue, is_offline()),
            daemon=True,
            name="continuous-voice-listener",
        )
        st.session_state["_continuous_voice_queue"] = _voice_queue
        st.session_state["_continuous_voice_stop"] = _voice_stop
        st.session_state["_continuous_voice_thread"] = _voice_worker
        st.session_state["_continuous_voice_status"] = "กำลังเตรียมไมค์..."
        st.session_state["_continuous_voice_last_phrase"] = ""
        _voice_worker.start()
    st.rerun()

if stop_continuous_voice:
    _voice_stop = st.session_state.get("_continuous_voice_stop")
    if _voice_stop:
        _voice_stop.set()
        st.session_state["_continuous_voice_status"] = "กำลังหยุดฟัง..."
    st.rerun()


@st.fragment(run_every="1s")
def _continuous_voice_updates():
    result_queue = st.session_state.get("_continuous_voice_queue")
    if result_queue:
        for _ in range(20):
            try:
                kind, value = result_queue.get_nowait()
            except queue.Empty:
                break
            if kind == "recognized":
                st.session_state["_continuous_voice_last_phrase"] = value
                st.session_state["_continuous_voice_pending"].append(value)
                st.session_state["_continuous_voice_status"] = "รับคำสั่งแล้ว กำลังรอฟังต่อ..."
            elif kind == "error":
                st.session_state["_continuous_voice_status"] = f"เกิดข้อผิดพลาด: {value}"
            elif kind == "stopped":
                if not str(st.session_state.get("_continuous_voice_status", "")).startswith("เกิดข้อผิดพลาด:"):
                    st.session_state["_continuous_voice_status"] = "หยุดฟังแล้ว"

    if st.session_state.get("_continuous_voice_pending") and not st.session_state.get("pending_prompt"):
        st.session_state.pending_prompt = st.session_state["_continuous_voice_pending"].pop(0)
        st.session_state["_pending_prompt_source"] = "continuous_voice"
        st.rerun()

    _thread = st.session_state.get("_continuous_voice_thread")
    if _thread and _thread.is_alive():
        _status = st.session_state.get("_continuous_voice_status", "กำลังฟัง...")
        st.info(f"🎙️ {_status}")
        _last_phrase = st.session_state.get("_continuous_voice_last_phrase")
        if _last_phrase:
            st.caption(f"ได้ยินล่าสุด: {_last_phrase}")
    elif st.session_state.get("_continuous_voice_status"):
        st.caption(st.session_state["_continuous_voice_status"])

    if (not (_thread and _thread.is_alive()) and result_queue and result_queue.empty()
            and not st.session_state.get("_continuous_voice_pending")):
        st.rerun()


_voice_queue = st.session_state.get("_continuous_voice_queue")
_voice_thread = st.session_state.get("_continuous_voice_thread")
if ((_voice_thread and _voice_thread.is_alive())
        or (_voice_queue and not _voice_queue.empty())
        or st.session_state.get("_continuous_voice_pending")):
    _continuous_voice_updates()
elif st.session_state.get("_continuous_voice_status"):
    st.caption(st.session_state["_continuous_voice_status"])

if mic_clicked:
    listening_fx = st.empty()
    mic_status = st.empty()
    mic_status.info("⏳ กำลังเตรียมไมค์...")

    def _mic_ready():
        listening_fx.markdown(MIC_LISTENING_CSS, unsafe_allow_html=True)
        mic_status.success("🎙️ พูดได้เลย!")

    def _mic_captured():
        listening_fx.empty()
        mic_status.info("🔄 กำลังแปลงเสียงเป็นข้อความ...")

    voice_txt = listen_from_mic(on_ready=_mic_ready, on_captured=_mic_captured, offline=is_offline())
    listening_fx.empty()
    mic_status.empty()
    if not voice_txt.startswith("❌"):
        st.success(f"🗣️ ได้ยินว่า: '{voice_txt}'")
        st.session_state.pending_prompt = voice_txt
    else:
        st.error(voice_txt)

if "pending_image" in st.session_state and st.session_state.pending_image:
    st.info("🖼️ มีรูปภาพแนบค้างไว้ พร้อมส่งพร้อมคำสั่งถัดไป")
    st.image(st.session_state.pending_image, width=220)
    if st.button("🗑️ ลบรูปที่แนบ", key="btn_clear_img"):
        del st.session_state.pending_image
        st.session_state.uploader_n = st.session_state.get("uploader_n", 0) + 1
        st.rerun()

prompt_to_process = None
image_bytes_to_process = None

if "pending_prompt" in st.session_state and st.session_state.pending_prompt:
    prompt_to_process = st.session_state.pending_prompt
    del st.session_state.pending_prompt
    prompt_source = st.session_state.pop("_pending_prompt_source", None)
else:
    prompt_source = None

user_input = st.chat_input("พิมพ์สั่งงาน (เช่น taskbar 1, ปิด live caption, เปิด vs code, ข่าวใหม่)...")
if user_input:
    if prompt_to_process and prompt_source == "continuous_voice":
        st.session_state["_continuous_voice_pending"].insert(0, prompt_to_process)
    prompt_to_process = user_input
    if "pending_image" in st.session_state:
        image_bytes_to_process = st.session_state.pending_image
        del st.session_state.pending_image
        st.session_state.uploader_n = st.session_state.get("uploader_n", 0) + 1

if prompt_to_process:
    st.session_state.messages.append({"role": "user", "content": prompt_to_process})
    with st.chat_message("user"):
        st.markdown(prompt_to_process)

    with st.chat_message("assistant"):
        p_lower = prompt_to_process.lower()

        if "ปิดเครื่อง" in p_lower and "ยกเลิก" in p_lower:
            out = run_system_command("shutdown /a")
            reply = ("🛑 ยกเลิกการปิดเครื่องที่ตั้งเวลาไว้แล้วครับ" if out.strip() == "Success"
                     else f"ℹ️ ไม่มีการปิดเครื่องที่ตั้งเวลาไว้ให้ยกเลิก ({out.strip()[:100]})")
            st.markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})
        elif "อีก" in p_lower and "ปิดเครื่อง" in p_lower:
            nums = re.findall(r'\d+', prompt_to_process)
            amount = int(nums[0]) if nums else 10
            unit_hours = "ชั่วโมง" in p_lower or "ชม" in p_lower
            mins = amount * 60 if unit_hours else amount
            label = f"ตั้งเวลาปิดเครื่องอีก {amount} {'ชั่วโมง' if unit_hours else 'นาที'}"
            request_confirmation(st.session_state, [{"kind": "launch", "payload": f"shutdown /s /t {mins * 60}", "reason": label}])
            reply = f"⏸️ **รอการยืนยัน:** {label} — กดยืนยันในหน้าต่างที่เด้งขึ้นมาครับ"
            st.warning(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})
        else:
            fast_result = check_and_run_fast_path(prompt_to_process, st.session_state)

            if fast_result and not image_bytes_to_process:
                if fast_result.startswith("⏸️"):
                    st.warning(fast_result)
                else:
                    st.success("✅ ดำเนินการด่วนสำเร็จ!")
                    st.markdown(fast_result)
                st.session_state.messages.append({"role": "assistant", "content": fast_result})
            elif "youtube.com" in prompt_to_process or "youtu.be" in prompt_to_process:
                status_box = st.empty()
                status_box.warning("🎥 กำลังดึงซับและสรุป YouTube...")
                urls = re.findall(r'(https?://[^\s]+)', prompt_to_process)
                yt_url = urls[0] if urls else prompt_to_process
                transcript = get_youtube_transcript(yt_url)
                if "❌" in transcript:
                    st.error(transcript)
                else:
                    if is_offline():
                        transcript = transcript[:8000]
                    try:
                        summary = llm_text(f"สรุปสาระสำคัญจากซับคลิปนี้เป็นภาษาไทย:\n{transcript}")
                    except Exception as e:
                        summary = f"❌ สรุปไม่สำเร็จ: {e}"
                    status_box.success("✅ สรุปเรียบร้อย!")
                    st.markdown(summary)
                    st.session_state.messages.append({"role": "assistant", "content": summary})
            else:
                status_box = st.empty()
                if is_offline():
                    status_box.warning("🔒 กำลังประมวลผลด้วยโมเดลในเครื่อง...")
                    run_ollama_agent(prompt_to_process, status_box, image_bytes_to_process)
                else:
                    status_box.warning("🚀 กำลังจับภาพหน้าจอและประมวลผลคำสั่งด้วย AI Agent...")
                    asyncio.run(run_gemini_agent(prompt_to_process, status_box, image_bytes_to_process))
                st.session_state.messages.append({"role": "assistant", "content": "ดำเนินการเรียบร้อยแล้วครับ"})

# ==================== CONFIRM DIALOG ====================
if st.session_state.get("pending_confirm"):
    _pending_items = st.session_state.pop("pending_confirm")
    confirm_dialog(_pending_items)
