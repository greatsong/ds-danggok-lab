"""모의 채팅 진행기.

시나리오(content/<이름>.json)의 대사를 한 단계씩 보여 주고, AI가 준 코드를 그 자리에서 실행해
결과를 보여 준다. 화면에 보이는 코드와 실행하는 코드는 같은 문자열이다.
새 페이지(모델, 평가)는 시나리오 파일을 하나 더 쓰고 pages/ 에 run_chat('<이름>')을 부르는 파일을 더하면 된다.

시나리오 형식
{
  "title": "페이지 제목", "intro": "도입 글(마크다운)",
  "steps": [
    {"who": "student", "text": "학생이 AI에게 보낸 말"},
    {"who": "ai", "text": "AI의 답", "code": "실행할 코드(선택)", "after": "결과를 본 뒤 AI의 설명(선택)", "flag": "wrong(선택, 틀린 제안: 화면에는 표시하지 않음)"},
    {"who": "check", "text": "학생이 직접 확인한 것(검증)"},
    {"who": "note", "title": "제목", "text": "정리 카드"}
  ],
  "summary": "마무리 글(마크다운)",
  "setup": "페이지를 열 때 조용히 실행할 코드(선택, 앞 페이지에서 이어지는 df 등)", "setup_note": "그 안내 한 줄(선택)"
}
단계 사이에 이어지는 변수(df, df_prep 등)는 앞 단계의 코드를 차례로 다시 실행해 만든다.
"""
import builtins
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent


@st.cache_data(show_spinner='데이터를 불러오는 중…')
def _read_csv_cached(path, kw_json):
    return pd.read_csv(path, **json.loads(kw_json))


class _CachedPandas:
    """코드 속 `import pandas as pd`가 받는 pandas. 인터넷 주소의 CSV는 한 번만 내려받는다."""

    def __getattr__(self, name):
        return getattr(pd, name)

    def read_csv(self, path, *args, **kwargs):
        if isinstance(path, str) and path.startswith('http') and not args:
            try:
                return _read_csv_cached(path, json.dumps(kwargs, sort_keys=True)).copy()
            except TypeError:
                pass
        return pd.read_csv(path, *args, **kwargs)


_PD = _CachedPandas()
_real_import = builtins.__import__


def _import(name, globals=None, locals=None, fromlist=(), level=0):
    if name == 'pandas' and not fromlist:
        return _PD
    return _real_import(name, globals, locals, fromlist, level)


def md(text):
    """마크다운으로 그리되, 코드 바깥의 물결표(~)는 그대로 보이게 한다(77~114가 취소선이 되지 않게)."""
    out, in_block = [], False
    for line in str(text).split('\n'):
        if line.strip().startswith('```'):
            in_block = not in_block
            out.append(line)
            continue
        if in_block:
            out.append(line)
            continue
        parts = line.split('`')
        out.append('`'.join(x if i % 2 else x.replace('~', '\\~') for i, x in enumerate(parts)))
    st.markdown('\n'.join(out))


def load_scenario(name):
    return json.loads((ROOT / 'content' / (name + '.json')).read_text(encoding='utf-8'))


def _namespace():
    b = dict(builtins.__dict__)
    b['__import__'] = _import
    return {'__builtins__': b, 'pd': _PD, 'np': np, 'px': px, 'st': st}


@st.cache_resource(show_spinner='앞 단계의 결과를 준비하는 중…')
def _setup_cached(code):
    """앞 페이지에서 이어지는 준비 코드는 한 번만 실행한다(모델 학습 포함).
    결과(데이터·모델)는 모든 사용자가 함께 쓰므로, 단계 코드에서 제자리 수정(inplace)을 하지 않는다."""
    ns = _namespace()
    exec(compile(code, '<준비>', 'exec'), ns)
    return {k: v for k, v in ns.items() if not k.startswith('__')}


def _run_code(code, ns, idx):
    with st.container(border=True):
        st.caption('▶ 이 코드를 실행한 결과')
        try:
            exec(compile(code, '<단계 %d>' % (idx + 1), 'exec'), ns)
        except Exception as e:  # 시나리오 오류는 화면에 그대로 보인다
            st.error('코드 실행 중 오류: %s' % e)


def run_chat(name):
    sc = load_scenario(name)
    steps = sc['steps']
    key = 'step_' + name
    if key not in st.session_state:
        st.session_state[key] = 1

    st.title(sc['title'])
    if sc.get('intro'):
        md(sc['intro'])

    with st.sidebar:
        st.markdown('### 진행')
        show_all = st.toggle('대화를 한 번에 모두 보기', key='all_' + name)
        st.progress(min(st.session_state[key], len(steps)) / len(steps),
                    text='%d / %d 단계' % (min(st.session_state[key], len(steps)), len(steps)))
        if st.button('처음부터 다시', key='reset_' + name, width='stretch'):
            st.session_state[key] = 1
            st.rerun()

    upto = len(steps) if show_all else st.session_state[key]
    ns = _namespace()
    if sc.get('setup'):
        ns.update(_setup_cached(sc['setup']))
        if sc.get('setup_note'):
            st.caption(sc['setup_note'])
    for i, s in enumerate(steps[:upto]):
        who = s['who']
        if who == 'note':
            with st.container(border=True):
                if s.get('title'):
                    md('#### ' + s['title'])
                md(s['text'])
            continue
        if who == 'check':
            with st.chat_message('user', avatar='🔎'):
                st.markdown('**학생 · 직접 확인하기**')
                md(s['text'])
            continue
        role = 'user' if who == 'student' else 'assistant'
        with st.chat_message(role, avatar='🧑‍🎓' if role == 'user' else '🤖'):
            st.markdown('**학생**' if role == 'user' else '**AI**')
            md(s['text'])
            if s.get('code'):
                st.code(s['code'], language='python')
                _run_code(s['code'], ns, i)
            if s.get('after'):
                md(s['after'])

    if not show_all and st.session_state[key] < len(steps):
        nxt = steps[st.session_state[key]]
        label = {'student': '다음: 학생이 묻기', 'ai': '다음: AI가 답하기', 'check': '다음: 직접 확인하기',
                 'note': '다음: 정리하기'}.get(nxt['who'], '다음')
        if st.button(label + ' ▶', type='primary', key='next_' + name, width='stretch'):
            st.session_state[key] += 1
            st.rerun()
    elif sc.get('summary'):
        st.divider()
        md(sc['summary'])
    return ns
