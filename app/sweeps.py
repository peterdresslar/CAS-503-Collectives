import streamlit as st
import streamlit.components.v1 as components  # for the custom sweep component

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import pathlib

sweep_component_dir = pathlib.Path(__file__).parent / "sweep_component"
# note that the following points at a directory. While we have two js files in the folder,
# Streamlit will automatically see the index.html file as the component and moutn it
_run_sweep_component = components.declare_component("boids_sweep", path=str(sweep_component_dir))

def render_sweep_component(configs, key=None):
    """Run batch of boids simulations, return list of results."""
    return _run_sweep_component(configs=configs, key=key, default=None)

# arbitrary sim box, just choosing a 1000x1000 box for now
WIDTH = 1000
HEIGHT = 1000
VERBOSE = True  # not sure if we will use this when deployed

# as in 1e[SCALE_ADAPT]
SCALE_ADAPTERS = {
  "attractive": -3,
  "alignment": -2,
  "avoid": -2,
}

# not scaled. use SCALE_ADAPT to scale
DEFAULT_PARAMS = {
    "attractive": 5,
    "alignment": 50,
    "avoid": 50,
    "visual_range": 75,
}

EXP_OPTIONS_DICT = {
    "OFAT Attractive": {
        "type": "ofat",
        "factors": ["attractive"],
    },
    "OFAT Alignment": {
        "type": "ofat", 
        "factors": ["alignment"],
    },
    "OFAT Avoid": {
        "type": "ofat",
        "factors": ["avoid"],
    },
    "Pairwise Attractive vs Alignment": {
        "type": "pairwise",
        "factors": ["attractive", "alignment"],
    },
    "Pairwise Attractive vs Avoid": {
        "type": "pairwise",
        "factors": ["attractive", "avoid"],
    },
    "Pairwise Alignment vs Avoid": {
        "type": "pairwise",
        "factors": ["alignment", "avoid"],
    },
    "Full Factor Interaction": {
        "type": "full",
        "factors": ["attractive", "alignment", "avoid"],
    },
}

st.session_state.setdefault("sweep_state", "waiting")

# ----------
# Sweep funcitons
# ----------

def build_js_config(params, duration, num_boids):
    return {
        "attractiveFactor": params["attractive"] * (10 ** SCALE_ADAPTERS["attractive"]),
        "alignmentFactor": params["alignment"] * (10 ** SCALE_ADAPTERS["alignment"]),
        "avoidFactor": params["avoid"] * (10 ** SCALE_ADAPTERS["avoid"]),
        "visualRange": params["visual_range"],
        "numBoids": num_boids,
        "width": WIDTH,
        "height": HEIGHT,
        "steps": duration,
        "verbose": VERBOSE,
    }

def run_sweep():
    """Build configs and store in session state. Component renders later."""
    st.session_state.sweep_state = "running"
    
    exp_type = st.session_state.get("exp_type_select")
    granularity = st.session_state.get("granularity_slider")
    range_val = st.session_state.get("range_slider")
    duration = st.session_state.get("run_duration_slider")
    num_boids = st.session_state.get("num_boids_slider")
    
    exp_config = EXP_OPTIONS_DICT[exp_type]
    configs = []
    
    if exp_config["type"] == "ofat":
        factor = exp_config["factors"][0]
        scale_adapter = SCALE_ADAPTERS[factor]
        sweep_max = range_val * (10 ** scale_adapter)
        sweep_stops = np.linspace(0, sweep_max, granularity)
        
        for stop in sweep_stops:
            params = DEFAULT_PARAMS.copy()
            params[factor] = stop
            configs.append(build_js_config(params, duration, num_boids))
    
    elif exp_config["type"] == "pairwise":
        # TODO: build 2D grid of configs
        pass
    
    elif exp_config["type"] == "full":
        # TODO: build 3D grid of configs
        pass
    
    st.session_state["sweep_configs"] = configs





# 1. Start by getting a rough idea of the space of possibilities by running the simulation while varying `attractiveFactor` and `alignmentFactor` (say, between 0 and 10).  What different types of long-term collective behavior do you see? *Hint: Don't worry about strange behavior at very large values of the parameters, unless you're feeling brave!*
# </br>

# 2. Make a list of key properties of the collective behavior that help distinguish the different types of long-term behavior.  These can be qualitative for now—properties you can measure roughly, by eye.  You might consider, for example, how close the boids are to one another, or how well aligned boids are.  (Some choices here could lead to more easily distinguished phases in the next step.)
# </br>

# 3. Define two or more *phases* in terms of one of the collective properties on your list (or more than one property if you're so inclined).  Example: You might identify a "disordered" phase as one in which individual boids typically point in all directions.  *Hint: Remember that phases should tell us something about behavior at the collective scale after a long time has passed.*
# </br>

