import streamlit as st

from lab.engine import run_chat

st.set_page_config(page_title="평가지표·결과", page_icon="📏", layout="centered")
run_chat("eval")
