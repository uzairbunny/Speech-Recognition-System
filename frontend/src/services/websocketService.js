class WebSocketService {
  constructor() {
    this.ws = null;
    this.connectionId = null;
    this.listeners = new Map();
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
    this.isReconnecting = false;
  }

  connect() {
    return new Promise((resolve, reject) => {
      try {
        // Generate unique connection ID
        this.connectionId = 'client_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        
        // Determine WebSocket URL
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const wsUrl = `${protocol}//${host}/ws/${this.connectionId}`;
        
        console.log('Connecting to WebSocket:', wsUrl);
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = (event) => {
          console.log('WebSocket connected');
          this.reconnectAttempts = 0;
          this.isReconnecting = false;
          this.emit('connected', { connectionId: this.connectionId });
          resolve(event);
        };
        
        this.ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            console.log('Received message:', message);
            this.emit(message.type, message);
            this.emit('message', message);
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };
        
        this.ws.onclose = (event) => {
          console.log('WebSocket disconnected:', event.code, event.reason);
          this.emit('disconnected', event);
          
          // Attempt to reconnect if not intentionally closed
          if (!event.wasClean && !this.isReconnecting) {
            this.attemptReconnect();
          }
        };
        
        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          this.emit('error', error);
          reject(error);
        };
        
      } catch (error) {
        console.error('Error creating WebSocket connection:', error);
        reject(error);
      }
    });
  }

  attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('Max reconnect attempts reached');
      this.emit('reconnect_failed');
      return;
    }

    this.isReconnecting = true;
    this.reconnectAttempts++;
    
    console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
    this.emit('reconnecting', { attempt: this.reconnectAttempts });
    
    setTimeout(() => {
      this.connect().catch(() => {
        // Connection failed, will try again
      });
    }, this.reconnectDelay * this.reconnectAttempts);
  }

  disconnect() {
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
      this.connectionId = null;
    }
  }

  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(JSON.stringify(message));
        console.log('Sent message:', message);
      } catch (error) {
        console.error('Error sending message:', error);
      }
    } else {
      console.warn('WebSocket not connected. Cannot send message:', message);
    }
  }

  // Event listener management
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  off(event, callback) {
    if (this.listeners.has(event)) {
      const listeners = this.listeners.get(event);
      const index = listeners.indexOf(callback);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  }

  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error('Error in event listener:', error);
        }
      });
    }
  }

  // Transcription session methods
  startSession(sessionName, language = null) {
    this.send({
      type: 'start_session',
      session_name: sessionName,
      language: language
    });
  }

  joinSession(sessionId) {
    this.send({
      type: 'join_session',
      session_id: sessionId
    });
  }

  stopSession(sessionId) {
    this.send({
      type: 'stop_session',
      session_id: sessionId
    });
  }

  sendAudioData(sessionId, audioData, sampleRate = 16000, language = null) {
    // Convert audio data to base64
    let audioBase64;
    if (audioData instanceof ArrayBuffer) {
      const uint8Array = new Uint8Array(audioData);
      audioBase64 = btoa(String.fromCharCode.apply(null, uint8Array));
    } else if (audioData instanceof Uint8Array) {
      audioBase64 = btoa(String.fromCharCode.apply(null, audioData));
    } else {
      console.error('Unsupported audio data format');
      return;
    }

    this.send({
      type: 'audio_data',
      session_id: sessionId,
      audio_data: audioBase64,
      sample_rate: sampleRate,
      language: language
    });
  }

  addSpeaker(speakerName, audioSample, sampleRate = 16000) {
    // Convert audio sample to base64
    let audioBase64;
    if (audioSample instanceof ArrayBuffer) {
      const uint8Array = new Uint8Array(audioSample);
      audioBase64 = btoa(String.fromCharCode.apply(null, uint8Array));
    } else if (audioSample instanceof Uint8Array) {
      audioBase64 = btoa(String.fromCharCode.apply(null, audioSample));
    } else {
      console.error('Unsupported audio data format');
      return;
    }

    this.send({
      type: 'add_speaker',
      speaker_name: speakerName,
      audio_sample: audioBase64,
      sample_rate: sampleRate
    });
  }

  exportTranscript(sessionId, format = 'txt') {
    this.send({
      type: 'export_transcript',
      session_id: sessionId,
      format: format
    });
  }

  isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN;
  }

  getConnectionId() {
    return this.connectionId;
  }
}

// Create singleton instance
const websocketService = new WebSocketService();

export default websocketService;
