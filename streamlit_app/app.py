import streamlit as st

st.set_page_config(layout="wide", page_title="Voice AI Dashboard")

st.markdown("""
<div style="text-align: center; margin-bottom: 2rem;">
    <h1 style="background: linear-gradient(to right, #60a5fa, #34d399); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
        Healthcare Voice AI Dashboard
    </h1>
    <p style="color: #94a3b8; font-size: 1.1rem;">
        This Streamlit interface is seamlessly integrated with our ultra-low latency WebSocket Agent.
    </p>
</div>
""", unsafe_allow_html=True)

import streamlit.components.v1 as components

# Embed the vanilla JS frontend via components.html to ensure microphone permissions are passed through Streamlit's sandbox.
components.html("""
<iframe src="http://localhost:8000/static/index.html" 
        allow="microphone; autoplay" 
        width="100%" 
        height="900px" 
        style="border: none; border-radius: 24px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); background-color: #0f172a;">
</iframe>
""", height=900)
