"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/services/api";
import TranscriptViewer from "@/components/TranscriptViewer";
import SummaryPanel from "@/components/SummaryPanel";
import SearchBar from "@/components/SearchBar";
import MeetingChatbot from "@/components/MeetingChatbot";
import { FiArrowLeft, FiLoader, FiDownload, FiGlobe } from "react-icons/fi";
import Link from "next/link";

interface Meeting {
  id: number;
  title: string;
  status: string;
  duration?: number;
  created_at: string;
}

interface Summary {
  summary?: string;
  key_points?: string[];
  action_items?: any[];
  sentiment?: string;
}

interface Transcript {
  id: number;
  speaker: string;
  text: string;
  start_time: number;
  end_time: number;
}

export default function MeetingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const meetingId = parseInt(params.id as string);

  const [meeting, setMeeting] = useState<Meeting | null>(null);
  const [transcript, setTranscript] = useState<Transcript[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [isLoadingMeeting, setIsLoadingMeeting] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<"transcript" | "summary">("transcript");
  const [selectedLanguage, setSelectedLanguage] = useState("en");
  const [translatedTranscript, setTranslatedTranscript] = useState<Transcript[]>([]);
  const [isTranslating, setIsTranslating] = useState(false);
  const [isDownloadingPDF, setIsDownloadingPDF] = useState(false);

  useEffect(() => {
    loadMeetingData();
  }, [meetingId]);

  const loadMeetingData = async () => {
    try {
      setIsLoadingMeeting(true);
      const [meetingRes, transcriptRes] = await Promise.all([
        api.getMeeting(meetingId),
        api.getTranscript(meetingId),
      ]);

      setMeeting(meetingRes.data);
      setTranscript(transcriptRes.data.segments || []);

      // Load summary if available
      try {
        const summaryRes = await api.getSummary(meetingId);
        setSummary(summaryRes.data);
      } catch (err: any) {
        // Summary might not be ready yet or needs to be generated
        console.log("Summary not available yet, will generate on demand");
      }
    } catch (err: any) {
      if (err.response?.status === 401) {
        router.push("/login");
      } else {
        setError("Failed to load meeting data");
      }
    } finally {
      setIsLoadingMeeting(false);
    }
  };

  const generateSummary = async () => {
    try {
      const summaryRes = await api.getSummary(meetingId);
      setSummary(summaryRes.data);
    } catch (err: any) {
      console.error("Failed to generate summary:", err);
      setError("Failed to generate summary");
    }
  };

  const handleSearch = async (query: string) => {
    try {
      const response = await api.searchTranscript(meetingId, query, 5);
      return response.data.results || [];
    } catch (err) {
      console.error("Search failed:", err);
      return [];
    }
  };

  const handleDownloadPDF = async () => {
    try {
      setIsDownloadingPDF(true);
      const response = await api.downloadTranscriptPDF(meetingId);
      
      // Create blob and download
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${meeting?.title || 'transcript'}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      console.error("Failed to download PDF:", err);
      setError("Failed to download PDF");
    } finally {
      setIsDownloadingPDF(false);
    }
  };

  const handleTranslate = async (language: string) => {
    if (language === "en") {
      setTranslatedTranscript([]);
      setSelectedLanguage(language);
      return;
    }

    try {
      setIsTranslating(true);
      const response = await api.translateTranscript(meetingId, language);
      setTranslatedTranscript(response.data.segments || []);
      setSelectedLanguage(language);
    } catch (err: any) {
      console.error("Failed to translate:", err);
      setError("Failed to translate transcript");
    } finally {
      setIsTranslating(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "bg-green-100 text-green-800";
      case "processing":
        return "bg-yellow-100 text-yellow-800";
      case "failed":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  const formatDuration = (seconds?: number) => {
    if (!seconds) return "-";
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    if (hours > 0) {
      return `${hours}h ${minutes % 60}m`;
    }
    return `${minutes}m`;
  };

  if (isLoadingMeeting) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <FiLoader className="w-12 h-12 text-gray-400 mx-auto mb-4 animate-spin" />
          <p className="text-gray-600">Loading meeting...</p>
        </div>
      </div>
    );
  }

  if (error || !meeting) {
    return (
      <div className="min-h-screen bg-gray-50 py-12 px-4">
        <div className="max-w-4xl mx-auto">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-500 mb-4"
          >
            <FiArrowLeft className="w-5 h-5" />
            Back to Dashboard
          </Link>
          <div className="rounded-md bg-red-50 p-4">
            <p className="text-red-800">{error || "Meeting not found"}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-500 mb-4"
          >
            <FiArrowLeft className="w-5 h-5" />
            Back to Dashboard
          </Link>
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">{meeting.title}</h1>
              <div className="mt-2 flex items-center gap-4 text-sm text-gray-600">
                <span>{formatDate(meeting.created_at)}</span>
                <span>{formatDuration(meeting.duration)}</span>
                <span
                  className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(
                    meeting.status
                  )}`}
                >
                  {meeting.status.charAt(0).toUpperCase() + meeting.status.slice(1)}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {meeting.status === "processing" && (
          <div className="mb-6 rounded-md bg-blue-50 p-4 border border-blue-200">
            <p className="text-blue-800">
              Your meeting is being processed. Check back shortly for transcript and summary.
            </p>
          </div>
        )}

        {/* Search Bar */}
        <div className="mb-6">
          <SearchBar onSearch={handleSearch} />
        </div>

        {/* Action Buttons */}
        <div className="mb-6 flex gap-4 flex-wrap">
          {/* PDF Download Button */}
          <button
            onClick={handleDownloadPDF}
            disabled={isDownloadingPDF}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            <FiDownload className="w-5 h-5" />
            {isDownloadingPDF ? "Downloading..." : "Download PDF"}
          </button>

          {/* Language Selector */}
          <div className="flex items-center gap-2">
            <FiGlobe className="w-5 h-5 text-gray-600" />
            <select
              value={selectedLanguage}
              onChange={(e) => handleTranslate(e.target.value)}
              disabled={isTranslating}
              className="px-4 py-2 border border-gray-300 rounded-lg bg-white text-gray-900 hover:border-gray-400 disabled:bg-gray-100 disabled:cursor-not-allowed transition-colors"
            >
              <option value="en">English</option>
              <option value="es">Spanish</option>
              <option value="fr">French</option>
              <option value="de">German</option>
              <option value="it">Italian</option>
              <option value="pt">Portuguese</option>
              <option value="ru">Russian</option>
              <option value="zh">Chinese</option>
              <option value="ja">Japanese</option>
              <option value="ko">Korean</option>
              <option value="ar">Arabic</option>
              <option value="hi">Hindi</option>
            </select>
            {isTranslating && <FiLoader className="w-5 h-5 text-blue-600 animate-spin" />}
          </div>
        </div>

        {/* Tabs */}
        <div className="mb-6 border-b border-gray-200">
          <div className="flex gap-8">
            <button
              onClick={() => setActiveTab("transcript")}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === "transcript"
                  ? "border-blue-500 text-blue-600"
                  : "border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300"
              }`}
            >
              Transcript ({transcript.length} segments)
            </button>
            <button
              onClick={() => setActiveTab("summary")}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === "summary"
                  ? "border-blue-500 text-blue-600"
                  : "border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300"
              }`}
            >
              Summary & Insights
            </button>
          </div>
        </div>

        {/* Tab Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            {activeTab === "transcript" && (
              <TranscriptViewer segments={translatedTranscript.length > 0 ? translatedTranscript : transcript} />
            )}
            {activeTab === "summary" && (
              <div className="space-y-6">
                <SummaryPanel
                  summary={summary?.summary}
                  keyPoints={summary?.key_points}
                  actionItems={summary?.action_items}
                  sentiment={summary?.sentiment}
                  isLoading={meeting.status === "processing"}
                  onGenerateSummary={generateSummary}
                />
                <MeetingChatbot meetingId={meetingId} />
              </div>
            )}
            )}
          </div>

          {/* Sidebar */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Quick Info
            </h3>
            <dl className="space-y-4">
              <div>
                <dt className="text-sm font-medium text-gray-600">Status</dt>
                <dd className="mt-1">
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(
                      meeting.status
                    )}`}
                  >
                    {meeting.status.charAt(0).toUpperCase() +
                      meeting.status.slice(1)}
                  </span>
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-600">Duration</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {formatDuration(meeting.duration)}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-600">Created</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {formatDate(meeting.created_at)}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-600">Segments</dt>
                <dd className="mt-1 text-sm text-gray-900">{transcript.length}</dd>
              </div>
            </dl>
          </div>
        </div>
      </div>
    </div>
  );
}
