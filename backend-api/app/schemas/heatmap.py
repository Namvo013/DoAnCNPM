from pydantic import BaseModel


class HeatCell(BaseModel):
    latitude: float
    longitude: float
    count: int
    warning: bool


class PoiCrowd(BaseModel):
    poi_id: str
    name: str
    visitor_count: int
    warning: bool


class HeatmapResponse(BaseModel):
    cells: list[HeatCell]
    poi_crowds: list[PoiCrowd]
    located_visitors: int
    crowd_threshold: int
