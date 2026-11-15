from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    sql_server: str
    redis: str
