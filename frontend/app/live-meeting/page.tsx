'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/services/api';

interface TranscriptSegment {
  text: string;
  speaker: string;
  language: string;
  timestamp: string;
}

export default function LiveMeetingPage() {
  const router = useRouter();
  const [meetingTitle, setMeetingTitle] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [sessionToken, setSessionToken] = useState('');
  const [meetingId, setMeetingId] = useState('');
  const [transcripts, setTranscripts] = useState<TranscriptSegment[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [duration, setDuration] = useState(0);
  const [audioSource, setAudioSource] = useState<'microphone' | 'tab' | 'both'>('both');

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const websocketRef = useRef<WebSocket | null>(null);
  const transcriptEndRef = useRef<HTMLDivElement>(null);
  const durationIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Auto-scroll to latest transcript
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcripts]);

  const startLiveMeeting = async () => {
    if (!meetingTitle.trim()) {
      setError('Please enter a meeting title');
      return;
    }

    try {
      setLoading(true);
      setError('');

      // Create live session on backend
      const response = await api.startLiveMeeting(meetingTitle);

      const { meeting_id, session_token } = response.data;
      setMeetingId(meeting_id);
      setSessionToken(session_token);

      // Request audio based on selected source
      let audioStream: MediaStream;
      
      if (audioSource === 'microphone') {
        console.log('Requesting microphone access...');
        audioStream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
        });
        console.log('Microphone access granted:', audioStream);
        console.log('Audio tracks:', audioStream.getAudioTracks());
      } else if (audioSource === 'both') {
        // Hybrid: Microphone + System Audio
        console.log('Requesting hybrid audio (microphone + system audio)...');
        
        // Get system audio FIRST (entire screen)
        const displayStream = await navigator.mediaDevices.getDisplayMedia({
          audio: {
            echoCancellation: false,
            noiseSuppression: false,
            autoGainControl: false,
            sampleRate: 48000,
            channelCount: 2,
          },
          video: {
            width: 1280,
            height: 720,
          },
        });
        
        console.log('Display stream:', displayStream);
        
        // Check if audio track exists in display stream
        const displayAudioTracks = displayStream.getAudioTracks();
        if (displayAudioTracks.length === 0) {
          throw new Error('No audio track found in screen share! Make sure to check "Share audio" when selecting entire screen.');
        }
        
        // Get microphone AFTER display (to avoid conflicts)
        let micStream: MediaStream | null = null;
        try {
          micStream = await navigator.mediaDevices.getUserMedia({
            audio: {
              echoCancellation: false, // Disable to capture your voice
              noiseSuppression: false, // Disable to get raw audio
              autoGainControl: true,
              sampleRate: 48000,
            },
          });
          console.log('Microphone stream:', micStream);
          console.log('Microphone audio tracks:', micStream.getAudioTracks());
          console.log('Microphone track settings:', micStream.getAudioTracks()[0]?.getSettings());
        } catch (micError: any) {
          console.warn('Failed to get microphone access:', micError);
          console.warn('Continuing with system audio only');
          // Continue without microphone if it fails
        }
        
        // Stop video track (we only need audio)
        const videoTracks = displayStream.getVideoTracks();
        videoTracks.forEach(track => {
          console.log('Stopping video track:', track.label);
          track.stop();
          displayStream.removeTrack(track);
        });
        
        // Create audio context to mix both streams
        const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
        const destination = audioContext.createMediaStreamDestination();
        
        // Add system audio
        const systemSource = audioContext.createMediaStreamSource(displayStream);
        const systemGain = audioContext.createGain();
        systemGain.gain.value = 1.2; // Boost system audio slightly
        systemSource.connect(systemGain);
        systemGain.connect(destination);
        console.log('System audio connected to mixer');
        
        // Add microphone audio if available
        if (micStream) {
          const micSource = audioContext.createMediaStreamSource(micStream);
          const micGain = audioContext.createGain();
          micGain.gain.value = 1.5; // Boost microphone more to ensure it's heard
          micSource.connect(micGain);
          micGain.connect(destination);
          console.log('Microphone audio connected to mixer with gain 1.5');
        }
        
        audioStream = destination.stream;
        console.log('Hybrid audio stream created with', audioStream.getAudioTracks().length, 'tracks');
        console.log('Final audio track settings:', audioStream.getAudioTracks()[0]?.getSettings());
        
        // Store original streams for cleanup
        const originalStreams = micStream ? [micStream, displayStream] : [displayStream];
        (audioStream as any)._originalStreams = originalStreams;
        (audioStream as any)._audioContext = audioContext;
      } else {
        // Tab/Screen audio only
        console.log('Requesting display media (entire screen recommended)...');
        const displayStream = await navigator.mediaDevices.getDisplayMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
            sampleRate: 48000,
            channelCount: 2,
          },
          video: {
            width: 1280,
            height: 720,
          },
        });

        console.log('Display media granted:', displayStream);
        console.log('All tracks:', displayStream.getTracks());
        console.log('Audio tracks:', displayStream.getAudioTracks());
        console.log('Video tracks:', displayStream.getVideoTracks());
        
        // Check if audio track exists
        const audioTracks = displayStream.getAudioTracks();
        if (audioTracks.length === 0) {
          throw new Error('No audio track found! Make sure to check "Share audio" and select "Entire Screen" (not Chrome Tab).');
        }
        
        console.log('Audio track settings:', audioTracks[0].getSettings());
        console.log('Audio track enabled:', audioTracks[0].enabled);
        console.log('Audio track muted:', audioTracks[0].muted);
        console.log('Audio track label:', audioTracks[0].label);
        
        // Stop video track (we only need audio)
        const videoTracks = displayStream.getVideoTracks();
        videoTracks.forEach(track => {
          console.log('Stopping video track:', track.label);
          track.stop();
          displayStream.removeTrack(track);
        });
        
        // Verify audio track is still active
        if (audioTracks[0].readyState !== 'live') {
          throw new Error('Audio track is not live! Current state: ' + audioTracks[0].readyState);
        }
        
        audioStream = displayStream;
        console.log('Final audio stream tracks:', audioStream.getTracks());
      }
      
      streamRef.current = audioStream;

      // Create audio context and media recorder
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(audioStream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);

      source.connect(processor);
      processor.connect(audioContext.destination);

      // Create media recorder for chunks
      const mediaRecorder = new MediaRecorder(audioStream, {
        mimeType: 'audio/webm;codecs=opus',
      });
      mediaRecorderRef.current = mediaRecorder;
      
      console.log('MediaRecorder created with MIME type:', mediaRecorder.mimeType);
      console.log('MediaRecorder state:', mediaRecorder.state);

      // Connect to WebSocket
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const backendHost = process.env.NEXT_PUBLIC_API_URL?.replace('http://', '').replace('https://', '') || 'localhost:8000';
      const token = localStorage.getItem('access_token');
      const wsUrl = `${wsProtocol}//${backendHost}/ws/live/${session_token}?token=${token}`;
      console.log('Connecting to WebSocket:', wsUrl);
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('WebSocket connected');
        setLoading(false);
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'connection_established') {
          console.log('Connection established:', data);
        } else if (data.type === 'transcript') {
          setTranscripts((prev) => [
            ...prev,
            {
              text: data.text,
              speaker: data.speaker,
              language: data.language,
              timestamp: data.timestamp,
            },
          ]);
        } else if (data.type === 'ping') {
          // Respond to ping with pong
          ws.send(JSON.stringify({ type: 'pong', timestamp: new Date().toISOString() }));
        } else if (data.type === 'error') {
          console.error('WebSocket error message:', data.message);
          setError(data.message);
        } else if (data.type === 'status') {
          console.log('Status:', data.status, data.message);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setError('WebSocket connection error');
      };

      ws.onclose = () => {
        console.log('WebSocket closed');
      };

      websocketRef.current = ws;

      // Handle media recorder data
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0 && ws.readyState === WebSocket.OPEN) {
          console.log(`Sending audio chunk: ${event.data.size} bytes, type: ${event.data.type}`);
          ws.send(event.data);
        } else {
          console.warn(`Skipping audio chunk: size=${event.data.size}, wsState=${ws.readyState}`);
        }
      };
      
      mediaRecorder.onerror = (event: any) => {
        console.error('MediaRecorder error:', event.error);
        setError('Recording error: ' + event.error?.message);
      };
      
      mediaRecorder.onstart = () => {
        console.log('MediaRecorder started');
      };
      
      mediaRecorder.onstop = () => {
        console.log('MediaRecorder stopped');
      };

      // Send audio chunks every 3 seconds
      mediaRecorder.start(3000);

      setIsRecording(true);

      // Start duration timer
      const startTime = Date.now();
      durationIntervalRef.current = setInterval(() => {
        setDuration(Math.floor((Date.now() - startTime) / 1000));
      }, 1000);

      // Handle stream end (user stops sharing)
      audioStream.getTracks().forEach((track) => {
        track.onended = () => {
          stopLiveMeeting();
        };
      });
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to start live meeting');
      setLoading(false);
    }
  };

  const stopLiveMeeting = async () => {
    try {
      setIsRecording(false);

      // Stop media recorder
      if (mediaRecorderRef.current) {
        mediaRecorderRef.current.stop();
      }

      // Close WebSocket
      if (websocketRef.current) {
        websocketRef.current.close();
      }

      // Stop audio context
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }

      // Stop all tracks
      if (streamRef.current) {
        // Stop hybrid mode original streams if they exist
        const originalStreams = (streamRef.current as any)._originalStreams;
        const audioContext = (streamRef.current as any)._audioContext;
        
        if (originalStreams) {
          originalStreams.forEach((stream: MediaStream) => {
            stream.getTracks().forEach((track) => track.stop());
          });
        }
        
        if (audioContext) {
          audioContext.close();
        }
        
        // Stop main stream tracks
        streamRef.current.getTracks().forEach((track) => track.stop());
      }

      // Clear duration timer
      if (durationIntervalRef.current) {
        clearInterval(durationIntervalRef.current);
      }

      // End session on backend
      if (sessionToken && meetingId) {
        await api.endLiveMeeting(Number(meetingId), sessionToken);

        // Redirect to meeting details
        router.push(`/meeting/${meetingId}`);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to end live meeting');
    }
  };

  const downloadTranscript = () => {
    const content = transcripts
      .map((t) => `${t.timestamp} ${t.speaker}: ${t.text}`)
      .join('\n');

    const element = document.createElement('a');
    element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(content));
    element.setAttribute('download', `transcript-${meetingId}.txt`);
    element.style.display = 'none';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const formatTime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  if (!isRecording) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-8">
        <div className="max-w-2xl mx-auto">
          <div className="bg-white rounded-lg shadow-lg p-8">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">Live Meeting Capture</h1>
            <p className="text-gray-600 mb-8">
              Start capturing your meeting in real-time. The system will automatically transcribe and identify speakers.
            </p>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
                {error}
              </div>
            )}

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Meeting Title
                </label>
                <input
                  type="text"
                  value={meetingTitle}
                  onChange={(e) => setMeetingTitle(e.target.value)}
                  placeholder="e.g., Q1 Planning Meeting"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  disabled={loading}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Audio Source
                </label>
                <div className="grid grid-cols-3 gap-3">
                  <button
                    type="button"
                    onClick={() => setAudioSource('both')}
                    className={`px-4 py-3 rounded-lg border-2 transition ${
                      audioSource === 'both'
                        ? 'border-green-500 bg-green-50 text-green-700'
                        : 'border-gray-300 bg-white text-gray-700 hover:border-gray-400'
                    }`}
                    disabled={loading}
                  >
                    <div className="font-semibold">✨ Both</div>
                    <div className="text-xs mt-1">Recommended</div>
                  </button>
                  <button
                    type="button"
                    onClick={() => setAudioSource('microphone')}
                    className={`px-4 py-3 rounded-lg border-2 transition ${
                      audioSource === 'microphone'
                        ? 'border-blue-500 bg-blue-50 text-blue-700'
                        : 'border-gray-300 bg-white text-gray-700 hover:border-gray-400'
                    }`}
                    disabled={loading}
                  >
                    <div className="font-semibold">🎤 Mic Only</div>
                    <div className="text-xs mt-1">Your voice</div>
                  </button>
                  <button
                    type="button"
                    onClick={() => setAudioSource('tab')}
                    className={`px-4 py-3 rounded-lg border-2 transition ${
                      audioSource === 'tab'
                        ? 'border-blue-500 bg-blue-50 text-blue-700'
                        : 'border-gray-300 bg-white text-gray-700 hover:border-gray-400'
                    }`}
                    disabled={loading}
                  >
                    <div className="font-semibold">🖥️ Screen Only</div>
                    <div className="text-xs mt-1">Others' voices</div>
                  </button>
                </div>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h3 className="font-semibold text-blue-900 mb-2">How it works:</h3>
                {audioSource === 'both' ? (
                  <>
                    <ul className="text-sm text-blue-800 space-y-1 mb-3">
                      <li>✓ Click "Start Meeting" to begin</li>
                      <li>✓ Select "Entire Screen" and check "Share audio" (captures OTHERS)</li>
                      <li>✓ Allow microphone access when prompted (captures YOUR voice)</li>
                      <li>✓ Both you and other participants will be transcribed</li>
                      <li>✓ <strong>Best for Google Meet/Zoom meetings</strong></li>
                    </ul>
                    <div className="bg-yellow-50 border border-yellow-300 rounded p-2 text-xs text-yellow-800">
                      <strong>Note:</strong> If your microphone is already in use by the meeting app, 
                      the system will capture system audio only. For best results, use "Screen Only" mode 
                      and unmute yourself in the meeting.
                    </div>
                  </>
                ) : audioSource === 'microphone' ? (
                  <ul className="text-sm text-blue-800 space-y-1">
                    <li>✓ Click "Start Meeting" to begin</li>
                    <li>✓ Allow microphone access when prompted</li>
                    <li>✓ Speak clearly into your microphone</li>
                    <li>✓ Only YOUR voice will be transcribed</li>
                  </ul>
                ) : (
                  <>
                    <ul className="text-sm text-blue-800 space-y-1 mb-3">
                      <li>✓ Click "Start Meeting" to begin</li>
                      <li>✓ Select "Entire Screen" (not Chrome Tab)</li>
                      <li>✓ <strong>Important:</strong> Check "Share audio" in the dialog</li>
                      <li>✓ Make sure you are UNMUTED in the meeting</li>
                      <li>✓ All participants (including you) will be transcribed</li>
                    </ul>
                    <div className="bg-green-50 border border-green-300 rounded p-2 text-xs text-green-800">
                      <strong>Recommended:</strong> This mode captures all meeting audio including your voice 
                      when you speak in the meeting. Make sure to unmute yourself when speaking!
                    </div>
                  </>
                )}
              </div>

              <button
                onClick={startLiveMeeting}
                disabled={loading || !meetingTitle.trim()}
                className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-bold py-3 px-4 rounded-lg transition duration-200"
              >
                {loading ? 'Starting...' : 'Start Meeting'}
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 p-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="bg-gray-800 rounded-lg p-6 mb-6 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-white">{meetingTitle}</h1>
            <p className="text-gray-400 mt-2">Live Meeting in Progress</p>
          </div>
          <div className="text-right">
            <div className="text-4xl font-bold text-red-500">{formatTime(duration)}</div>
            <div className="text-gray-400 text-sm mt-2">Duration</div>
          </div>
        </div>

        {/* Transcript Display */}
        <div className="bg-gray-800 rounded-lg p-6 mb-6 h-96 overflow-y-auto">
          <h2 className="text-xl font-bold text-white mb-4">Live Transcript</h2>
          <div className="space-y-3">
            {transcripts.length === 0 ? (
              <p className="text-gray-400 text-center py-8">Waiting for audio...</p>
            ) : (
              transcripts.map((segment, index) => (
                <div key={index} className="bg-gray-700 rounded p-3">
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="font-semibold text-blue-400">{segment.speaker}</span>
                      <p className="text-gray-200 mt-1">{segment.text}</p>
                    </div>
                    <span className="text-xs text-gray-500 ml-4">{segment.timestamp}</span>
                  </div>
                </div>
              ))
            )}
            <div ref={transcriptEndRef} />
          </div>
        </div>

        {/* Controls */}
        <div className="flex gap-4">
          <button
            onClick={downloadTranscript}
            disabled={transcripts.length === 0}
            className="flex-1 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white font-bold py-3 px-4 rounded-lg transition duration-200"
          >
            Download Transcript
          </button>
          <button
            onClick={stopLiveMeeting}
            className="flex-1 bg-red-600 hover:bg-red-700 text-white font-bold py-3 px-4 rounded-lg transition duration-200"
          >
            End Meeting
          </button>
        </div>
      </div>
    </div>
  );
}
