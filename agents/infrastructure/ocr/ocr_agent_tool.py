"""
OCR Agent Tool - Genesis Agents Integration
Provides OCR capabilities to all Genesis agents via standardized tool interface
"""

import requests
import logging
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class OCRAgentTool:
    """
    Standardized OCR tool for Genesis agents

    Usage in agents:
        from infrastructure.ocr.ocr_agent_tool import ocr_tool

        # In agent code
        result = ocr_tool(
            image_path="/path/to/document.png",
            mode="document"
        )
        text = result['text']
    """

    def __init__(self, service_url: str = "http://localhost:8001"):
        self.service_url = service_url
        self._health_checked = False

    def _check_health(self) -> bool:
        """Check if OCR service is healthy"""
        if self._health_checked:
            return True

        try:
            response = requests.get(f"{self.service_url}/health", timeout=5)
            if response.status_code == 200:
                health = response.json()
                logger.info(f"OCR service healthy: {health['engine']}")
                self._health_checked = True
                return True
        except Exception as e:
            logger.error(f"OCR service health check failed: {e}")

        return False

    def process_document(
        self,
        image_path: str,
        mode: str = "document"
    ) -> Dict:
        """
        Process a document/image with OCR

        Args:
            image_path: Path to image file (PNG, JPG, PDF page)
            mode: OCR mode
                - "document": Extract text + bounding boxes
                - "raw": Text only
                - "described": Text + description

        Returns:
            Dict with keys:
                - text: Extracted text (str)
                - bounding_boxes: List of text regions (List[Dict])
                - mode: OCR mode used (str)
                - inference_time: Processing time in seconds (float)
                - engine: OCR engine ("tesseract" or "deepseek-ocr")
                - cached: Whether result was from cache (bool)
                - error: Error message if failed (str, only if error)

        Example:
            result = tool.process_document("/path/to/invoice.png")
            if 'error' not in result:
                print(f"Extracted text: {result['text']}")
                print(f"Found {len(result['bounding_boxes'])} text regions")
                print(f"Took {result['inference_time']:.2f}s")
        """
        # Validate file exists
        if not Path(image_path).exists():
            return {'error': f'File not found: {image_path}'}

        # Check service health
        if not self._check_health():
            return {'error': 'OCR service unavailable'}

        # Make API request
        try:
            response = requests.post(
                f"{self.service_url}/ocr",
                json={
                    'image_path': image_path,
                    'mode': mode
                },
                timeout=300  # 5 minute timeout for slow CPU inference
            )

            if response.status_code == 200:
                return response.json()
            else:
                error_data = response.json()
                return {'error': error_data.get('error', 'Unknown error')}

        except requests.exceptions.Timeout:
            return {'error': 'OCR request timed out (>5 minutes)'}
        except Exception as e:
            logger.error(f"OCR request failed: {e}")
            return {'error': str(e)}

    def process_batch(
        self,
        image_paths: List[str],
        mode: str = "document"
    ) -> List[Dict]:
        """
        Process multiple documents in batch

        Args:
            image_paths: List of image file paths
            mode: OCR mode (same for all images)

        Returns:
            List of OCR results (one per image)

        Example:
            results = tool.process_batch([
                "/path/to/page1.png",
                "/path/to/page2.png",
                "/path/to/page3.png"
            ])

            for i, result in enumerate(results):
                if 'error' not in result:
                    print(f"Page {i+1}: {len(result['text'])} characters")
        """
        # Check service health
        if not self._check_health():
            return [{'error': 'OCR service unavailable'} for _ in image_paths]

        # Make batch API request
        try:
            response = requests.post(
                f"{self.service_url}/ocr/batch",
                json={
                    'image_paths': image_paths,
                    'mode': mode
                },
                timeout=600  # 10 minute timeout for batch
            )

            if response.status_code == 200:
                data = response.json()
                return data['results']
            else:
                error_data = response.json()
                error_msg = error_data.get('error', 'Unknown error')
                return [{'error': error_msg} for _ in image_paths]

        except requests.exceptions.Timeout:
            return [{'error': 'Batch OCR timed out (>10 minutes)'} for _ in image_paths]
        except Exception as e:
            logger.error(f"Batch OCR request failed: {e}")
            return [{'error': str(e)} for _ in image_paths]

    def __call__(self, image_path: str, mode: str = "document") -> Dict:
        """
        Allow tool to be called directly

        Example:
            from infrastructure.ocr.ocr_agent_tool import ocr_tool
            result = ocr_tool("/path/to/document.png")
        """
        return self.process_document(image_path, mode)


# Global instance for easy import
ocr_tool = OCRAgentTool()


