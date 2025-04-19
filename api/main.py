from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import uuid
import logging
from datetime import datetime
import yt_dlp
from pydub import AudioSegment
import openai
from moviepy.editor import VideoFileClip
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI(
    title="YouTube Thumbnail Generator API",
    description="API for generating thumbnails from YouTube videos",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class VideoRequest(BaseModel):
    videoId: str
    apiKey: Optional[str] = None  # For Relevance AI integration

class VideoResponse(BaseModel):
    videoId: str
    title: str
    transcription: str
    wave_peaks: List[str]
    frame_url: str
    timestamp: str
    status: str

# Utility functions
def download_video(video_id: str, filename: str) -> str:
    """Download YouTube video using yt-dlp"""
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        ydl_opts = {
            "outtmpl": filename,
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "quiet": True,
            "no_warnings": True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return filename
    except Exception as e:
        logger.error(f"Error downloading video: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error downloading video: {str(e)}")

def extract_audio_peaks(audio_path: str) -> List[str]:
    """Extract audio peaks from the audio file"""
    try:
        audio = AudioSegment.from_file(audio_path)
        duration_seconds = int(audio.duration_seconds)
        loudness_scores = []
        
        for i in range(duration_seconds):
            segment = audio[i * 1000: (i + 1) * 1000]
            loudness = segment.dBFS
            loudness_scores.append((loudness, i))
        
        top_peaks = sorted(loudness_scores, reverse=True)[:5]
        return [format_time(p[1]) for p in top_peaks]
    except Exception as e:
        logger.error(f"Error extracting audio peaks: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error extracting audio peaks: {str(e)}")

def format_time(seconds: int) -> str:
    """Format seconds into HH:MM:SS"""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def extract_frame(video_path: str, time_str: str, output_path: str) -> str:
    """Extract frame from video at specific timestamp"""
    try:
        clip = VideoFileClip(video_path)
        h, m, s = map(int, time_str.split(":"))
        frame_time = h * 3600 + m * 60 + s
        clip.save_frame(output_path, t=frame_time)
        return output_path
    except Exception as e:
        logger.error(f"Error extracting frame: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error extracting frame: {str(e)}")

def transcribe_audio(audio_path: str) -> str:
    """Transcribe audio using OpenAI Whisper"""
    try:
        with open(audio_path, "rb") as f:
            transcript = openai.Audio.transcribe("whisper-1", f)
        return transcript["text"]
    except Exception as e:
        logger.error(f"Error transcribing audio: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error transcribing audio: {str(e)}")

# API Endpoints
@app.post("/api/process-video", response_model=VideoResponse)
async def process_video(data: VideoRequest):
    """Process YouTube video and generate thumbnail"""
    try:
        # Generate unique filenames
        video_file = f"temp_{uuid.uuid4()}.mp4"
        audio_file = f"temp_{uuid.uuid4()}.mp3"
        frame_file = f"temp_{uuid.uuid4()}.jpg"

        # Process video
        download_video(data.videoId, video_file)
        
        # Extract audio
        video = VideoFileClip(video_file)
        video.audio.write_audiofile(audio_file)
        
        # Get audio peaks
        peaks = extract_audio_peaks(audio_file)
        
        # Transcribe audio
        transcription = transcribe_audio(audio_file)
        
        # Extract frame from loudest moment
        frame_time = peaks[0]
        extract_frame(video_file, frame_time, frame_file)
        
        # Clean up temporary files
        for file in [video_file, audio_file]:
            if os.path.exists(file):
                os.remove(file)
        
        # Prepare response
        response = VideoResponse(
            videoId=data.videoId,
            title=f"https://www.youtube.com/watch?v={data.videoId}",
            transcription=transcription,
            wave_peaks=peaks,
            frame_url=f"/frames/{os.path.basename(frame_file)}",
            timestamp=datetime.utcnow().isoformat(),
            status="success"
        )
        
        return response

    except Exception as e:
        logger.error(f"Error processing video: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 