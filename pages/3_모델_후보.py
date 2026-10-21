import streamlit as st

from lab.engine import run_chat

st.set_page_config(page_title="모델 후보·베이스라인", page_icon="🧠", layout="centered")
run_chat("model")
