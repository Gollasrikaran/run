# app.py - Complete Flask API for Video to Audio Conversion
from flask import Flask, request, jsonify
import requests
import os
import tempfile
import base64
from moviepy.editor import VideoFileClip
import uuid
import shutil

app = Flask(__name__)

def download_from_drive(file_id, unique_id):
    """Download video from Google Drive"""
    try:
        url = f"https://drive.google.com/uc?export=download&id={file_id}"
        
        session = requests.Session()
        response = session.get(url, stream=True)
        
        # Handle large files with download warning
        for key, value in response.cookies.items():
            if key.startswith('download_warning'):
                params = {'confirm': value}
                response = session.get(url, params=params, stream=True)
                break
        
        if response.status_code != 200:
            return None
        
        # Save to temp directory
        video_path = f"/tmp/video_{unique_id}.mp4"
        with open(video_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        return video_path
    except Exception as e:
        print(f"Download error: {e}")
        return None

def convert_to_audio(video_path, unique_id):
    """Convert video to audio"""
    try:
        audio_path = f"/tmp/audio_{unique_id}.mp3"
        
        # Load video and extract audio
        video = VideoFileClip(video_path)
        audio = video.audio
        
        # Write audio file
        audio.write_audiofile(audio_path, verbose=False, logger=None)
        
        # Clean up video clip
        audio.close()
        video.close()
        
        return audio_path
    except Exception as e:
        print(f"Conversion error: {e}")
        return None

def cleanup_files(file_paths):
    """Clean up temporary files"""
    for path in file_paths:
        try:
            if os.path.exists(path):
                os.remove(path)
        except:
            pass

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'message': 'Video to Audio Converter API',
        'status': 'running',
        'usage': 'POST /convert with {"file_id": "your_google_drive_file_id"}'
    })

@app.route('/convert', methods=['POST'])
def convert_video_to_audio():
    try:
        # Get file_id from request
        data = request.json
        file_id = data.get('file_id')
        
        if not file_id:
            return jsonify({'error': 'file_id is required'}), 400
        
        # Generate unique identifier
        unique_id = str(uuid.uuid4())[:8]
        
        # Download video
        print(f"Downloading video: {file_id}")
        video_path = download_from_drive(file_id, unique_id)
        
        if not video_path:
            return jsonify({'error': 'Failed to download video from Google Drive'}), 500
        
        # Convert to audio
        print("Converting to audio...")
        audio_path = convert_to_audio(video_path, unique_id)
        
        if not audio_path:
            cleanup_files([video_path])
            return jsonify({'error': 'Failed to convert video to audio'}), 500
        
        # Read audio file and encode to base64
        try:
            with open(audio_path, 'rb') as f:
                audio_data = f.read()
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            file_size = len(audio_data)
        except Exception as e:
            cleanup_files([video_path, audio_path])
            return jsonify({'error': f'Failed to read audio file: {str(e)}'}), 500
        
        # Clean up temporary files
        cleanup_files([video_path, audio_path])
        
        return jsonify({
            'success': True,
            'file_id': file_id,
            'audio_base64': audio_base64,
            'file_size_bytes': file_size,
            'format': 'mp3'
        })
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    # Create temp directory if it doesn't exist
    os.makedirs('/tmp', exist_ok=True)
    
    # Run the app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)