# Implementation Tasks: Advanced Meeting Intelligence Features

## Phase 1: PDF Export & Multilingual Support

### Task 1: PDF Export Service
- [x] 1.1 Create `backend/app/services/pdf_service.py`
  - [ ] Implement `PDFService` class
  - [ ] Add `generate_transcript_pdf()` method
  - [ ] Add `_format_transcript_segment()` helper
  - [ ] Add header with meeting metadata
  - [ ] Add footer with page numbers
  - [ ] Test with various transcript lengths

- [x] 1.2 Create PDF export endpoint
  - [ ] Add route in `backend/app/routers/export_routes.py`
  - [ ] Implement `GET /api/v1/meetings/{meeting_id}/transcript/pdf`
  - [ ] Add authentication check
  - [ ] Add error handling (404, 500)
  - [ ] Test endpoint with Postman

- [ ] 1.3 Frontend PDF download button
  - [ ] Create `frontend/components/TranscriptExport.tsx`
  - [ ] Add download button to meeting detail page
  - [ ] Implement download handler
  - [ ] Add loading state
  - [ ] Test download functionality

### Task 2: Translation Service
- [x] 2.1 Create translation service
  - [ ] Create `backend/app/services/translation_service.py`
  - [ ] Implement `TranslationService` class
  - [ ] Add `translate_transcript()` method
  - [ ] Add `translate_text()` method
  - [ ] Implement caching mechanism
  - [ ] Support 10+ languages

- [x] 2.2 Create translation endpoint
  - [ ] Add route in `backend/app/routers/translation_routes.py`
  - [ ] Implement `POST /api/v1/meetings/{meeting_id}/transcript/translate`
  - [ ] Add language validation
  - [ ] Add caching headers
  - [ ] Test with multiple languages

- [ ] 2.3 Frontend language selector
  - [ ] Create `frontend/components/LanguageSelector.tsx`
  - [ ] Add language dropdown
  - [ ] Implement translation handler
  - [ ] Add loading state
  - [ ] Display translated transcript
  - [ ] Test with different languages

### Task 3: Database Updates for Phase 1
- [ ] 3.1 Create translation cache table
  - [ ] Add `translation_cache` table
  - [ ] Add indexes for performance
  - [ ] Run migration

- [ ] 3.2 Update requirements.txt
  - [ ] Add `reportlab` for PDF generation
  - [ ] Add `google-cloud-translate` or `deepl` for translation
  - [ ] Add `PyPDF2` for PDF utilities

## Phase 2: Meeting Q&A Chatbot

### Task 4: Chatbot Service
- [ ] 4.1 Create chatbot service
  - [ ] Create `backend/app/services/chatbot_service.py`
  - [ ] Implement `ChatbotService` class
  - [ ] Add `answer_question()` method
  - [ ] Add `_build_context()` method
  - [ ] Add `_extract_sources()` method
  - [ ] Implement prompt engineering for context

- [ ] 4.2 Create chat message model
  - [ ] Create `backend/app/models/chat_message.py`
  - [ ] Define `ChatMessage` table
  - [ ] Add relationships to Meeting and User
  - [ ] Add indexes for queries

- [ ] 4.3 Create chatbot endpoints
  - [ ] Create `backend/app/routers/chatbot_routes.py`
  - [ ] Implement `POST /api/v1/meetings/{meeting_id}/chat`
  - [ ] Implement `GET /api/v1/meetings/{meeting_id}/chat/history`
  - [ ] Implement `DELETE /api/v1/meetings/{meeting_id}/chat/history`
  - [ ] Add rate limiting
  - [ ] Add error handling

- [ ] 4.4 Frontend chatbot component
  - [ ] Create `frontend/components/MeetingChatbot.tsx`
  - [ ] Add message display area
  - [ ] Add input field
  - [ ] Implement send message handler
  - [ ] Add loading state
  - [ ] Display sources/citations
  - [ ] Add chat history display

### Task 5: Chatbot Integration
- [ ] 5.1 Integrate chatbot into summary page
  - [ ] Add chatbot component to `frontend/app/summary/page.tsx`
  - [ ] Add chatbot component to `frontend/app/insights/page.tsx`
  - [ ] Style chatbot interface
  - [ ] Test integration

- [ ] 5.2 Test chatbot functionality
  - [ ] Test with various questions
  - [ ] Test context retrieval
  - [ ] Test source extraction
  - [ ] Test error handling
  - [ ] Test rate limiting

## Phase 3: Document Context Upload

### Task 6: Document Service
- [ ] 6.1 Create document model
  - [ ] Create `backend/app/models/document.py`
  - [ ] Define `Document` table
  - [ ] Add relationships to Meeting and User
  - [ ] Add indexes

- [ ] 6.2 Create document processing service
  - [ ] Create `backend/app/services/document_service.py`
  - [ ] Implement `DocumentService` class
  - [ ] Add `process_document()` method
  - [ ] Add `extract_text()` method for PDF
  - [ ] Add `extract_text()` method for DOCX
  - [ ] Add `extract_text()` method for TXT
  - [ ] Add file validation
  - [ ] Add malware scanning (optional)

