from flask import Flask, request, jsonify
import os
from werkzeug.utils import secure_filename
from tiktokautouploader import upload_tiktok

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = '/app/uploads'
COOKIES_FOLDER = '/app/cookies'
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'wmv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_video():
    try:
        # Check if video file is present
        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided'}), 400
        
        video = request.files['video']
        if video.filename == '':
            return jsonify({'error': 'No selected video file'}), 400
            
        if not allowed_file(video.filename):
            return jsonify({'error': 'Invalid file type'}), 400

        # Get other parameters
        data = request.form
        accountname = data.get('accountname')
        if not accountname:
            return jsonify({'error': 'Account name is required'}), 400

        description = data.get('description', '')
        hashtags = data.get('hashtags', '').split(',') if data.get('hashtags') else None
        sound_name = data.get('sound_name')
        sound_aud_vol = data.get('sound_aud_vol', 'mix')
        schedule = data.get('schedule')
        copyrightcheck = data.get('copyrightcheck', 'false').lower() == 'true'

        # Save video temporarily
        video_path = os.path.join(UPLOAD_FOLDER, secure_filename(video.filename))
        video.save(video_path)

        # Upload to TikTok
        upload_tiktok(
            video=video_path,
            description=description,
            accountname=accountname,
            hashtags=hashtags,
            sound_name=sound_name,
            sound_aud_vol=sound_aud_vol,
            schedule=schedule,
            copyrightcheck=copyrightcheck,
            suppressprint=True
        )

        # Clean up
        os.remove(video_path)

        return jsonify({'message': 'Video uploaded successfully'}), 200

    except Exception as e:
        if os.path.exists(video_path):
            os.remove(video_path)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(COOKIES_FOLDER, exist_ok=True)
    app.run(host='0.0.0.0', port=5000)
