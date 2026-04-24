"""Service for processing uploaded documents"""

import logging
from typing import Optional
import os
from io import BytesIO

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for processing documents"""

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_TYPES = {"pdf", "docx", "txt"}

    def __init__(self):
        pass

    def process_document(self, file_content: bytes, filename: str) -> dict:
        """Process uploaded document and extract text

        Args:
            file_content: File content as bytes
            filename: Original filename

        Returns:
            Dictionary with extracted content and metadata
        """
        try:
            logger.info(f"Processing document: {filename}")

            # Validate file
            file_type = self._get_file_type(filename)
            if file_type not in self.ALLOWED_TYPES:
                raise ValueError(f"Unsupported file type: {file_type}")

            if len(file_content) > self.MAX_FILE_SIZE:
                raise ValueError(f"File too large: {len(file_content)} bytes (max {self.MAX_FILE_SIZE})")

            # Extract text based on file type
            if file_type == "txt":
                content = self._extract_text_from_txt(file_content)
            elif file_type == "pdf":
                content = self._extract_text_from_pdf(file_content)
            elif file_type == "docx":
                content = self._extract_text_from_docx(file_content)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")

            logger.info(f"✓ Document processed: {len(content)} characters extracted")

            return {
                "filename": filename,
                "file_type": file_type,
                "content": content,
                "file_size": len(file_content),
            }

        except Exception as e:
            logger.error(f"Error processing document: {e}", exc_info=True)
            raise

    def _get_file_type(self, filename: str) -> str:
        """Get file type from filename

        Args:
            filename: Original filename

        Returns:
            File type (extension)
        """
        return filename.split(".")[-1].lower()

    def _extract_text_from_txt(self, file_content: bytes) -> str:
        """Extract text from TXT file

        Args:
            file_content: File content as bytes

        Returns:
            Extracted text
        """
        try:
            return file_content.decode("utf-8")
        except UnicodeDecodeError:
            return file_content.decode("latin-1")

    def _extract_text_from_pdf(self, file_content: bytes) -> str:
        """Extract text from PDF file

        Args:
            file_content: File content as bytes

        Returns:
            Extracted text
        """
        try:
            import PyPDF2

            pdf_file = BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"

            return text.strip()

        except ImportError:
            logger.warning("PyPDF2 not installed, returning empty text")
            return ""
        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            return ""

    def _extract_text_from_docx(self, file_content: bytes) -> str:
        """Extract text from DOCX file

        Args:
            file_content: File content as bytes

        Returns:
            Extracted text
        """
        try:
            from docx import Document

            docx_file = BytesIO(file_content)
            doc = Document(docx_file)

            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"

            return text.strip()

        except ImportError:
            logger.warning("python-docx not installed, returning empty text")
            return ""
        except Exception as e:
            logger.error(f"Error extracting DOCX text: {e}")
            return ""


# Global document service instance
document_service = DocumentService()