- [ ] 6.3 Create document endpoints
  - [ ] Create `backend/app/routers/document_routes.py`
  - [ ] Implement `POST /api/v1/meetings/{meeting_id}/documents`
  - [ ] Implement `GET /api/v1/meetings/{meeting_id}/documents`
  - [ ] Implement `DELETE /api/v1/meetings/{meeting_id}/documents/{doc_id}`
  - [ ] Add file upload handling
  - [ ] Add error handling

### Task 7: Document Upload UI
- [ ] 7.1 Create document upload component
  - [ ] Create `frontend/components/DocumentUpload.tsx`
  - [ ] Add file input
  - [ ] Add drag-and-drop support
  - [ ] Add file validation
  - [ ] Add upload progress
  - [ ] Add error handling

- [ ] 7.2 Create document list component
  - [ ] Create `frontend/components/DocumentList.tsx`
  - [ ] Display uploaded documents
  - [ ] Add delete button
  - [ ] Add file preview (optional)
  - [ ] Add search/filter

### Task 8: Enhanced Chatbot with Documents
- [ ] 8.1 Update chatbot service
  - [ ] Add `answer_question_with_documents()` method
  - [ ] Implement document search
  - [ ] Combine transcript + document context
  - [ ] Update source extraction

- [ ] 8.2 Update chatbot component
  - [ ] Add document upload widget
  - [ ] Add document list display
  - [ ] Update chatbot to use documents
  - [ ] Display document sources in answers

- [ ] 8.3 Test document integration
  - [ ] Test document upload
  - [ ] Test document search
  - [ ] Test chatbot with documents
  - [ ] Test source attribution

## Phase 4: Testing & Optimization

### Task 9: Comprehensive Testing
- [ ] 9.1 Unit tests
  - [ ] Test PDF generation
  - [ ] Test translation service
  - [ ] Test chatbot service
  - [ ] Test document processing

- [ ] 9.2 Integration tests
  - [ ] Test PDF export flow
  - [ ] Test translation flow
  - [ ] Test chatbot flow
  - [ ] Test document upload flow

- [ ] 9.3 End-to-end tests
  - [ ] Test complete workflows
  - [ ] Test error scenarios
  - [ ] Test performance
  - [ ] Test security

### Task 10: Performance Optimization
- [ ] 10.1 Optimize PDF generation
  - [ ] Implement streaming for large PDFs
  - [ ] Add compression
  - [ ] Cache generated PDFs

- [ ] 10.2 Optimize translation
  - [ ] Implement batch translation
  - [ ] Improve caching
  - [ ] Add async processing

- [ ] 10.3 Optimize chatbot
  - [ ] Implement response streaming
  - [ ] Add caching for common questions
  - [ ] Optimize context retrieval

- [ ] 10.4 Optimize document processing
  - [ ] Implement async processing
  - [ ] Add indexing
  - [ ] Optimize search

### Task 11: Documentation
- [ ] 11.1 API documentation
  - [ ] Document all new endpoints
  - [ ] Add request/response examples
  - [ ] Add error codes

- [ ] 11.2 User documentation
  - [ ] Create user guide for PDF export
  - [ ] Create user guide for translation
  - [ ] Create user guide for chatbot
  - [ ] Create user guide for document upload

- [ ] 11.3 Developer documentation
  - [ ] Document service architecture
  - [ ] Document database schema
  - [ ] Document configuration

### Task 12: Deployment & Monitoring
- [ ] 12.1 Prepare for deployment
  - [ ] Update Docker files
  - [ ] Update environment variables
  - [ ] Update requirements.txt

- [ ] 12.2 Set up monitoring
  - [ ] Add logging for all features
  - [ ] Add error tracking
  - [ ] Add performance monitoring

- [ ] 12.3 Final testing
  - [ ] Test in staging environment
  - [ ] Performance testing
  - [ ] Security testing
  - [ ] User acceptance testing

## Dependencies & Prerequisites

### External Services
- Google Translate API (or DeepL)
- Groq API (already configured)

### Python Packages
- reportlab (PDF generation)
- PyPDF2 (PDF utilities)
- python-docx (DOCX processing)
- google-cloud-translate (Translation)

### Database
- PostgreSQL (existing)
- New tables: chat_messages, documents, translation_cache

## Estimated Timeline

- Phase 1 (PDF + Translation): 3-4 days
- Phase 2 (Chatbot): 3-4 days
- Phase 3 (Documents): 2-3 days
- Phase 4 (Testing & Optimization): 2-3 days
- **Total**: 10-14 days

## Success Criteria

- ✅ All features implemented and tested
- ✅ All endpoints working correctly
- ✅ Frontend UI complete and responsive
- ✅ Performance meets requirements (<5s for PDF, <10s for translation, <3s for chatbot)
- ✅ Error handling comprehensive
- ✅ Security validated
- ✅ Documentation complete
- ✅ User acceptance testing passed