# 4. Systematically vary `attractiveFactor` and `alignmentFactor`, recording which of your phases the system is in for each setting of the parameters.  Choose sensible ranges over which to vary the parameters to highlight any transitions between phases.
# </br>

# 5. Draw a two-dimensional phase diagram, with one axis of your plot representing `attractiveFactor` and the other `alignmentFactor`.  Draw lines on your plot representing boundaries between different phases.  *Hints: One simple way to build your phase diagram is by starting with a two-dimensional grid of points.  Each point in the grid corresponds to values for the parameters `attractiveFactor` and `alignmentFactor`, and the collective behavior at each point in the grid is characterized by its phase.  Once you have mapped out which points in the diagram correspond to which phases, phase boundaries happen where changes in the parameters lead to a change in the phase.  Phases may become difficult to distinguish near phase boundaries, with the system taking a long time to come to equilibrium.  This is typical, and even has a name: "critical slowing down".  Don't worry about making your phase diagram exact—your phase boundaries may be somewhat blurry.*
# </br>

# 6. Pick one of your key collective properties and write down a quantitative measure that one could use to distinguish phases more precisely.  Your measure should be a number that describes the aggregate state and something that one could calculate given any particular detailed state of the system.  You can describe your measure using a formula or in words. *Hint: In statistical physics, collective properties that define phases are typically called "order parameters" because they often measure the degree to which the system is ordered versus disordered.*
st.set_page_config(page_title="Boids Sweeps", page_icon="📊", layout="wide")

# navigation  (disabled for now)
# st.page_link("app.py", label="Simulation", icon="🐦")
# st.page_link("sweeps.py", label="Sweeps", icon="📊")
# st.divider()

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
# main content
# -------------------------
st.title("Sweeps")

with st.container(border=True):
  if st.session_state.sweep_state == "waiting":
    st.write("No sweep has been run yet.")
  elif st.session_state.sweep_state == "running":
    st.write("Sweep is running. Please wait for it to complete.")
  elif st.session_state.sweep_state == "completed":
    st.write("Sweep has completed. Results are shown below.")





# -------------------------
# Sweep configurator and controls.
# -------------------------
st.header("Sweep Configuration")
with st.container(border=True):
    st.write("Select an experiment type and choose sweep parameters.")
    exp_options = list(EXP_OPTIONS_DICT.keys())
    exp_type = st.selectbox("Experiment Type", exp_options, key="exp_type_select")
    selected_exp_info = EXP_OPTIONS_DICT[exp_type]
    st.slider("Granularity", 1, 100, step=1, key="granularity_slider")
    st.slider("Range", 1, 100, step=1, key="range_slider")
    st.slider("Run duration", 1, 100, step=1, key="run_duration_slider")
    st.slider("Number of boids", 100, 1000, step=100, key="num_boids_slider")
    
    st.caption("Granularity and range will be scaled according to factor.")

    st.button("Run Sweep", on_click=run_sweep, use_container_width=True, key="run_sweep")

# -------------------------
# Sweep component
# -------------------------
if st.session_state.sweep_state == "running":
  # report to sweep state container
  with st.container(border=True):
    st.write(f"Sweep initialized. Experiment type: {exp_type}. Parameters: ")
    st.table(st.session_state.get("sweep_configs", []))
    st.write("Running {len(configs)} simulations...")

  # actually run the sweep


    configs = st.session_state.get("sweep_configs", [])
    if configs:
      with st.spinner(f"Running {len(configs)} simulations..."):
        results = render_sweep_component(configs=configs, key="sweep_batch")
      
        if results is not None:
            st.session_state["sweep_results"] = results
            st.json(results, expanded=False)  # TODO replace with a downloader
            st.session_state.sweep_state = "completed"

# -------------------------
# Sweep discussion
# -------------------------

st.write("Discussion")
st.markdown("""
Because of the fact that, along with the three main "factors," we have a number of ancillary parameters, here we need to lay down
a few constraints:
- While we can see in the interactive Boids simulation that `visualRange` has a strong effect especially on cluster size, for now we will leave it pegged at 75.
- We will run each sweep with two initial quantities of boids: 100 and 1000. In other words, each sweep listed below will actually be split into two sweeps. I do not actually expect
that the differences at different quantities will be *so* material as to make additional quantity tiers interesting, but we shall see.
- We will run each sweep by [I don't know how many steps], determined for now by me looking at some plots and making an arbitary call.
- Finally, and most challenging, we will run every sweep using the same height and width parameters as supplied by Prof. Daniels. I observe that
when resizing the canvas in the interactive sim, behavior of the flocks is significantly altered particularly under different aspect ratios. However, the study of that phenomenon
seems beyond the scope of this homework. 

We will start with OFAT (One Factor At A Time) runs. Then we will do pairwise interaction sweeps.
Finally, we will have our three-way interaction "battle royale." (Absolutely a scientific term.)
""")
