'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

interface SummaryData {
  totalMeetings: number;
  totalTranscripts: number;
  totalDuration: number;
  averageTranscriptionTime: number;
  successRate: number;
  recentMeetings: Array<{
    id: number;
    title: string;
    duration: number;
    status: string;
    created_at: string;
  }>;
}

export default function SummaryPage() {
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSummary();
  }, []);

  const fetchSummary = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('access_token');
      
      if (!token) {
        setError('Not authenticated');
        return;
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/meetings`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error('Failed to fetch meetings');
      }

      const meetings = await response.json();

      // Calculate summary statistics
      const totalMeetings = meetings.length;
      const totalDuration = meetings.reduce((sum: number, m: any) => sum + (m.duration || 0), 0);
      const completedMeetings = meetings.filter((m: any) => m.status === 'completed').length;
      const successRate = totalMeetings > 0 ? (completedMeetings / totalMeetings) * 100 : 0;

      setSummary({
        totalMeetings,
        totalTranscripts: completedMeetings,
        totalDuration: Math.round(totalDuration),
        averageTranscriptionTime: totalMeetings > 0 ? Math.round(totalDuration / totalMeetings) : 0,
        successRate: Math.round(successRate),
        recentMeetings: meetings.slice(0, 5),
      });

      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load summary');
      console.error('Error fetching summary:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatDuration = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    if (minutes > 0) {
      return `${minutes}m ${secs}s`;
    }
    return `${secs}s`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-8">
        <div className="max-w-6xl mx-auto">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
            <p className="mt-4 text-gray-600">Loading summary...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">Summary Dashboard</h1>
          <p className="text-gray-600">Overview of your meeting transcriptions and statistics</p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {summary && (
          <>
            {/* Statistics Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              {/* Total Meetings */}
              <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 text-sm font-medium">Total Meetings</p>
                    <p className="text-3xl font-bold text-indigo-600 mt-2">{summary.totalMeetings}</p>
                  </div>
                  <div className="text-4xl text-indigo-200">📊</div>
                </div>
              </div>

              {/* Successful Transcriptions */}
              <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 text-sm font-medium">Transcriptions</p>
                    <p className="text-3xl font-bold text-green-600 mt-2">{summary.totalTranscripts}</p>
                  </div>
                  <div className="text-4xl text-green-200">✅</div>
                </div>
              </div>

              {/* Total Duration */}
              <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 text-sm font-medium">Total Duration</p>
                    <p className="text-3xl font-bold text-blue-600 mt-2">{formatDuration(summary.totalDuration)}</p>
                  </div>
                  <div className="text-4xl text-blue-200">⏱️</div>
                </div>
              </div>

              {/* Success Rate */}
              <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 text-sm font-medium">Success Rate</p>
                    <p className="text-3xl font-bold text-purple-600 mt-2">{summary.successRate}%</p>
                  </div>
                  <div className="text-4xl text-purple-200">🎯</div>
                </div>
              </div>
            </div>

            {/* Recent Meetings */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-2xl font-bold text-gray-800 mb-4">Recent Meetings</h2>
              
              {summary.recentMeetings.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="text-left py-3 px-4 font-semibold text-gray-700">Title</th>
                        <th className="text-left py-3 px-4 font-semibold text-gray-700">Duration</th>
                        <th className="text-left py-3 px-4 font-semibold text-gray-700">Status</th>
                        <th className="text-left py-3 px-4 font-semibold text-gray-700">Date</th>
                        <th className="text-left py-3 px-4 font-semibold text-gray-700">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {summary.recentMeetings.map((meeting) => (
                        <tr key={meeting.id} className="border-b border-gray-100 hover:bg-gray-50">
                          <td className="py-3 px-4 text-gray-800">{meeting.title}</td>
                          <td className="py-3 px-4 text-gray-600">{formatDuration(meeting.duration)}</td>
                          <td className="py-3 px-4">
                            <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                              meeting.status === 'completed' 
                                ? 'bg-green-100 text-green-800' 
                                : meeting.status === 'processing'
                                ? 'bg-yellow-100 text-yellow-800'
                                : 'bg-gray-100 text-gray-800'
                            }`}>
                              {meeting.status}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-gray-600 text-sm">{formatDate(meeting.created_at)}</td>
                          <td className="py-3 px-4">
                            <Link 
                              href={`/meeting/${meeting.id}`}
                              className="text-indigo-600 hover:text-indigo-800 font-medium"
                            >
                              View
                            </Link>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-gray-600 text-center py-8">No meetings yet. Start by uploading an audio file!</p>
              )}
            </div>

            {/* Action Buttons */}
            <div className="mt-8 flex gap-4 justify-center">
              <Link 
                href="/upload"
                className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 px-8 rounded-lg transition"
              >
                Upload New Meeting
              </Link>
              <Link 
                href="/dashboard"
                className="bg-gray-600 hover:bg-gray-700 text-white font-bold py-3 px-8 rounded-lg transition"
              >
                Back to Dashboard
              </Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
