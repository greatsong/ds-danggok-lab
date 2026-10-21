"""진행기(lab/engine.py)를 늘 최신 파일로 쓰게 하는 장치. 이 파일은 고치지 않는다.

스트림릿 클라우드는 새 커밋을 받아도 이미 불러온 모듈을 그대로 쓴다. 페이지가 engine()으로 진행기를 받으면
파일이 바뀌었을 때 캐시된 바이트코드를 지우고 다시 읽는다. 여러 사용자가 동시에 들어와도 잠금으로 한 번만 다시 읽고,
다시 읽기가 끝난 뒤에야 새 수정 시각을 기록한다.
"""
import importlib
import importlib.util
import os
import threading

import lab.engine as _engine

_lock = threading.Lock()


def engine():
    with _lock:
        mtime = os.path.getmtime(_engine.__file__)
        if getattr(_engine, 'LOADED_MTIME', None) != mtime:
            try:
                os.remove(importlib.util.cache_from_source(_engine.__file__))
            except OSError:
                pass
            importlib.reload(_engine)
            _engine.LOADED_MTIME = mtime
        return _engine
