"""MathMate 학생용 채팅 화면 (Streamlit).

FastAPI 백엔드(/api/chat)의 SSE 스트림을 받아 튜터 답변을 타이핑되듯 보여준다.
초등학생(4~6학년) 사용자를 위해 화면엔 튜터의 말만 보여주고,
intent/diagnosis 같은 내부 처리 과정은 절대 노출하지 않는다.

디자인: 학생 말풍선은 왼쪽(하늘색), 튜터 말풍선은 오른쪽(따뜻한 노란색)으로
배치해 어린이용 학습 채팅 앱 느낌을 낸다.
"""
import html as html_lib
import os
import uuid

import httpx
import streamlit as st

BACKEND_URL = os.getenv("MATHMATE_BACKEND_URL", "http://127.0.0.1:8000")
TUTOR_AVATAR = "🧮"
STUDENT_AVATAR = "🧒"
CONGRATS_MARKERS = ["정확해요", "잘했어요"]
STUDENT_BUBBLE_COLOR = "#E3F2FD"
TUTOR_BUBBLE_COLOR = "#FFF3C4"

st.set_page_config(page_title="MathMate", page_icon="🧮", layout="centered")

st.markdown(
    """
    <style>
    html, body, [class*="css"] {
        font-size: 17px !important;
        line-height: 1.7 !important;
    }
    .stApp {
        background: linear-gradient(180deg, #FFF9EC 0%, #EAF6FF 100%);
    }
    h1 {
        color: #FF8FAB;
    }
    .stButton>button {
        border-radius: 999px;
        font-size: 17px;
        padding: 0.5em 1.2em;
        background-color: #FFD6E8;
        border: none;
    }
    .problem-card {
        background-color: #FFFFFF;
        border: 1px solid #D8ECFF;
        border-radius: 18px;
        padding: 16px 20px;
        font-size: 18px;
        margin-bottom: 16px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def fetch_problems():
    try:
        res = httpx.get(f"{BACKEND_URL}/api/problems", timeout=5)
        res.raise_for_status()
        return res.json()["items"]
    except httpx.HTTPError:
        return []


def parse_sse_lines(lines):
    """sse-starlette가 보낸 'data: <chunk>' 줄에서 원문 청크만 뽑아낸다.

    청크 자체가 공백일 수 있으므로 strip()을 쓰면 안 되고,
    'data:' 뒤에 붙는 구분용 공백 1개만 제거한다.
    """
    for line in lines:
        if not line.startswith("data:"):
            continue
        content = line[len("data:"):]
        if content.startswith(" "):
            content = content[1:]
        yield content


def render_bubble(role: str, text: str, placeholder=None):
    """학생=왼쪽/하늘색, 튜터=오른쪽/노란색 말풍선을 그린다."""
    safe_text = html_lib.escape(text).replace("\n", "<br>")
    if role == "user":
        block = f"""
        <div style="display:flex; justify-content:flex-start; align-items:flex-end; margin:14px 0;">
          <div style="font-size:26px; margin-right:8px;">{STUDENT_AVATAR}</div>
          <div style="background:{STUDENT_BUBBLE_COLOR}; border-radius:20px; padding:12px 16px;
                      max-width:75%; font-size:17px; line-height:1.7; color:#2B2B2B;">
            {safe_text}
          </div>
        </div>
        """
    else:
        block = f"""
        <div style="display:flex; justify-content:flex-end; align-items:flex-end; margin:14px 0;">
          <div style="background:{TUTOR_BUBBLE_COLOR}; border-radius:20px; padding:12px 16px;
                      max-width:75%; font-size:17px; line-height:1.7; color:#2B2B2B; text-align:left;">
            {safe_text}
          </div>
          <div style="font-size:26px; margin-left:8px;">{TUTOR_AVATAR}</div>
        </div>
        """
    (placeholder if placeholder is not None else st).markdown(block, unsafe_allow_html=True)


def stream_tutor_reply(problem_id: str, message: str, placeholder) -> str:
    payload = {"student_id": st.session_state.student_id, "problem_id": problem_id, "message": message}
    full_text = ""
    with httpx.stream("POST", f"{BACKEND_URL}/api/chat", json=payload, timeout=None) as res:
        for line in res.iter_lines():
            for chunk in parse_sse_lines([line]):
                full_text += chunk
                render_bubble("assistant", full_text, placeholder)
    return full_text


if "student_id" not in st.session_state:
    st.session_state.student_id = f"guest-{uuid.uuid4().hex[:8]}"
if "problems" not in st.session_state:
    st.session_state.problems = fetch_problems()
if "problem_id" not in st.session_state and st.session_state.problems:
    st.session_state.problem_id = st.session_state.problems[0]["id"]
if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("🧮 MathMate")
st.caption("선생님이랑 같이 수학 문제를 풀어볼까요? 😊")

if not st.session_state.problems:
    st.error("앗, 서버랑 연결이 안 돼요. 선생님을 불러주세요! (백엔드 서버가 켜져 있는지 확인해주세요)")
    st.stop()

labels = {p["id"]: f'{p["problem"][:20]}...' if len(p["problem"]) > 20 else p["problem"]
          for p in st.session_state.problems}


def on_problem_change():
    st.session_state.messages = []


st.selectbox(
    "어떤 문제를 풀어볼까요?",
    options=list(labels.keys()),
    format_func=lambda pid: labels[pid],
    key="problem_id",
    on_change=on_problem_change,
)

current_problem = next(p for p in st.session_state.problems if p["id"] == st.session_state.problem_id)
st.markdown(f'<div class="problem-card">📝 {current_problem["problem"]}</div>', unsafe_allow_html=True)

if st.button("🔄 새 문제 보기"):
    ids = list(labels.keys())
    idx = ids.index(st.session_state.problem_id)
    st.session_state.problem_id = ids[(idx + 1) % len(ids)]
    st.session_state.messages = []
    st.rerun()

for msg in st.session_state.messages:
    render_bubble(msg["role"], msg["content"])

user_message = st.chat_input("여기에 답을 써 볼까? ✏️")

if user_message:
    st.session_state.messages.append({"role": "user", "content": user_message})
    render_bubble("user", user_message)

    placeholder = st.empty()
    reply = stream_tutor_reply(st.session_state.problem_id, user_message, placeholder)
    st.session_state.messages.append({"role": "assistant", "content": reply})

    if any(marker in reply for marker in CONGRATS_MARKERS):
        st.balloons()
        st.success("🎉 정답이에요! 참 잘했어요! 🎉")
