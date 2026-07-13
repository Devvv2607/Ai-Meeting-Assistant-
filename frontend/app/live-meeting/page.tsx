'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/services/api';
import ThemeToggle from '@/components/theme/ThemeToggle';
import { fmtClock } from '@/lib/format';

interface LiveNote {
  time: string;
  text: string;
}

export default function LiveMeetingPage() {
  const router = useRouter();
  type AudioSource = 'microphone' | 'system' | 'both';
  // Always capture BOTH your microphone and the meeting's system/tab audio so the
  // transcript includes you and every other participant. No user-facing choice.
  const AUDIO_SOURCE: AudioSource = 'both';
  const [title, setTitle] = useState('Untitled meeting');
  const [started, setStarted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [elapsed, setElapsed] = useState(0);
  const [notes, setNotes] = useState<LiveNote[]>([]);
  const [noteInput, setNoteInput] = useState('');
  const [wsReady, setWsReady] = useState(false);
  // After End: the recording is transcribed + diarized server-side (1-2 min).
  const [processing, setProcessing] = useState(false);

  const meetingIdRef = useRef<number | null>(null);
  const sessionRef = useRef<string>('');
  const wsRef = useRef<WebSocket | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const extraStreamsRef = useRef<MediaStream[]>([]); // raw streams to stop (mic/display)
  const audioCtxRef = useRef<AudioContext | null>(null); // mixer for 'both'
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const segTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const recordingRef = useRef(false);
  const finishingRef = useRef(false);
  const finalizedRef = useRef(false);
  const recordStartMsRef = useRef(0); // when recording actually began (ws open)

  // Each segment is recorded as a STANDALONE WebM file (recorder restarted per
  // segment) so the backend can decode every one independently and append it to
  // the recording. Timeslice chunks would leave only the first chunk with a
  // WebM header.
  const SEGMENT_MS = 4000;

  // Authenticated route without AppShell — apply the same login guard.
  useEffect(() => {
    if (!localStorage.getItem('access_token')) router.replace('/login');
  }, [router]);

  // Cleanup on unmount
  useEffect(() => () => cleanup(), []);

  /** Stop all media capture (recorder, tracks, mixer) without navigating. */
  const stopMedia = () => {
    recordingRef.current = false;
    if (timerRef.current) clearInterval(timerRef.current);
    if (segTimeoutRef.current) clearTimeout(segTimeoutRef.current);
    try {
      if (recorderRef.current && recorderRef.current.state !== 'inactive') {
        recorderRef.current.stop();
      }
    } catch {}
    streamRef.current?.getTracks().forEach((t) => t.stop());
    extraStreamsRef.current.forEach((s) => s.getTracks().forEach((t) => t.stop()));
    extraStreamsRef.current = [];
    try {
      audioCtxRef.current?.close();
    } catch {}
    audioCtxRef.current = null;
  };

  /** Hard teardown used on unmount (no navigation, no end call). */
  const cleanup = () => {
    finishingRef.current = false;
    stopMedia();
    wsRef.current?.close();
  };

  /** Acquire an audio stream for the chosen source, stashing raw streams for cleanup. */
  const getAudioStream = async (source: AudioSource): Promise<MediaStream> => {
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error(
        'This browser blocks audio capture unless the page is served over HTTPS or http://localhost.'
      );
    }

    if (source === 'microphone') {
      const mic = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
      extraStreamsRef.current = [mic];
      return mic;
    }

    // 'system' or 'both' need the screen-share picker for system/tab audio.
    const display = await navigator.mediaDevices.getDisplayMedia({ audio: true, video: true });
    if (display.getAudioTracks().length === 0) {
      display.getTracks().forEach((t) => t.stop());
      throw new Error('No audio in the screen share. Re-share and tick "Share tab/system audio".');
    }
    // We only need audio.
    display.getVideoTracks().forEach((t) => {
      t.stop();
      display.removeTrack(t);
    });

    if (source === 'system') {
      extraStreamsRef.current = [display];
      return display;
    }

    // 'both' → mix microphone + system audio into one stream.
    let mic: MediaStream | null = null;
    try {
      mic = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: true },
      });
    } catch {
      // Mic unavailable (e.g. in use by the meeting app) — fall back to system only.
    }

    const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
    audioCtxRef.current = ctx;
    const dest = ctx.createMediaStreamDestination();

    const sysGain = ctx.createGain();
    sysGain.gain.value = 1.0;
    ctx.createMediaStreamSource(display).connect(sysGain);
    sysGain.connect(dest);

    if (mic) {
      const micGain = ctx.createGain();
      micGain.gain.value = 1.3;
      ctx.createMediaStreamSource(mic).connect(micGain);
      micGain.connect(dest);
    }

    extraStreamsRef.current = mic ? [display, mic] : [display];
    return dest.stream;
  };

  /** Record one standalone WebM segment, send its timing + bytes, then chain. */
  const recordSegment = () => {
    const stream = streamRef.current;
    if (!stream || !recordingRef.current) return;

    const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
    recorderRef.current = recorder;
    const parts: Blob[] = [];
    const segStartMs = Date.now();

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) parts.push(e.data);
    };
    recorder.onstop = () => {
      const blob = new Blob(parts, { type: 'audio/webm' });
      const ws = wsRef.current;
      if (blob.size > 0 && ws?.readyState === WebSocket.OPEN) {
        // Send the real timing this segment covers, then the audio bytes.
        const start = (segStartMs - recordStartMsRef.current) / 1000;
        const end = (Date.now() - recordStartMsRef.current) / 1000;
        ws.send(JSON.stringify({ type: 'segment', start, end }));
        ws.send(blob);
      }
      if (recordingRef.current) {
        recordSegment(); // next segment
      } else if (finishingRef.current) {
        finalize(); // last segment flushed — now tear down
      }
    };

    recorder.start();
    segTimeoutRef.current = setTimeout(() => {
      if (recorder.state !== 'inactive') recorder.stop();
    }, SEGMENT_MS);
  };

  const start = async () => {
    if (!title.trim()) {
      setError('Please name the meeting.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const res = await api.startLiveMeeting(title.trim());
      meetingIdRef.current = res.data.meeting_id;
      sessionRef.current = res.data.session_token;

      const stream = await getAudioStream(AUDIO_SOURCE);
      streamRef.current = stream;

      // WebSocket
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const host = apiUrl.replace(/^https?:\/\//, '');
      const proto = apiUrl.startsWith('https') ? 'wss' : 'ws';
      const token = localStorage.getItem('access_token');
      const ws = new WebSocket(`${proto}://${host}/ws/live/${sessionRef.current}?token=${token}`);
      wsRef.current = ws;

      // Only begin recording once the socket is OPEN, so no segment is dropped.
      ws.onopen = () => {
        setWsReady(true);
        recordStartMsRef.current = Date.now();
        recordingRef.current = true;
        recordSegment();
        const t0 = recordStartMsRef.current;
        timerRef.current = setInterval(
          () => setElapsed(Math.floor((Date.now() - t0) / 1000)),
          1000
        );
      };
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'ping') {
            ws.send(JSON.stringify({ type: 'pong', timestamp: new Date().toISOString() }));
          } else if (data.type === 'error') {
            setError(data.message || 'Live error');
          }
        } catch {}
      };
      ws.onerror = () => setError('WebSocket connection error.');

      // Show the live view immediately (transcript column shows "Connecting…").
      setStarted(true);
      setLoading(false);
    } catch (err: any) {
      // Failed before recording started — release anything already acquired.
      stopMedia();
      const name = err?.name || '';
      if (name === 'NotAllowedError' || name === 'SecurityError' || /permission denied/i.test(err?.message || '')) {
        setError(
          'Audio access was blocked. Allow the microphone (or screen audio) for this site in your browser, then press Start again.'
        );
      } else if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
        setError('No microphone was found. Connect a microphone and try again.');
      } else if (name === 'NotReadableError' || name === 'TrackStartError') {
        setError('Your microphone is already in use by another app (e.g. Zoom or Meet). Close it and try again.');
      } else {
        setError(err.response?.data?.detail || err.message || 'Could not start the meeting.');
      }
      setLoading(false);
    }
  };

  const addNote = () => {
    const t = noteInput.trim();
    if (!t) return;
    setNotes((n) => [...n, { time: fmtClock(elapsed), text: t }]);
    setNoteInput('');
  };

  /** Tear down media + socket, end the session, navigate. Runs once. */
  const finalize = async () => {
    if (finalizedRef.current) return;
    finalizedRef.current = true;

    stopMedia();
    wsRef.current?.close();

    const id = meetingIdRef.current;
    try {
      if (id) await api.endLiveMeeting(id, sessionRef.current);
    } catch {
      /* ignore */
    }
    router.push(id ? `/meeting/${id}` : '/dashboard');
  };

  const end = () => {
    // Show the processing screen while the recording is transcribed + diarized.
    setProcessing(true);
    // Stop the loop but let the in-progress segment flush before tearing down.
    finishingRef.current = true;
    recordingRef.current = false;
    if (timerRef.current) clearInterval(timerRef.current);
    if (segTimeoutRef.current) clearTimeout(segTimeoutRef.current);

    const rec = recorderRef.current;
    if (rec && rec.state !== 'inactive') {
      rec.stop(); // onstop sends the final segment, then calls finalize()
    } else {
      finalize();
    }
  };

  // ----- Pre-start gate -----
  if (!started) {
    return (
      <div className="min-h-screen bg-bg">
        <ThemeToggle />
        <div className="mx-auto max-w-lg px-8 py-20">
          <h1 className="font-display text-[clamp(28px,4vw,40px)] font-medium tracking-[-0.01em] text-ink">
            Start a live meeting
          </h1>
          <p className="mt-2 text-[15px] text-ink2">
            Margin captures notes as it happens — no bot in the call. It records
            <strong> you and everyone else</strong> in the meeting.
          </p>

          {error && (
            <div className="mt-6 rounded-lg border border-rec-border bg-rec-bg px-4 py-3 text-[14px] text-rec-ink">
              {error}
            </div>
          )}

          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Meeting title"
            className="mt-7 w-full rounded-md border border-line-input bg-surface px-4 py-3 text-[15px] text-ink outline-none focus:border-line-hover placeholder:text-muted"
          />

          <div className="mt-4 rounded-lg border border-accent-soft-border bg-accent-soft px-4 py-3 text-[12.5px] text-accent-ink">
            When you press Start you&apos;ll be asked to <strong>share your screen or the meeting tab</strong> —
            tick <strong>“Share tab/system audio”</strong> so other participants are captured. Your microphone
            is added automatically.
          </div>

          <button
            onClick={start}
            disabled={loading}
            className="mt-3 w-full rounded-md bg-accent px-5 py-3 text-[15px] font-semibold text-on-accent transition-transform hover:-translate-y-0.5 hover:bg-accent-hover disabled:opacity-50"
          >
            {loading ? 'Starting…' : 'Start meeting'}
          </button>
          <button
            onClick={() => router.push('/dashboard')}
            className="mt-3 w-full rounded-md border border-line-input px-5 py-3 text-[14.5px] font-semibold text-ink2 hover:border-line-hover"
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  // ----- Processing gate (after End) -----
  if (processing) {
    return (
      <div className="min-h-screen bg-bg">
        <ThemeToggle />
        <div className="mx-auto flex min-h-screen max-w-lg flex-col items-center justify-center px-8 text-center">
          <span className="h-10 w-10 rounded-full border-2 border-line-hover border-t-accent animate-spin-mg" />
          <h1 className="mt-7 font-display text-[clamp(24px,3.5vw,32px)] font-medium tracking-[-0.01em] text-ink">
            Processing your meeting…
          </h1>
          <p className="mt-3 text-[15px] leading-relaxed text-ink2">
            Transcribing the recording in English and identifying who spoke. This
            usually takes a minute or two — please keep this tab open.
          </p>
          <p className="mt-4 font-mono text-[12px] text-muted3">
            You&apos;ll be taken to the meeting when it&apos;s ready.
          </p>
        </div>
      </div>
    );
  }

  // ----- Live view -----
  return (
    <div className="flex h-screen flex-col bg-bg">
      <ThemeToggle />
      {/* Top bar */}
      <div className="flex items-center justify-between border-b border-line bg-panel2 px-8 py-4">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="max-w-[50%] bg-transparent font-display text-[24px] font-medium text-ink outline-none"
        />
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 rounded-pill border border-rec-border bg-rec-bg px-3.5 py-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-rec-ink animate-blink" />
            <span className="font-mono text-[12px] font-bold text-rec-ink">REC</span>
            <span className="font-mono text-[12px] text-rec-ink2">{fmtClock(elapsed)}</span>
          </div>
          <button
            onClick={end}
            className="rounded-md bg-accent px-5 py-2.5 text-[14px] font-semibold text-on-accent hover:bg-accent-hover"
          >
            End meeting
          </button>
        </div>
      </div>

      {error && (
        <div className="border-b border-rec-border bg-rec-bg px-8 py-2 text-[13px] text-rec-ink">{error}</div>
      )}

      {/* Two columns */}
      <div className="grid min-h-0 flex-1 grid-cols-[1.35fr_1fr]">
        {/* Recording status */}
        <div className="mgScroll flex flex-col items-center justify-center overflow-y-auto px-8 py-6 text-center">
          <div className="relative flex h-20 w-20 items-center justify-center">
            <span className="absolute inset-0 rounded-full bg-rec-bg animate-ping" />
            <span className="relative flex h-14 w-14 items-center justify-center rounded-full border border-rec-border bg-rec-bg">
              <span className="h-4 w-4 rounded-full bg-rec-ink animate-blink" />
            </span>
          </div>
          <h2 className="mt-7 font-display text-[22px] font-medium text-ink">
            {wsReady ? 'Recording your meeting' : 'Connecting…'}
          </h2>
          <p className="mt-2 max-w-sm text-[14.5px] leading-relaxed text-ink2">
            Capturing you and everyone else in the call. The full transcript and
            each speaker are identified <strong>after you press End</strong> — no
            live transcript, so nothing distracts you during the meeting.
          </p>
          <p className="mt-5 font-mono text-[12px] text-muted3">{fmtClock(elapsed)} elapsed</p>
        </div>

        {/* Notes */}
        <div className="mgScroll flex flex-col overflow-hidden border-l border-line bg-panel2">
          <div className="flex-1 overflow-y-auto px-6 py-6">
            <div className="mb-4 font-mono text-[11px] uppercase tracking-wider text-muted2">
              Margin notes
            </div>
            {notes.length === 0 ? (
              <p className="text-[13.5px] text-ink3">Key moments and your notes will appear here…</p>
            ) : (
              <div className="space-y-2.5">
                {notes.map((n, i) => (
                  <div
                    key={i}
                    className="flex gap-3 rounded-lg border border-line bg-surface3 px-3.5 py-3 animate-fadeUp"
                  >
                    <span className="mt-1.5 h-2 w-2 flex-shrink-0 rounded-full bg-lime" />
                    <div>
                      <span className="font-mono text-[11px] text-muted3">{n.time}</span>
                      <p className="text-[14px] leading-relaxed text-ink-soft">{n.text}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          <div className="border-t border-line p-4">
            <input
              value={noteInput}
              onChange={(e) => setNoteInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && addNote()}
              placeholder="Jot a thought…"
              className="w-full rounded-md border border-line-input bg-surface3 px-3.5 py-2.5 text-[14px] text-ink outline-none focus:border-line-hover placeholder:text-muted"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
