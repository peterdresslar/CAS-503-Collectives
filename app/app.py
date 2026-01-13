import streamlit as st
import streamlit.components.v1 as components
import pathlib
import base64
from typing import Any
import html

from sklearn.cluster import DBSCAN

import numpy as np

component_dir = pathlib.Path(__file__).parent / "canvas_component"
_component_func = components.declare_component("my_canvas", path=str(component_dir))

# For cluster analysis,min samples is arbitrarily set based on the model, thus a constant in this context
MIN_SAMPLES = 3 # could defensibly choose 3 or 4 for 2D data, but i like 3 better. this is a fun thing to explore in the future though.

st.set_page_config(page_title="Boids Simulator", page_icon="🐦", layout="wide")

# Small UI helper styling (keeps “report/warning” content compact and horizontal).
st.markdown(
    """
<style>
.boids-report-box {
  border: 1px solid rgba(49, 51, 63, 0.2);
  border-radius: 0.5rem;
  padding: 0.75rem 0.9rem;
  background: rgba(49, 51, 63, 0.02);
}
.boids-report-box.warning {
  border-color: #d32f2f;
  background: #fff5f5;
}
.boids-report-warning-title {
  color: #d32f2f;
  font-weight: 700;
  margin-bottom: 0.35rem;
}
.boids-report-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.9rem;
}
.boids-report-item {
  white-space: nowrap;
}
</style>
""",
    unsafe_allow_html=True,
)

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

    Args:
        telemetry: dict[str, Any] - telemetry from JS. We expect for this to contain the data b64 string we have sent from the JS side. The reason
        we need to decode data is that we have packed it up as u16xy to conserve bandwidth.

    Returns:
        dict[str, Any] - a dictionary with the format, positions_px, and positions_norm.
        
    Keys (of the returned dictionary):
        positions_px is a numpy array of shape (n,2) float32, where n is the number of boids and the columns are the x and y coordinates.
        positions_norm is a numpy array of shape (n,2) float32, where n is the number of boids and the columns are the x and y coordinates in the range [0,1].
        format is also returned to confirm that the telemetry from JS is indeed in the u16xy format.
    """
    fmt = telemetry.get("format")
    if fmt != "u16xy":  # confirm that telemetry from JS is indeed in the u16xy format
        return {"format": fmt, "positions_px": None, "positions_norm": None}  # if not, return None[s]

    data_b64 = telemetry.get("data")  # the data b64 string we have sent from the JS side
    if not isinstance(data_b64, str) or not data_b64:  # bail if bad data. maybe we should just exception out, though
        return {"format": fmt, "positions_px": None, "positions_norm": None}

    w = int(telemetry.get("w", 1)) # width for position alignment in decoding, if this is wrong the decoding will be wrong.
    h = int(telemetry.get("h", 1)) # height for position alignment in decoding
    positions_px = _decode_u16xy_base64_to_positions_px(data_b64=data_b64, w=w, h=h)  # actually decode

    # Data integrity check: the JS sends n and we should decode exactly n points.
    # If we ever disagree, something upstream is corrupted/truncated and we should NOT silently trim.
    n_reported = telemetry.get("n")   # number of boids reported by JS.
    if isinstance(n_reported, int) and n_reported >= 0 and positions_px.shape[0] != n_reported:
        # Strong diagnostic: decoded byte length should be 4*n (2 uint16 values per boid).
        raw_len = None
        expected_len = 4 * n_reported
        try:
            raw_len = len(base64.b64decode(data_b64))
        except Exception:
            pass

        warning = (
            "Telemetry integrity warning: decoded positions length does not match JS-reported n. "
            f"reported n={n_reported}, decoded n={positions_px.shape[0]}, "
            f"decoded_bytes={raw_len}, expected_bytes={expected_len}, w={w}, h={h}"
        )
        return {"format": fmt, "positions_px": None, "positions_norm": None, "warning": warning}

    wh = np.array([max(1, w), max(1, h)], dtype=np.float32)
    positions_norm = positions_px / wh
    return {"format": fmt, "positions_px": positions_px, "positions_norm": positions_norm}

def calculate_eps(n, _x, _y):
    # we will be sending in normalized positions, so we need to use a relatively small eps to catch small clusters
    # this was kind of a nightmare to troubleshoot, the absolute killer being that
    # x and y are correct in the formula, but we are using *normalized* positions. x and y both equal 1!
    # i have intentially masked the inputs for that reason.
    x = 1
    y = 1
    eps = np.sqrt(x*y*MIN_SAMPLES / (np.pi*n)) # Diggle, 2013, complete spatial randomness. TODO this was a google-ai-search, should verify
    return eps

# cluster measurements using DBSCAN
def analyze_clusters(positions, calculated_eps):
    # we will be sending in normalized positions, so we need to use a relatively small eps to catch small clusters

    db = DBSCAN(eps=calculated_eps, min_samples=MIN_SAMPLES, metric="euclidean").fit(
        positions
    )
    labels = db.labels_

    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = list(labels).count(-1)

    return n_clusters, n_noise


def getShoalPhase(telemetry):
    # We thus define that the school is in: 
    # the polar state (P) when Op>0.65 and Or<0.35; 
    # the milling state (M) when Op<0.35 and Or>0.65...
    # otherwise the school is in the swarm state (S)
    Op = telemetry["polarization"]
    Or = telemetry["rotationOrder"]
    if Op > 0.65 and Or < 0.35:
        return "polar"
    elif Op < 0.35 and Or > 0.65:
        return "milling"
    else:
        return "swarm"


def reset_params():
    for k, v in DEFAULT_PARAMS.items():
        st.session_state[k] = v # force

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
# command helpers
#
# Streamlit is kind of weird. Buttons set session state, and that state is then passed along to the component
# on the next render (which is triggered by just about anything happening.)
#
# Since we have a custom streamlitcomponent we need to pass along the boids command state to run the javascript code from the HTML component shell.
#
# We also have our "button commands" which have been hardwired into the shell to signal the javascript as needed.
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
st.markdown("**Boids Simulator**")

# init command state
if "boids_command" not in st.session_state:
    st.session_state["boids_command"] = None

DEFAULT_PARAMS = {
    "attractive": 5,
    "alignment": 5,
    "avoid": 5,
    "num_boids": 500,
    "visual_range": 75,
    "tele_throttle": 2,
    "draw_trail": False,
}

def init_params():
    # When using widget keys, Streamlit expects Session State to be the
    # single source of truth for the initial/default values.
    for k, v in DEFAULT_PARAMS.items():
        st.session_state.setdefault(k, v)

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


    st.caption("Factors are scaled for convenient setting.")
    attractive = st.slider("Attractive Factor (*1000)", 0, 100, step=1, key="attractive")
    alignment = st.slider("Alignment Factor (*100)", 0, 100, step=10, key="alignment")
    avoid = st.slider("Avoid Factor (*100)", 0, 100, step=10, key="avoid")
    num_boids = st.slider("Number of Boids", 1, 5000, step=50, key="num_boids")
    visual_range = st.slider("Visual Range", 10, 200, step=5, key="visual_range")
    tele_throttle = st.slider("Telemetry Throttle (Hz)", 0, 10, step=1, key="tele_throttle")
    draw_trail = st.checkbox("Draw Trail", key="draw_trail")
    st.button("Reset Parameters", on_click=reset_params, use_container_width=False, key="reset_params")
    st.button("Start", on_click=start, use_container_width=True, key="start")
    st.button("Stop", on_click=stop, use_container_width=True, key="stop")
    st.button("Reload", on_click=reload, use_container_width=True, key="reload")

params = {
    # Don't forget to scale the Factors!
    "attractiveFactor": attractive/1000,
    "alignmentFactor": alignment/100,  # so nasty, this could be handled way better
    "avoidFactor": avoid/100,
    "numBoids": num_boids,
    "visualRange": visual_range,
    "teleThrottle": tele_throttle,
    "drawTrail": draw_trail,
}

command = st.session_state["boids_command"]

# Here is the custom (Boids) component call.
# Params are passed along as you might expect, along with a height param that I need to double-check
#
# The way that streamlit componenets work is that they automatically return a state object, into which we can write telemetry (see basically the rest of the app.)
telemetry = render_canvas(params=params, command=command, key="boids", height=500)

# consume the command so it doesn't repeat on next rerun. We don't want to call the main command over and over
st.session_state["boids_command"] = None


with st.container(border=True):
    if telemetry:
        calculated_eps = calculate_eps(telemetry["n"], telemetry["w"], telemetry["h"])
        degrees_vector = np.degrees(np.arctan2(telemetry["vector"]["dy"], telemetry["vector"]["dx"]))
        degrees_vector_text = f"Mean Vector: {degrees_vector:.1f} degrees"
        polarization = telemetry["polarization"]
        polarization_text = f"Polarization (normalized): {polarization:.2f}"
        rotationOrder = telemetry["rotationOrder"]
        rotationOrder_text = f"Rotation (normalized): {rotationOrder:.2f}"
        report_items: list[str] = []
        warning_text: str | None = None

        # instantaneous SPS from deltas (persist previous values across reruns)
        prev_step = st.session_state.get("prev_stepCount")
        prev_tms = st.session_state.get("prev_tMs")
        sps_text = "SPS (inst): n/a (warming up)"

        if prev_step is not None and prev_tms is not None:
            phase = getShoalPhase(telemetry)
            # phase text: green if polar, blue if milling, yellow if swarm
            phase_color = "green" if phase == "polar" else "blue" if phase == "milling" else "yellow"
            phase_text = f"<span style='color: {phase_color};'>{html.escape(phase.capitalize())}</span>"
            report_items.append(f"<span class='boids-report-item'>{phase_text}</span>")
            d_step = telemetry["stepCount"] - prev_step
            d_tms = telemetry["tMs"] - prev_tms
            velocity = telemetry["velocity"]
            vector = telemetry["vector"]
            velocity_text = f"Mean Velocity (inst): {velocity:.1f}"
            report_items.append(f"<span class='boids-report-item'>{html.escape(velocity_text)}</span>")
            report_items.append(f"<span class='boids-report-item'>{html.escape(degrees_vector_text)}</span>")
            report_items.append(f"<span class='boids-report-item'>{html.escape(polarization_text)}</span>")
            report_items.append(f"<span class='boids-report-item'>{html.escape(rotationOrder_text)}</span>")
            if d_tms > 0 and d_step >= 0:
                sps_inst = d_step / d_tms * 1000.0
                sps_text = f"SPS (inst): {sps_inst:.1f}"
   
            else:
                sps_text = "SPS (inst): n/a"

        report_items.append(f"<span class='boids-report-item'><b>{html.escape(sps_text)}</b></span>")

        st.session_state["prev_stepCount"] = telemetry["stepCount"]
        st.session_state["prev_tMs"] = telemetry["tMs"]

        # Decode high-volume telemetry (positions) into NumPy arrays for downstream use.
        try:
            decoded = decode_boids_telemetry(telemetry)
            warning_text = decoded.get("warning")

            st.session_state["boids_positions_px"] = decoded["positions_px"]
            st.session_state["boids_positions_norm"] = decoded["positions_norm"]
        except Exception as e:
            st.session_state["boids_positions_px"] = None
            st.session_state["boids_positions_norm"] = None
            warning_text = f"Failed to decode telemetry positions: {e}"

        positions_px = st.session_state.get("boids_positions_px")
        positions_norm = st.session_state.get("boids_positions_norm")
        if isinstance(positions_px, np.ndarray) and positions_px.size:
            com = positions_px.mean(axis=0)
            com_text = f"Center of mass (px): x={com[0]:.1f}, y={com[1]:.1f}"
            report_items.append(f"<span class='boids-report-item'>{html.escape(com_text)}</span>")
        if isinstance(positions_norm, np.ndarray) and positions_norm.size:
            n_clusters, n_noise = analyze_clusters(positions_norm, calculated_eps) # normalized positions
            cluster_text = f"Clusters: {n_clusters}, Noise: {n_noise} Eps: {calculated_eps:.2f}"
            report_items.append(f"<span class='boids-report-item'>{html.escape(cluster_text)}</span>")
        else:
            report_items.append("<span class='boids-report-item'>Center of mass (px): n/a</span>")
            report_items.append("<span class='boids-report-item'>Clusters: n/a</span>")
            report_items.append("<span class='boids-report-item'>Noise: n/a</span>")
            report_items.append("<span class='boids-report-item'>Eps: n/a</span>")

        # Compact “report box”: always shows derived stats; turns red and prepends warning when needed.
        warning_html = ""
        klass = "boids-report-box"
        if warning_text:
            klass += " warning"
            warning_html = (
                "<div class='boids-report-warning-title'>"
                f"WARNING: {html.escape(warning_text)}"
                "</div>"
            )

        items_html = "".join(report_items) if report_items else ""
        st.markdown(
            f"<div class='{klass}'>{warning_html}<div class='boids-report-row'>{items_html}</div></div>",
            unsafe_allow_html=True,
        )

        st.json(telemetry, expanded=False)
    else:
        st.info("No telemetry yet.")

st.caption("This app uses boids.js code from Ben Eater, as adapted/shared by Professor Bryan Daniels, Arizona State University.")
st.caption("Shoaling characteristics were adapted from \"Collective States, Multistability and Transitional Behavior in Schooling Fish\", Tunstrøm et al., 2013, PLOS Computational Biology.")
st.caption("Version v0.1.0. Peter Dresslar.")
