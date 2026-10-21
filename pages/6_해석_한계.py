import streamlit as st

from lab.fresh import engine

st.set_page_config(page_title="해석·한계", page_icon="💡", layout="centered")
engine().run_chat("interp")
