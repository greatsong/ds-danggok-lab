import streamlit as st

from lab.fresh import engine

st.set_page_config(page_title="모델 후보·베이스라인", page_icon="🧠", layout="centered")
engine().run_chat("model")
