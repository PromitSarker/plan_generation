# Enhanced financial_extractor.py

import re
import json
import logging
from typing import Optional, Dict, List, Tuple, Any
import pandas as pd
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LTTextBoxHorizontal, LTRect, LTLine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FinancialDataExtractor:
    def __init__(self):
        """Initialize the financial data extractor with comprehensive Italian financial patterns"""
        self.logger = logging.getLogger(__name__ + "." + self.__class__.__name__)
        
        # Comprehensive Italian financial terminology patterns
        self.financial_patterns = {
            # Profit & Loss Statement items
            'ricavi_vendite_prestazioni': [
                r'(?i)(ricavi[\s:]*totali|ricavi|fatturato|ricavi\s+delle\s+vendite|ricavi\s+da\s+vendite|vendite)[\s:]*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?',
                r'(?i)(Totale\s+ricavi|Totale\s+fatturato)\D*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?',
                r'(?i)(Ricavi\s+operativi)\D*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?'
            ],
            'acquisti_merci': [
                r'(?i)(acquisti\s+di\s+merci|costo\s+merci\s+vendute|costo\s+delle\s+merci|c\.o\.g\.s)[\s:]*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?',
                r'(?i)(Costi\s+materiali)\D*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?'
            ],
            'acquisti_servizi': [
                r'(?i)(acquisti\s+di\s+servizi|costi\s+servizi|servizi\s+esterni)[\s:]*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?',
                r'(?i)(Costi\s+per\s+servizi)\D*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?'
            ],
            'godimento_beni_terzi': [
                r'(?i)(godimento\s+di\s+beni\s+di\s+terzi|canoni\s+di\s+locazione|affitti\s+attivi|leasing\s+operativo\s+attivo)[\s:]*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?',
                r'(?i)(Canoni\s+di\s+locazione)\D*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?'
            ],
            'costi_personale': [
                r'(?i)(costi\s+del\s+personale|spese\s+personale|salari\s+e\s+stipendi|stipendi|personale)[\s:]*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?',
                r'(?i)(Costi\s+personale|Totale\s+costi\s+personale)\D*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?'
            ],
            'ammortamenti_immateriali': [
                r'(?i)(ammortamenti\s+immobilizzazioni\s+immateriali|ammortamenti\s+immateriali)[\s:]*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?',
                r'(?i)(Amm\.?\s+immateriali)\D*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?'
            ],
            'ammortamenti_materiali': [
                r'(?i)(ammortamenti\s+immobilizzazioni\s+materiali|ammortamenti\s+materiali)[\s:]*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?',
                r'(?i)(Amm\.?\s+materiali)\D*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?'
            ],
            'oneri_finanziari': [
                r'(?i)(oneri\s+finanziari|interessi\s+passivi|costi\s+finanziari)[\s:]*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?',
                r'(?i)(Interessi\s+passivi|Oneri\s+finanziari)\D*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?'
            ],
            'imposte_reddito': [
                r'(?i)(imposte\s+sul\s+reddito|imposta\s+sul\s+reddito|imposte|iva|tasse)[\s:]*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?',
                r'(?i)(Imposte|Totale\s+imposte)\D*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?'
            ],
            'utile_netto': [
                r'(?i)(utile\s+netto|risultato\s+netto|utile\s+d\'esercizio|profitto|utile\s+di\s+esercizio)[\s:]*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?',
                r'(?i)(Totale\s+utile|Utile|Perdita)\D*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?'
            ],
            
            # Balance Sheet items
            'disponibilita_liquide': [
                r'(?i)(disponibilit[aà]\s+liquide|cassa\s+e\s+banche|liquidit[aà]|cash|disponibilit[aà]\s+finanziarie)[\s:]*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?',
                r'(?i)(Totale\s+disponibilit[aà]\s+liquide|Totale\s+liquidit[aà])\D*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?'
            ],
            'crediti_commerciali': [
                r'(?i)(crediti\s+commerciali|crediti\s+v/clienti|clienti|crediti\s+vs\s+clienti)[\s:]*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?',
                r'(?i)(Totale\s+crediti\s+commerciali|Crediti\s+clienti)\D*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?'
            ],
            'debiti_vs_fornitori': [
                r'(?i)(debiti\s+commerciali|debiti\s+v/fornitori|fornitori|debiti\s+vs\s+fornitori)[\s:]*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?',
                r'(?i)(Totale\s+debiti\s+commerciali|Debiti\s+fornitori)\D*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?'
            ],
            'debiti_vs_banche': [
                r'(?i)(debiti\s+v/banche|debiti\s+bancari|mutui|prestiti|finanziamenti)[\s:]*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?',
                r'(?i)(Totale\s+debiti\s+bancari|Debiti\s+banche)\D*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?'
            ],
            'capitale_sociale': [
                r'(?i)(capitale\s+sociale|capitale)[\s:]*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?',
                r'(?i)(Capitale\s+sociale)\D*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?'
            ],
            'patrimonio_netto': [
                r'(?i)(patrimonio\s+netto|capitale\s+proprio|netto\s+worth)[\s:]*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?',
                r'(?i)(Totale\s+patrimonio\s+netto)\D*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?'
            ],
            'totale_attivo': [
                r'(?i)(totale\s+attivo|attivo\s+totale|assets\s+totali)[\s:]*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?',
                r'(?i)(Totale\s+attivo)\D*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?'
            ],
            'totale_passivo': [
                r'(?i)(totale\s+passivo|passivo\s+totale|liabilities\s+totali)[\s:]*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?',
                r'(?i)(Totale\s+passivo|Totale\s+passivit[aà])\D*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?'
            ],
            
            # Cash Flow items
            'operating': [
                r'(?i)(flusso\s+di\s+cassa\s+operativo|cash\s+flow\s+operativo|attivit[aà]\s+operative)[\s:]*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?',
                r'(?i)(Flusso\s+operativo|Cash\s+flow\s+da\s+attivit[aà]\s+operative)\D*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?'
            ],
            'investing': [
                r'(?i)(flusso\s+di\s+cassa\s+per\s+investimenti|cash\s+flow\s+investimenti|attivit[aà]\s+di\s+investimento)[\s:]*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?',
                r'(?i)(Flusso\s+investimenti|Cash\s+flow\s+da\s+attivit[aà]\s+di\s+investimento)\D*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?'
            ],
            'financing': [
                r'(?i)(flusso\s+di\s+cassa\s+finanziario|cash\s+flow\s+finanziario|attivit[aà]\s+di\s+finanziamento)[\s:]*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?',
                r'(?i)(Flusso\s+finanziario|Cash\s+flow\s+da\s+attivit[aà]\s+di\s+finanziamento)\D*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?'
            ],
            
            # Debt Structure items
            'outstanding_debt': [
                r'(?i)(debito\s+residuo|debito\s+totale|indebitamento\s+totale|posizione\s+debito)[\s:]*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?',
                r'(?i)(Totale\s+debiti|Indebitamento)\D*([\d.,]+)(?:\s*(K|k|M|m|mln|B|b|mrd))?'
            ],
            'interest_rate': [
                r'(?i)(tasso\s+interesse|interest\s+rate|tasso\s+annuo)[\s:]*([\d.,]+)%?',
                r'(?i)(Tasso\s+di\s+interesse)\D*([\d.,]+)%?'
            ],
            
            # General items
            'year': [
                r'(?i)(bilancio\s+al|esercizio|anno\s+di\s+riferimento|anno)[\s:]*(20\d{2})',
                r'(?i)(Esercizio\s+chiuso\s+al|Al\s+31\s+dicembre\s+)(20\d{2})'
            ],
            'currency': [
                r'(?i)(valuta|currency)\s*[:\s]*\s*(euro|eur|€)',
                r'(?i)\b(euro|eur|€)\b'
            ]
        }
        
        # Field mapping to normalize extracted fields to schema fields
        self.field_mapping = {
            'ricavi': 'ricavi_vendite_prestazioni',
            'fatturato': 'ricavi_vendite_prestazioni',
            'revenue': 'ricavi_vendite_prestazioni',
            'total_revenue': 'ricavi_vendite_prestazioni',
            'utile': 'utile_netto',
            'profit': 'utile_netto',
            'net_income': 'utile_netto',
            'cash': 'disponibilita_liquide',
            'liquidita': 'disponibilita_liquide',
            'cash_and_banks': 'disponibilita_liquide',
            'assets': 'totale_attivo',
            'total_assets': 'totale_attivo',
            'liabilities': 'totale_passivo',
            'total_liabilities': 'totale_passivo',
            'equity': 'patrimonio_netto',
            'net_worth': 'patrimonio_netto',
            'total_debt': 'outstanding_debt',
            'indebitamento': 'outstanding_debt',
            'operating_cash_flow': 'operating',
            'investing_cash_flow': 'investing',
            'financing_cash_flow': 'financing'
        }
        
        # Confidence thresholds for different extraction methods
        self.confidence_thresholds = {
            'regex_match': 0.7,
            'table_match': 0.8,
            'context_match': 0.6
        }

    def get_scale_multiplier(self, scale: Optional[str]) -> float:
        """Determine the multiplier based on the scale indicator"""
        if not scale:
            return 1000  # Default to thousands (common in financial statements)
        
        scale = scale.strip().lower()
        if scale in ['k', 'migliaia', 'thousands', 'millesimi']:
            return 1  # Already in thousands
        elif scale in ['m', 'mln', 'milioni', 'millions']:
            return 1000  # Convert millions to thousands
        elif scale in ['b', 'bln', 'mld', 'miliardi', 'billions']:
            return 1000000  # Convert billions to thousands
        return 1000  # Default: convert to thousands

    def clean_number(self, value: str, scale: Optional[str] = None) -> float:
        """Clean and convert string numbers to float in thousands"""
        try:
            # Remove any non-numeric characters except . , - and parentheses
            cleaned = re.sub(r'[^\d.,\-()]', '', value)
            
            # Handle negative numbers in parentheses
            is_negative = False
            if '(' in cleaned and ')' in cleaned:
                is_negative = True
                cleaned = cleaned.replace('(', '').replace(')', '')
            
            # Convert Italian number format (1.234,56) to standard float
            if ',' in cleaned and '.' in cleaned:
                # If it has both, assume . is thousands separator and , is decimal
                cleaned = cleaned.replace('.', '').replace(',', '.')
            elif ',' in cleaned:
                # If only commas, check if it's used as decimal or thousands separator
                parts = cleaned.split(',')
                if len(parts[-1]) == 3 and len(cleaned) > 4:  # Likely thousands separator
                    cleaned = cleaned.replace(',', '')
                else:  # Likely decimal separator
                    cleaned = cleaned.replace(',', '.')
            
            number = float(cleaned)
            if is_negative:
                number = -abs(number)
            
            # Apply scale multiplier
            multiplier = self.get_scale_multiplier(scale)
            return number * multiplier
            
        except Exception as e:
            self.logger.warning(f"Error cleaning number '{value}': {str(e)}")
            return 0.0

    def extract_year_from_context(self, text: str) -> Optional[int]:
        """Extract year from the document context with higher priority"""
        # Look for explicit year mentions in headers or footers
        year_patterns = [
            r'(?i)bilancio\s+al\s+31\s+dice[mn]bre\s+(20\d{2})',
            r'(?i)esercizio\s+(20\d{2})',
            r'(?i)al\s+31\s+[0-9]+\s+[a-z]+\s+(20\d{2})',
            r'(?i)31/12/(20\d{2})',
            r'(?i)(?:^|\s)(20\d{2})(?:$|\s)'
        ]
        
        for pattern in year_patterns:
            matches = re.findall(pattern, text)
            if matches:
                try:
                    # Return the most recent year found
                    return max(int(match) for match in matches if match)
                except (ValueError, TypeError):
                    continue
        return None

    def extract_currency_from_context(self, text: str) -> str:
        """Extract currency from the document context"""
        currency_patterns = [
            r'(?i)\b(euro|eur|€)\b',
            r'(?i)(?:valuta|currency)\s*[:\s]*\s*(euro|eur|€)'
        ]
        
        for pattern in currency_patterns:
            matches = re.findall(pattern, text)
            if matches:
                return "EUR"  # Standardize to EUR code
        return "EUR"  # Default to EUR

    def extract_financial_data_from_tables(self, text: str) -> Dict[str, Any]:
        """Attempt to extract financial data from table structures in the text"""
        financial_data = {}
        
        try:
            # Split text into lines and look for table-like structures
            lines = text.split('\n')
            table_candidates = []
            current_table = []
            
            # Identify potential tables based on alignment markers
            for line in lines:
                # Look for lines that might be part of a table (contain numbers and separators)
                if re.search(r'[\d.,]+', line) and (re.search(r'[\|:]', line) or len(line.strip().split()) > 3):
                    current_table.append(line.strip())
                elif current_table:
                    # End of potential table
                    if len(current_table) > 2:  # Minimum table size
                        table_candidates.append(current_table)
                    current_table = []
            
            # Process each candidate table
            for table in table_candidates:
                # Try to parse as structured data
                for line in table:
                    # Look for common financial line items
                    for field_key, patterns in self.financial_patterns.items():
                        if field_key in ['year', 'currency']:  # Skip non-amount fields
                            continue
                            
                        for pattern in patterns:
                            match = re.search(pattern, line)
                            if match:
                                try:
                                    # Extract value and scale
                                    groups = match.groups()
                                    if len(groups) >= 2:
                                        value_str = groups[1]
                                        scale_str = groups[2] if len(groups) > 2 else None
                                        
                                        # Clean and convert the value
                                        value = self.clean_number(value_str, scale_str)
                                        
                                        # Only use if value is non-zero and reasonable
                                        if abs(value) > 0.01:  # Avoid tiny values
                                            if field_key not in financial_data or abs(value) > abs(financial_data[field_key]):
                                                financial_data[field_key] = value
                                                self.logger.debug(f"Table extraction: {field_key} = {value}")
                                except Exception as e:
                                    self.logger.debug(f"Error processing table match: {str(e)}")
        except Exception as e:
            self.logger.warning(f"Error extracting from tables: {str(e)}")
        
        return financial_data

    def extract_financial_data_from_text(self, text: str) -> Dict[str, Any]:
        """Extract financial data from text using regex patterns"""
        financial_data = {}
        confidence_scores = {}
        
        # Extract year and currency first (contextual information)
        year = self.extract_year_from_context(text)
        if year:
            financial_data["year"] = year
            confidence_scores["year"] = 0.9
        
        currency = self.extract_currency_from_context(text)
        financial_data["currency"] = currency
        
        # Try table-based extraction first (higher confidence)
        table_data = self.extract_financial_data_from_tables(text)
        for field, value in table_data.items():
            financial_data[field] = value
            confidence_scores[field] = self.confidence_thresholds['table_match']
        
        # Then do regex pattern matching for remaining fields
        for field_key, patterns in self.financial_patterns.items():
            if field_key in financial_data:  # Skip if already extracted from tables
                continue
            
            best_match = None
            best_value = None
            best_confidence = 0
            
            for pattern in patterns:
                matches = re.findall(pattern, text)
                if matches:
                    for match in matches:
                        try:
                            # Extract value and scale
                            if field_key == 'year':
                                value = int(match[1])
                                confidence = 0.85
                            else:
                                value_str = match[1]
                                scale_str = match[2] if len(match) > 2 else None
                                value = self.clean_number(value_str, scale_str)
                                confidence = 0.75  # Base confidence for regex match
                            
                            # Adjust confidence based on context
                            if field_key in value_str.lower():  # Exact term match
                                confidence += 0.1
                            
                            # Prefer larger absolute values (likely totals rather than components)
                            if best_value is None or abs(value) > abs(best_value):
                                best_match = match
                                best_value = value
                                best_confidence = confidence
                        
                        except Exception as e:
                            self.logger.debug(f"Error processing match for {field_key}: {str(e)}")
                            continue
            
            if best_value is not None and best_confidence >= self.confidence_thresholds['regex_match']:
                financial_data[field_key] = best_value
                confidence_scores[field_key] = best_confidence
                self.logger.debug(f"Regex extraction: {field_key} = {best_value} (confidence: {best_confidence:.2f})")
        
        # Apply field mapping to normalize to schema fields
        normalized_data = {}
        for field, value in financial_data.items():
            # Map to standard field name if needed
            normalized_field = self.field_mapping.get(field, field)
            normalized_data[normalized_field] = value
        
        # Add confidence scores for debugging
        normalized_data["_confidence_scores"] = confidence_scores
        
        return normalized_data

    def validate_financial_data(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean the extracted financial data"""
        validated_data = {}
        
        # Validate year
        if "year" in financial_data:
            year = financial_data["year"]
            if isinstance(year, (int, float)) and 2000 <= year <= 2030:
                validated_data["year"] = int(year)
        
        # Validate currency
        validated_data["currency"] = financial_data.get("currency", "EUR")
        
        # Validate numeric fields
        for field, value in financial_data.items():
            if field in ["year", "currency", "_confidence_scores"]:
                continue
            
            if isinstance(value, (int, float)):
                # Apply reasonable bounds checks
                if field.startswith("utile") or field.startswith("risultato"):
                    # Net income should typically be within -50% to +50% of revenue
                    if "ricavi_vendite_prestazioni" in validated_data:
                        revenue = validated_data["ricavi_vendite_prestazioni"]
                        if abs(value) > abs(revenue) * 1.5:
                            self.logger.warning(f"Unusual net income value: {value} vs revenue {revenue}")
                
                # Skip extremely large or small values that are likely extraction errors
                if abs(value) < 1e-6 or abs(value) > 1e12:
                    self.logger.warning(f"Skipping extreme value for {field}: {value}")
                    continue
                
                validated_data[field] = round(float(value), 2)
        
        return validated_data

    def extract_financial_data(self, text: str) -> Dict[str, Any]:
        """
        Main method to extract financial data from text.
        Combines multiple extraction strategies and validates the results.
        """
        self.logger.info("Starting financial data extraction")
        self.logger.debug(f"Text length: {len(text)} characters")
        
        try:
            # 1. Extract data using text patterns
            raw_data = self.extract_financial_data_from_text(text)
            
            # 2. Validate and clean the extracted data
            validated_data = self.validate_financial_data(raw_data)
            
            # 3. Log the extraction results
            if validated_data:
                self.logger.info(f"Successfully extracted {len(validated_data)} financial data points")
                self.logger.debug(f"Extracted data: {json.dumps(validated_data, indent=2)}")
            else:
                self.logger.warning("No financial data extracted")
            
            # 4. Remove internal fields before returning
            if "_confidence_scores" in validated_data:
                del validated_data["_confidence_scores"]
            
            return validated_data
            
        except Exception as e:
            self.logger.error(f"Error in financial data extraction: {str(e)}")
            return {}

    def extract_from_pdf_layout(self, pdf_content: bytes) -> Dict[str, Any]:
        """
        Advanced extraction using PDF layout analysis to identify financial tables and figures
        """
        try:
            # Use pdfminer to analyze the layout
            resource_manager = PDFResourceManager()
            laparams = LAParams()
            device = PDFPageAggregator(resource_manager, laparams=laparams)
            interpreter = PDFPageInterpreter(resource_manager, device)
            
            # Convert bytes to file-like object
            from io import BytesIO
            pdf_file = BytesIO(pdf_content)
            
            # Get all pages
            pages = list(PDFPage.get_pages(pdf_file))
            
            # Store potential financial data
            financial_data = {}
            table_regions = []
            
            # Analyze each page
            for page_num, page in enumerate(pages, 1):
                interpreter.process_page(page)
                layout = device.get_result()
                
                # Find text boxes and rectangles (potential table boundaries)
                text_boxes = []
                rectangles = []
                
                for element in layout:
                    if isinstance(element, LTTextBoxHorizontal):
                        text_boxes.append({
                            'text': element.get_text().strip(),
                            'bbox': element.bbox,
                            'x0': element.bbox[0],
                            'y0': element.bbox[1],
                            'x1': element.bbox[2],
                            'y1': element.bbox[3]
                        })
                    elif isinstance(element, LTRect) or isinstance(element, LTLine):
                        rectangles.append({
                            'bbox': element.bbox,
                            'width': abs(element.bbox[2] - element.bbox[0]),
                            'height': abs(element.bbox[3] - element.bbox[1])
                        })
                
                # Identify potential table regions based on rectangle density
                if rectangles:
                    # Group rectangles that might form table boundaries
                    table_candidates = self._identify_table_regions(rectangles)
                    table_regions.extend(table_candidates)
            
            # Extract data from identified table regions (simplified)
            if table_regions:
                self.logger.info(f"Found {len(table_regions)} potential table regions for financial data")
                # This would involve more complex spatial analysis to extract tabular data
                # For now, we'll return what we have from text extraction
                pass
            
            return financial_data
            
        except Exception as e:
            self.logger.error(f"Error in PDF layout analysis: {str(e)}")
            return {}

    def _identify_table_regions(self, rectangles: List[Dict]) -> List[Dict]:
        """Identify potential table regions from rectangle elements"""
        # This is a simplified implementation
        # In a real-world scenario, this would involve spatial clustering algorithms
        
        table_regions = []
        min_width = 100  # Minimum width for a table region
        min_height = 50  # Minimum height for a table region
        
        for rect in rectangles:
            if rect['width'] > min_width and rect['height'] > min_height:
                table_regions.append({
                    'bbox': rect['bbox'],
                    'confidence': 0.7  # Base confidence
                })
        
        return table_regions

    def combine_extraction_methods(self, text_content: str, pdf_content: Optional[bytes] = None) -> Dict[str, Any]:
        """
        Combine multiple extraction methods for higher accuracy
        """
        combined_data = {}
        
        # 1. Text-based extraction (always available)
        text_data = self.extract_financial_data(text_content)
        combined_data.update(text_data)
        
        # 2. PDF layout analysis (if PDF content is provided)
        if pdf_content:
            layout_data = self.extract_from_pdf_layout(pdf_content)
            for field, value in layout_data.items():
                # Only override text extraction if layout extraction has higher confidence
                if field not in combined_data or abs(value) > abs(combined_data.get(field, 0)):
                    combined_data[field] = value
        
        # 3. Apply validation to the combined results
        validated_data = self.validate_financial_data(combined_data)
        
        return validated_data