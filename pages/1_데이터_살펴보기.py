import streamlit as st

from lab.fresh import engine

st.set_page_config(page_title="데이터 살펴보기", page_icon="🔍", layout="centered")
engine().run_chat("eda")
