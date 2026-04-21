'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

interface InsightData {
  systemStatus: {
    backend: string;
    database: string;
    groqApi: string;
  };
  configuration: {
    provider: string;
    model: string;
    environment: string;
  };
  performance: {
    avgTranscriptionTime: number;
    avgFileSize: number;
    totalProcessed: number;
    completedMeetings: number;
    failedMeetings: number;
    processingMeetings: number;
  };
  features: string[];
  technicalStack: {
    frontend: string;
    backend: string;
    database: string;
    ai: string;
  };
  statistics: {
    totalMeetings: number;
    completedMeetings: number;
    failedMeetings: number;
    processingMeetings: number;
    totalDuration: number;
    averageDuration: number;
    summariesGenerated: number;
  };
}

export default function InsightsPage() {
  const [insights, setInsights] = useState<InsightData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchInsights();
  }, []);

  const fetchInsights = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('access_token');
      
      if (!token) {
        setError('Not authenticated');
        return;
      }

      // Fetch insights from backend
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/insights`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch insights: ${response.statusText}`);
      }

      const data = await response.json();
      setInsights(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load insights');
      console.error('Error fetching insights:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 to-pink-100 p-8">
        <div className="max-w-6xl mx-auto">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
            <p className="mt-4 text-gray-600">Loading insights...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-pink-100 p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">Technical Insights</h1>
          <p className="text-gray-600">System architecture, configuration, and performance metrics</p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {insights && (
          <>
            {/* System Status */}
            <div className="bg-white rounded-lg shadow-md p-6 mb-8">
              <h2 className="text-2xl font-bold text-gray-800 mb-4">System Status</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="border-l-4 border-blue-500 pl-4">
                  <p className="text-gray-600 font-medium">Backend Server</p>
                  <p className="text-xl font-bold text-blue-600 mt-2">{insights.systemStatus.backend}</p>
                  <p className="text-sm text-gray-500 mt-1">http://localhost:8000</p>
                </div>
                <div className="border-l-4 border-green-500 pl-4">
                  <p className="text-gray-600 font-medium">Database</p>
                  <p className="text-xl font-bold text-green-600 mt-2">{insights.systemStatus.database}</p>
                  <p className="text-sm text-gray-500 mt-1">PostgreSQL localhost:5433</p>
                </div>
                <div className="border-l-4 border-purple-500 pl-4">
                  <p className="text-gray-600 font-medium">Groq API</p>
                  <p className="text-xl font-bold text-purple-600 mt-2">{insights.systemStatus.groqApi}</p>
                  <p className="text-sm text-gray-500 mt-1">Whisper Model Active</p>
                </div>
              </div>
            </div>

            {/* Configuration */}
            <div className="bg-white rounded-lg shadow-md p-6 mb-8">
              <h2 className="text-2xl font-bold text-gray-800 mb-4">Configuration</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-gradient-to-br from-indigo-50 to-indigo-100 rounded-lg p-4">
                  <p className="text-gray-700 font-medium">AI Provider</p>
                  <p className="text-lg font-bold text-indigo-600 mt-2">{insights.configuration.provider}</p>
                </div>
                <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-4">
                  <p className="text-gray-700 font-medium">Transcription Model</p>
                  <p className="text-lg font-bold text-green-600 mt-2">{insights.configuration.model}</p>
                </div>
                <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-4">
                  <p className="text-gray-700 font-medium">Environment</p>
                  <p className="text-lg font-bold text-purple-600 mt-2">{insights.configuration.environment}</p>
                </div>
              </div>
            </div>

            {/* Performance Metrics */}
            <div className="bg-white rounded-lg shadow-md p-6 mb-8">
              <h2 className="text-2xl font-bold text-gray-800 mb-4">Performance Metrics</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="text-center">
                  <div className="text-4xl font-bold text-blue-600">{insights.performance.avgTranscriptionTime}s</div>
                  <p className="text-gray-600 mt-2">Avg Transcription Time</p>
                </div>
                <div className="text-center">
                  <div className="text-4xl font-bold text-green-600">{insights.performance.avgFileSize} MB</div>
                  <p className="text-gray-600 mt-2">Avg File Size</p>
                </div>
                <div className="text-center">
                  <div className="text-4xl font-bold text-purple-600">{insights.performance.totalProcessed}</div>
                  <p className="text-gray-600 mt-2">Total Processed</p>
                </div>
              </div>
            </div>

            {/* Statistics */}
            <div className="bg-white rounded-lg shadow-md p-6 mb-8">
              <h2 className="text-2xl font-bold text-gray-800 mb-4">Meeting Statistics</h2>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-blue-50 rounded-lg p-4 text-center">
                  <p className="text-gray-600 text-sm font-medium">Total Meetings</p>
                  <p className="text-3xl font-bold text-blue-600 mt-2">{insights.statistics.totalMeetings}</p>
                </div>
                <div className="bg-green-50 rounded-lg p-4 text-center">
                  <p className="text-gray-600 text-sm font-medium">Completed</p>
                  <p className="text-3xl font-bold text-green-600 mt-2">{insights.statistics.completedMeetings}</p>
                </div>
                <div className="bg-yellow-50 rounded-lg p-4 text-center">
                  <p className="text-gray-600 text-sm font-medium">Processing</p>
                  <p className="text-3xl font-bold text-yellow-600 mt-2">{insights.statistics.processingMeetings}</p>
                </div>
                <div className="bg-red-50 rounded-lg p-4 text-center">
                  <p className="text-gray-600 text-sm font-medium">Failed</p>
                  <p className="text-3xl font-bold text-red-600 mt-2">{insights.statistics.failedMeetings}</p>
                </div>
              </div>
            </div>

            {/* Technical Stack */}
            <div className="bg-white rounded-lg shadow-md p-6 mb-8">
              <h2 className="text-2xl font-bold text-gray-800 mb-4">Technical Stack</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="border border-gray-200 rounded-lg p-4">
                  <h3 className="font-bold text-gray-800 mb-2">Frontend</h3>
                  <p className="text-gray-600">{insights.technicalStack.frontend}</p>
                </div>
                <div className="border border-gray-200 rounded-lg p-4">
                  <h3 className="font-bold text-gray-800 mb-2">Backend</h3>
                  <p className="text-gray-600">{insights.technicalStack.backend}</p>
                </div>
                <div className="border border-gray-200 rounded-lg p-4">
                  <h3 className="font-bold text-gray-800 mb-2">Database</h3>
                  <p className="text-gray-600">{insights.technicalStack.database}</p>
                </div>
                <div className="border border-gray-200 rounded-lg p-4">
                  <h3 className="font-bold text-gray-800 mb-2">AI Service</h3>
                  <p className="text-gray-600">{insights.technicalStack.ai}</p>
                </div>
              </div>
            </div>

            {/* Features */}
            <div className="bg-white rounded-lg shadow-md p-6 mb-8">
              <h2 className="text-2xl font-bold text-gray-800 mb-4">Implemented Features</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {insights.features.map((feature, index) => (
                  <div key={index} className="flex items-center">
                    <span className="text-green-500 text-xl mr-3">✓</span>
                    <span className="text-gray-700">{feature}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-4 justify-center">
              <Link 
                href="/summary"
                className="bg-purple-600 hover:bg-purple-700 text-white font-bold py-3 px-8 rounded-lg transition"
              >
                View Summary
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
