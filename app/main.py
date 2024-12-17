from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from typing import List, Optional
import os
import shutil
import tempfile
from tiktokautouploader import upload_tiktok
import logging

app = FastAPI(title="TikTok Uploader API")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get cookie directory from environment variable
COOKIE_DIR = os.getenv('COOKIE_DIR', '/data/cookies')

@app.post("/upload")
async def upload_video(
    video: UploadFile = File(...),
    description: str = Form(...),
    accountname: str = Form(...),
    hashtags: Optional[str] = Form(None),
    sound_name: Optional[str] = Form(None),
    sound_aud_vol: Optional[str] = Form('mix'),
    schedule: Optional[str] = Form(None),
    day: Optional[int] = Form(None),
    copyrightcheck: bool = Form(False)
):
    try:
        # Copy cookie file to the location tiktokautouploader expects
        cookie_source = os.path.join(COOKIE_DIR, f'TK_cookies_{accountname}.json')
        if not os.path.exists(cookie_source):
            raise HTTPException(status_code=400, detail=f"Cookie file not found for account {accountname}")
        
        # Create temporary file for video
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_video:
            shutil.copyfileobj(video.file, temp_video)
            temp_video_path = temp_video.name
            
        # Copy cookie file to current directory
        shutil.copy2(cookie_source, f'TK_cookies_{accountname}.json')

        # Process hashtags
        hashtag_list = None
        if hashtags:
            hashtag_list = [tag.strip() for tag in hashtags.split(',')]

        try:
            # Upload to TikTok
            upload_tiktok(
                video=temp_video_path,
                description=description,
                accountname=accountname,
                hashtags=hashtag_list,
                sound_name=sound_name,
                sound_aud_vol=sound_aud_vol,
                schedule=schedule,
                day=day,
                copyrightcheck=copyrightcheck,
                suppressprint=True
            )
        finally:
            # Clean up files
            if os.path.exists(temp_video_path):
                os.unlink(temp_video_path)
            if os.path.exists(f'TK_cookies_{accountname}.json'):
                os.unlink(f'TK_cookies_{accountname}.json')

        return {"success": True, "message": "Video uploaded successfully"}

    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)