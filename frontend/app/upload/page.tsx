'use client';

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useDropzone } from 'react-dropzone';
import { api } from '@/services/api';
import AppShell from '@/components/layout/AppShell';

export default function UploadPage() {
  const router = useRouter();
  const [title, setTitle] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState('');
  const [processing, setProcessing] = useState(false);

  const onDrop = useCallback((accepted: File[]) => {
    if (accepted.length > 0) {
      setFile(accepted[0]);
      setError('');
      if (!title) setTitle(accepted[0].name.replace(/\.[^/.]+$/, ''));
    }
  }, [title]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'audio/*': ['.mp3', '.wav', '.m4a'],
      'video/mp4': ['.mp4'],
    },
    maxFiles: 1,
    disabled: processing,
  });

  const handleUpload = async () => {
    if (!file) {
      setError('Please choose an audio or video file.');
      return;
    }
    if (!title.trim()) {
      setError('Please give this recording a title.');
      return;
    }
    setProcessing(true);
    setError('');
    try {
      const res = await api.uploadMeeting(title.trim(), file);
      const meetingId = res.data.id;
      router.push(`/meeting/${meetingId}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload failed. Please try again.');
      setProcessing(false);
    }
  };

  return (
    <AppShell>
      <div className="mx-auto max-w-2xl px-10 py-12">
        <h1 className="font-display text-[clamp(26px,3.5vw,36px)] font-medium tracking-[-0.01em] text-ink">
          Upload a recording
        </h1>
        <p className="mt-2 text-[15px] text-ink2">
          Drop in audio or video and Margin will transcribe and summarize it.
        </p>

        {error && (
          <div className="mt-6 rounded-lg border border-rec-border bg-rec-bg px-4 py-3 text-[14px] text-rec-ink">
            {error}
          </div>
        )}

        <div className="mt-7 space-y-4">
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Meeting title"
            disabled={processing}
            className="w-full rounded-md border border-line-input bg-surface px-4 py-3 text-[15px] text-ink outline-none transition-colors focus:border-line-hover placeholder:text-muted"
          />

          <div
            {...getRootProps()}
            className={`flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-14 text-center transition-colors ${
              isDragActive ? 'border-accent bg-accent-soft' : 'border-line-input bg-surface'
            }`}
          >
            <input {...getInputProps()} />
            <span className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-accent-soft text-[22px] text-accent-ink">
              ↑
            </span>
            {file ? (
              <div>
                <div className="font-display text-[17px] font-semibold text-ink">{file.name}</div>
                <div className="mt-1 font-mono text-[12px] text-muted3">
                  {(file.size / 1024 / 1024).toFixed(1)} MB
                </div>
              </div>
            ) : (
              <>
                <div className="font-display text-[17px] font-semibold text-ink">
                  {isDragActive ? 'Drop it here' : 'Drag a file here, or click to browse'}
                </div>
                <div className="mt-1 text-[13px] text-ink3">MP3, WAV, M4A or MP4</div>
              </>
            )}
          </div>

          <button
            onClick={handleUpload}
            disabled={processing}
            className="w-full rounded-md bg-accent px-5 py-3 text-[15px] font-semibold text-on-accent transition-transform hover:-translate-y-0.5 hover:bg-accent-hover disabled:opacity-50"
          >
            {processing ? 'Uploading…' : 'Transcribe & summarize'}
          </button>
        </div>
      </div>

      {/* Processing overlay */}
      {processing && (
        <div
          className="fixed inset-0 z-50 flex flex-col items-center justify-center backdrop-blur-sm"
          style={{ background: 'var(--overlay)' }}
        >
          <div className="h-12 w-12 rounded-full border-[3px] border-line-hover border-t-accent animate-spin-mg" />
          <div className="mt-5 font-display text-[20px] font-medium text-ink">
            Transcribing your recording…
          </div>
          <div className="mt-1.5 font-mono text-[12.5px] text-muted3">
            {file?.name} · {file ? (file.size / 1024 / 1024).toFixed(1) : 0} MB
          </div>
        </div>
      )}
    </AppShell>
  );
}
