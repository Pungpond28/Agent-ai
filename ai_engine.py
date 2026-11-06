import os
import io
import re
import json
import base64
import inspect
import urllib.parse
import urllib.request
import urllib.error
import asyncio
import pyautogui
import streamlit as st
from google import genai
from google.genai import types

from system_tools import tools_list, tools_map, capture_desktop, capture_desktop_scaled

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    YouTubeTranscriptApi = None

try:
    import speech_recognition as sr
except ImportError:
    sr = None

GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash"]
SCREEN_WIDTH, SCREEN_HEIGHT = pyautogui.size()

def _load_env_file(name=".env"):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), name)
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except Exception:
        pass

_load_env_file()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "")
OLLAMA_NUM_CTX = int(os.environ.get("OLLAMA_NUM_CTX", "8192"))
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "small")
WHISPER_HINT = os.environ.get("WHISPER_HINT",
    "คำสั่งคอมพิวเตอร์ ปนภาษาอังกฤษ: VS Code, Chrome, YouTube, Classroom, "
    "NotebookLM, Task Manager, RAM, CPU, Shutdown, Taskbar 1")

@st.cache_resource
def _get_recognizer():
    r = sr.Recognizer()
    r.dynamic_energy_threshold = True
    return r, {"calibrated": False}

def listen_from_mic(on_ready=None, on_captured=None, offline=False):
    if not sr:
        return "❌ ไลบรารี SpeechRecognition ยังไม่ได้ติดตั้ง"
    try:
        r, state = _get_recognizer()
        with sr.Microphone() as source:
            if not state["calibrated"]:
                r.adjust_for_ambient_noise(source, duration=0.3)
                state["calibrated"] = True
            if on_ready:
                on_ready()
            audio = r.listen(source, timeout=5, phrase_time_limit=8)
        if on_captured:
            on_captured()
        if offline:
            try:
                try:
                    return r.recognize_whisper(audio, model=WHISPER_MODEL, language="thai",
                                               initial_prompt=WHISPER_HINT).strip()
                except TypeError:
                    return r.recognize_whisper(audio, model=WHISPER_MODEL, language="thai").strip()
            except ImportError as e:
                return f"❌ โหลด Whisper ไม่สำเร็จ ({e})"
            except AttributeError as e:
                return f"❌ SpeechRecognition เวอร์ชันนี้ไม่มี recognize_whisper ({e})"
        return r.recognize_google(audio, language="th-TH")
    except Exception as e:
        return f"❌ ข้อผิดพลาดไมค์: {str(e)}"


def listen_continuously(stop_event, result_queue, offline=False):
    """Listen for successive phrases and send results through a thread-safe queue."""
    if not sr:
        result_queue.put(("error", "ไลบรารี SpeechRecognition ยังไม่ได้ติดตั้ง"))
        result_queue.put(("stopped", None))
        return

    try:
        recognizer = sr.Recognizer()
        recognizer.dynamic_energy_threshold = True
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.3)

            while not stop_event.is_set():
                try:
                    audio = recognizer.listen(source, timeout=1, phrase_time_limit=8)
                except sr.WaitTimeoutError:
                    continue

                try:
                    if offline:
                        try:
                            phrase = recognizer.recognize_whisper(
                                audio, model=WHISPER_MODEL, language="thai",
                                initial_prompt=WHISPER_HINT
                            ).strip()
                        except TypeError:
                            phrase = recognizer.recognize_whisper(
                                audio, model=WHISPER_MODEL, language="thai"
                            ).strip()
                    else:
                        phrase = recognizer.recognize_google(audio, language="th-TH").strip()
                except sr.UnknownValueError:
                    continue

                if phrase:
                    result_queue.put(("recognized", phrase))
    except Exception as e:
        result_queue.put(("error", f"ข้อผิดพลาดไมค์: {e}"))
    finally:
        result_queue.put(("stopped", None))

def get_youtube_transcript(url: str):
    if not YouTubeTranscriptApi:
        return "❌ ไลบรารี youtube-transcript-api ยังไม่ได้ติดตั้ง"
    try:
        video_id_match = re.search(r"(?:v=|\/|embed\/|shorts\/)([0-9A-Za-z_-]{11})", url)
        if not video_id_match:
            return "❌ URL YouTube ไม่ถูกต้อง"
        video_id = video_id_match.group(1)
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['th', 'en'])
        except:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript = transcript_list.find_transcript(['th', 'en', 'auto']).fetch()
        return " ".join([item['text'] for item in transcript])[:15000]
    except Exception as e:
        return f"❌ ดึงซับไม่ได้: {str(e)}"

def generate_handoff_summary(messages):
    if not messages:
        return "ยังไม่มีประวัติแชท"
    chat_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in messages])
    prompt = f"สร้าง Handoff Summary สรุปเป้าหมาย สิ่งที่ทำไปแล้ว และงานค้างจากประวัติต่อไปนี้:\n{chat_text}"
    try:
        return llm_text(prompt)
    except Exception as e:
        return f"❌ เกิดข้อผิดพลาดในการสร้าง Handoff: {e}"

