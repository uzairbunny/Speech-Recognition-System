# Real-Time Speech Recognition & Speaker Identification System

A comprehensive system that transcribes live conversations and identifies speakers in real time, perfect for meetings, interviews, podcasts, and more.

## 🎯 Key Features

- **Real-Time Speech-to-Text**: Uses OpenAI Whisper for accurate multilingual transcription
- **Speaker Diarization**: Automatically identifies "Speaker 1", "Speaker 2", etc. using pyannote.audio
- **Speaker Recognition**: Optional matching of speakers to known voice profiles
- **Live Dashboard**: Real-time transcription display with speaker labels
- **Multiple Export Formats**: Download transcripts as TXT, SRT, JSON, CSV, or DOCX
- **WebSocket Integration**: Real-time communication between frontend and backend
- **MongoDB Storage**: Persistent storage of transcripts and speaker profiles

## 🛠 Tech Stack

### Backend
- **Python 3.8+** with FastAPI
- **PyTorch** for ML model inference
- **OpenAI Whisper** for speech recognition
- **pyannote.audio** for speaker diarization
- **MongoDB** with Motor for async database operations
- **WebSocket** for real-time communication

### Frontend
- **React 18** with Material-UI
- **WebSocket** client for real-time updates
- **Audio API** for microphone access
- **Responsive design** for mobile and desktop

## 📋 Prerequisites

Before setting up the system, ensure you have:

1. **Python 3.8 or higher**
2. **Node.js 16 or higher** (for frontend development)
3. **MongoDB** (Community Edition)
4. **Git** for version control
5. **Hugging Face account** (for pyannote models)

### Hardware Requirements
- **RAM**: 8GB minimum, 16GB recommended
- **GPU**: Optional but recommended (CUDA-compatible for faster processing)
- **Storage**: 5GB free space for models and data
- **Microphone**: For live transcription

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone <your-repository-url>
cd speech-recognition-system
```

### 2. Set Up Environment
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
# Important: Add your Hugging Face token for pyannote models
```

### 3. Install Dependencies
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies (if developing frontend)
cd frontend
npm install
cd ..
```

### 4. Start MongoDB
```bash
# On Windows
net start MongoDB

# On Linux/Mac
sudo systemctl start mongod
```

### 5. Run the Application
```bash
# For development (both backend and frontend)
python run.py dev

# For production
python run.py run
```

## 🔧 Detailed Setup

### Environment Configuration

Edit `.env` file with your settings:

```env
# Database Configuration
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=speech_recognition

# Audio Configuration
SAMPLE_RATE=16000
CHUNK_SIZE=1024
CHANNELS=1
FORMAT=int16

# Model Configuration
WHISPER_MODEL=base  # Options: tiny, base, small, medium, large
DIARIZATION_MODEL=pyannote/speaker-diarization-3.1
SPEAKER_EMBEDDING_MODEL=pyannote/embedding

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true

# Hugging Face Token (REQUIRED for pyannote models)
HUGGINGFACE_TOKEN=your-huggingface-token-here
```

### Getting a Hugging Face Token

1. Sign up at [Hugging Face](https://huggingface.co/)
2. Go to Settings → Access Tokens
3. Create a new token with read permissions
4. Add it to your `.env` file

### MongoDB Setup

#### Local Installation
```bash
# Ubuntu/Debian
sudo apt-get install -y mongodb

# macOS with Homebrew
brew tap mongodb/brew
brew install mongodb-community

# Windows
# Download from https://www.mongodb.com/try/download/community
```

#### Using Docker
```bash
# Start MongoDB in Docker
docker run --name mongodb -p 27017:27017 -d mongo:latest
```

## 📖 Usage Guide

### Starting a Live Transcription Session

1. **Open the Web Interface**
   - Navigate to `http://localhost:8000` (or your configured host/port)
   - Click "Live Transcription" in the navigation

2. **Create a New Session**
   - Enter a session name
   - Select language (optional, auto-detection available)
   - Click "Start Session"

3. **Grant Microphone Access**
   - Allow microphone permissions when prompted
   - Start speaking - transcription will appear in real-time

4. **View Results**
   - See real-time transcription with speaker identification
   - Speaker segments are color-coded for easy reading
   - Confidence scores indicate transcription quality

### Managing Speaker Profiles

1. **Add Known Speakers**
   - Go to "Speaker Management"
   - Click "Add Speaker"
   - Upload a clear audio sample (10-30 seconds)
   - Enter the speaker's name

2. **Speaker Recognition**
   - Once added, the system will try to match new speech to known speakers
   - Unknown speakers will still be labeled as "Speaker_1", "Speaker_2", etc.

### Exporting Transcripts

1. **From Live Sessions**
   - Click "Export" during or after a session
   - Choose format: TXT, SRT, JSON, CSV, or DOCX
   - Download the file

2. **From Session History**
   - Go to "Session History"
   - Find your session
   - Click "Export" and choose format

## 🔌 API Reference

### WebSocket Endpoints

Connect to: `ws://localhost:8000/ws/{connection_id}`

#### Message Types

**Start Session**
```json
{
  "type": "start_session",
  "session_name": "My Meeting",
  "language": "en"
}
```

**Send Audio Data**
```json
{
  "type": "audio_data",
  "session_id": "session_id_here",
  "audio_data": "base64_encoded_audio",
  "sample_rate": 16000,
  "language": "en"
}
```

