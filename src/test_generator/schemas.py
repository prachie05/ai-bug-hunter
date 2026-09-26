from pydantic import BaseModel


class GeneratedTest(BaseModel):
    test_code: str
    description:str