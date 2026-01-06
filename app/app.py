import streamlit as st
import streamlit.components.v1 as components
import pathlib

component_dir = pathlib.Path(__file__).parent / "canvas_component"

# declare the component using the streamlit component API
_component_func = components.declare_component("my_canvas", path=str(component_dir))

# wrapper function to render the component
def render_canvas(drawing_color="black", clear_flag=False, key=None):
    """
    Renders the component and returns the value sent from JavaScript.
    
    Args:
        drawing_color: A signal to send to JS.
        clear_flag: Another signal to send to JS.
        key: Unique Streamlit key to prevent re-renders loops.
    """
    component_value = _component_func(
        drawing_color=drawing_color,
        clear_flag=clear_flag,
        key=key,
        default={} # Default return value before JS sends anything
    )
    return component_value

# 3. The Streamlit App Logic
st.title("Bi-Directional Canvas Component")

with st.sidebar:
    st.header("Controls (Python -> JS)")
    # Signal 1: Color Picker
    color = st.color_picker("Pick a color", "#FF0000")
    # Signal 2: Clear Button
    clear = st.button("Clear Canvas")

with st.container(border=True):
    st.header("Simulator")
    # Render the component and capture telemetry
    # Note: Streamlit re-runs the script whenever the component sends data back.
    telemetry = render_canvas(drawing_color=color, clear_flag=clear)
    
    if telemetry:
        st.write("Received from JS:")
        st.json(telemetry)
    else:
        st.info("Click on the canvas to send data.")

# Note on "Clear": The clear button is stateless. In a real app, you might want
# to use st.session_state to manage the clear flag so it resets after one frame.