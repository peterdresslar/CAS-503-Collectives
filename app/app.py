import streamlit as st
import streamlit.components.v1 as components
import pathlib

component_dir = pathlib.Path(__file__).parent / "canvas_component"
_component_func = components.declare_component("my_canvas", path=str(component_dir))

st.set_page_config(page_title="Boids Simulator", page_icon="bird", layout="wide")

# wrapper function to render the component
def render_canvas(params=None, command=None, key=None, height=500):
    return _component_func(
        params=params or {},
        command=command,
        key=key,
        default={},
        height=height
    )

# -------------------------
# command helpers (one-shot)
# -------------------------
def _set_command(cmd: str):
    st.session_state["boids_command"] = cmd

def start():
    _set_command("start")

def stop():
    _set_command("stop")

def reload():
    _set_command("reload")

# -------------------------
# Streamlit app
# -------------------------
st.title("Boids Simulator")

# init command state
if "boids_command" not in st.session_state:
    st.session_state["boids_command"] = None

with st.sidebar:
    # These slider values should match whatever units you want in JS.
    attractive = st.slider("Attractive Factor", 0.0, 10.0, value=2.0, step=0.1)
    alignment = st.slider("Alignment Factor", 0.0, 10.0, value=1.0, step=0.1)
    avoid = st.slider("Avoid Factor", 0.0, 10.0, value=1.0, step=0.1)
    num_boids = st.slider("Number of Boids", 10, 5000, value=100, step=50)
    visual_range = st.slider("Visual Range", 10, 200, value=75, step=5)
    tele_throttle = st.slider("Telemetry Throttle (Hz)", 0, 100, value=10, step=1)
    draw_trail = st.checkbox("Draw Trail", value=False)

    st.button("Start", on_click=start, use_container_width=True)
    st.button("Stop", on_click=stop, use_container_width=True)
    st.button("Reload", on_click=reload, use_container_width=True)

# always send params; command is one-shot
params = {
    "attractiveFactor": attractive,
    "alignmentFactor": alignment,
    "avoidFactor": avoid,
    "numBoids": num_boids,
    "visualRange": visual_range,
    "teleThrottle": tele_throttle,
    "drawTrail": draw_trail,
}

command = st.session_state["boids_command"]
telemetry = render_canvas(params=params, command=command, key="boids", height=500)

# consume the command so it doesn't repeat on next rerun
st.session_state["boids_command"] = None

with st.container(border=True):
    pass
    if telemetry:
        # instantaneous SPS from deltas (persist previous values across reruns)
        prev_step = st.session_state.get("prev_stepCount")
        prev_tms = st.session_state.get("prev_tMs")

        if prev_step is not None and prev_tms is not None:
            d_step = telemetry["stepCount"] - prev_step
            d_tms = telemetry["tMs"] - prev_tms
            if d_tms > 0 and d_step >= 0:
                sps_inst = d_step / d_tms * 1000.0
                st.write(f"SPS (inst): {sps_inst:.1f}")
            else:
                st.write("SPS (inst): n/a")
        else:
            st.write("SPS (inst): n/a (warming up)")

        st.session_state["prev_stepCount"] = telemetry["stepCount"]
        st.session_state["prev_tMs"] = telemetry["tMs"]
        st.json(telemetry)
    else:
        st.info("No telemetry yet.")