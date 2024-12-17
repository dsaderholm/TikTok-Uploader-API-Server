from pydantic import BaseModel
from typing import Optional, List

class UploadResponse(BaseModel):
    success: bool
    message: str

class UploadRequest(BaseModel):
    description: str
    accountname: str
    hashtags: Optional[List[str]] = None
    sound_name: Optional[str] = None
    sound_aud_vol: Optional[str] = 'mix'
    schedule: Optional[str] = None
    day: Optional[int] = None
    copyrightcheck: bool = False