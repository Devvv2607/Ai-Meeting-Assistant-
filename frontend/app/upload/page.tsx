"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import AudioUpload from "@/components/AudioUpload";
import { api } from "@/services/api";
import { FiArrowLeft } from "react-icons/fi";
import Link from "next/link";

export default function UploadPage() {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const router = useRouter();

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    setError("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess(false);

    if (!title.trim()) {
      setError("Please enter a meeting title");
      return;
    }

    if (!selectedFile) {
      setError("Please select an audio file");
      return;
    }

    setIsLoading(true);

    try {
      const response = await api.uploadMeeting(title, selectedFile, description);
      setSuccess(true);
      setTitle("");
      setDescription("");
      setSelectedFile(null);

      // Redirect to meeting after 2 seconds
      setTimeout(() => {
        router.push(`/meeting/${response.data.id}`);
      }, 2000);
    } catch (err: any) {
      setError(
        err.response?.data?.detail || "Upload failed. Please try again."
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-500 mb-4"
          >
            <FiArrowLeft className="w-5 h-5" />
            Back to Dashboard
          </Link>
          <h1 className="text-3xl font-bold text-gray-900">Upload Meeting</h1>
          <p className="text-gray-600 mt-2">
            Upload your meeting audio file to get started
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="rounded-md bg-red-50 p-4 border border-red-200">
              <p className="text-sm font-medium text-red-800">{error}</p>
            </div>
          )}

          {success && (
            <div className="rounded-md bg-green-50 p-4 border border-green-200">
              <p className="text-sm font-medium text-green-800">
                Upload successful! Redirecting...
              </p>
            </div>
          )}

          {/* Title Input */}
          <div>
            <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-2">
              Meeting Title *
            </label>
            <input
              id="title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g., Q4 Planning Meeting"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isLoading}
              required
            />
          </div>

          {/* Description Input */}
          <div>
            <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-2">
              Description (Optional)
            </label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Add a description of the meeting..."
              rows={4}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              disabled={isLoading}
            />
          </div>

          {/* Audio Upload */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Audio File *
            </label>
            <AudioUpload
              onFileSelect={handleFileSelect}
              isLoading={isLoading}
              disabled={isLoading}
            />
            {selectedFile && (
              <p className="text-sm text-gray-600 mt-2">
                Selected: <span className="font-medium">{selectedFile.name}</span>
              </p>
            )}
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isLoading || !selectedFile || !title.trim()}
            className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium"
          >
            {isLoading ? "Uploading..." : "Upload & Process"}
          </button>
        </form>
      </div>
    </div>
  );
}
