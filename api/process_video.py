from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import subprocess
import os
import uuid
import yt_dlp
from pydub import AudioSegment
import openai
from moviepy.editor import VideoFileClip
from dotenv import load_dotenv

# ✅ تحميل المتغيرات من ملف .env
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

# ====== تعريف بيانات JSON المطلوبة من RelevanceAI ======
class VideoRequest(BaseModel):
    videoId: str

# ====== تحميل الفيديو من يوتيوب ======
def download_video(video_id, filename="video.mp4"):
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        "outtmpl": filename,
        "format": "bestvideo+bestaudio",
        "quiet": True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return filename

# ====== تحليل الذروة الصوتية ======
def extract_audio_peaks(audio_path):
    audio = AudioSegment.from_file(audio_path)
    duration_seconds = int(audio.duration_seconds)
    loudness_scores = []
    for i in range(duration_seconds):
        segment = audio[i * 1000: (i + 1) * 1000]
        loudness = segment.dBFS
        loudness_scores.append((loudness, i))
    top_peaks = sorted(loudness_scores, reverse=True)[:5]
    return [format_time(p[1]) for p in top_peaks]

def format_time(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

# ====== استخراج صورة من لحظة معينة ======
def extract_frame(video_path, time_str, output_path="frame.jpg"):
    clip = VideoFileClip(video_path)
    h, m, s = map(int, time_str.split(":"))
    frame_time = h * 3600 + m * 60 + s
    clip.save_frame(output_path, t=frame_time)
    return output_path

# ====== تحويل الصوت إلى نص باستخدام Whisper API ======
def transcribe_audio(audio_path):
    with open(audio_path, "rb") as f:
        transcript = openai.Audio.transcribe("whisper-1", f)
    return transcript["text"]

# ====== نقطة البداية للـ API ======
@app.post("/api/process-video")
async def process_video(data: VideoRequest):
    video_id = data.videoId
    video_file = f"{uuid.uuid4()}.mp4"
    audio_file = "temp.mp3"
    frame_file = "frame.jpg"

    try:
        # 1. تحميل الفيديو
        download_video(video_id, filename=video_file)

        # 2. استخراج الصوت بصيغة MP3
        subprocess.run(["ffmpeg", "-i", video_file, "-q:a", "0", "-map", "a", audio_file, "-y"], check=True)

        # 3. تحليل الصوت لأعلى لحظات
        peaks = extract_audio_peaks(audio_file)

        # 4. تحويل الصوت إلى نص
        transcription = transcribe_audio(audio_file)

        # 5. التقاط صورة من أقوى لحظة
        frame_time = peaks[0]
        extract_frame(video_file, frame_time, frame_file)

        # 6. رفع مؤقت (تحديث لاحقًا)
        frame_url = f"https://your-cdn.com/temp/{frame_file}"  # replace later with actual hosting

        # 7. تنظيف الملفات
        os.remove(video_file)
        os.remove(audio_file)

        return {
            "title": f"https://www.youtube.com/watch?v={video_id}",
            "transcription": transcription,
            "wave_peaks": peaks,
            "frame_url": frame_url
        }

    except Exception as e:
        return {"error": str(e)}
