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
import time

app = FastAPI(title="TikTok Uploader API")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get cookie directory from environment variable
COOKIE_DIR = os.getenv('COOKIE_DIR', '/data/cookies')

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
    """Run the synchronous upload_tiktok function in a thread pool."""
    logger.info(f"Starting upload for account: {accountname}")
    
    def verify_upload(response_text):
        success_indicators = [
            "Leaving the page does not interrupt",
            "Upload completed successfully",
            "Done uploading video"
        ]
        return any(indicator in response_text for indicator in success_indicators)

    try:
        upload_func = partial(
            upload_tiktok,
            video=video_path,
            description=description,
            accountname=accountname,
            hashtags=hashtags,
            sound_name=sound_name,
            sound_aud_vol=sound_aud_vol,
            schedule=schedule,
            day=day,
            copyrightcheck=copyrightcheck,
            suppressprint=False  # Enable printing for debugging
        )
        
        # Run the upload
        logger.info("Executing upload...")
        result = await asyncio.to_thread(upload_func)
        
        # Wait a bit to ensure TikTok processes the upload
        logger.info("Waiting for TikTok to process the upload...")
        await asyncio.sleep(10)
        
        return result

    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        if "Save draft" in str(e):
            logger.info("Video saved as draft")
            return "DRAFT"
        raise e

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
    start_time = time.time()
    
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
            logger.info(f"Processing hashtags: {hashtag_list}")

        try:
            # Upload to TikTok in a thread pool
            result = await run_upload_in_thread(
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
            
            if result == "DRAFT":
                return {
                    "success": True,
                    "message": "Video saved as draft",
                    "status": "draft",
                    "upload_time": f"{time.time() - start_time:.2f} seconds"
                }
            
            return {
                "success": True,
                "message": "Video uploaded successfully",
                "status": "posted",
                "upload_time": f"{time.time() - start_time:.2f} seconds"
            }

        except Exception as e:
            logger.error(f"Upload process error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

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