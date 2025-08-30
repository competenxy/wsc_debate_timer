
import time, base64
import streamlit as st
import plotly.graph_objects as go
import streamlit.components.v1 as components

st.set_page_config(page_title="RKR WSC Debate Timer", page_icon="⏱️", layout="wide")

st.markdown(
    """
    <style>
    .stage {font-size: 26px; font-weight: 700; text-align:center; margin-top: -6px;}
    .clock {font-size: 96px; font-weight: 900; text-align:center; margin-top: -18px;}
    .muted {opacity: .75; font-size: 16px; text-align:center;}
    .toolbar .stButton>button {width: 100%; font-weight:700; padding: 10px 0; border-radius: 14px;}
    .toolbar .stSelectbox>div>div {font-weight:700;}
    </style>
    """,
    unsafe_allow_html=True
)

st.title("⏱️ RKR WSC Debate Timer")

def load_bytes(path):
    with open(path, "rb") as f:
        return f.read()

BELL_BYTES = load_bytes("bell.wav")
KNOCK1_BYTES = load_bytes("knock1.wav")
KNOCK2_BYTES = load_bytes("knock2.wav")

def play_audio_bytes(audio_bytes: bytes, volume: float = 1.0, key: str = "audio"):
    b64 = base64.b64encode(audio_bytes).decode("utf-8")
    uid = f"{key}_{int(time.time()*1000)}"
    html = f"""
    <audio id="{uid}" autoplay>
      <source src="data:audio/wav;base64,{b64}" type="audio/wav">
    </audio>
    <script>
    const el = document.getElementById("{uid}");
    if (el) {{
      el.volume = {max(0.0, min(volume, 1.0))};
      const p = el.play();
      if (p) p.catch(_=>{{}});
    }}
    </script>
    """
    components.html(html, height=0, width=0)

def build_sequence():
    seq = []
    seq.append(dict(name="Prep – Both Teams", secs=15*60, kind="prep"))
    for i in range(1,7):
        seq.append(dict(name=f"Speaker {i}", secs=4*60, kind="speaker"))
        if i < 6:
            seq.append(dict(name=f"Prep Gap before Speaker {i+1}", secs=60, kind="gap"))
    seq.append(dict(name="Team Feedback – Negative first", secs=90, kind="teamfb"))
    seq.append(dict(name="Team Feedback – Affirmative", secs=90, kind="teamfb"))
    seq.append(dict(name="Peer Feedback – Negative", secs=90, kind="peerfb"))
    seq.append(dict(name="Peer Feedback – Affirmative", secs=90, kind="peerfb"))
    return seq

SEQUENCE = build_sequence()

ss = st.session_state
ss.setdefault("stage_idx", 0)
ss.setdefault("remaining", SEQUENCE[0]["secs"])
ss.setdefault("running", False)
ss.setdefault("last_tick", None)
ss.setdefault("played3", False)
ss.setdefault("played4", False)
ss.setdefault("knock_vol", 0.9)
ss.setdefault("bell_vol", 0.9)

def reset_knocks():
    ss.played3 = False
    ss.played4 = False

def start_stage(idx=None):
    if idx is not None:
        ss.stage_idx = idx
        ss.remaining = SEQUENCE[idx]["secs"]
        reset_knocks()
    ss.running = True
    ss.last_tick = time.time()

def pause_stage():
    if ss.running and ss.last_tick:
        delta = time.time() - ss.last_tick
        ss.remaining = max(0.0, ss.remaining - delta)
    ss.running = False
    ss.last_tick = None

def stop_and_reset():
    ss.running = False
    ss.remaining = SEQUENCE[ss.stage_idx]["secs"]
    ss.last_tick = None
    reset_knocks()

def next_stage():
    pause_stage()
    ss.stage_idx = min(len(SEQUENCE)-1, ss.stage_idx + 1)
    ss.remaining = SEQUENCE[ss.stage_idx]["secs"]
    reset_knocks()

def prev_stage():
    pause_stage()
    ss.stage_idx = max(0, ss.stage_idx - 1)
    ss.remaining = SEQUENCE[ss.stage_idx]["secs"]
    reset_knocks()

def tick():
    if not ss.running:
        return
    now = time.time()
    if ss.last_tick is None:
        ss.last_tick = now
        return
    delta = now - ss.last_tick
    ss.last_tick = now
    ss.remaining = max(0.0, ss.remaining - delta)

