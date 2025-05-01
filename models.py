from pydantic import BaseModel
from typing import Optional, Any, List

class APIResponse(BaseModel):
    data: Optional[Any] = None
    next_step: Optional[Any] = None
    message: Optional[str] = None

class DownloadButton(BaseModel):
    text: str
    link: str
    next_step: Optional[dict] = None

class DownloadGroup(BaseModel):
    title: str
    buttons: List[DownloadButton]

class SearchResult(BaseModel):
    title: str
    url: str
    thumbnail: Optional[str] = None
    next_step: Optional[dict] = None

class ExtractResponse(BaseModel):
    title: Optional[str] = None
    image: Optional[str] = None
    groups: List[DownloadGroup]