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
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))
