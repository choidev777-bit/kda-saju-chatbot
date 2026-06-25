"""pytest 부트스트랩: 프로젝트 루트를 import 경로에 추가한다.

이렇게 해야 테스트에서 `from src.tools.saju_chart import ...` 가 안정적으로 동작한다.
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
