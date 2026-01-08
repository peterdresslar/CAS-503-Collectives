import streamlit as st
import streamlit.components.v1 as components
import pathlib
import base64
from typing import Any

import numpy as np

component_dir = pathlib.Path(__file__).parent / "canvas_component"
_component_func = components.declare_component("my_canvas", path=str(component_dir))

st.set_page_config(page_title="Boids Simulator", page_icon="bird", layout="wide")

# -------------------------
# telemetry decoding helpers
# -------------------------
def _decode_u16xy_base64_to_positions_px(*, data_b64: str, w: int, h: int) -> np.ndarray:
    """
    Decode boid positions from JS telemetry format "u16xy".

    JS side packs interleaved [x0,y0,x1,y1,...] into a Uint16Array,
    quantized in [0..65535] relative to the canvas drawing buffer (w,h),
    then base64 encodes the underlying bytes.
    """
    raw = base64.b64decode(data_b64)
    u16 = np.frombuffer(raw, dtype="<u2")  # browsers are little-endian in practice
    if u16.size % 2 != 0:
        raise ValueError(f"u16xy payload must have even count, got {u16.size}")
    xy_u16 = u16.reshape(-1, 2).astype(np.float32, copy=False)
    denom_x = max(1, int(w))
    denom_y = max(1, int(h))
    xy_u16[:, 0] = (xy_u16[:, 0] / 65535.0) * denom_x
    xy_u16[:, 1] = (xy_u16[:, 1] / 65535.0) * denom_y
    return xy_u16


def decode_boids_telemetry(telemetry: dict[str, Any]) -> dict[str, Any]:
    """
    Return a small, Python-friendly view of incoming telemetry.

    Adds:
      - positions_px: np.ndarray (n,2) float32 when format == "u16xy"
      - positions_norm: np.ndarray (n,2) float32 in [0,1] (approx)
    """
    fmt = telemetry.get("format")
    if fmt != "u16xy":
        return {"format": fmt, "positions_px": None, "positions_norm": None}

    data_b64 = telemetry.get("data")
    if not isinstance(data_b64, str) or not data_b64:
        return {"format": fmt, "positions_px": None, "positions_norm": None}

    w = int(telemetry.get("w", 1))
    h = int(telemetry.get("h", 1))
    positions_px = _decode_u16xy_base64_to_positions_px(data_b64=data_b64, w=w, h=h)

    # Safety: align with reported n if present (avoid downstream shape surprises).
    n_reported = telemetry.get("n")
    if isinstance(n_reported, int) and n_reported >= 0 and positions_px.shape[0] != n_reported:
        n = min(positions_px.shape[0], n_reported)
        positions_px = positions_px[:n]

    wh = np.array([max(1, w), max(1, h)], dtype=np.float32)
    positions_norm = positions_px / wh
    return {"format": fmt, "positions_px": positions_px, "positions_norm": positions_norm}


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

DEFAULT_PARAMS = {
    "attractive": 5,
    "alignment": 50,
    "avoid": 50,
    "num_boids": 100,
    "visual_range": 75,
    "tele_throttle": 10,
    "draw_trail": False,
}

def init_params():
    # When using widget keys, Streamlit expects Session State to be the
    # single source of truth for the initial/default values.
    for k, v in DEFAULT_PARAMS.items():
        st.session_state.setdefault(k, v)

def reset_params():
    for k, v in DEFAULT_PARAMS.items():
        st.session_state[k] = v

init_params()

with st.sidebar:
    # (From the js file...)
    # These slider values should match whatever units you want in JS.

    #     // strength of attractive force pulling boids toward nearby boids
    # // (default value 0.005; typical values from 0 to 0.01)
    # const attractiveFactor = 0.005;

    # // strength of alignment force
    # // (default value 0.05; typical values from 0 to 0.1)
    # const alignmentFactor = 0.05;

    # // strength of repulsive force pushing boids away from others who are too close
    # // (default value 0.05; typical values from 0 to 0.1)
    # const avoidFactor = 0.05;


    st.caption("Factors are scaled by 1000 for convenient setting.")
    attractive = st.slider("Attractive Factor (*1000)", 1, 20, step=1, key="attractive")
    alignment = st.slider("Alignment Factor (*1000)", 1, 100, step=1, key="alignment")
    avoid = st.slider("Avoid Factor (*1000)", 1, 100, step=1, key="avoid")
    num_boids = st.slider("Number of Boids", 10, 5000, step=10, key="num_boids")
    visual_range = st.slider("Visual Range", 10, 200, step=5, key="visual_range")
    tele_throttle = st.slider("Telemetry Throttle (Hz)", 0, 60, step=1, key="tele_throttle")
    draw_trail = st.checkbox("Draw Trail", key="draw_trail")
    st.button("Reset Parameters", on_click=reset_params, use_container_width=False, key="reset_params")
    st.button("Start", on_click=start, use_container_width=True, key="start")
    st.button("Stop", on_click=stop, use_container_width=True, key="stop")
    st.button("Reload", on_click=reload, use_container_width=True, key="reload")

# always send params; command is one-shot
params = {
    "attractiveFactor": attractive/1000,
    "alignmentFactor": alignment/1000,
    "avoidFactor": avoid/1000,
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

        # Decode high-volume telemetry (positions) into NumPy arrays for downstream use.
        try:
            decoded = decode_boids_telemetry(telemetry)
            st.session_state["boids_positions_px"] = decoded["positions_px"]
            st.session_state["boids_positions_norm"] = decoded["positions_norm"]
        except Exception as e:
            st.session_state["boids_positions_px"] = None
            st.session_state["boids_positions_norm"] = None
            st.warning(f"Failed to decode telemetry positions: {e}")

        # Example: quick sanity check you can build on (center of mass in pixels).
        positions_px = st.session_state.get("boids_positions_px")
        if isinstance(positions_px, np.ndarray) and positions_px.size:
            com = positions_px.mean(axis=0)
            st.write(f"Center of mass (px): x={com[0]:.1f}, y={com[1]:.1f}")

        st.json(telemetry)
    else:
        st.info("No telemetry yet.")

st.caption("This app uses boids.js code from Professor Bryan Daniels, Arizona State University.")