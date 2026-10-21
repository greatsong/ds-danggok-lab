import importlib
import os

import streamlit as st

import lab.engine

# 클라우드는 새 커밋을 받아도 이미 불러온 진행기 모듈을 그대로 쓴다. 파일이 바뀌었으면 다시 읽는다
if getattr(lab.engine, "MTIME", None) != os.path.getmtime(lab.engine.__file__):
    importlib.reload(lab.engine)
from lab.engine import run_chat  # noqa: E402

st.set_page_config(page_title="모델 후보·베이스라인", page_icon="🧠", layout="centered")
run_chat("model")
