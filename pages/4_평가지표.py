import streamlit as st

from lab.fresh import engine

st.set_page_config(page_title="평가지표·결과", page_icon="📏", layout="centered")
engine().run_chat("eval")