_LOCAL_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def is_offline() -> bool:
    return bool(st.session_state.get("offline_mode", False))

def get_ollama_model() -> str:
    return st.session_state.get("ollama_model") or OLLAMA_DEFAULT_MODEL

def _ollama_call(path, payload=None, timeout=180):
    url = OLLAMA_URL.rstrip("/") + path
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with _LOCAL_OPENER.open(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode("utf-8")).get("error", "")
        except Exception:
            detail = ""
        raise RuntimeError(detail or f"Ollama ตอบกลับ HTTP {e.code}")
    except urllib.error.URLError:
        raise RuntimeError("เชื่อมต่อ Ollama ไม่ได้ — เปิดแอป Ollama ก่อนครับ")
    except TimeoutError:
        raise RuntimeError("โมเดลตอบช้าเกินกำหนด")

def ollama_list_models():
    try:
        data = _ollama_call("/api/tags", timeout=2)
        return sorted(m["name"] for m in data.get("models", [])), None
    except RuntimeError as e:
        return [], str(e)

def ollama_chat(messages, tools=None, model=None):
    payload = {"model": model or get_ollama_model(), "messages": messages, "stream": False,
               "options": {"num_ctx": OLLAMA_NUM_CTX}}
    if tools:
        payload["tools"] = tools
    return _ollama_call("/api/chat", payload)

def _strip_think(text):
    return re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()

def ollama_text(prompt):
    if not get_ollama_model():
        raise RuntimeError("ยังไม่ได้เลือกโมเดล Ollama")
    resp = ollama_chat([{"role": "user", "content": prompt}])
    return _strip_think(resp.get("message", {}).get("content", "")) or "(โมเดลไม่ตอบกลับ)"

def llm_text(prompt):
    if is_offline():
        return ollama_text(prompt)
    if client is None:
        raise RuntimeError("ยังไม่ได้ตั้งค่า GEMINI_API_KEY")
    last = ""
    for model_name in GEMINI_MODELS:
        try:
            return client.models.generate_content(model=model_name, contents=prompt).text
        except Exception as e:
            last = str(e)[:200]
    raise RuntimeError(f"Gemini ไม่ตอบสนอง: {last}")

def call_tool(name, args, coord_scale=1.0):
    fn = tools_map.get(name)
    if fn is None:
        return f"ไม่มีเครื่องมือชื่อ {name}"
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception:
            args = {}
    allowed = inspect.signature(fn).parameters
    args = {k: v for k, v in dict(args or {}).items() if k in allowed}
    try:
        if name == "click_screen":
            args["x"] = int(float(args["x"]) * coord_scale)
            args["y"] = int(float(args["y"]) * coord_scale)
        elif name == "type_text" and "press_enter" in args:
            args["press_enter"] = str(args["press_enter"]).lower() in ("true", "1", "yes")
        elif name == "press_hotkey" and isinstance(args.get("keys"), (list, tuple)):
            args["keys"] = ",".join(map(str, args["keys"]))
        return fn(**args)
    except Exception as e:
        return f"Error: {e}"

def _tool_schema(name, desc, props=None, required=None):
    return {"type": "function", "function": {
        "name": name, "description": desc,
        "parameters": {"type": "object", "properties": props or {}, "required": required or []}}}

OLLAMA_TOOLS = [
    _tool_schema("click_screen", "Click mouse", {"x": {"type": "integer"}, "y": {"type": "integer"}}, ["x", "y"]),
    _tool_schema("type_text", "Type text", {"text": {"type": "string"}, "press_enter": {"type": "boolean"}}, ["text"]),
    _tool_schema("press_hotkey", "Press hotkey", {"keys": {"type": "string"}}, ["keys"]),
    _tool_schema("run_system_command", "Run cmd", {"command": {"type": "string"}}, ["command"]),
    _tool_schema("exec_python_code", "Run python", {"code": {"type": "string"}}, ["code"]),
    _tool_schema("get_system_stats", "Get stats"),
    _tool_schema("read_clipboard", "Read clip"),
]

