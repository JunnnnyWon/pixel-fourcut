# 서버 세션 상태 (단일 인스턴스, 재시작 시 초기화)
from typing import Optional

class SessionState:
    def __init__(self):
        self.images: list[str] = []          # 갤러리 이미지 파일명 목록
        self.selected: Optional[str] = None  # 선택된 이미지 파일명
        self.status: str = "idle"            # idle | processing | done | error
        self.prompt_id: Optional[str] = None
        self.result_filename: Optional[str] = None
        self.error: Optional[str] = None

    def reset(self):
        self.__init__()

    def to_dict(self):
        return {
            "images": self.images,
            "selected": self.selected,
            "status": self.status,
            "prompt_id": self.prompt_id,
            "result_filename": self.result_filename,
            "error": self.error,
        }

session = SessionState()
