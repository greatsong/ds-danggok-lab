"""진행기(lab/engine.py)를 늘 최신 파일로 쓰게 하는 장치. 이 파일은 고치지 않는다.

스트림릿 클라우드는 새 커밋을 받아도 이미 불러온 모듈을 그대로 쓴다. 페이지가 engine()으로 진행기를 받으면,
파일이 바뀌었을 때 소스를 직접 읽어(바이트코드 캐시를 거치지 않음) 새 모듈 객체로 만든다. 같은 객체를 덮어쓰지 않으므로
진행 중인 다른 사용자는 옛 객체로 끝까지 실행하고, 새로 들어오는 사용자부터 새 객체를 쓴다(두 버전이 섞이지 않는다).
모듈 이름은 늘 lab.engine이라, 스트림릿 캐시(데이터·학습한 모델)는 함수 소스가 같으면 버전 사이에 그대로 함께 쓴다
(이름이 버전마다 다르면 캐시가 버전마다 쌓인다). 확인과 만들기는 잠금 안에서 한 번만 한다.
"""
import os
import sys
import threading
import types

ENGINE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'engine.py')
_lock = threading.Lock()
_current = {'mtime': None, 'module': None}


def engine():
    with _lock:
        mtime = os.path.getmtime(ENGINE_FILE)
        if _current['mtime'] != mtime:
            with open(ENGINE_FILE, encoding='utf-8') as f:
                code = compile(f.read(), ENGINE_FILE, 'exec')
            module = types.ModuleType('lab.engine')
            module.__file__ = ENGINE_FILE
            exec(code, module.__dict__)
            sys.modules['lab.engine'] = module   # 진행 중인 세션은 옛 함수가 쥔 전역으로 끝까지 쓴다
            _current.update(mtime=mtime, module=module)
        return _current['module']
