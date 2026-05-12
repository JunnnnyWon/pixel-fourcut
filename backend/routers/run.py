from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend import runner

router = APIRouter()


class RunRequest(BaseModel):
    filename: str


@router.post("/api/run")
async def run(req: RunRequest):
    try:
        prompt_id = await runner.enqueue(req.filename)
        return {"prompt_id": prompt_id}
    except FileNotFoundError as e:
        raise HTTPException(400, "활성화된 워크플로우 프리셋이 없습니다. 관리자 패널에서 프리셋을 활성화해주세요.")
    except Exception as e:
        raise HTTPException(500, f"처리 중 오류가 발생했습니다: {str(e)}")
