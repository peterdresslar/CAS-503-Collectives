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
    st.header("Sim controls")

    # These slider values should match whatever units you want in JS.
    attractive = st.slider("Attractive Factor", 0.0, 10.0, 2.0)
    alignment = st.slider("Alignment Factor", 0.0, 10.0, 1.0)
    avoid = st.slider("Avoid Factor", 0.0, 10.0, 1.0)
    num_boids = st.slider("Number of Boids", 10, 500, 100)
    visual_range = st.slider("Visual Range", 10, 200, 75)
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
    "drawTrail": draw_trail,
}

command = st.session_state["boids_command"]
telemetry = render_canvas(params=params, command=command, key="boids", height=500)

# consume the command so it doesn't repeat on next rerun
st.session_state["boids_command"] = None

with st.container(border=True):
    st.header("Telemetry (JS → Python)")
    if telemetry:
        st.json(telemetry)
    else:
        st.info("No telemetry yet.")