def donut(remaining, total):
    fig = go.Figure(go.Pie(
        values=[max(remaining, 0.0001), max(total-remaining, 0.0001)],
        hole=0.82, sort=False, direction="clockwise",
        textinfo="none", marker=dict(line=dict(width=0))
    ))
    fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=10, b=10), height=460)
    return fig

col_main, col_ctl = st.columns([2,1], gap="large")

with col_ctl:
    st.subheader("Moderator Controls")
    st.caption("Timer always waits for moderator to Start/Resume.")
    st.markdown('<div class="toolbar">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("⏯ Start / Resume"):
            start_stage()
    with c2:
        if st.button("⏸ Pause"):
            pause_stage()
    with c3:
        if st.button("⏹ Reset Stage"):
            stop_and_reset()

    c4, c5 = st.columns(2)
    with c4:
        if st.button("⏮ Prev"):
            prev_stage()
    with c5:
        if st.button("⏭ Next"):
            next_stage()

    stage_names = [f"{i+1:02d}. {s['name']}" for i, s in enumerate(SEQUENCE)]
    target = st.selectbox("Jump to stage", options=list(range(len(SEQUENCE))), index=ss.stage_idx, format_func=lambda i: stage_names[i])
    if st.button("➡️ Jump"):
        start_stage(idx=target)

    cur = SEQUENCE[ss.stage_idx]
    if cur["kind"] == "speaker":
        if st.button("↦ Jump to 3:00 (one knock)"):
            ss.remaining = 60.0
            if not ss.played3:
                play_audio_bytes(KNOCK1_BYTES, ss.knock_vol, key="knock1jump")
                ss.played3 = True

    st.divider()
    st.markdown("**Sound Check & Volume**")
    ss.knock_vol = st.slider("Knock Volume", 0.0, 1.0, ss.knock_vol, 0.05)
    ss.bell_vol = st.slider("Bell Volume", 0.0, 1.0, ss.bell_vol, 0.05)
    t1, t2, t3 = st.columns([1,1,1])
    with t1:
        if st.button("🔊 Test KNOCK (1x)"):
            play_audio_bytes(KNOCK1_BYTES, ss.knock_vol, key="knock1btn")
    with t2:
        if st.button("🔊 Test KNOCK (2x)"):
            play_audio_bytes(KNOCK2_BYTES, ss.knock_vol, key="knock2btn")
    with t3:
        if st.button("🔔 Test BELL"):
            play_audio_bytes(BELL_BYTES, ss.bell_vol, key="bellbtn")

    st.divider()
    st.write("**Stage Order**")
    st.write("- 1) Prep 15:00")
    st.write("- 2) Speakers 1–6 (each 4:00), with 1:00 prep gaps after Speakers 1–5")
    st.write("- 3) Team Feedback: 90s each (Neg → Aff)")
    st.write("- 4) Peer Feedback: 90s each (Neg → Aff)")
    st.caption("You can jump to any stage at any time.")

with col_main:
    tick()
    stage = SEQUENCE[ss.stage_idx]
    total = stage["secs"]
    remaining = ss.remaining

    if stage["kind"] == "speaker" and total == 240:
        elapsed = total - remaining
        if elapsed >= 180 and not ss.played3:
            play_audio_bytes(KNOCK1_BYTES, ss.knock_vol, key="knock1auto"); ss.played3 = True
        if elapsed >= 240 and not ss.played4:
            play_audio_bytes(KNOCK2_BYTES, ss.knock_vol, key="knock2auto"); ss.played4 = True

    # End-of-stage handling
    if remaining <= 0.01 and ss.running:
        # Do NOT play the bell for speaker rounds (two knocks are the cue)
        if stage["kind"] != "speaker":
            play_audio_bytes(BELL_BYTES, ss.bell_vol, key="bellauto")
        ss.running = False
        ss.last_tick = None
        remaining = 0.0

    st.markdown(f"<div class='stage'>{ss.stage_idx+1:02d} / {len(SEQUENCE)} — {stage['name']}</div>", unsafe_allow_html=True)
    st.plotly_chart(donut(remaining, total), use_container_width=True)
    m, s = divmod(int(remaining), 60)
    st.markdown(f"<div class='clock'>{m:02d}:{s:02d}</div>", unsafe_allow_html=True)
    if ss.running:
        st.markdown("<div class='muted'>Running… (Pause / Next anytime)</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='muted'>Paused — Waiting for moderator to press Start/Resume</div>", unsafe_allow_html=True)

    if ss.running:
        time.sleep(0.5)
        st.rerun()
