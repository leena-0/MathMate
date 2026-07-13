"""MathMate 학생용 채팅 화면 (Streamlit).

FastAPI 백엔드(/api/chat)의 SSE 스트림을 받아 튜터 답변을 타이핑되듯 보여준다.
초등학생(4~6학년) 사용자를 위해 화면엔 튜터의 말만 보여주고,
intent/diagnosis 같은 내부 처리 과정은 절대 노출하지 않는다.

- 학생 말풍선은 왼쪽(하늘색), 튜터 말풍선은 오른쪽(따뜻한 노란색)으로 배치.
- 처음 접속하면 이름+학년으로 간단한 프로필(비밀번호 없음)을 만들고,
  사이드바에서 "학습"/"피드백" 화면을 오갈 수 있다.
"""
import html as html_lib
import os

import httpx
import streamlit as st

BACKEND_URL = os.getenv("MATHMATE_BACKEND_URL", "http://127.0.0.1:8000")
TUTOR_AVATAR = "🧮"
STUDENT_AVATAR = "🧒"
CONGRATS_MARKERS = ["정확해요", "잘했어요"]
STUDENT_BUBBLE_COLOR = "#E3F2FD"
TUTOR_BUBBLE_COLOR = "#FFF3C4"
MASTERY_COLOR = {"취약": "#EF6B6B", "보통": "#F0A93E", "잘함": "#3FB27F"}

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
    .mastery-card {
        background-color: #FFFFFF;
        border: 1px solid #EEE;
        border-radius: 18px;
        padding: 16px 20px;
        margin-bottom: 14px;
    }
    .mastery-bar-track {
        background-color: #F0F0F0;
        border-radius: 999px;
        height: 10px;
        margin: 10px 0 8px 0;
    }
    .mastery-bar-fill {
        border-radius: 999px;
        height: 10px;
    }
    .mastery-tag {
        border-radius: 999px;
        padding: 4px 14px;
        font-size: 14px;
        font-weight: 700;
    }
    .recommend-banner {
        background-color: #DCEBFF;
        border-radius: 18px;
        padding: 18px 22px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def create_or_get_profile(name: str, grade: int, semester: int, password: str, create_new: bool = False):
    """성공하면 프로필 dict, 이름은 있는데 비번이 다르면 'name_conflict', 연결 실패면 None."""
    try:
        res = httpx.post(f"{BACKEND_URL}/api/profile",
                          json={"name": name, "grade": grade, "semester": semester,
                                "password": password, "create_new": create_new},
                          timeout=5)
        if res.status_code == 409:
            return "name_conflict"
        res.raise_for_status()
        return res.json()
    except httpx.HTTPError:
        return None


def fetch_semesters(grade: int) -> list[int]:
    try:
        res = httpx.get(f"{BACKEND_URL}/api/problems/semesters", params={"grade": grade}, timeout=5)
        res.raise_for_status()
        return res.json()["semesters"]
    except httpx.HTTPError:
        return []


def fetch_units(grade: int, semester: int) -> list[str]:
    try:
        res = httpx.get(f"{BACKEND_URL}/api/problems/units", params={"grade": grade, "semester": semester},
                         timeout=5)
        res.raise_for_status()
        return res.json()["units"]
    except httpx.HTTPError:
        return []


def fetch_problems(grade: int, semester: int, unit: str | None, difficulty: str | None) -> list[dict]:
    params = {"grade": grade, "semester": semester}
    if unit:
        params["unit"] = unit
    if difficulty:
        params["difficulty"] = difficulty
    try:
        res = httpx.get(f"{BACKEND_URL}/api/problems", params=params, timeout=5)
        res.raise_for_status()
        return res.json()["items"]
    except httpx.HTTPError:
        return []


def fetch_feedback(user_id: int) -> dict | None:
    try:
        res = httpx.get(f"{BACKEND_URL}/api/feedback", params={"user_id": user_id}, timeout=5)
        res.raise_for_status()
        return res.json()
    except httpx.HTTPError:
        return None


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


def stream_tutor_reply(user_id: int, problem_id: str, message: str, placeholder) -> str:
    payload = {"student_id": str(user_id), "problem_id": problem_id, "message": message}
    full_text = ""
    with httpx.stream("POST", f"{BACKEND_URL}/api/chat", json=payload, timeout=None) as res:
        for line in res.iter_lines():
            for chunk in parse_sse_lines([line]):
                full_text += chunk
                render_bubble("assistant", full_text, placeholder)
    return full_text


def mastery_bar_width(avg_hints_used: float) -> int:
    """힌트를 적게 쓸수록 막대가 길어지는 0~100 점수(시각화용)."""
    score = 100 / (1 + avg_hints_used)
    return max(5, min(100, round(score)))


# ---------- 프로필(로그인 대체) ----------

if "user" not in st.session_state:
    st.title("🧮 MathMate")
    st.caption("먼저 이름, 학년, 비밀번호를 알려줄래? 😊")
    st.caption("비밀번호는 나중에 다시 들어올 때 '나'인지 확인하는 용도야. 아무거나 정해도 괜찮아!")

    if "pending_profile" not in st.session_state:
        with st.form("profile_form"):
            name = st.text_input("이름이 뭐야?")
            grade = st.selectbox("몇 학년이야?", [4, 5, 6])
            semester = st.selectbox("몇 학기야?", [1, 2])
            password = st.text_input("비밀번호(암호)를 정해줄래?", type="password")
            submitted = st.form_submit_button("시작하기 ✏️")
        if submitted:
            if not name.strip():
                st.warning("이름을 입력해줄래?")
            elif not password:
                st.warning("비밀번호도 정해줄래?")
            else:
                profile = create_or_get_profile(name.strip(), grade, semester, password)
                if profile is None:
                    st.error("앗, 서버랑 연결이 안 돼요. 선생님을 불러주세요!")
                elif profile == "name_conflict":
                    st.session_state.pending_profile = {
                        "name": name.strip(), "grade": grade, "semester": semester, "password": password,
                    }
                    st.rerun()
                else:
                    st.session_state.user = profile
                    st.rerun()
    else:
        pending = st.session_state.pending_profile
        st.warning(f"'{pending['name']}'(이)라는 이름이 이미 있는데, 비밀번호가 달라요.")
        st.caption("혹시 비밀번호를 잘못 눌렀니, 아니면 다른 친구니?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔁 비밀번호 다시 확인할래요"):
                del st.session_state.pending_profile
                st.rerun()
        with col2:
            if st.button("🙋 저는 다른 친구예요"):
                profile = create_or_get_profile(pending["name"], pending["grade"], pending["semester"],
                                                 pending["password"], create_new=True)
                del st.session_state.pending_profile
                if isinstance(profile, dict):
                    st.session_state.user = profile
                    st.rerun()
                else:
                    st.error("앗, 서버랑 연결이 안 돼요. 선생님을 불러주세요!")
    st.stop()

user = st.session_state.user

# ---------- 사이드바 네비게이션 ----------

st.sidebar.markdown(f"### 🧮 MathMate\n**{user['name']}** ({user['grade']}학년 {user['semester']}학기)")
page = st.sidebar.radio("메뉴", ["💬 학습", "📊 피드백"], label_visibility="collapsed")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "selected_grade" not in st.session_state:
    st.session_state.selected_grade = user["grade"]
if "selected_semester" not in st.session_state:
    st.session_state.selected_semester = user["semester"]


# ---------- 학습 화면 ----------

def render_study_page():
    st.title("🧮 MathMate")
    st.caption("선생님이랑 같이 수학 문제를 풀어볼까요? 😊")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        grade = st.selectbox("학년", [4, 5, 6], key="selected_grade")

    semesters = fetch_semesters(grade) or [1, 2]
    if st.session_state.selected_semester not in semesters:
        st.session_state.selected_semester = semesters[0]
    with col2:
        semester = st.selectbox("학기", semesters, key="selected_semester")

    units = fetch_units(grade, semester)
    if not units:
        st.info("이 학년·학기엔 아직 문제가 없어요. 다른 학년이나 학기를 골라볼까요?")
        st.stop()
    with col3:
        default_unit = st.session_state.get("preselect_unit")
        unit_options = units
        unit_index = unit_options.index(default_unit) if default_unit in unit_options else 0
        unit = st.selectbox("단원", unit_options, index=unit_index)
    with col4:
        difficulty = st.selectbox("난이도", ["쉬움", "중간", "어려움"], index=0)

    problems = fetch_problems(grade, semester, unit, difficulty)
    if not problems:
        st.info("이 조건에 맞는 문제가 아직 없어요. 다른 난이도나 단원을 골라볼까요?")
        st.stop()

    labels = {p["id"]: f'{p["problem"][:24]}...' if len(p["problem"]) > 24 else p["problem"] for p in problems}

    problem_id = st.selectbox(
        "어떤 문제를 풀어볼까요?",
        options=list(labels.keys()),
        format_func=lambda pid: labels[pid],
        key="problem_id",
    )

    # 문제가 바뀐 이유(직접 선택/학년·학기·단원 변경/새 문제 보기 버튼)에 상관없이,
    # 이전에 보여준 문제와 달라졌으면 채팅 기록을 초기화한다.
    if st.session_state.get("_last_problem_id") != problem_id:
        st.session_state.messages = []
        st.session_state._last_problem_id = problem_id

    current_problem = next(p for p in problems if p["id"] == problem_id)
    st.markdown(f'<div class="problem-card">📝 {current_problem["problem"]}</div>', unsafe_allow_html=True)

    def _go_to_next_problem(ids):
        idx = ids.index(st.session_state.problem_id)
        st.session_state.problem_id = ids[(idx + 1) % len(ids)]

    st.button("🔄 새 문제 보기", on_click=_go_to_next_problem, args=(list(labels.keys()),))

    for msg in st.session_state.messages:
        render_bubble(msg["role"], msg["content"])

    user_message = st.chat_input("여기에 답을 써 볼까? ✏️")

    if user_message:
        st.session_state.messages.append({"role": "user", "content": user_message})
        render_bubble("user", user_message)

        placeholder = st.empty()
        reply = stream_tutor_reply(user["user_id"], problem_id, user_message, placeholder)
        st.session_state.messages.append({"role": "assistant", "content": reply})

        if any(marker in reply for marker in CONGRATS_MARKERS):
            st.balloons()
            st.success("🎉 정답이에요! 참 잘했어요! 🎉")


# ---------- 피드백 화면 ----------

def render_feedback_page():
    st.title("📊 단원별 학습 리포트")
    st.caption("힌트를 적게 쓰고 스스로 풀수록 숙련도가 높아요")

    feedback = fetch_feedback(user["user_id"])
    if feedback is None:
        st.error("앗, 서버랑 연결이 안 돼요. 선생님을 불러주세요!")
        st.stop()

    items = feedback["items"]
    if not items:
        st.info("아직 푼 문제가 없어요. 학습 화면에서 문제를 풀어보면 여기에 리포트가 쌓여요!")
        return

    for item in items:
        color = MASTERY_COLOR.get(item["mastery_level"], "#999")
        width = mastery_bar_width(item["avg_hints_used"])
        st.markdown(
            f"""
            <div class="mastery-card">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <div style="font-size:20px; font-weight:700;">{html_lib.escape(item['unit'])}</div>
                <div class="mastery-tag" style="background:{color}22; color:{color};">
                  {item['mastery_level']}
                </div>
              </div>
              <div class="mastery-bar-track">
                <div class="mastery-bar-fill" style="width:{width}%; background:{color};"></div>
              </div>
              <div style="color:#888; font-size:15px;">
                평균 힌트 {item['avg_hints_used']}개 · {item['problems_attempted']}문제
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    weakest = feedback.get("weakest_unit")
    if weakest:
        st.markdown(
            f"""
            <div class="recommend-banner">
              <div style="font-size:18px; color:#1B4E8F; font-weight:600;">
                {html_lib.escape(weakest)}가 가장 약해요.<br>이 단원 문제를 더 풀어볼까요?
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(f"📝 {weakest} 문제 풀기 →"):
            st.session_state.preselect_unit = weakest
            st.info("왼쪽 사이드바에서 '💬 학습'을 눌러 문제를 풀어보세요!")


if page == "💬 학습":
    render_study_page()
else:
    render_feedback_page()
