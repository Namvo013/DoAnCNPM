from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    mongodb: str
    redis: str
