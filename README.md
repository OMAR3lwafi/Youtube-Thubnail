# YouTube Thumbnail Generator API

A FastAPI-based service that generates thumbnails from YouTube videos by analyzing audio peaks and extracting frames from the most impactful moments.

## Features

- YouTube video processing
- Audio peak detection
- Audio transcription using OpenAI Whisper
- Frame extraction from key moments
- Relevance AI integration ready

## Setup on Replit

1. Clone this repository to your Replit workspace
2. Install required system dependencies:
   ```bash
   apt-get update
   apt-get install -y ffmpeg
   ```

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key
   ```

5. Run the application:
   ```bash
   python api/main.py
   ```

## API Endpoints

### Process Video
```
POST /api/process-video
```
Request body:
```json
{
    "videoId": "youtube_video_id",
    "apiKey": "optional_relevance_ai_key"
}
```

### Health Check
```
GET /health
```

## Response Format

```json
{
    "videoId": "string",
    "title": "string",
    "transcription": "string",
    "wave_peaks": ["string"],
    "frame_url": "string",
    "timestamp": "string",
    "status": "string"
}
```

## Integration with Relevance AI

The API is designed to work seamlessly with Relevance AI. Simply include your Relevance AI API key in the request to enable integration.

## Error Handling

The API includes comprehensive error handling and logging. All errors are returned with appropriate HTTP status codes and detailed error messages.

## Development

To run the development server:
```bash
uvicorn api.main:app --reload
```

## License

MIT License 