"use client";

import React, { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { FiUploadCloud } from "react-icons/fi";

interface AudioUploadProps {
  onFileSelect: (file: File) => void;
  isLoading?: boolean;
  disabled?: boolean;
}

export const AudioUpload: React.FC<AudioUploadProps> = ({
  onFileSelect,
  isLoading = false,
  disabled = false,
}) => {
  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length > 0) {
        onFileSelect(acceptedFiles[0]);
      }
    },
    [onFileSelect]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "audio/*": [".wav", ".mp3", ".m4a"],
      "video/*": [".mp4"],
    },
    disabled: isLoading || disabled,
    maxFiles: 1,
  });

  return (
    <div
      {...getRootProps()}
      className={`
        relative border-2 border-dashed rounded-lg p-12 text-center
        transition-colors cursor-pointer
        ${
          isDragActive
            ? "border-blue-500 bg-blue-50"
            : "border-gray-300 bg-gray-50"
        }
        ${isLoading || disabled ? "opacity-50 cursor-not-allowed" : ""}
      `}
    >
      <input {...getInputProps()} />
      
      <div className="flex flex-col items-center justify-center">
        <FiUploadCloud className="w-12 h-12 text-gray-400 mb-4" />
        
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          {isDragActive ? "Drop your file here" : "Upload Meeting Audio"}
        </h3>
        
        <p className="text-sm text-gray-600 mb-2">
          Drag and drop your audio file here, or click to select
        </p>
        
        <p className="text-xs text-gray-500">
          Supported formats: WAV, MP3, M4A, MP4 (Max 2GB)
        </p>
      </div>
    </div>
  );
};

export default AudioUpload;