# Convenience functions for common use cases
def extract_text(image_path: str) -> str:
    """
    Extract text from image (simple interface)

    Args:
        image_path: Path to image

    Returns:
        Extracted text (empty string if error)

    Example:
        text = extract_text("/path/to/screenshot.png")
        if text:
            print(f"Found text: {text}")
    """
    result = ocr_tool(image_path, mode="raw")
    return result.get('text', '')


def extract_with_boxes(image_path: str) -> Dict:
    """
    Extract text with bounding box coordinates

    Args:
        image_path: Path to image

    Returns:
        Dict with 'text' and 'boxes' keys

    Example:
        result = extract_with_boxes("/path/to/form.png")
        for box in result['boxes']:
            print(f"Text '{box['text']}' at ({box['x']}, {box['y']})")
    """
    result = ocr_tool(image_path, mode="document")
    if 'error' in result:
        return {'text': '', 'boxes': []}

    return {
        'text': result.get('text', ''),
        'boxes': result.get('bounding_boxes', [])
    }


# Agent-specific helpers
def qa_agent_screenshot_validator(screenshot_path: str) -> Dict:
    """
    QA Agent: Validate screenshot contents

    Returns:
        Dict with extracted text and validation metadata
    """
    result = ocr_tool(screenshot_path, mode="document")

    if 'error' in result:
        return {
            'valid': False,
            'error': result['error'],
            'text': ''
        }

    return {
        'valid': True,
        'text': result['text'],
        'word_count': len(result['text'].split()),
        'has_content': len(result['text'].strip()) > 0,
        'inference_time': result['inference_time']
    }


def legal_agent_contract_parser(contract_image_path: str) -> Dict:
    """
    Legal Agent: Parse contract/legal document

    Returns:
        Dict with extracted text and legal metadata
    """
    result = ocr_tool(contract_image_path, mode="document")

    if 'error' in result:
        return {
            'valid': False,
            'error': result['error']
        }

    text = result['text']

    # Basic legal document detection
    legal_keywords = ['agreement', 'contract', 'party', 'whereas', 'terms', 'conditions']
    found_keywords = [kw for kw in legal_keywords if kw.lower() in text.lower()]

    return {
        'valid': True,
        'text': text,
        'likely_legal_doc': len(found_keywords) >= 2,
        'found_legal_terms': found_keywords,
        'char_count': len(text),
        'inference_time': result['inference_time']
    }


def marketing_agent_visual_analyzer(image_path: str) -> Dict:
    """
    Marketing Agent: Analyze competitor visuals/ads

    Returns:
        Dict with extracted text and marketing insights
    """
    result = ocr_tool(image_path, mode="document")

    if 'error' in result:
        return {
            'valid': False,
            'error': result['error']
        }

    text = result['text']

    # Basic marketing content detection
    marketing_signals = ['buy', 'sale', 'discount', 'offer', 'free', 'limited', 'now']
    found_signals = [sig for sig in marketing_signals if sig.lower() in text.lower()]

    return {
        'valid': True,
        'text': text,
        'likely_ad': len(found_signals) >= 1,
        'marketing_signals': found_signals,
        'call_to_action_detected': any(sig in text.lower() for sig in ['buy now', 'click here', 'sign up']),
        'inference_time': result['inference_time']
    }


def support_agent_ticket_image_processor(ticket_image_path: str) -> Dict:
    """
    Support Agent: Process customer support ticket images

    Returns:
        Dict with extracted text and support metadata
    """
    result = ocr_tool(ticket_image_path, mode="document")

    if 'error' in result:
        return {
            'valid': False,
            'error': result['error']
        }

    text = result['text']

    # Basic issue detection
    issue_keywords = ['error', 'problem', 'issue', 'bug', 'broken', 'not working', 'help']
    found_issues = [kw for kw in issue_keywords if kw.lower() in text.lower()]

    return {
        'valid': True,
        'text': text,
        'likely_issue_report': len(found_issues) >= 1,
        'detected_issues': found_issues,
        'urgency_high': any(word in text.lower() for word in ['urgent', 'critical', 'asap']),
        'inference_time': result['inference_time']
    }


def analyst_agent_chart_data_extractor(chart_image_path: str) -> Dict:
    """
    Analyst Agent: Extract data from charts/graphs

    Returns:
        Dict with extracted text and numerical data
    """
    result = ocr_tool(chart_image_path, mode="document")

    if 'error' in result:
        return {
            'valid': False,
            'error': result['error']
        }

    text = result['text']

    # Extract numbers from text
    import re
    numbers = re.findall(r'\d+\.?\d*', text)

    return {
        'valid': True,
        'text': text,
        'extracted_numbers': numbers,
        'number_count': len(numbers),
        'likely_chart': len(numbers) >= 3,  # Charts usually have multiple data points
        'inference_time': result['inference_time']
    }
