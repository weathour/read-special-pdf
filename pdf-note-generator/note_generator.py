import os
import json
import time
from pathlib import Path
from typing import Dict, List, Optional
import requests
from datetime import datetime

# Fix import - Use the optimized PDF processor if available
try:
    from pdf_processor_optimized import OptimizedPDFProcessor
except ImportError:
    try:
        from pdf_processor import PDFProcessor as OptimizedPDFProcessor
    except ImportError:
        OptimizedPDFProcessor = None

class NoteGenerator:
    """Note Generator (Structured JSON Extraction Only)"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.api_config = config.get('api', {})
        self.output_config = config.get('output', {})
        self.prompts = config.get('prompts', {})
        
        if OptimizedPDFProcessor:
            self.pdf_processor = OptimizedPDFProcessor(config)
        else:
            raise ImportError("Cannot import PDF processor. Check pdf_processor_optimized.py or pdf_processor.py")
    
    def process_pdf(self, pdf_path: Path, output_dir: Path):
        """Process a single PDF file, only extracting structured JSON info"""
        try:
            # Extract text
            text = self.pdf_processor.extract_text(pdf_path)
            if not text or not text.strip():
                raise Exception("No text content extracted from PDF.")
            
            # Split into chunks
            chunks = self.pdf_processor.chunk_text(text)
            
            # Extract structured info (English JSON)
            structured_info = self.extract_structured_info(chunks)
            
            # Save only the extracted structured info
            self.save_structured_info(pdf_path, structured_info, output_dir)
            
        except Exception as e:
            raise Exception(f"Failed to process PDF: {str(e)}")
    
    def extract_structured_info(self, chunks: List[str]) -> Dict:
        """Extract only structured JSON info (in English)"""
        if not chunks:
            return {}
        try:
            combined_text = "\n".join(chunks)
            
            extraction_prompt = self.prompts.get(
                'extraction_prompt', 
                "Please extract key information from the paper in strict JSON format (English only, no extra text)."
            )
            response = self._call_api(extraction_prompt, combined_text)
            try:
                cleaned_response = response.replace('```json', '').replace('```', '').strip()
                return json.loads(cleaned_response)
            except json.JSONDecodeError:
                return {"raw_response": cleaned_response}
        except Exception as e:
            return {"error": f"Failed to extract structured info: {str(e)}"}
    
    def _call_api(self, prompt: str, content: str) -> str:
        """Call API for info extraction"""
        try:
            # Force English output
            system_prompt = "You are a professional information extractor. Return only pure JSON in English, no extra text or code blocks."
            data = {
                "model": self.api_config.get('model', 'deepseek-reasoner'),
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"{prompt}\n\nPaper content:\n{content}"}
                ],
                "temperature": 0.7,
                "max_tokens": 4000
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_config.get('api_key', '')}"
            }
            response = requests.post(
                url=f"{self.api_config.get('base_url', '')}/v1/chat/completions",
                json=data,
                headers=headers,
                timeout=self.api_config.get('timeout', 120)
            )
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {str(e)}")
        except KeyError as e:
            raise Exception(f"API response format error (missing field): {str(e)}")
        except Exception as e:
            raise Exception(f"API call exception: {str(e)}")
    
    def save_structured_info(self, pdf_path: Path, structured_info: Dict, output_dir: Path):
        """Save only structured JSON info"""
        try:
            base_name = pdf_path.stem
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            json_dir = output_dir / "json"
            json_dir.mkdir(parents=True, exist_ok=True)
            json_file = json_dir / f"{base_name}_{timestamp}.json"

            if 'raw_response' in structured_info:
                raw_response = structured_info['raw_response']
                cleaned_response = raw_response.replace('```json\n', '').replace('\n```', '')
                try:
                    structured_info = json.loads(cleaned_response)
                except json.JSONDecodeError:
                    pass

            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "file_name": pdf_path.name,
                    "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "structured_info": structured_info
                }, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Structured info saved: {json_file}")
        except Exception as e:
            raise Exception(f"Failed to save structured info: {str(e)}")