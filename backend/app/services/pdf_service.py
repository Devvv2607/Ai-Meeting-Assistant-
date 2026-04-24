"""Service for generating PDF transcripts"""

from typing import List, Optional
import logging
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from app.models.meeting import Meeting
from app.models.transcript import Transcript
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class PDFService:
    """Service for generating PDF transcripts"""
    
    def __init__(self):
        self.page_size = letter
        self.margin = 0.5 * inch
        
    def generate_transcript_pdf(
        self, 
        meeting: Meeting, 
        transcripts: List[Transcript]
    ) -> bytes:
        """Generate PDF from meeting transcript
        
        Args:
            meeting: Meeting object
            transcripts: List of transcript segments
            
        Returns:
            PDF file as bytes
        """
        try:
            logger.info(f"Generating PDF for meeting {meeting.id}")
            
            # Create PDF buffer
            pdf_buffer = BytesIO()
            
            # Create PDF document
            doc = SimpleDocTemplate(
                pdf_buffer,
                pagesize=self.page_size,
                rightMargin=self.margin,
                leftMargin=self.margin,
                topMargin=self.margin,
                bottomMargin=self.margin,
                title=f"{meeting.title} - Transcript"
            )
            
            # Build PDF content
            story = []
            
            # Add header
            story.extend(self._build_header(meeting))
            
            # Add transcript
            story.extend(self._build_transcript(transcripts))
            
            # Build PDF
            doc.build(story)
            
            # Get PDF bytes
            pdf_bytes = pdf_buffer.getvalue()
            logger.info(f"✓ PDF generated successfully: {len(pdf_bytes)} bytes")
            
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"Error generating PDF: {e}", exc_info=True)
            raise
    
    def _build_header(self, meeting: Meeting) -> List:
        """Build PDF header with meeting metadata
        
        Args:
            meeting: Meeting object
            
        Returns:
            List of reportlab elements
        """
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f2937'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        elements.append(Paragraph(meeting.title, title_style))
        
        # Meeting metadata
        metadata_style = ParagraphStyle(
            'Metadata',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#6b7280'),
            spaceAfter=6,
            alignment=TA_CENTER
        )
        
        # Format date
        created_date = meeting.created_at.strftime('%B %d, %Y') if meeting.created_at else 'N/A'
        
        # Format duration
        duration_minutes = int(meeting.duration / 60) if meeting.duration else 0
        duration_str = f"{duration_minutes} minutes" if duration_minutes > 0 else "N/A"
        
        elements.append(Paragraph(f"Date: {created_date}", metadata_style))
        elements.append(Paragraph(f"Duration: {duration_str}", metadata_style))
        
        if meeting.description:
            desc_style = ParagraphStyle(
                'Description',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#4b5563'),
                spaceAfter=12,
                alignment=TA_JUSTIFY
            )
            elements.append(Paragraph(f"<b>Description:</b> {meeting.description}", desc_style))
        
        # Add separator
        elements.append(Spacer(1, 0.3 * inch))
        
        # Add horizontal line
        from reportlab.platypus import HRFlowable
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e5e7eb')))
        elements.append(Spacer(1, 0.2 * inch))
        
        return elements
    
    def _build_transcript(self, transcripts: List[Transcript]) -> List:
        """Build transcript section
        
        Args:
            transcripts: List of transcript segments
            
        Returns:
            List of reportlab elements
        """
        elements = []
        styles = getSampleStyleSheet()
        
        # Transcript heading
        heading_style = ParagraphStyle(
            'TranscriptHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1f2937'),
            spaceAfter=12,
            fontName='Helvetica-Bold'
        )
        elements.append(Paragraph("Transcript", heading_style))
        
        # Transcript segments
        segment_style = ParagraphStyle(
            'Segment',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#374151'),
            spaceAfter=8,
            leading=14,
            alignment=TA_JUSTIFY
        )
        
        speaker_style = ParagraphStyle(
            'Speaker',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#1f2937'),
            spaceAfter=4,
            fontName='Helvetica-Bold'
        )
        
        time_style = ParagraphStyle(
            'Time',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#9ca3af'),
            spaceAfter=2
        )
        
        for segment in transcripts:
            # Format timestamp
            timestamp = self._format_timestamp(segment.start_time)
            
            # Add timestamp
            elements.append(Paragraph(f"<font color='#9ca3af'>[{timestamp}]</font>", time_style))
            
            # Add speaker
            elements.append(Paragraph(f"<b>{segment.speaker}</b>", speaker_style))
            
            # Add text
            # Escape special characters
            text = segment.text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            elements.append(Paragraph(text, segment_style))
            
            # Add spacing between segments
            elements.append(Spacer(1, 0.1 * inch))
        
        return elements
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds to HH:MM:SS
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted timestamp string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"


# Global PDF service instance
pdf_service = PDFService()
