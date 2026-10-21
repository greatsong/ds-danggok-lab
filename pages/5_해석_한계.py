import streamlit as st

from lab.engine import run_chat

st.set_page_config(page_title="해석·한계", page_icon="💡", layout="centered")
run_chat("interp")
