import streamlit as st

from lab.engine import run_chat

st.set_page_config(page_title="데이터 살펴보기", page_icon="🔍", layout="centered")
run_chat("eda")
