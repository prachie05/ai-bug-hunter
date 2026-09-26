from pydantic import BaseModel


class GeneratedPatch(BaseModel):
    file_path: str
    old_code: str
    new_code: str
    description: str