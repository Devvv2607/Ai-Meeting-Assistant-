"use client";

import React, { useState, useEffect } from "react";
import { FiPlay, FiPause, FiVolume2 } from "react-icons/fi";

interface TranscriptSegment {
  id: number;
  speaker: string;
  text: string;
  start_time: number;
  end_time: number;
}

interface TranscriptViewerProps {
  segments: TranscriptSegment[];
  audioUrl?: string;
  onTimeClick?: (time: number) => void;
}

export const TranscriptViewer: React.FC<TranscriptViewerProps> = ({
  segments,
  audioUrl,
  onTimeClick,
}) => {
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [highlightedSegmentId, setHighlightedSegmentId] = useState<number | null>(
    null
  );

  useEffect(() => {
    // Highlight segment based on current time
    const activeSegment = segments.find(
      (s) => currentTime >= s.start_time && currentTime < s.end_time
    );
    setHighlightedSegmentId(activeSegment?.id || null);
  }, [currentTime, segments]);

  const formatTime = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${hours.toString().padStart(2, "0")}:${minutes
      .toString()
      .padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  const handleSegmentClick = (time: number) => {
    onTimeClick?.(time);
    setCurrentTime(time);
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow">
      {/* Audio Player */}
      {audioUrl && (
        <div className="p-4 border-b">
          <audio
            src={audioUrl}
            controls
            className="w-full h-10"
            onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
          />
        </div>
      )}

      {/* Transcript */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {segments.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            No transcript available yet
          </div>
        ) : (
          segments.map((segment) => (
            <div
              key={segment.id}
              onClick={() => handleSegmentClick(segment.start_time)}
              className={`
                p-4 rounded-lg cursor-pointer transition-colors
                ${
                  highlightedSegmentId === segment.id
                    ? "bg-blue-100 border-l-4 border-blue-500"
                    : "bg-gray-50 hover:bg-gray-100"
                }
              `}
            >
              <div className="flex items-start gap-3">
                <div className="text-xs text-gray-500 min-w-fit font-mono">
                  {formatTime(segment.start_time)}
                </div>
                <div className="flex-1">
                  <div className="font-semibold text-sm text-gray-700 mb-1">
                    {segment.speaker}
                  </div>
                  <p className="text-gray-800 text-sm leading-relaxed">
                    {segment.text}
                  </p>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default TranscriptViewer;
