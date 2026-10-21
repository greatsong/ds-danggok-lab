import streamlit as st

from lab.fresh import engine

st.set_page_config(page_title="전처리", page_icon="🧹", layout="centered")
engine().run_chat("prep")
