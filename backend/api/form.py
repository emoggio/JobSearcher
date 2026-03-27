from fastapi import APIRouter
from pydantic import BaseModel
from backend.agents.form_filler import fill_form

router = APIRouter()


class FormFillRequest(BaseModel):
    job_id: str
    form_url: str
    form_fields: list[dict]   # [{"label": "...", "type": "text|select|textarea"}]


@router.post("/fill/{job_id}")
async def fill_application_form(body: FormFillRequest):
    """AI fills in application form fields using your CV and the job description."""
    answers = await fill_form(body.job_id, body.form_url, body.form_fields)
    return {"answers": answers}
