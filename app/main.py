from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from typing import List, Optional
import os
import shutil
import tempfile
from tiktokautouploader import upload_tiktok
import logging
import asyncio
from functools import partial

app = FastAPI(title="TikTok Uploader API")

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get cookie directory from environment variable
COOKIE_DIR = os.getenv('COOKIE_DIR', '/data/cookies')

def process_hashtags(hashtags: str) -> List[str]:
    """
    Process hashtags string into proper format.
    Returns list of hashtags with # prefix.
    """
    if not hashtags:
        return None
    
    tags = hashtags.split(',')
    processed_tags = [f'#{tag.lstrip("#").strip()}' for tag in tags if tag.strip()]
    return processed_tags if processed_tags else None

async def run_upload_in_thread(
    video_path: str,
    description: str,
    accountname: str,
    hashtags: Optional[str] = None,
    sound_name: Optional[str] = None,
    sound_aud_vol: Optional[str] = 'mix',
    schedule: Optional[str] = None,
    day: Optional[int] = None,
    copyrightcheck: Optional[bool] = True
):
    """Run the upload_tiktok function in a thread pool with detailed logging."""
    processed_hashtags = process_hashtags(hashtags) if hashtags else None
    
    logger.info(f"Starting upload for account: {accountname}")
    logger.info(f"Processed hashtags: {processed_hashtags}")
    
    if sound_name:
        logger.info(f"Attempting to add sound: {sound_name} with volume: {sound_aud_vol}")
    
    # Ensure sound_aud_vol is valid
    if sound_aud_vol not in ['mix', 'background', 'main']:
        logger.warning(f"Invalid sound_aud_vol value: {sound_aud_vol}, defaulting to 'mix'")
        sound_aud_vol = 'mix'

    upload_func = partial(
        upload_tiktok,
        video=video_path,
        description=description,
        accountname=accountname,
        hashtags=processed_hashtags,
        sound_name=sound_name,
        sound_aud_vol=sound_aud_vol,
        schedule=schedule,
        day=day,
        copyrightcheck=copyrightcheck,
        suppressprint=False
    )
    
    try:
        return await asyncio.to_thread(upload_func)
    except Exception as e:
        logger.error(f"Upload failed with error: {str(e)}")
        raise

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
    copyrightcheck: Optional[bool] = Form(True)
):
    temp_video_path = None
    try:
        logger.info(f"Received upload request for account: {accountname}")
        logger.info(f"Sound parameters - name: {sound_name}, volume: {sound_aud_vol}")
        
        # Validate account and cookie
        cookie_source = os.path.join(COOKIE_DIR, f'TK_cookies_{accountname}.json')
        if not os.path.exists(cookie_source):
            raise HTTPException(status_code=400, detail=f"Cookie file not found for account {accountname}")
        
        # Handle video file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_video:
            shutil.copyfileobj(video.file, temp_video)
            temp_video_path = temp_video.name
            
        # Copy cookie file
        shutil.copy2(cookie_source, f'TK_cookies_{accountname}.json')

        try:
            # Attempt upload
            await run_upload_in_thread(
                video_path=temp_video_path,
                description=description,
                accountname=accountname,
                hashtags=hashtags,
                sound_name=sound_name,
                sound_aud_vol=sound_aud_vol,
                schedule=schedule,
                day=day,
                copyrightcheck=copyrightcheck
            )
            
            return {"success": True, "message": "Video uploaded successfully"}
            
        except Exception as e:
            error_msg = str(e)
            if "SAVE AS DRAFT BUTTON NOT FOUND" in error_msg:
                logger.error("Failed to save as draft - this might be due to account restrictions or permissions")
                raise HTTPException(
                    status_code=400,
                    detail="Failed to add sound and couldn't save as draft. Please verify account permissions or try without sound."
                )
            raise

    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # Cleanup
        try:
            if temp_video_path and os.path.exists(temp_video_path):
                os.unlink(temp_video_path)
            if os.path.exists(f'TK_cookies_{accountname}.json'):
                os.unlink(f'TK_cookies_{accountname}.json')
        except Exception as cleanup_error:
            logger.error(f"Cleanup failed: {str(cleanup_error)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)