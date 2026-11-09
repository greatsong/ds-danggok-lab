"""모의 채팅 진행기.

시나리오(content/<이름>.json)의 대사를 한 단계씩 보여 주고, AI가 준 코드를 그 자리에서 실행해
결과를 보여 준다. 화면에 보이는 코드와 실행하는 코드는 같은 문자열이다.
새 페이지는 시나리오 파일을 하나 더 쓰고 pages/ 에 lab.fresh.engine().run_chat('<이름>')을 부르는 파일을 더하면 된다.

시나리오 형식
{
  "title": "페이지 제목", "intro": "도입 글(마크다운)",
  "steps": [
    {"who": "student", "text": "학생이 AI에게 보낸 말"},
    {"who": "ai", "text": "AI의 답", "code": "실행할 코드(선택)", "after": "결과를 본 뒤 AI의 설명(선택)", "flag": "wrong(선택, 틀린 제안: 화면에는 표시하지 않음)"},
    {"who": "check", "text": "학생이 직접 확인한 것(검증)"},
    {"who": "note", "title": "제목", "text": "정리 카드"},
    {"who": "oral", "title": "구술 인터뷰 대비: ...", "text": "안내", "checklist": "c3(선택, 그 회차의 준비 체크리스트)",
     "qa": [{"cp": "c3", "q": "opener 또는 꼬리질문 번호(0부터)", "label": "③ 질문", "asked": "예시 답을 쓸 때의 질문", "a": "예시 답"}]},
    구술 연습(선생님과 학생 한 명의 문답)에 쓰는 세 가지:
    {"who": "teacher", "cp": "c34", "q": "opener 또는 꼬리질문 번호", "asked": "대사를 쓸 때의 질문", "text": "질문 앞뒤에 붙일 말(선택)"},
    {"who": "answer", "text": "학생의 답(선생님께 말하는 합쇼체)"},
    {"who": "rubric", "cp": "c34", "item": "m-1", "checked": [0, 1], "text": "빠진 것·다음 질문으로 이어지는 까닭(선택)"}
  ],
  "summary": "마무리 글(마크다운)",
  "setup": "페이지를 열 때 조용히 실행할 코드(선택, 앞 페이지에서 이어지는 df 등)", "setup_note": "그 안내 한 줄(선택)",
  "code_fold": true(선택, 코드를 '코드 보기'로 접고 실행한 앱 화면을 먼저 보여 준다)
}
단계 사이에 이어지는 변수(df, df_prep 등)는 앞 단계의 코드를 차례로 다시 실행해 만든다.
구술 인터뷰 대비 카드(who: oral)의 질문과 체크리스트는 content/oral.json에서 읽는다. 이 파일은 2026-ds-danggok의
구술평가_루브릭.json에서 scripts/build_oral.py가 만든다. 루브릭의 질문을 고치면 카드도 함께 바뀐다.
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


def _oral_checkpoints():
    p = ROOT / 'content' / 'oral.json'
    if not p.exists():
        return {}
    return {c['id']: c for c in json.loads(p.read_text(encoding='utf-8'))['checkpoints']}


def _oral_card(s):
    """구술 인터뷰 대비 카드: 질문은 루브릭(oral.json)에서, 예시 답은 시나리오에서"""
    cps = _oral_checkpoints()
    with st.container(border=True):
        if s.get('title'):
            md('#### ' + s['title'])
        if s.get('text'):
            md(s['text'])
        for qa in s.get('qa', []):
            c = cps.get(qa['cp'], {})
            fu = c.get('followups', [])
            q = c.get('opener') if qa['q'] == 'opener' else (fu[qa['q']] if type(qa['q']) is int and 0 <= qa['q'] < len(fu) else None)
            md('**%s** %s' % (qa.get('label', ''), q or qa.get('asked', '')))
            md('> 예시 답: ' + qa['a'])
        if s.get('checklist') in cps:
            c = cps[s['checklist']]
            with st.expander('%s %s 준비 체크리스트(구술 평가 안내와 같은 목록)' % (c['no'], c['title'])):
                md('\n'.join('- ' + x for x in c['checklist']))


def _ask(s):
    """선생님 질문: 루브릭(oral.json)의 지금 문구를 쓰고, 없으면 시나리오에 적어 둔 질문을 쓴다"""
    c = _oral_checkpoints().get(s.get('cp'), {})
    fu = c.get('followups', [])
    q = c.get('opener') if s.get('q') == 'opener' else (fu[s['q']] if type(s.get('q')) is int and 0 <= s['q'] < len(fu) else None)
    return q or s.get('asked', '')


def _rubric_card(s):
    """담은 내용 확인: 선생님 앱처럼 그 항목의 평가 요소를 체크로 보여 준다(상·중·하는 선생님이 정하므로 보여 주지 않는다)"""
    c = _oral_checkpoints().get(s.get('cp'), {})
    it = next((x for x in c.get('items', []) if x['id'] == s.get('item')), None)
    with st.container(border=True):
        if not it:
            md(s.get('text', ''))
            return
        done = set(s.get('checked', []))
        md('#### 담은 내용 확인 · %s' % it['title'])
        md('\n'.join(('- ✅ ' if i in done else '- ⬜ ') + e for i, e in enumerate(it['elements'])))
        st.caption('담은 내용 %d / %d' % (len(done), len(it['elements'])))
        if s.get('text'):
            md(s['text'])


def load_scenario(name):
    return json.loads((ROOT / 'content' / (name + '.json')).read_text(encoding='utf-8'))


_RUNTIME = {'pd': _PD, 'np': np, 'px': px, 'st': st}   # 코드가 쓰는 실행 환경(준비 캐시에 넣지 않는다)


def _namespace():
    b = dict(builtins.__dict__)
    b['__import__'] = _import
    return {'__builtins__': b, **_RUNTIME}


@st.cache_resource(show_spinner='앞 단계의 결과를 준비하는 중…')
def _setup_cached(code):
    """앞 페이지에서 이어지는 준비 코드는 한 번만 실행한다(모델 학습 포함).
    결과(데이터·모델)는 모든 사용자가 함께 쓰므로, 단계 코드에서 제자리 수정(inplace)을 하지 않는다."""
    ns = _namespace()
    exec(compile(code, '<준비>', 'exec'), ns)
    # 데이터·모델만 남긴다. 실행 환경까지 캐시하면 진행기가 바뀐 뒤에도 옛 환경이 되살아난다
    return {k: v for k, v in ns.items() if not k.startswith('__') and k not in _RUNTIME}


def _run_code(code, ns, idx):
    with st.container(border=True):
        st.caption('▶ 이 코드를 실행한 결과')
        try:
            exec(compile(code, '<단계 %d>' % (idx + 1), 'exec'), ns)
        except Exception as e:  # 시나리오 오류는 화면에 그대로 보인다
            st.error('코드 실행 중 오류: %s' % e)


# 대화 속 마크다운 표: 한글이 글자 단위로 줄바꿈되지 않게 낱말 단위로 끊는다(좁은 첫 열의 "로지스틱 회귀"가 한 글자씩 내려가던 문제).
# 그 대신 휴대폰처럼 좁은 화면에서는 표가 넓어지므로 표 안에서만 옆으로 밀어 보게 한다
_TABLE_CSS = '''<style>
[data-testid="stMarkdownContainer"] table td, [data-testid="stMarkdownContainer"] table th { word-break: keep-all; overflow-wrap: break-word; }
[data-testid="stMarkdownContainer"] table td:first-child, [data-testid="stMarkdownContainer"] table th:first-child { min-width: 5.5em; }
[data-testid="stMarkdownContainer"] table { display: block; max-width: 100%; overflow-x: auto; }
</style>'''


def run_chat(name):
    sc = load_scenario(name)
    steps = sc['steps']
    key = 'step_' + name
    if key not in st.session_state:
        st.session_state[key] = 1

    st.markdown(_TABLE_CSS, unsafe_allow_html=True)
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
        if who == 'oral':
            _oral_card(s)
            continue
        if who == 'note':
            with st.container(border=True):
                if s.get('title'):
                    md('#### ' + s['title'])
                md(s['text'])
            continue
        if who == 'teacher':
            with st.chat_message('assistant', avatar='👩‍🏫'):
                st.markdown('**선생님**')
                if s.get('text'):
                    md(s['text'])
                md('**' + _ask(s) + '**')
            continue
        if who == 'answer':
            with st.chat_message('user', avatar='🧑‍🎓'):
                st.markdown('**학생 · 답**')
                md(s['text'])
            continue
        if who == 'rubric':
            _rubric_card(s)
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
                if sc.get('code_fold'):   # 앱 화면을 먼저 보게 코드는 접어 둔다
                    with st.expander('코드 보기'):
                        st.code(s['code'], language='python')
                else:
                    st.code(s['code'], language='python')
                _run_code(s['code'], ns, i)
            if s.get('after'):
                md(s['after'])

    if not show_all and st.session_state[key] < len(steps):
        nxt = steps[st.session_state[key]]
        label = {'student': '다음: 학생이 묻기', 'ai': '다음: AI가 답하기', 'check': '다음: 직접 확인하기',
                 'note': '다음: 정리하기', 'oral': '다음: 구술 인터뷰 대비', 'teacher': '다음: 선생님 질문',
                 'answer': '다음: 학생이 답하기', 'rubric': '다음: 담은 내용 확인'}.get(nxt['who'], '다음')
        if st.button(label + ' ▶', type='primary', key='next_' + name, width='stretch'):
            st.session_state[key] += 1
            st.rerun()
    elif sc.get('summary'):
        st.divider()
        md(sc['summary'])
    return ns
