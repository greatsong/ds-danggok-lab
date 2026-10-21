import streamlit as st

from lab.fresh import engine

st.set_page_config(page_title="모델 원리", page_icon="⚙️", layout="centered")
engine().run_chat("principle")
