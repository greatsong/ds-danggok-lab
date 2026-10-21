import json
from pathlib import Path

import importlib
import os

import pandas as pd
import streamlit as st

import lab.engine

# 클라우드는 새 커밋을 받아도 이미 불러온 진행기 모듈을 그대로 쓴다. 파일이 바뀌었으면 다시 읽는다
if getattr(lab.engine, "MTIME", None) != os.path.getmtime(lab.engine.__file__):
    importlib.reload(lab.engine)
from lab.engine import md  # noqa: E402

st.set_page_config(page_title="데이터 과학 실습실", page_icon="🧪", layout="centered")

home = json.loads((Path(__file__).parent / "content" / "home.json").read_text(encoding="utf-8"))

st.title("🧪 " + home["title"])
md(home["intro"])

# 팀 프로젝트 흐름: 단계마다 팀이 하는 일과 이 앱의 해당 페이지
for s in home["stages"]:
    with st.container(border=True):
        left, right = st.columns([1, 3])
        left.markdown("**%s %s**" % (s["no"], s["title"]))
        with right:
            md(s["do"])
            if s["pages"]:
                st.caption("이 앱에서: " + s["app"])
                for path, label in s["pages"]:
                    st.page_link(path, label=label, icon="➡️")
            elif s.get("soon"):
                st.caption("이 앱에서: 준비 중")
            elif s["app"]:
                st.caption("이 앱에서: " + s["app"])

st.caption(home["record"])

with st.expander("데이터: 뇌졸중 데이터(Stroke Prediction Dataset)"):
    md(home["data"])
    st.dataframe(pd.DataFrame(home["columns"], columns=["열 이름", "뜻"]), hide_index=True, width="stretch")

st.info(home["note"])