**Add Speaker**
```json
{
  "type": "add_speaker",
  "speaker_name": "John Doe",
  "audio_sample": "base64_encoded_audio",
  "sample_rate": 16000
}
```

### REST API Endpoints

- `GET /api/sessions` - List all sessions
- `GET /api/sessions/{id}` - Get specific session
- `DELETE /api/sessions/{id}` - Delete session
- `POST /api/sessions/{id}/export` - Export session
- `GET /api/speakers` - List all speakers
- `POST /api/speakers` - Create speaker profile
- `DELETE /api/speakers/{id}` - Delete speaker

## 🎛 Configuration Options

### Model Selection

**Whisper Models** (accuracy vs speed trade-off):
- `tiny`: Fastest, least accurate
- `base`: Good balance (default)
- `small`: Better accuracy
- `medium`: Even better accuracy
- `large`: Best accuracy, slowest

**Audio Settings**:
- `SAMPLE_RATE`: 16000 Hz recommended
- `CHUNK_SIZE`: 1024 samples for real-time processing
- `CHANNELS`: 1 (mono) for better processing

### Performance Tuning

**For Better Accuracy**:
- Use larger Whisper models (`medium` or `large`)
- Increase audio quality/sample rate
- Ensure quiet recording environment
- Use external microphone for better audio

**For Better Speed**:
- Use smaller Whisper models (`tiny` or `base`)
- Enable GPU acceleration
- Reduce chunk size for faster processing
- Close other resource-intensive applications

## 🔍 Troubleshooting

### Common Issues

**"Failed to connect to MongoDB"**
- Ensure MongoDB is running: `sudo systemctl status mongod`
- Check connection string in `.env`
- Verify MongoDB is listening on port 27017

**"Failed to load diarization pipeline"**
- Verify Hugging Face token is correct
- Check internet connection
- Run: `huggingface-hub login` in terminal

**"Microphone not working"**
- Grant microphone permissions in browser
- Check if other applications are using the microphone
- Try a different browser (Chrome recommended)

**"WebSocket connection failed"**
- Check if backend server is running
- Verify port 8000 is not blocked by firewall
- Check browser console for error messages

**"ModuleNotFoundError" errors**
- Run: `pip install -r requirements.txt`
- Ensure you're using Python 3.8+
- Check if virtual environment is activated

### Performance Issues

**Slow Transcription**:
- Enable GPU acceleration if available
- Use smaller Whisper model
- Reduce audio quality if needed
- Check system resources (CPU/RAM usage)

**High Memory Usage**:
- Use smaller models
- Restart application periodically
- Monitor memory usage: `htop` or Task Manager

## 🧪 Development

### Project Structure
```
speech-recognition-system/
├── backend/                 # Python FastAPI backend
│   ├── main.py             # Main application
│   ├── config.py           # Configuration
│   ├── models.py           # Database models
│   ├── database.py         # Database operations
│   ├── speech_processor.py # Core ML processing
│   ├── websocket_manager.py# WebSocket handling
│   └── export_service.py   # Export functionality
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Page components
│   │   ├── services/       # API services
│   │   └── hooks/          # Custom hooks
│   └── package.json
├── models/                 # Saved ML models
├── data/                   # Audio data
├── exports/                # Exported transcripts
├── requirements.txt        # Python dependencies
├── run.py                 # Setup and run script
└── README.md              # This file
```

### Adding New Features

1. **Backend Changes**:
   - Add new endpoints in `main.py`
   - Update models in `models.py`
   - Add database operations in `database.py`

2. **Frontend Changes**:
   - Add components in `frontend/src/components/`
   - Create new pages in `frontend/src/pages/`
   - Update routing in `App.js`

3. **Testing**:
   - Add tests in `tests/` directory
   - Run tests: `pytest` for backend, `npm test` for frontend

## 📊 Use Cases

### Business Applications
- **Meeting Transcription**: Automatic meeting notes and action items
- **Customer Support**: Call center conversation analysis
- **Interviews**: HR interviews and candidate assessment
- **Legal**: Court proceedings and depositions

### Content Creation
- **Podcasts**: Automatic episode transcripts
- **YouTube**: Video subtitles and captions
- **Webinars**: Educational content transcription
- **Conferences**: Speaker session documentation

### Accessibility
- **Hearing Impaired**: Real-time captions for conversations
- **Language Learning**: Practice pronunciation and listening
- **Note-Taking**: Students and researchers

## 🔒 Security & Privacy

- **Local Processing**: All audio processing happens locally
- **Data Control**: You control where transcripts are stored
- **No Cloud Dependencies**: Works completely offline (except for initial model downloads)
- **Secure WebSocket**: Uses secure WebSocket connections (WSS) in production
- **Database Security**: MongoDB authentication recommended for production

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Add tests for new functionality
5. Ensure code follows project style guidelines
6. Commit changes: `git commit -m "Add feature description"`
7. Push to branch: `git push origin feature-name`
8. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **OpenAI Whisper** for excellent speech recognition
- **pyannote.audio** for speaker diarization capabilities
- **FastAPI** for the robust backend framework
- **React & Material-UI** for the frontend interface
- **MongoDB** for reliable data storage

## 📞 Support

For questions, issues, or contributions:

1. Check the [Issues](https://github.com/your-repo/issues) page
2. Create a new issue with detailed description
3. Include system information and error logs
4. Use appropriate labels for bug reports or feature requests

---

**Happy transcribing! 🎤→📝**
