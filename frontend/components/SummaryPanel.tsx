"use client";

import React from "react";
import { FiCheck, FiTrendingUp } from "react-icons/fi";

interface ActionItem {
  task: string;
  owner?: string;
  due_date?: string;
}

interface KeyPoint {
  text?: string;
  [key: string]: any;
}

interface SummaryPanelProps {
  summary?: string;
  keyPoints?: (KeyPoint | string)[];
  actionItems?: ActionItem[];
  sentiment?: string;
  isLoading?: boolean;
  onGenerateSummary?: () => void;
}

export const SummaryPanel: React.FC<SummaryPanelProps> = ({
  summary,
  keyPoints = [],
  actionItems = [],
  sentiment,
  isLoading = false,
  onGenerateSummary,
}) => {
  const getSentimentColor = (sentimentValue?: string) => {
    switch (sentimentValue?.toLowerCase()) {
      case "positive":
        return "bg-green-100 text-green-800 border-green-300";
      case "negative":
        return "bg-red-100 text-red-800 border-red-300";
      default:
        return "bg-yellow-100 text-yellow-800 border-yellow-300";
    }
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-gray-200 rounded w-3/4"></div>
          <div className="h-4 bg-gray-200 rounded w-full"></div>
          <div className="h-4 bg-gray-200 rounded w-2/3"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6 space-y-6">
      {/* Sentiment Badge */}
      {sentiment && (
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">Sentiment:</span>
          <span
            className={`
              px-3 py-1 rounded-full text-xs font-medium
              border ${getSentimentColor(sentiment)}
            `}
          >
            {sentiment.charAt(0).toUpperCase() + sentiment.slice(1)}
          </span>
        </div>
      )}

      {/* Summary */}
      {summary && (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Summary</h3>
          <p className="text-gray-700 leading-relaxed text-sm">{summary}</p>
        </div>
      )}

      {/* Key Points */}
      {keyPoints.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <FiTrendingUp className="w-5 h-5" />
            Key Points
          </h3>
          <ul className="space-y-2">
            {keyPoints.map((point, idx) => (
              <li
                key={idx}
                className="flex items-start gap-3 text-sm text-gray-700"
              >
                <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-blue-100 text-blue-600 text-xs font-bold flex-shrink-0 mt-0.5">
                  {idx + 1}
                </span>
                <span>
                  {typeof point === "string" ? point : point.text || JSON.stringify(point)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Action Items */}
      {actionItems.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <FiCheck className="w-5 h-5" />
            Action Items
          </h3>
          <ul className="space-y-3">
            {actionItems.map((item, idx) => (
              <li key={idx} className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                <div className="font-medium text-sm text-gray-900 mb-1">
                  {typeof item === "string" ? item : item.task || JSON.stringify(item)}
                </div>
                {typeof item !== "string" && (
                  <>
                    {item.owner && (
                      <div className="text-xs text-gray-600">
                        Owner: <span className="font-medium">{item.owner}</span>
                      </div>
                    )}
                    {item.due_date && (
                      <div className="text-xs text-gray-600">
                        Due: <span className="font-medium">{item.due_date}</span>
                      </div>
                    )}
                  </>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {!summary && keyPoints.length === 0 && actionItems.length === 0 && (
        <div className="text-center text-gray-500 py-8">
          <p className="mb-4">No summary available yet</p>
          {onGenerateSummary && (
            <button
              onClick={onGenerateSummary}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Generate Summary with AI
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default SummaryPanel;
