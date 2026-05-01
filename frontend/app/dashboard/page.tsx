"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/services/api";
import { FiPlus, FiLogOut, FiLoader } from "react-icons/fi";

interface Meeting {
  id: number;
  title: string;
  status: string;
  duration?: number;
  created_at: string;
}

export default function DashboardPage() {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const router = useRouter();

  useEffect(() => {
    loadMeetings();
  }, []);

  const loadMeetings = async () => {
    try {
      setIsLoading(true);
      const response = await api.getMeetings();
      setMeetings(response.data);
    } catch (err: any) {
      if (err.response?.status === 401) {
        router.push("/login");
      } else {
        setError("Failed to load meetings");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    router.push("/login");
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

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-3xl font-bold text-gray-900">
              AI Meeting Intelligence
            </h1>
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <FiLogOut className="w-5 h-5" />
              Logout
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Navigation Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <Link
            href="/upload"
            className="bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-lg p-6 hover:shadow-lg transition-shadow"
          >
            <div className="flex items-center gap-3">
              <FiPlus className="w-6 h-6" />
              <div>
                <h3 className="font-semibold">Upload Meeting</h3>
                <p className="text-sm opacity-90">Add audio file</p>
              </div>
            </div>
          </Link>

          <Link
            href="/live-meeting"
            className="bg-gradient-to-br from-red-500 to-red-600 text-white rounded-lg p-6 hover:shadow-lg transition-shadow"
          >
            <div className="flex items-center gap-3">
              <span className="text-2xl">🔴</span>
              <div>
                <h3 className="font-semibold">Live Meeting</h3>
                <p className="text-sm opacity-90">Capture live</p>
              </div>
            </div>
          </Link>
          
          <Link
            href="/summary"
            className="bg-gradient-to-br from-indigo-500 to-indigo-600 text-white rounded-lg p-6 hover:shadow-lg transition-shadow"
          >
            <div className="flex items-center gap-3">
              <span className="text-2xl">📊</span>
              <div>
                <h3 className="font-semibold">Summary</h3>
                <p className="text-sm opacity-90">View statistics</p>
              </div>
            </div>
          </Link>
          
          <Link
            href="/insights"
            className="bg-gradient-to-br from-purple-500 to-pink-600 text-white rounded-lg p-6 hover:shadow-lg transition-shadow"
          >
            <div className="flex items-center gap-3">
              <span className="text-2xl">💡</span>
              <div>
                <h3 className="font-semibold">Insights</h3>
                <p className="text-sm opacity-90">Technical details</p>
              </div>
            </div>
          </Link>
        </div>

        {/* Meetings List */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">Your Meetings</h2>
          </div>

          {isLoading ? (
            <div className="px-6 py-12 text-center">
              <FiLoader className="w-8 h-8 text-gray-400 mx-auto mb-2 animate-spin" />
              <p className="text-gray-500">Loading meetings...</p>
            </div>
          ) : error ? (
            <div className="px-6 py-4 bg-red-50 border-b border-red-200">
              <p className="text-red-800">{error}</p>
            </div>
          ) : meetings.length === 0 ? (
            <div className="px-6 py-12 text-center">
              <p className="text-gray-500 mb-4">No meetings yet</p>
              <Link
                href="/upload"
                className="text-blue-600 hover:text-blue-500 font-medium"
              >
                Upload your first meeting
              </Link>
            </div>
          ) : (
            <div className="divide-y">
              {meetings.map((meeting) => (
                <div
                  key={meeting.id}
                  onClick={() => router.push(`/meeting/${meeting.id}`)}
                  className="px-6 py-4 hover:bg-gray-50 cursor-pointer transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <h3 className="text-lg font-medium text-gray-900">
                        {meeting.title}
                      </h3>
                      <div className="mt-2 flex items-center gap-4 text-sm text-gray-500">
                        <span>{formatDate(meeting.created_at)}</span>
                        {meeting.duration && (
                          <span>{formatDuration(meeting.duration)}</span>
                        )}
                      </div>
                    </div>
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(
                        meeting.status
                      )}`}
                    >
                      {meeting.status.charAt(0).toUpperCase() +
                        meeting.status.slice(1)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
