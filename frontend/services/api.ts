import axios, { AxiosInstance, AxiosError } from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class APIClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      headers: {
        // Don't set Content-Type here - let axios/FormData handle it for files
        "Content-Type": "application/json",
      },
    });

    // Add token to requests
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem("access_token");
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      
      // Don't set Content-Type for FormData - let axios handle it
      if (config.data instanceof FormData) {
        delete config.headers["Content-Type"];
      }
      
      return config;
    });

    // Handle response errors
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          localStorage.removeItem("access_token");
          window.location.href = "/login";
        }
        return Promise.reject(error);
      }
    );
  }

  // Auth endpoints
  async register(email: string, password: string, fullName?: string) {
    return this.client.post("/api/v1/auth/register", {
      email,
      password,
      full_name: fullName,
    });
  }

  async login(email: string, password: string) {
    return this.client.post("/api/v1/auth/login", {
      email,
      password,
    });
  }

  async verifyToken(token: string) {
    return this.client.post("/api/v1/auth/verify-token", { token });
  }

  // Meeting endpoints
  async uploadMeeting(
    title: string,
    file: File,
    description?: string
  ) {
    const formData = new FormData();
    formData.append("title", title);
    formData.append("file", file);
    if (description) {
      formData.append("description", description);
    }

    return this.client.post("/api/v1/meetings/upload", formData);
  }

  async getMeetings(skip: number = 0, limit: number = 20) {
    return this.client.get("/api/v1/meetings", {
      params: { skip, limit },
    });
  }

  async getMeeting(meetingId: number) {
    return this.client.get(`/api/v1/meetings/${meetingId}`);
  }

  async updateMeeting(
    meetingId: number,
    data: { title?: string; description?: string }
  ) {
    return this.client.put(`/api/v1/meetings/${meetingId}`, data);
  }

  async deleteMeeting(meetingId: number) {
    return this.client.delete(`/api/v1/meetings/${meetingId}`);
  }

  // Transcript endpoints
  async getTranscript(meetingId: number) {
    return this.client.get(`/api/v1/meetings/${meetingId}/transcripts`);
  }

  async getSummary(meetingId: number) {
    return this.client.get(`/api/v1/meetings/${meetingId}/summary`);
  }

  async searchTranscript(
    meetingId: number,
    query: string,
    topK: number = 5
  ) {
    return this.client.get(`/api/v1/meetings/${meetingId}/search`, {
      params: { q: query, top_k: topK },
    });
  }

  // Export endpoints
  async downloadTranscriptPDF(meetingId: number) {
    return this.client.get(`/api/v1/meetings/${meetingId}/transcript/pdf`, {
      responseType: 'arraybuffer',
    });
  }

  async translateTranscript(meetingId: number, targetLanguage: string) {
    return this.client.post(`/api/v1/meetings/${meetingId}/transcript/translate`, {
      target_language: targetLanguage,
    });
  }

  async getSupportedLanguages() {
    return this.client.get("/api/v1/languages");
  }

  // Chatbot endpoints
  async askQuestion(meetingId: number, question: string) {
    return this.client.post(`/api/v1/meetings/${meetingId}/chat`, {
      question,
    });
  }

  async getChatHistory(meetingId: number) {
    return this.client.get(`/api/v1/meetings/${meetingId}/chat/history`);
  }

  async uploadDocument(meetingId: number, file: File) {
    const formData = new FormData();
    formData.append("file", file);
    return this.client.post(`/api/v1/meetings/${meetingId}/documents`, formData);
  }

  async getDocuments(meetingId: number) {
    return this.client.get(`/api/v1/meetings/${meetingId}/documents`);
  }

  async deleteDocument(meetingId: number, documentId: number) {
    return this.client.delete(`/api/v1/meetings/${meetingId}/documents/${documentId}`);
  }

  // Live meeting endpoints
  async startLiveMeeting(meetingTitle: string) {
    return this.client.post("/api/v1/meetings/start-live", {}, {
      params: { meeting_title: meetingTitle },
    });
  }

  async endLiveMeeting(meetingId: number, sessionToken: string) {
    return this.client.post(`/api/v1/meetings/${meetingId}/end`, {}, {
      params: { session_token: sessionToken },
    });
  }

  async getLiveStatus(meetingId: number, sessionToken: string) {
    return this.client.get(`/api/v1/meetings/${meetingId}/live-status`, {
      params: { session_token: sessionToken },
    });
  }
}

export const api = new APIClient();
