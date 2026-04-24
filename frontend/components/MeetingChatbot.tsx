"use client";

import React, { useState, useEffect, useRef } from "react";
import { api } from "@/services/api";
import { FiSend, FiUpload, FiX, FiLoader } from "react-icons/fi";

interface Message {
  id?: number;
  role: "user" | "assistant";
  content: string;
  sources?: any[];
  created_at?: string;
}

interface Document {
  id: number;
  filename: string;
  file_type: string;
  file_size: number;
  created_at: string;
}

interface MeetingChatbotProps {
  meetingId: number;
}

export default function MeetingChatbot({ meetingId }: MeetingChatbotProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isUploadingDoc, setIsUploadingDoc] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadChatHistory();
    loadDocuments();
  }, [meetingId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const loadChatHistory = async () => {
    try {
      const response = await api.getChatHistory(meetingId);
      setMessages(response.data.messages || []);
    } catch (err) {
      console.error("Failed to load chat history:", err);
    }
  };

  const loadDocuments = async () => {
    try {
      const response = await api.getDocuments(meetingId);
      setDocuments(response.data.documents || []);
    } catch (err) {
      console.error("Failed to load documents:", err);
    }
  };

  const handleSendMessage = async () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      role: "user",
      content: input,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await api.askQuestion(meetingId, input);

      const assistantMessage: Message = {
        role: "assistant",
        content: response.data.answer,
        sources: response.data.sources,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      console.error("Failed to get answer:", err);
      const errorMessage: Message = {
        role: "assistant",
        content: "Sorry, I encountered an error while processing your question. Please try again.",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDocumentUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploadingDoc(true);
    try {
      const response = await api.uploadDocument(meetingId, file);
      setDocuments((prev) => [...prev, response.data]);
      
      // Show success message
      const successMessage: Message = {
        role: "assistant",
        content: `Document "${file.name}" uploaded successfully. You can now ask questions about it!`,
      };
      setMessages((prev) => [...prev, successMessage]);
    } catch (err: any) {
      console.error("Failed to upload document:", err);
      const errorMessage: Message = {
        role: "assistant",
        content: "Failed to upload document. Please try again.",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsUploadingDoc(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleDeleteDocument = async (docId: number) => {
    try {
      await api.deleteDocument(meetingId, docId);
      setDocuments((prev) => prev.filter((doc) => doc.id !== docId));
    } catch (err) {
      console.error("Failed to delete document:", err);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-4 rounded-t-lg">
        <h3 className="text-lg font-semibold">Meeting Q&A Assistant</h3>
        <p className="text-sm text-blue-100">Ask questions about the meeting transcript</p>
      </div>

      {/* Documents Section */}
      {documents.length > 0 && (
        <div className="border-b border-gray-200 p-4 bg-gray-50">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">Uploaded Documents</h4>
          <div className="space-y-2">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center justify-between bg-white p-2 rounded border border-gray-200"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{doc.filename}</p>
                  <p className="text-xs text-gray-500">{formatFileSize(doc.file_size)}</p>
                </div>
                <button
                  onClick={() => handleDeleteDocument(doc.id)}
                  className="ml-2 p-1 text-gray-400 hover:text-red-600 transition-colors"
                  title="Delete document"
                >
                  <FiX className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-center">
            <div>
              <p className="text-gray-500 mb-2">No messages yet</p>
              <p className="text-sm text-gray-400">Ask a question about the meeting to get started</p>
            </div>
          </div>
        ) : (
          messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-xs lg:max-w-md xl:max-w-lg px-4 py-2 rounded-lg ${
                  message.role === "user"
                    ? "bg-blue-600 text-white rounded-br-none"
                    : "bg-gray-100 text-gray-900 rounded-bl-none"
                }`}
              >
                <p className="text-sm">{message.content}</p>

                {/* Sources */}
                {message.sources && message.sources.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-gray-300">
                    <p className="text-xs font-semibold mb-1">Sources:</p>
                    <div className="space-y-1">
                      {message.sources.map((source, idx) => (
                        <div key={idx} className="text-xs">
                          {source.type === "transcript" ? (
                            <p>
                              <span className="font-semibold">{source.speaker}</span> ({source.time})
                            </p>
                          ) : (
                            <p>
                              <span className="font-semibold">📄 {source.filename}</span>
                            </p>
                          )}
                          <p className="text-gray-600 italic">{source.text}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 text-gray-900 px-4 py-2 rounded-lg rounded-bl-none">
              <FiLoader className="w-5 h-5 animate-spin" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-200 p-4 bg-gray-50 rounded-b-lg">
        {/* Document Upload */}
        <div className="mb-3">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.txt"
            onChange={handleDocumentUpload}
            disabled={isUploadingDoc}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploadingDoc}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100 disabled:bg-gray-100 disabled:cursor-not-allowed transition-colors"
          >
            {isUploadingDoc ? (
              <>
                <FiLoader className="w-4 h-4 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <FiUpload className="w-4 h-4" />
                Upload Document (PDF, DOCX, TXT)
              </>
            )}
          </button>
        </div>

        {/* Message Input */}
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === "Enter" && handleSendMessage()}
            placeholder="Ask a question about the meeting..."
            disabled={isLoading}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
          />
          <button
            onClick={handleSendMessage}
            disabled={isLoading || !input.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            {isLoading ? (
              <FiLoader className="w-4 h-4 animate-spin" />
            ) : (
              <FiSend className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