def run_ollama_agent(user_prompt, status_box, input_image_bytes=None):
    model = get_ollama_model()
    if not model:
        status_box.error("❌ ยังไม่ได้เลือกโมเดล Ollama")
        return

    images, scale, note = [], 1.0, ""
    if st.session_state.get("ollama_vision"):
        shot, scale, (w, h) = capture_desktop_scaled()
        images.append(base64.b64encode(shot).decode())
        note = f"\n(แนบภาพหน้าจอปัจจุบันขนาด {w}x{h} พิกเซล)"
    if input_image_bytes:
        images.append(base64.b64encode(input_image_bytes).decode())
        note += "\n(มีรูปแนบมาด้วย)"

    system = (f"คุณคือ OS Assistant ที่ควบคุมเครื่อง Windows (หน้าจอ {SCREEN_WIDTH}x{SCREEN_HEIGHT}) "
              "ตอบเป็นภาษาไทยสั้นๆ กระชับ ถ้าสั่งเปิดแอป เปิดเว็บ หรือเปิดเพลง ให้เรียกใช้ Tool สั่งงานทันที ห้ามถามยืนยัน")
    user_msg = {"role": "user", "content": user_prompt + note}
    if images:
        user_msg["images"] = images
    messages = [{"role": "system", "content": system}, user_msg]

    use_tools = True
    for _ in range(5):
        try:
            resp = ollama_chat(messages, tools=OLLAMA_TOOLS if use_tools else None, model=model)
        except RuntimeError as e:
            err = str(e)
            if use_tools and "tool" in err.lower():
                use_tools = False
                status_box.warning(f"⚠️ โมเดล `{model}` เรียกเครื่องมือไม่ได้ ตอบเป็นข้อความอย่างเดียว")
                continue
            status_box.error(f"❌ Ollama: {err}")
            return
        msg = resp.get("message", {}) or {}
        calls = msg.get("tool_calls") or []
        if not calls:
            text = _strip_think(msg.get("content", "")) or "เสร็จสิ้น"
            status_box.success("✅ ดำเนินการเสร็จเรียบร้อย!")
            st.markdown(text)
            return
        messages.append(msg)
        for c in calls:
            fn = c.get("function", {}) or {}
            name, args = fn.get("name", ""), fn.get("arguments") or {}
            status_box.info(f"👉 โมเดลสั่งการ: `{name}` -> `{args}`")
            result = call_tool(name, args, scale)
            messages.append({"role": "tool", "tool_name": name, "content": str(result)[:4000]})
    status_box.warning("⚠️ โมเดลเรียกเครื่องมือครบ 5 รอบแล้ว")

async def run_gemini_agent(user_prompt, status_box, input_image_bytes=None):
    sys_instruction = f"""คุณคือ Gemini OS Assistant คุมเครื่อง Windows (ความละเอียด {SCREEN_WIDTH}x{SCREEN_HEIGHT})
    คุณมี tools ในการสั่งรันคำสั่ง, ควบคุมเมาส์/คีย์บอร์ดบนหน้าจอจริง
    ห้ามถามยืนยันผู้ใช้สำหรับการเปิดเว็บ, เปิดเพลง, เปิดโปรแกรม หรือคำสั่งทั่วไปเด็ดขาด
    ย้ำ: ให้เรียกรัน Tool ทำงานทันทีโดยไม่ต้องถามยืนยัน ยกเว้นคำสั่งปิดเครื่อง/รีสตาร์ทเท่านั้น
    """
    contents = []
    screen_bytes = capture_desktop()

    parts = [types.Part.from_bytes(data=screen_bytes, mime_type="image/jpeg")]
    if input_image_bytes:
        parts.append(types.Part.from_bytes(data=input_image_bytes, mime_type="image/jpeg"))
        parts.insert(0, types.Part.from_text(text=f"{sys_instruction}\n\nคำสั่งผู้ใช้: {user_prompt}\n(หมายเหตุ: มีรูปแนบอ้างอิงจากผู้ใช้มาด้วย)"))
    else:
        parts.insert(0, types.Part.from_text(text=f"{sys_instruction}\n\nคำสั่งผู้ใช้: {user_prompt}"))

    contents.append(types.Content(role="user", parts=parts))

    if client is None:
        status_box.error("❌ ยังไม่ได้ตั้งค่า GEMINI_API_KEY")
        return

    response = None
    last_err = ""
    for model_name in GEMINI_MODELS:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(tools=tools_list)
            )
            if response:
                break
        except Exception as e:
            last_err += f"\n- {model_name}: {str(e)[:300]}"
            continue

    if not response:
        status_box.error(f"❌ เกิดข้อผิดพลาดจากเซิร์ฟเวอร์: {last_err}")
        return

    if not response.candidates:
        status_box.error("❌ ไม่ได้รับคำตอบจากโมเดล")
        return
    candidate = response.candidates[0]

    function_calls = getattr(response, "function_calls", None)
    if function_calls:
        for fc in function_calls:
            fname = fc.name
            fargs = fc.args or {}
            status_box.info(f"👉 Gemini สั่งการ: `{fname}` -> `{fargs}`")
            call_tool(fname, fargs)
            await asyncio.sleep(0.5)
        status_box.success("✅ ดำเนินการเรียบร้อย!")
    else:
        text_resp = None
        try:
            text_resp = response.text
        except Exception:
            pass
        if not text_resp:
            parts = (candidate.content.parts or []) if candidate.content else []
            text_resp = next((p.text for p in parts if getattr(p, "text", None)), None) or "เสร็จสิ้น"
        status_box.success("✅ ดำเนินการเสร็จเรียบร้อย!")
        st.markdown(text_resp)
