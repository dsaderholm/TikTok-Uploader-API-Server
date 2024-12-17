from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from typing import List, Optional
import os
import shutil
import tempfile
from tiktokautouploader import upload_tiktok
from playwright.sync_api import sync_playwright
import logging
import asyncio
from functools import partial

app = FastAPI(title="TikTok Uploader API")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get cookie directory from environment variable
COOKIE_DIR = os.getenv('COOKIE_DIR', '/data/cookies')

def custom_upload_tiktok(**kwargs):
    """Modified version of upload_tiktok with custom browser settings"""
    with sync_playwright() as p:
        browser_args = [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--single-process',
            '--disable-gpu'
        ]
        
        browser = p.firefox.launch(
            headless=True,
            args=browser_args
        )
        
        try:
            # Set the browser instance for the upload
            kwargs['browser'] = browser
            # Call the original upload function
            result = upload_tiktok(**kwargs)
            return result
        finally:
            browser.close()

async def run_upload_in_thread(
    video_path: str,
    description: str,
    accountname: str,
    hashtags: Optional[List[str]] = None,
    sound_name: Optional[str] = None,
    sound_aud_vol: Optional[str] = 'mix',
    schedule: Optional[str] = None,
    day: Optional[int] = None,
    copyrightcheck: bool = False
):
    """Run the custom upload function in a thread pool."""
    logger.info(f"Starting upload for account: {accountname}")
    
    upload_func = partial(
        custom_upload_tiktok,
        video=video_path,
        description=description,
        accountname=accountname,
        hashtags=hashtags,
        sound_name=sound_name,
        sound_aud_vol=sound_aud_vol,
        schedule=schedule,
        day=day,
        copyrightcheck=copyrightcheck,
        suppressprint=False
    )
    
    return await asyncio.to_thread(upload_func)

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
    temp_video_path = None
    try:
        logger.info(f"Processing upload request for account: {accountname}")
        
        # Verify cookie file exists
        cookie_source = os.path.join(COOKIE_DIR, f'TK_cookies_{accountname}.json')
        if not os.path.exists(cookie_source):
            raise HTTPException(status_code=400, detail=f"Cookie file not found for account {accountname}")
        
        # Create temporary file for video
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_video:
            shutil.copyfileobj(video.file, temp_video)
            temp_video_path = temp_video.name
        
        logger.info(f"Video saved to temporary file: {temp_video_path}")
        
        # Copy cookie file to current directory
        cookie_dest = f'TK_cookies_{accountname}.json'
        shutil.copy2(cookie_source, cookie_dest)
        logger.info(f"Cookie file copied from {cookie_source} to {cookie_dest}")

        # Process hashtags
        hashtag_list = None
        if hashtags:
            hashtag_list = [tag.strip() for tag in hashtags.split(',')]

        try:
            # Upload to TikTok in a thread pool
            await run_upload_in_thread(
                video_path=temp_video_path,
                description=description,
                accountname=accountname,
                hashtags=hashtag_list,
                sound_name=sound_name,
                sound_aud_vol=sound_aud_vol,
                schedule=schedule,
                day=day,
                copyrightcheck=copyrightcheck
            )
            
            return {"success": True, "message": "Video uploaded successfully"}

        except Exception as e:
            if "Save draft" in str(e):
                return {"success": True, "message": "Video uploaded but saved as draft"}
            raise e

    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Clean up files
        try:
            if temp_video_path and os.path.exists(temp_video_path):
                os.unlink(temp_video_path)
                logger.info(f"Cleaned up temporary video file: {temp_video_path}")
            
            cookie_dest = f'TK_cookies_{accountname}.json'
            if os.path.exists(cookie_dest):
                os.unlink(cookie_dest)
                logger.info(f"Cleaned up cookie file: {cookie_dest}")
                
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)