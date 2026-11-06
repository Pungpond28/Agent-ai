import streamlit as st

def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+Thai:wght@400;500;600;700;800&display=swap');

        :root {
            --bg-main: #05070d;
            --bg-card: #0a1020;
            --bg-card-hover: #0d1830;
            --border: rgba(47, 123, 255, 0.25);
            --border-glow: rgba(34, 211, 238, 0.6);
            --accent-blue: #2f7bff;
            --accent-cyan: #22d3ee;
            --text-main: #f1f5ff;
            --text-muted: #8da2c8;
            --success: #22c55e;
            --warning: #f59e0b;
            --danger: #ef4444;
            --pad-l: 5rem;
            --pad-r: 5rem;
            --pad-b: 20px;
            --input-h: 56px;
            --btn: 40px;
        }

        @media (max-width: 768px) {
            :root { --pad-l: 4rem; --pad-r: 1rem; }
        }

        html, body, [data-testid="stAppViewContainer"] {
            font-family: 'Inter', 'Noto Sans Thai', sans-serif !important;
            background-color: var(--bg-main) !important;
            color: var(--text-main) !important;
        }

        [data-testid="stAppViewContainer"] {
            background-image:
                radial-gradient(circle at 88% 12%, rgba(34, 211, 238, 0.15) 0%, rgba(47, 123, 255, 0.06) 35%, transparent 65%),
                linear-gradient(rgba(47, 123, 255, 0.05) 1px, transparent 1px),
                linear-gradient(90deg, rgba(47, 123, 255, 0.05) 1px, transparent 1px) !important;
            background-size: 100% 100%, 36px 36px, 36px 36px !important;
            background-attachment: fixed !important;
        }

        header[data-testid="stHeader"], footer {
            display: none !important;
        }

        .header-container {
            text-align: center;
            padding: 15px 0 20px 0;
            margin-bottom: 10px;
        }
        .main-title {
            font-family: 'Noto Sans Thai', 'Inter', sans-serif;
            font-size: 2.2rem;
            font-weight: 800;
            color: var(--text-main);
            letter-spacing: -0.5px;
            margin: 0;
        }
        .gradient-text {
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-cyan));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800;
        }
        .glow-bolt {
            color: var(--accent-cyan);
            text-shadow: 0 0 12px var(--accent-cyan);
            margin-right: 6px;
        }
        .main-subtitle {
            font-size: 0.9rem;
            color: var(--text-muted);
            margin-top: 6px;
            font-weight: 500;
        }

        [data-testid="stSidebar"] {
            background-color: #030509 !important;
            border-right: 1px solid var(--border) !important;
            box-shadow: 4px 0 24px rgba(0, 0, 0, 0.6) !important;
        }

        .sidebar-card-header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-top: 15px;
            margin-bottom: 6px;
        }
        .icon-box {
            width: 34px;
            height: 34px;
            border-radius: 9px;
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-cyan));
            display: flex;
            align-items: center;
            justify-content: center;
            color: #05070d;
            font-weight: 800;
            font-size: 1.1rem;
            box-shadow: 0 0 10px rgba(34, 211, 238, 0.3);
        }
        .header-text-title {
            font-size: 1.05rem;
            font-weight: 700;
            color: #ffffff !important;
            margin: 0;
            line-height: 1.2;
        }
        .header-text-sub {
            font-size: 0.78rem;
            color: var(--accent-cyan);
            font-weight: 500;
            margin: 0;
        }

        .stButton > button {
            background: var(--bg-card) !important;
            color: var(--text-main) !important;
            border: 1px solid var(--border) !important;
            border-radius: 12px !important;
            padding: 8px 16px !important;
            font-weight: 600 !important;
            font-family: 'Noto Sans Thai', 'Inter', sans-serif !important;
            transition: all 0.2s ease-in-out !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
        }

        .stButton > button:hover {
            background: var(--bg-card-hover) !important;
            border-color: var(--border-glow) !important;
            box-shadow: 0 0 16px var(--border-glow) !important;
            transform: translateY(-2px) !important;
            color: #ffffff !important;
        }

        /* ตกแต่งปุ่มใน Sidebar ไม่ให้ตัวอักษรโดนตัด */
        [data-testid="stSidebar"] .stButton > button {
            padding: 6px 2px !important;
            font-size: 0.78rem !important;
            line-height: 1.2 !important;
            white-space: nowrap !important;
        }

        .primary-btn-wrapper > button {
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-cyan)) !important;
            border: none !important;
            color: #05070d !important;
            font-weight: 700 !important;
            box-shadow: 0 0 16px rgba(34, 211, 238, 0.4) !important;
        }
        .primary-btn-wrapper > button:hover {
            box-shadow: 0 0 24px rgba(34, 211, 238, 0.8) !important;
            color: #000000 !important;
        }

        [data-testid="stExpander"] {
            background: rgba(10, 16, 32, 0.65) !important;
            backdrop-filter: blur(14px) !important;
            -webkit-backdrop-filter: blur(14px) !important;
            border: 1px solid var(--border) !important;
            border-radius: 14px !important;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4) !important;
            margin-bottom: 12px !important;
        }
        [data-testid="stExpander"]:hover {
            border-color: var(--border-glow) !important;
            box-shadow: 0 0 16px rgba(34, 211, 238, 0.3) !important;
        }

        [data-testid="stBottom"] {
            background: linear-gradient(to top, rgba(5, 7, 13, 0.96) 60%, rgba(5, 7, 13, 0)) !important;
        }
        [data-testid="stBottom"] > div {
            background: transparent !important;
        }
        [data-testid="stBottomBlockContainer"] {
            background: transparent !important;
            max-width: none !important;
            padding: 14px var(--pad-r) var(--pad-b) var(--pad-l) !important;
        }
        [data-testid="stMainBlockContainer"], [data-testid="stMain"] .block-container, section.main .block-container {
            max-width: none !important;
            padding: 2.5rem var(--pad-r) 9rem var(--pad-l) !important;
        }

        [data-testid="stChatInput"] {
            position: relative !important;
            min-height: var(--input-h) !important;
            background: rgba(10, 16, 32, 0.92) !important;
            border: 1px solid var(--border) !important;
            border-radius: 18px !important;
            box-shadow: 0 4px 24px rgba(0, 0, 0, 0.6) !important;
            backdrop-filter: blur(12px) !important;
            -webkit-backdrop-filter: blur(12px) !important;
        }
        [data-testid="stChatInput"]:focus-within {
            border-color: var(--accent-cyan) !important;
            box-shadow: 0 0 18px rgba(34, 211, 238, 0.45) !important;
        }
        [data-testid="stChatInput"] > div,
        [data-testid="stChatInput"] [data-baseweb="textarea"],
        [data-testid="stChatInput"] [data-baseweb="base-input"] {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }
        [data-testid="stChatInput"] > div,
        [data-testid="stChatInput"] > div > div {
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            margin-top: 0 !important;
            margin-bottom: 0 !important;
        }
        [data-testid="stChatInput"] textarea::placeholder {
            color: var(--text-muted) !important;
            opacity: 1 !important;
        }
        [data-testid="stChatInput"] textarea {
            color: var(--text-main) !important;
            background: transparent !important;
            line-height: 24px !important;
            padding: 16px calc(var(--btn) * 2 + 28px) 16px calc(var(--btn) + 20px) !important;
        }
        [data-testid="stChatInput"] button {
            position: absolute !important;
            right: 8px !important;
            bottom: 8px !important;
            width: var(--btn) !important;
            height: var(--btn) !important;
            min-width: var(--btn) !important;
            border-radius: 50% !important;
            border: none !important;
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-cyan)) !important;
            color: #05070d !important;
            box-shadow: 0 0 14px rgba(34, 211, 238, 0.35) !important;
        }

        .st-key-attach_btn, .st-key-mic_btn {
            position: fixed !important;
            bottom: calc(var(--pad-b) + (var(--input-h) - var(--btn)) / 2) !important;
            width: var(--btn) !important;
            height: var(--btn) !important;
            z-index: 1000 !important;
        }
        .st-key-attach_btn {
            margin-left: 10px !important;
        }
        .st-key-mic_btn {
            right: calc(var(--pad-r) + var(--btn) + 16px) !important;
        }
        .st-key-attach_btn [data-testid="stButton"],
        .st-key-attach_btn [data-testid="stPopover"],
        .st-key-mic_btn [data-testid="stButton"] {
            width: var(--btn) !important;
        }
        .st-key-mic_btn button,
        .st-key-attach_btn button {
            width: var(--btn) !important;
            height: var(--btn) !important;
            min-height: var(--btn) !important;
            padding: 0 !important;
            border-radius: 50% !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            font-size: 1.15rem !important;
            line-height: 1 !important;
        }
        .st-key-attach_btn button,
        .st-key-mic_btn button {
            background: transparent !important;
            color: var(--text-main) !important;
            border: none !important;
            box-shadow: none !important;
            transition: all 0.2s ease-in-out !important;
        }
        .st-key-attach_btn button:hover,
        .st-key-mic_btn button:hover {
            background: rgba(47, 123, 255, 0.18) !important;
            color: var(--accent-cyan) !important;
            box-shadow: 0 0 14px rgba(34, 211, 238, 0.35) !important;
            transform: none !important;
        }
        .st-key-attach_btn button p {
            font-size: 1.7rem !important;
            font-weight: 400 !important;
            line-height: 1 !important;
            margin: 0 !important;
        }
        .st-key-attach_btn button [data-testid="stIconMaterial"],
        .st-key-attach_btn button svg {
            display: none !important;
        }
        .st-key-mic_btn button p {
            display: none !important;
        }
        .st-key-mic_btn button [data-testid="stIconMaterial"] {
            font-size: 1.5rem !important;
        }

        [data-testid="stPopoverBody"] {
            background: rgba(10, 16, 32, 0.96) !important;
            backdrop-filter: blur(14px) !important;
            -webkit-backdrop-filter: blur(14px) !important;
            border: 1px solid var(--border) !important;
            border-radius: 14px !important;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6), 0 0 18px rgba(47, 123, 255, 0.2) !important;
            min-width: min(380px, 92vw) !important;
            max-height: 70vh !important;
            overflow-y: auto !important;
        }
        [data-testid="stPopoverBody"] p,
        [data-testid="stPopoverBody"] label,
        [data-testid="stPopoverBody"] small {
            color: var(--text-main) !important;
        }
        [data-testid="stFileUploaderDropzone"] {
            background: var(--bg-card) !important;
            border: 1px dashed var(--border) !important;
            border-radius: 12px !important;
        }
        [data-testid="stFileUploaderDropzone"] button {
            background: var(--bg-card-hover) !important;
            color: var(--text-main) !important;
            border: 1px solid var(--border) !important;
            border-radius: 10px !important;
        }
        [data-testid="stFileUploaderDropzone"] small,
        [data-testid="stFileUploaderDropzone"] span {
            color: var(--text-muted) !important;
        }

        div[data-testid="stChatMessage"] {
            background-color: var(--bg-card) !important;
            border: 1px solid var(--border) !important;
            border-radius: 14px !important;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3) !important;
        }

        .stProgress > div > div > div > div {
            background: linear-gradient(90deg, var(--accent-blue), var(--accent-cyan)) !important;
            border-radius: 8px !important;
        }

        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        ::-webkit-scrollbar-track {
            background: var(--bg-main);
        }
        ::-webkit-scrollbar-thumb {
            background: #101c38;
            border-radius: 4px;
            border: 1px solid var(--border);
        }
        ::-webkit-scrollbar-thumb:hover {
            background: var(--accent-blue);
        }

        hr {
            border-color: var(--border) !important;
            margin: 16px 0 !important;
        }

        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li {
            color: var(--text-main) !important;
        }
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p,
        [data-testid="stSidebar"] [data-testid="stCheckbox"] p,
        [data-testid="stSidebar"] [data-testid="stToggle"] p,
        [data-testid="stExpander"] summary p {
            color: var(--text-main) !important;
            opacity: 1 !important;
        }

        div[role="dialog"] {
            background: var(--bg-card) !important;
            border: 1px solid var(--danger) !important;
            border-radius: 16px !important;
            box-shadow: 0 0 28px rgba(239, 68, 68, 0.35) !important;
        }
        .st-key-cf_yes button { border-color: var(--danger) !important; }
        .st-key-cf_yes button:hover {
            border-color: var(--danger) !important;
            box-shadow: 0 0 16px var(--danger) !important;
        }
    </style>
    """, unsafe_allow_html=True)
