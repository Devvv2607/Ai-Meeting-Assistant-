"use client";

import React, { useState } from "react";
import { FiSearch } from "react-icons/fi";

interface SearchResult {
  transcript_id: number;
  speaker: string;
  text: string;
  start_time: number;
  end_time: number;
  relevance_score: number;
}

interface SearchBarProps {
  onSearch: (query: string) => Promise<SearchResult[]>;
  onResultClick?: (result: SearchResult) => void;
  isLoading?: boolean;
  placeholder?: string;
}

export const SearchBar: React.FC<SearchBarProps> = ({
  onSearch,
  onResultClick,
  isLoading = false,
  placeholder = "Search transcript...",
}) => {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showResults, setShowResults] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) {
      setResults([]);
      return;
    }

    setIsSearching(true);
    try {
      const searchResults = await onSearch(query);
      setResults(searchResults);
      setShowResults(true);
    } catch (error) {
      console.error("Search error:", error);
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const handleResultClick = (result: SearchResult) => {
    onResultClick?.(result);
    setShowResults(false);
  };

  const formatTime = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${minutes}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div className="relative w-full">
      <form onSubmit={handleSearch} className="flex items-center gap-2">
        <div className="relative flex-1">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={placeholder}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 pr-10"
            disabled={isLoading || isSearching}
          />
          <button
            type="submit"
            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
            disabled={isLoading || isSearching}
          >
            <FiSearch className="w-5 h-5" />
          </button>
        </div>
      </form>

      {/* Search Results */}
      {showResults && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-white border border-gray-300 rounded-lg shadow-lg z-10 max-h-96 overflow-y-auto">
          {results.length === 0 ? (
            <div className="p-4 text-center text-gray-500">
              {isSearching ? "Searching..." : "No results found"}
            </div>
          ) : (
            <div className="divide-y">
              {results.map((result) => (
                <div
                  key={result.transcript_id}
                  onClick={() => handleResultClick(result)}
                  className="p-4 hover:bg-gray-50 cursor-pointer transition-colors"
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <span className="font-semibold text-sm text-gray-900">
                      {result.speaker}
                    </span>
                    <span className="text-xs text-gray-500">
                      {formatTime(result.start_time)}
                    </span>
                  </div>
                  <p className="text-sm text-gray-700 line-clamp-2 mb-2">
                    {result.text}
                  </p>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-500">
                      Relevance: {(result.relevance_score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SearchBar;
