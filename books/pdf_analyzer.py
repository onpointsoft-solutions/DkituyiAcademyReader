import re
import PyPDF2
import io
from typing import Dict, List, Tuple, Optional

class PDFContentAnalyzer:
    """
    Advanced PDF content analyzer for detecting chapters, pages, and sections
    """
    
    def __init__(self, pdf_content: bytes):
        self.pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
        self.total_pages = len(self.pdf_reader.pages)
        
    def extract_page_text(self, page_num: int) -> str:
        """Extract text from a specific page"""
        if 0 <= page_num < self.total_pages:
            return self.pdf_reader.pages[page_num].extract_text()
        return ""
    
    def analyze_content_structure(self, start_page: int = 0, end_page: Optional[int] = None) -> Dict:
        """
        Analyze PDF content structure to detect chapters, sections, and boundaries
        """
        if end_page is None:
            end_page = self.total_pages
        
        content_analysis = {
            'total_pages': self.total_pages,
            'analyzed_pages': end_page - start_page,
            'pages': [],
            'chapters': [],
            'sections': [],
            'content_boundaries': {
                'pages': [],
                'chapters': [],
                'sections': []
            }
        }
        
        # Analyze each page
        for page_num in range(start_page, min(end_page, self.total_pages)):
            page_text = self.extract_page_text(page_num)
            page_analysis = self._analyze_page(page_text, page_num)
            content_analysis['pages'].append(page_analysis)
            
            # Detect content boundaries
            if page_analysis['is_chapter_start']:
                content_analysis['chapters'].append({
                    'page': page_num,
                    'title': page_analysis['chapter_title'],
                    'type': 'chapter'
                })
            
            if page_analysis['is_section_start']:
                content_analysis['sections'].append({
                    'page': page_num,
                    'title': page_analysis['section_title'],
                    'type': 'section'
                })
            
            content_analysis['content_boundaries']['pages'].append({
                'page': page_num,
                'word_count': page_analysis['word_count'],
                'line_count': page_analysis['line_count'],
                'has_content': page_analysis['has_content']
            })
        
        return content_analysis
    
    def _analyze_page(self, text: str, page_num: int) -> Dict:
        """Analyze individual page for content patterns"""
        lines = text.split('\n')
        
        # Basic metrics
        word_count = len(text.split())
        line_count = len([line for line in lines if line.strip()])
        has_content = word_count > 10 and line_count > 2
        
        # Chapter detection patterns
        chapter_patterns = [
            r'^Chapter\s+\d+',
            r'^CHAPTER\s+\d+',
            r'^\d+\.\s+[A-Z]',
            r'^[A-Z][A-Z\s]+$',
            r'^Chapter\s+[A-Z]',
            r'^Part\s+\d+',
            r'^PART\s+\d+'
        ]
        
        # Section detection patterns
        section_patterns = [
            r'^\d+\.\d+\s+[A-Z]',
            r'^Section\s+\d+',
            r'^\d+\.\s+[a-z]',
            r'^[A-Z][a-z\s]+:$',
            r'^[A-Z][A-Z\s]*\s+\d+'
        ]
        
        # Detect chapter start
        is_chapter_start = False
        chapter_title = ""
        
        for pattern in chapter_patterns:
            for line in lines[:10]:  # Check first 10 lines
                match = re.match(pattern, line.strip())
                if match:
                    is_chapter_start = True
                    chapter_title = line.strip()
                    break
            if is_chapter_start:
                break
        
        # Detect section start
        is_section_start = False
        section_title = ""
        
        for pattern in section_patterns:
            for line in lines[:10]:  # Check first 10 lines
                match = re.match(pattern, line.strip())
                if match:
                    is_section_start = True
                    section_title = line.strip()
                    break
            if is_section_start:
                break
        
        # Page end detection
        page_end_indicators = [
            r'.*\.\.\.\s*$',
            r'.*\.\s*\d+$',
            r'.*Page\s+\d+$',
            r'.*\[continued\]$'
        ]
        
        is_page_end = False
        for pattern in page_end_indicators:
            for line in lines[-5:]:  # Check last 5 lines
                if re.match(pattern, line.strip()):
                    is_page_end = True
                    break
        
        return {
            'page_number': page_num,
            'text': text,
            'word_count': word_count,
            'line_count': line_count,
            'has_content': has_content,
            'is_chapter_start': is_chapter_start,
            'chapter_title': chapter_title,
            'is_section_start': is_section_start,
            'section_title': section_title,
            'is_page_end': is_page_end,
            'first_lines': lines[:5],
            'last_lines': lines[-5:]
        }
    
    def get_reading_progress(self, current_page: int, total_read_pages: int) -> Dict:
        """Calculate reading progress with content boundaries"""
        if current_page >= self.total_pages:
            return {
                'progress_percentage': 100,
                'current_chapter': 'Book Complete',
                'pages_remaining': 0,
                'estimated_completion': 'Complete'
            }
        
        # Get current chapter
        current_chapter = "Unknown"
        for page_num in range(max(0, current_page - 5), current_page + 1):
            page_text = self.extract_page_text(page_num)
            analysis = self._analyze_page(page_text, page_num)
            if analysis['chapter_title']:
                current_chapter = analysis['chapter_title']
                break
        
        # Calculate progress
        progress_percentage = (total_read_pages / self.total_pages) * 100
        pages_remaining = self.total_pages - total_read_pages
        
        return {
            'progress_percentage': round(progress_percentage, 1),
            'current_page': current_page,
            'current_chapter': current_chapter,
            'pages_read': total_read_pages,
            'pages_remaining': pages_remaining,
            'total_pages': self.total_pages
        }
    
    def find_content_boundaries(self, start_page: int = 0, num_pages: int = 20) -> Dict:
        """Find content boundaries within a range of pages"""
        boundaries = {
            'chapters': [],
            'sections': [],
            'page_breaks': [],
            'content_gaps': []
        }
        
        end_page = min(start_page + num_pages, self.total_pages)
        
        for page_num in range(start_page, end_page):
            page_text = self.extract_page_text(page_num)
            analysis = self._analyze_page(page_text, page_num)
            
            if analysis['is_chapter_start']:
                boundaries['chapters'].append({
                    'page': page_num,
                    'title': analysis['chapter_title']
                })
            
            if analysis['is_section_start']:
                boundaries['sections'].append({
                    'page': page_num,
                    'title': analysis['section_title']
                })
            
            # Detect content gaps (pages with very little content)
            if analysis['word_count'] < 10 and analysis['line_count'] < 3:
                boundaries['content_gaps'].append({
                    'page': page_num,
                    'reason': 'Minimal content'
                })
        
        return boundaries
    
    def get_smart_preview_pages(self, preview_percentage: float = 0.2) -> List[int]:
        """Get smart preview pages that include complete chapters/sections"""
        target_pages = max(1, int(self.total_pages * preview_percentage))
        smart_pages = []
        
        # Analyze first few pages to find chapter boundaries
        boundaries = self.find_content_boundaries(0, target_pages + 10)
        
        # Find the best stopping point
        last_chapter_page = 0
        for chapter in boundaries['chapters']:
            if chapter['page'] <= target_pages:
                last_chapter_page = chapter['page']
        
        # Include pages up to the last complete chapter or target pages
        if last_chapter_page > 0:
            # Include the complete chapter
            for page_num in range(0, min(last_chapter_page + 3, self.total_pages)):
                smart_pages.append(page_num)
        else:
            # No chapters found, use simple percentage
            smart_pages = list(range(target_pages))
        
        return smart_pages
