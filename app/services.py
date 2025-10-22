import asyncio
import json
from typing import List, Optional, Any, Dict
import re
import logging
from app.config import get_settings, get_openai_client

# --------------- LOGGING ---------------
logger = logging.getLogger(__name__)

# --------------- CONSTANTS ---------------
MAX_INPUT_LENGTH = 122000
MAX_RETRIES = 3
DEFAULT_LANGUAGE = "Italian"
DEFAULT_CURRENCY = "EUR"

# --------------- INDIVIDUAL SECTION SCHEMAS ---------------
INDIVIDUAL_SECTION_SCHEMAS = {
    "executiveSummary": {
        "type": "string",
        "description": "Summarize the overall business opportunity in 300+ words: include the core product or service, the market need it addresses, key team strengths, business traction (if any), and the long-term vision. Highlight why this business matters now.",
        "min_words": 300
    },
    "businessOverview": {
        "type": "string", 
        "description": "Describe the company's mission, vision, and founding story. Include when and why it was started, what goals it seeks to achieve, where it is currently based, and what motivates the team behind it.",
        "min_words": 500
    },
    "marketAnalysis": {
        "type": "string",
        "description": "Provide an analysis of the market that consist total addressable market (TAM), serviceable available market (SAM), and obtainable market (SOM). Make sure to Identify competitors, customer segments, market trends, and why the timing is right for this solution. Do not create any sub catagory.",
        "min_words": 500
    },
    "businessModel": {
        "type": "string",
        "description": "Explain how the business makes money. Describe primary and secondary revenue streams, customer acquisition strategy, pricing model, cost structure, margins, and how the model scales over time. DO NOT ADD SUBSECTIONS OF IT.",
        "min_words": 500
    },
    "marketingSalesStrategy": {
        "type": "string",
        "description": "Describe how the business plans to go to market. Include positioning, target customers, sales channels (online/offline), customer acquisition cost (CAC) strategies, conversion funnels, and how growth will be driven operationally.",
        "min_words": 500
    },
    "financialHighlights": {
        "type": "json",
        "description": "6 years of key financial metrics (Year 0 = current/recent data, Years 1-5 = projections) following Italian accounting standards (OIC). Provide realistic `numerical data with interpretive commentary on trends and performance indicators.",
        "schema": [
            {
                "data": [{"year": "int", "revenue": "float", "net_income": "float", "capex": "float", "debt_repayment": "float"}],
                "analysis": "string"
            }
        ],
        "example": [
            {
                "data": [
                    {"year": 0, "revenue": 180000, "net_income": 15000, "capex": 30000, "debt_repayment": 5000},
                    {"year": 1, "revenue": 250000, "net_income": 30000, "capex": 50000, "debt_repayment": 10000},
                    {"year": 2, "revenue": 400000, "net_income": 60000, "capex": 70000, "debt_repayment": 15000},
                    {"year": 3, "revenue": 650000, "net_income": 100000, "capex": 90000, "debt_repayment": 20000},
                    {"year": 4, "revenue": 850000, "net_income": 130000, "capex": 110000, "debt_repayment": 25000},
                    {"year": 5, "revenue": 1100000, "net_income": 170000, "capex": 130000, "debt_repayment": 30000}
                ],
                "analysis": "Analisi dei punti salienti finanziari: L'anno 0 rappresenta la situazione corrente. La crescita dei ricavi mostra un trend positivo con un CAGR del 43% nei successivi 5 anni. Il reddito netto migliora progressivamente, indicando una crescente efficienza operativa."
            }
        ]
    },
    "cashFlowAnalysis": {
        "type": "json",
        "description": "6 anni di rendiconto finanziario (Anno 0 = dati correnti, Anni 1-5 = proiezioni) secondo i principi contabili italiani (OIC) con terminologia italiana corretta.",
        "schema": [
            {
                "data": [{"year": "int", "operating": "float", "investing": "float", "financing": "float", "net_cash": "float"}],
                "analysis": "string"
            }
        ],
        "example": [
            {
                "data": [
                    {"year": 0, "operating": 60000, "investing": -30000, "financing": 5000, "net_cash": 35000},
                    {"year": 1, "operating": 80000, "investing": -50000, "financing": 10000, "net_cash": 40000},
                    {"year": 2, "operating": 120000, "investing": -70000, "financing": 15000, "net_cash": 50000},
                    {"year": 3, "operating": 200000, "investing": -90000, "financing": 20000, "net_cash": 110000},
                    {"year": 4, "operating": 280000, "investing": -110000, "financing": 25000, "net_cash": 145000},
                    {"year": 5, "operating": 380000, "investing": -130000, "financing": 30000, "net_cash": 200000}
                ],
                "analysis": "Analisi del flusso di cassa: L'anno 0 riflette la posizione corrente. Le Attività operative mostrano una crescita robusta, evidenziando una gestione efficiente del capitale circolante."
            }
        ]
    },
    "profitLossProjection": {
        "type": "json",
        "description": "6 years of profit & loss statement (Year 0 = current data from the provided input, Years 1-5 = projections) with detailed breakdown following Italian accounting principles.",
        "schema": [
            {
                "data": [{"year": "int", "revenue": "float", "cogs": "float", "gross_profit": "float", "operating_expenses": "float", "ebitda": "float", "depreciation_amortization": "float", "ebit": "float", "interest": "float", "taxes": "float", "net_income": "float"}],
                "analysis": "string"
            }
        ],
        "example": [
            {
                "data": [
                    {"year": 0, "revenue": 180000, "cogs": 72000, "gross_profit": 108000, "operating_expenses": 90000, "ebitda": 18000, "depreciation_amortization": 3000, "ebit": 15000, "interest": 1000, "taxes": 2000, "net_income": 15000},
                    {"year": 1, "revenue": 250000, "cogs": 100000, "gross_profit": 150000, "operating_expenses": 120000, "ebitda": 30000, "depreciation_amortization": 5000, "ebit": 25000, "interest": 2000, "taxes": 3000, "net_income": 30000}
                ],
                "analysis": "Analisi del conto economico: L'anno 0 rappresenta la performance corrente."
            }
        ]
    },
    "balanceSheet": {
        "type": "json",
        "description": "6 years of balance sheet following Italian accounting standards (Stato Patrimoniale) with proper Italian structure: Attività (Current/Non-Current), Passività (Current/Non-Current), Patrimonio Netto. Include interpretive commentary on financial position and ratios.",
        "schema": [
            {
                "data": [{"year": "int", "assets": "float", "current_assets": "float", "non_current_assets": "float", "liabilities": "float", "current_liabilities": "float", "non_current_liabilities": "float", "equity": "float"}],
                "analysis": "string"
            }
        ],
        "example": [
    {
        "data": [
            {"year": 0, "assets": 150000, "current_assets": 90000, "non_current_assets": 60000, "liabilities": 60000, "current_liabilities": 30000, "non_current_liabilities": 30000, "equity": 90000},
            {"year": 1, "assets": 160000, "current_assets": 95000, "non_current_assets": 65000, "liabilities": 62000, "current_liabilities": 31000, "non_current_liabilities": 31000, "equity": 98000},
            {"year": 2, "assets": 170000, "current_assets": 100000, "non_current_assets": 70000, "liabilities": 64000, "current_liabilities": 32000, "non_current_liabilities": 32000, "equity": 106000},
            {"year": 3, "assets": 180000, "current_assets": 105000, "non_current_assets": 75000, "liabilities": 66000, "current_liabilities": 33000, "non_current_liabilities": 33000, "equity": 114000},
            {"year": 4, "assets": 190000, "current_assets": 110000, "non_current_assets": 80000, "liabilities": 68000, "current_liabilities": 34000, "non_current_liabilities": 34000, "equity": 122000},
            {"year": 5, "assets": 200000, "current_assets": 115000, "non_current_assets": 85000, "liabilities": 70000, "current_liabilities": 35000, "non_current_liabilities": 35000, "equity": 130000}
        ],
        "analysis": "Il patrimonio netto mostra un rafforzamento progressivo..."
    }
]
    },
    "netFinancialPosition": {
        "type": "json",
        "description": "6 years of net financial position (Posizione Finanziaria Netta) following Italian accounting standards. Include interpretive commentary on liquidity and financial stability.",
        "schema": [
            {
                "data": [{"year": "int", "net_position": "float"}],
                "analysis": "string"
            }
        ],
        "example": [
            {
                "data":[
                    {"year": 1, "net_position": -50000},
                    {"year": 2, "net_position": -30000},
                    {"year": 3, "net_position": 10000}
                ],
                "analysis": "La posizione finanziaria netta migliora progressivamente, passando da indebitamento a liquidità positiva, riflettendo gestione efficiente del capitale circolante."
            }
        ]
    },
    "debtStructure": {
        "type": "json",
        "description": "6 years of debt structure and repayment schedule following Italian banking standards. Include interpretive commentary on debt management and cost of capital.",
        "schema": [
            {
                "data": [{"year": "int", "repayment": "float", "interest_rate": "float", "outstanding_debt": "float"}],
                "analysis": "string"
            }
        ],
        "example": [
            {
                "data": [
                    {"year": 1, "repayment": 10000, "interest_rate": 4.5, "outstanding_debt": 100000},
                    {"year": 2, "repayment": 15000, "interest_rate": 4.2, "outstanding_debt": 85000},
                    {"year": 3, "repayment": 20000, "interest_rate": 4.0, "outstanding_debt": 65000}
                ],
                "analysis": "Il piano di rimborso mostra riduzione progressiva del debito e ottimizzazione del costo del capitale, migliorando la leva finanziaria."
            }
        ]
    },
    "keyRatios": {
        "type": "json",
        "description": "6 years of key financial ratios following Italian financial analysis standards. Include interpretive commentary on ratio trends and industry comparisons.",
        "schema": [
            {
                "data": [{"year": "int", "roi": "float", "roe": "float", "debt_to_equity": "float", "gross_margin": "float", "ebitda_margin": "float", "net_margin": "float", "current_ratio": "float", "quick_ratio": "float", "asset_turnover": "float"}],
                "analysis": "string"
            }
        ],
        "example": [
            {
                "data": [
                    {"year": 1, "roi": 12.5, "roe": 15.2, "debt_to_equity": 2.0, "gross_margin": 60.0, "ebitda_margin": 12.0, "net_margin": 12.0, "current_ratio": 1.5, "quick_ratio": 1.2, "asset_turnover": 0.83},
                    {"year": 2, "roi": 15.8, "roe": 18.5, "debt_to_equity": 1.65, "gross_margin": 60.0, "ebitda_margin": 20.0, "net_margin": 15.0, "current_ratio": 1.54, "quick_ratio": 1.25, "asset_turnover": 0.89}
                ],
                "analysis": "Trend positivo dei principali indici: ROI e ROE in aumento, riduzione della leva finanziaria e miglioramento della liquidità."
            }
        ]
    },
    "financialAnalysis": {
        "type": "json",
        "description": "Comprehensive Italian financial analysis following Wayne SRL example structure with Italian GAAP standards and D.Lgs. 127/91 requirements. Include interpretive commentary on financial performance and position.",
        "schema": [
            {
                "data": [
                    {
                        "year": "int",
                        "gross_operating_cash_flow": "float",
                        "working_capital_change": "float",
                        "current_management_cash_flow": "float",
                        "operating_cash_flow": "float",
                        "debt_service_cash_flow": "float",
                        "shareholders_cash_flow": "float",
                        "net_cash_flow": "float",
                        "sales_revenue": "float",
                        "production_value": "float",
                        "gross_operating_margin": "float",
                        "ebit": "float",
                        "ebt": "float",
                        "net_income": "float",
                        "dividends": "float",
                        "net_tangible_assets": "float",
                        "net_intangible_assets": "float",
                        "financial_assets": "float",
                        "trade_assets": "float",
                        "inventory": "float",
                        "deferred_liquidity": "float",
                        "immediate_liquidity": "float",
                        "equity": "float",
                        "long_term_debt": "float",
                        "short_term_debt": "float",
                        "net_financial_position": "float",
                        "mortgage_loans": "float",
                        "other_financial_debts": "float",
                        "cash_and_banks": "float"
                    }
                ],
                "analysis": "Provide a full analysis of the datas within 200 words"
            }
        ],
        "example": [
            {
                "data": [
                    {
                        "year": 0,
                        "gross_operating_cash_flow": 60000,
                        "working_capital_change": -5000,
                        "current_management_cash_flow": 55000,
                        "operating_cash_flow": 60000,
                        "debt_service_cash_flow": 5000,
                        "shareholders_cash_flow": 10000,
                        "net_cash_flow": 45000,
                        "sales_revenue": 180000,
                        "production_value": 150000,
                        "gross_operating_margin": 108000,
                        "ebit": 15000,
                        "ebt": 14000,
                        "net_income": 15000,
                        "dividends": 2000,
                        "net_tangible_assets": 90000,
                        "net_intangible_assets": 30000,
                        "financial_assets": 5000,
                        "trade_assets": 40000,
                        "inventory": 20000,
                        "deferred_liquidity": 10000,
                        "immediate_liquidity": 15000,
                        "equity": 100000,
                        "long_term_debt": 50000,
                        "short_term_debt": 20000,
                        "net_financial_position": -55000,
                        "mortgage_loans": 25000,
                        "other_financial_debts": 15000,
                        "cash_and_banks": 15000
                    }
                ],
                "analysis": "L'anno 0 mostra una solida capacità di generazione di cassa operativa e gestione efficace del capitale circolante. La posizione finanziaria netta è negativa ma in miglioramento rispetto agli anni precedenti."
            }
        ]
    },
    "ratiosAnalysis": {
        "type": "json",
        "description": "Detailed Italian financial ratios analysis following Wayne SRL example with Italian financial indicators and interpretive commentary on ratio performance.",
        "schema": [
            {
                "data": [
                    {
                        "year": "int",
                        "roi": "float",
                        "roe": "float",
                        "ros": "float",
                        "ebit_margin": "float",
                        "net_debt_to_ebitda": "float",
                        "net_debt_to_equity": "float",
                        "net_debt_to_revenue": "float",
                        "current_ratio": "float",
                        "quick_ratio": "float",
                        "debt_to_equity": "float",
                        "treasury_margin": "float",
                        "structural_margin": "float",
                        "net_working_capital": "float",
                        "altman_z_score": "float"
                    }
                ],
                "analysis": "Provide a full analysis of the datas within 100 words"
            }
        ],
        "example": [
            {
                "data": [
                    {
                        "year": 0,
                        "roi": 12.5,
                        "roe": 15.0,
                        "ros": 8.5,
                        "ebit_margin": 10.0,
                        "net_debt_to_ebitda": 3.5,
                        "net_debt_to_equity": 0.55,
                        "net_debt_to_revenue": 0.3,
                        "current_ratio": 1.5,
                        "quick_ratio": 1.2,
                        "debt_to_equity": 0.55,
                        "treasury_margin": 0.25,
                        "structural_margin": 0.45,
                        "net_working_capital": 35000,
                        "altman_z_score": 2.5
                    }
                ],
                "analysis": "I principali indici finanziari mostrano stabilità: ROI e ROE positivi, leva finanziaria controllata e buona liquidità corrente."
            }
        ]
    },
    "productionSalesForecast": {
        "type": "json",
        "description": "Production and sales forecast following Italian market patterns with interpretive commentary on growth projections and market trends.",
        "schema": [
            {
                "data": [
                    {
                        "year": "int",
                        "sales_revenue": "float",
                        "revenue_growth": "float",
                        "units_sold": "int",
                        "average_price": "float",
                        "unit_production_cost": "float",
                        "unit_margin": "float"
                    }
                ],
                "analysis": "Provide a full analysis of the datas within 200 words"
            }
        ],
        "example": [
            {
                "data": [
                    {"year": 0, "sales_revenue": 180000, "revenue_growth": 0.0, "units_sold": 10000, "average_price": 18, "unit_production_cost": 10, "unit_margin": 8},
                    {"year": 1, "sales_revenue": 250000, "revenue_growth": 38.9, "units_sold": 12000, "average_price": 20, "unit_production_cost": 11, "unit_margin": 9}
                ],
                "analysis": "Previsioni di vendita mostrano crescita costante dei ricavi e margini unitari positivi grazie all'ottimizzazione dei costi di produzione."
            }
        ]
    },
    "managementTeam": {
        "type": "string",
        "description": "Detailed description about how management team should run. Do not add any sub secttions to it.",
        "min_words": 400
    }
}

# --------------- UTILITY FUNCTIONS ---------------

def clean_json_response(text: str) -> str:
    """Clean JSON response by removing code blocks and malformed content."""
    text = re.sub(r'^```json\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*```\s*$', '', text, flags=re.IGNORECASE)
    start = text.find('{')
    if start == -1:
        start = text.find('[')
    if start > 0:
        text = text[start:]
    end = max(text.rfind('}'), text.rfind(']'))
    if end < len(text) - 1 and end != -1:
        text = text[:end+1]
    text = re.sub(r',\s*]', ']', text)
    text = re.sub(r',\s*}', '}', text)
    return text.strip()

def fix_common_json_issues(text: str) -> str:
    """Fix common JSON formatting issues in API responses."""
    if not text:
        return text

    # Normalize whitespace and remove non-breaking spaces / control chars
    text = text.replace('\xa0', ' ')
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)

    # Remove code fences if present
    text = re.sub(r'^```json\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*```\s*$', '', text, flags=re.IGNORECASE)

    # --- Numeric cleanup ---
    # Remove underscores used as digit separators (e.g. 10_000 -> 10000)
    text = re.sub(r'(?<=\d)_(?=\d)', '', text)

    # Remove commas used as thousand separators (e.g. 10,000 -> 10000)
    text = re.sub(r'(?<=\d),(?=\d)', '', text)

    # Remove dots used as thousand separators (e.g. 10.000 -> 10000)
    # Only remove dot when it's followed by exactly 3 digits and not more (avoid removing decimal points)
    text = re.sub(r'(?<=\d)\.(?=\d{3}(?!\d))', '', text)

    # Remove spaces used as thousand separators (including NBSP)
    text = re.sub(r'(?<=\d)[\s\u00A0](?=\d{3}\b)', '', text)

    # Remove currency symbols adjacent to numbers or inside quotes (e.g. "€10.000" -> 10000)
    text = re.sub(r'["\']?€\s*([\d\.,_]+)["\']?', r'\1', text)
    text = re.sub(r'[£$¥]', '', text)

    # Remove grouping commas left before closing brackets/braces
    text = re.sub(r',\s*([}\]])', r'\1', text)

    # --- Structural fixes ---
    # Fix unquoted property names
    text = re.sub(r'(\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', text)

    # Convert single quotes to double quotes (avoid touching escaped quotes)
    text = re.sub(r"(?<!\\)'", '"', text)

    # Normalize Python-like literals to JSON
    text = re.sub(r'\bTrue\b', 'true', text)
    text = re.sub(r'\bFalse\b', 'false', text)
    text = re.sub(r'\bNone\b', 'null', text)

    # Clean up any stray commas in numbers or trailing separators
    text = re.sub(r'(\d),\s*([}\]])', r'\1\2', text)
    text = re.sub(r',\s*,', ',', text)

    return text.strip()

def extract_and_fix_json(text: str) -> str:
    """Extract and fix JSON from potentially malformed text."""
    # Find the JSON boundaries more precisely
    brace_count = 0
    start_pos = -1
    
    for i, char in enumerate(text):
        if char == '{':
            if start_pos == -1:
                start_pos = i
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0 and start_pos != -1:
                json_str = text[start_pos:i+1]
                # Clean up the extracted JSON
                json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)
                json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
                return json_str
    
    return text

def robust_json_load(text: str) -> dict:
    """Robust JSON parsing with multiple fallback strategies."""
    if not text or not text.strip():
        return {}
    
    # First try to extract clean JSON
    text = extract_and_fix_json(text.strip())
    
    strategies = [
        lambda: json.loads(text),
        lambda: json.loads(fix_common_json_issues(text)),
        lambda: json.loads(text.replace("'", '"')),
        lambda: json.loads(re.sub(r'(\w+):', r'"\1":', text)),  # Fix unquoted keys
        lambda: json.loads(re.sub(r',\s*}', '}', re.sub(r',\s*]', ']', text))),  # Remove trailing commas
    ]
    
    for i, strategy in enumerate(strategies):
        try:
            result = strategy()
            logger.info(f"JSON parsing successful with strategy {i + 1}")
            return result
        except (json.JSONDecodeError, AttributeError, ValueError) as e:
            logger.warning(f"Strategy {i + 1} failed: {e}")
            continue
    
    # Final fallback - try to manually construct valid JSON
    logger.error(f"All JSON parsing strategies failed. Text sample: {text[:500]}")
    raise ValueError(f"Could not parse JSON from response: {text[:200]}...")

def ensure_6_years(section_content: Any, recent_data: Dict = None, section_key: str = None) -> List[Dict]:
    """Ensure exactly one object with 6 years of data for numerical sections."""
    
    # Handle the case where OpenAI returns the wrong structure
    if isinstance(section_content, list):
        if len(section_content) > 0 and isinstance(section_content[0], dict):
            if 'data' in section_content[0]:
                # Already correct structure - return first item only
                section_content = section_content[0]
            else:
                # Raw data array - wrap it
                section_content = {"data": section_content, "analysis": ""}
        else:
            # Empty or malformed - create empty structure
            section_content = {"data": [], "analysis": ""}
    elif isinstance(section_content, dict):
        if 'data' not in section_content:
            # Assume it's raw data
            section_content = {"data": [section_content] if section_content else [], "analysis": ""}
    else:
        # Not expected format
        section_content = {"data": [], "analysis": ""}

    # Ensure we have exactly 6 years in the data array
    data_array = section_content.get("data", [])
    
    # Extract Year 0 data from uploaded file if available
    year_0_template = {}
    if recent_data:
        # Handle financial_data from PDF extraction
        if "financial_data" in recent_data:
            financial_data = recent_data["financial_data"]
            year_0_template = {
                "year": 0,
                "revenue": financial_data.get("total_revenue", 0),
                "net_income": financial_data.get("net_income", 0),
                "assets": financial_data.get("total_assets", 0),
                "liabilities": financial_data.get("total_liabilities", 0),
                "equity": financial_data.get("equity", 0)
            }
        
        # Handle previous_sections from sequential generation
        elif "previous_sections" in recent_data and section_key:
            prev_sections = recent_data["previous_sections"]
            
            # Extract Year 0 from P&L for other financial sections
            if "profitLossProjection" in prev_sections:
                pl_data = prev_sections["profitLossProjection"]
                if isinstance(pl_data, list) and len(pl_data) > 0:
                    pl_year_0 = next((item for item in pl_data[0].get("data", []) if item.get("year") == 0), None)
                    if pl_year_0:
                        year_0_template.update({
                            "year": 0,
                            "revenue": pl_year_0.get("revenue", 0),
                            "net_income": pl_year_0.get("net_income", 0),
                            "cogs": pl_year_0.get("cogs", 0),
                            "gross_profit": pl_year_0.get("gross_profit", 0),
                            "ebit": pl_year_0.get("ebit", 0)
                        })
            
            # Extract Year 0 from Balance Sheet for cash flow
            if "balanceSheet" in prev_sections and section_key == "cashFlowAnalysis":
                bs_data = prev_sections["balanceSheet"]
                if isinstance(bs_data, list) and len(bs_data) > 0:
                    bs_year_0 = next((item for item in bs_data[0].get("data", []) if item.get("year") == 0), None)
                    if bs_year_0:
                        year_0_template.update({
                            "assets": bs_year_0.get("assets", 0),
                            "liabilities": bs_year_0.get("liabilities", 0),
                            "equity": bs_year_0.get("equity", 0)
                        })
    
    # If we have no data, create structure for 6 years with Year 0 from template
    if not data_array:
        for year in range(6):
            if year == 0 and year_0_template:
                data_array.append(year_0_template)
            else:
                data_array.append({"year": year})
    else:
        # Force Year 0 to use uploaded/previous data if available
        year_0_exists = False
        for i, item in enumerate(data_array):
            if isinstance(item, dict) and item.get("year") == 0:
                year_0_exists = True
                if year_0_template:
                    # Merge uploaded data with generated data, prioritizing uploaded
                    for key, value in year_0_template.items():
                        if value and value != 0:  # Only override with real data
                            data_array[i][key] = value
                break
        
        # If Year 0 doesn't exist but we have template, add it
        if not year_0_exists and year_0_template:
            data_array.append(year_0_template)
        
        # Fill missing years 1-5 with realistic projections
        years_present = {item.get("year", -1) for item in data_array if isinstance(item, dict)}
        
        for year in range(6):  # Years 0-5
            if year not in years_present:
                # Create projected data based on previous years
                if year == 0 and year_0_template:
                    # Use template data for year 0
                    data_array.append(year_0_template)
                elif data_array:
                    # Find the closest previous year to base projections on
                    previous_years = [item for item in data_array if item.get("year", -1) < year]
                    if previous_years:
                        # Use the most recent previous year as template
                        template = max(previous_years, key=lambda x: x.get("year", 0)).copy()
                        
                        # Apply growth factors based on year difference
                        year_diff = year - template.get("year", 0)
                        
                        # Base growth rate (15% annual)
                        base_growth = 0.15
                        
                        # Diminishing growth over time (Year 1: 20%, Year 2: 18%, Year 3: 16%...)
                        growth_factor = 1.0 + (base_growth * (1.0 - (year * 0.02)))
                        
                        # Apply year difference
                        growth_multiplier = growth_factor ** year_diff
                        
                        # Update numeric fields with growth projections
                        for key, value in template.items():
                            if isinstance(value, (int, float)) and key != "year":
                                if "rate" in key.lower() or "ratio" in key.lower():
                                    # Keep rates and ratios relatively stable with slight improvement
                                    template[key] = round(value * (1.0 + (0.02 * year_diff)), 2)
                                elif "margin" in key.lower():
                                    # Slight margin improvement capped at 5% growth
                                    margin_growth = min(0.05 * year_diff, 0.15)
                                    template[key] = round(value * (1.0 + margin_growth), 2)
                                elif "debt" in key.lower() and value < 0:
                                    # Debt reduction over time (paying down)
                                    reduction_factor = 0.90 ** year_diff  # 10% reduction per year
                                    template[key] = round(value * reduction_factor, 2)
                                elif value > 0:
                                    # Apply growth to positive values
                                    template[key] = round(value * growth_multiplier, 2)
                                elif value < 0:
                                    # Apply growth to negative values (expenses, etc.)
                                    # Expenses grow slower than revenue (efficiency improvement)
                                    expense_growth = growth_multiplier * 0.85  # 85% of revenue growth
                                    template[key] = round(value * expense_growth, 2)
                        
                        template["year"] = year
                        new_year_data = template
                    else:
                        # No previous data, create minimal structure
                        new_year_data = {"year": year}
                else:
                    # Minimal structure
                    new_year_data = {"year": year}
                
                data_array.append(new_year_data)
    
    # Sort by year and keep only 6 years
    data_array = sorted([item for item in data_array if isinstance(item, dict)], 
                       key=lambda x: x.get("year", 0))[:6]
    
    # Ensure all years 0-5 are present and in order
    final_data_array = []
    for year in range(6):
        year_data = next((item for item in data_array if item.get("year") == year), None)
        if year_data:
            # Validate and fix financial relationships
            year_data = validate_financial_relationships(year_data, section_key)
            final_data_array.append(year_data)
        else:
            # Create empty data for missing year with template if Year 0
            if year == 0 and year_0_template:
                final_data_array.append(year_0_template)
            else:
                final_data_array.append({"year": year})
    
    # Ensure analysis is present
    analysis = section_content.get("analysis", "")
    if not analysis:
        analysis = f"Analisi finanziaria per 6 anni (Anno 0-5). Anno 0 rappresenta i dati correnti, Anni 1-5 sono proiezioni basate su ipotesi di crescita realistiche."
    
    # Return single object with data array and analysis
    return [{
        "data": final_data_array,
        "analysis": analysis
    }]


def validate_financial_relationships(year_data: dict, section_key: str = None) -> dict:
    """Validate and auto-correct financial relationships within a year's data"""
    
    if not section_key:
        return year_data
    
    # Profit & Loss validations
    if section_key == "profitLossProjection":
        revenue = year_data.get("revenue", 0)
        cogs = year_data.get("cogs", 0)
        
        # Ensure COGS doesn't exceed revenue (cap at 70%)
        if cogs > revenue * 0.7:
            year_data["cogs"] = round(revenue * 0.6, 2)
            cogs = year_data["cogs"]
        
        # Recalculate gross_profit
        year_data["gross_profit"] = round(revenue - cogs, 2)
        
        # Validate operating expenses
        operating_exp = year_data.get("operating_expenses", 0)
        if operating_exp > revenue * 0.5:
            year_data["operating_expenses"] = round(revenue * 0.4, 2)
        
        # Recalculate EBITDA
        year_data["ebitda"] = round(year_data["gross_profit"] - year_data["operating_expenses"], 2)
        
        # Ensure net_income is reasonable
        if year_data.get("net_income", 0) > revenue:
            year_data["net_income"] = round(year_data.get("ebitda", 0) * 0.7, 2)
    
    # Balance Sheet validations
    elif section_key == "balanceSheet":
        assets = year_data.get("assets", 0)
        liabilities = year_data.get("liabilities", 0)
        equity = year_data.get("equity", 0)
        
        # Ensure accounting equation: Assets = Liabilities + Equity
        calculated_equity = round(assets - liabilities, 2)
        if abs(calculated_equity - equity) > 1:  # Allow 1 unit rounding error
            year_data["equity"] = calculated_equity
        
        # Validate current vs non-current splits
        current_assets = year_data.get("current_assets", 0)
        non_current_assets = year_data.get("non_current_assets", 0)
        if current_assets + non_current_assets != assets:
            # Default split: 60% current, 40% non-current
            year_data["current_assets"] = round(assets * 0.6, 2)
            year_data["non_current_assets"] = round(assets * 0.4, 2)
        
        current_liabilities = year_data.get("current_liabilities", 0)
        non_current_liabilities = year_data.get("non_current_liabilities", 0)
        if current_liabilities + non_current_liabilities != liabilities:
            # Default split: 50% each
            year_data["current_liabilities"] = round(liabilities * 0.5, 2)
            year_data["non_current_liabilities"] = round(liabilities * 0.5, 2)
    
    # Cash Flow validations
    elif section_key == "cashFlowAnalysis":
        operating = year_data.get("operating", 0)
        investing = year_data.get("investing", 0)
        financing = year_data.get("financing", 0)
        
        # Recalculate net_cash
        year_data["net_cash"] = round(operating + investing + financing, 2)
        
        # Investing should typically be negative (outflow)
        if investing > 0 and operating > 0:
            year_data["investing"] = round(-operating * 0.3, 2)  # 30% of operating as capex
    
    return year_data

def create_empty_individual_section(section_key: str) -> dict:
    """Create empty section content based on section type."""
    schema = INDIVIDUAL_SECTION_SCHEMAS.get(section_key, {})
    if schema.get("type") == "string":
        return {section_key: ""}
    else:
        return {section_key: []}

# --------------- PROMPT BUILDING ---------------

def build_individual_section_prompt(section_key: str, language: str = "Italian", 
                                   currency: str = "EUR", recent_data: dict = None) -> str:
    """Build specialized prompt for a single section."""
    if section_key not in INDIVIDUAL_SECTION_SCHEMAS:
        raise ValueError(f"Unknown section: {section_key}")
    
    schema = INDIVIDUAL_SECTION_SCHEMAS[section_key]
    section_type = schema["type"]
    description = schema["description"]
    
    disclaimer = "NOTA: Questo business plan è stato generato automaticamente e deve essere considerato come documento preliminare. Si raccomanda la verifica con un commercialista italiano qualificato prima dell'utilizzo."
    
    recent_data_context = ""
    if recent_data and section_type == "json":
        recent_data_context = f"\nDATI RECENTI (ANNO 0): {json.dumps(recent_data, indent=2)}\n\nIMPORTANTE: L'anno 0 deve riflettere i dati correnti forniti. Gli anni 1-5 devono essere proiezioni realistiche basate su questi dati."
    
    if section_type == "string":
        min_words = schema.get("min_words", 0)
        return f"""
Sei un esperto senior di business plan italiano. Genera SOLAMENTE la sezione {section_key} per un business plan completo.

REQUISITI:
- Lingua: {language}
- Valuta: {currency}
- Conteggio parole: Minimo {min_words} parole
- Formato: JSON con chiave "{section_key}"
- Standard: OIC e D.Lgs. 127/91

DESCRIZIONE: {description}
{recent_data_context}
DISCLAIMER: {disclaimer}

ISTRUZIONI:
1. Output SOLAMENTE JSON: {{"{section_key}": "contenuto qui"}}
2. Minimo {min_words} parole
3. Nessun markdown o testo extra
4. Contenuto professionale e completo
"""
    else:
        example = schema.get("example", [])
        example_json = json.dumps({section_key: example}, indent=2)
        return f"""
Sei un analista finanziario senior italiano. Genera SOLAMENTE la sezione {section_key}.

REQUISITI:
- Lingua: {language}
- Valuta: {currency}
- Formato: JSON con chiave "{section_key}"
- Standard: OIC e D.Lgs. 127/91
- Periodo: 6 anni (Anno 0 = dati correnti, Anni 1-5 = proiezioni)

DESCRIZIONE: {description}
{recent_data_context}
DISCLAIMER: {disclaimer}

STRUTTURA:
{example_json}

# ADD THESE CONSTRAINTS to financial section prompts:
ISTRUZIONI CRITICHE:
- Anno 0 DEVE utilizzare i dati reali forniti ESATTAMENTE
- Crescita annuale: 10-30% massimo (NON 100%+)
- MAKE SURE EVERY COST DATA IS IN K , NOTHING IN MILLION (M)
- Revenue DEVE essere > COGS sempre
- Net Income DEVE essere < Revenue
- Total Assets = Liabilities + Equity (OBBLIGATORIO)
- NO numeri casuali - calcolare matematicamente
- Se Anno 0 revenue=180000, Anno 1 può essere 200000-234000 SOLO
"""





# --------------- SECTION GENERATION ---------------

async def call_individual_section(
    client, section_key: str, context: str, model: str,
    language: str = "Italian", currency: str = "EUR",
    recent_data: dict = None, max_retries: int = MAX_RETRIES
) -> dict:
    """Generate a single section of the business plan."""
    prompt = build_individual_section_prompt(section_key, language, currency, recent_data)

    for attempt in range(max_retries):
        try:
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": context}
            ]
            
            response = await client.chat.completions.create(
                messages=messages,
                model=model,
                temperature=0.1,
                max_tokens=12000
            )
            
            content = response.choices[0].message.content.strip()
            content = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', content)
            logger.info(f"Raw API response for {section_key}: {content[:200]}")

            # Parse JSON
            result = robust_json_load(content)
            if section_key not in result:
                raise ValueError(f"Missing key {section_key} in response")

            section_content = result[section_key]
            schema = INDIVIDUAL_SECTION_SCHEMAS[section_key]

            # Validate and process content based on type
            if schema["type"] == "string":
                if isinstance(section_content, dict):
                    # If we got a dict instead of string, convert it to plain text
                    section_content = " ".join([str(value) for value in section_content.values() if value])
                elif isinstance(section_content, list):
                    # If we got a list, join all elements into a string
                    section_content = " ".join([str(item) for item in section_content if item])
                elif not isinstance(section_content, str):
                    section_content = str(section_content) if section_content else ""
                
                # Remove any JSON-like structure from the text
                section_content = re.sub(r'^{.*?"([^"]+)":\s*"([^"]*)"', r'\2', section_content)
                section_content = re.sub(r'"\s*}\s*$', '', section_content)
                
                # Check word count instead of character count
                min_words = schema.get("min_words", 50)
                word_count = len(section_content.split())
                
                if word_count < min_words:
                    logger.warning(f"Content too short for {section_key}: {word_count} words, need {min_words}")
                    if word_count == 0:
                        raise ValueError(f"Empty content for {section_key}")
            else:
                section_content = ensure_6_years(section_content, recent_data)
                result[section_key] = section_content

            # --- NORMALIZE localized outputs into expected schema ---
            section_content = normalize_localized_section(section_key, section_content)
            # --- END NORMALIZATION ---

            # Additional validation for financial sections
            schema = INDIVIDUAL_SECTION_SCHEMAS.get(section_key, {})
            if schema.get("type") == "json":
                if not validate_financial_data(section_key, section_content):
                    raise ValueError(f"Financial data validation failed for {section_key}")


            return result

        except Exception as e:
            logger.warning(f"Attempt {attempt+1} failed for {section_key}: {e}")
            if attempt == max_retries - 1:
                logger.error(f"All retries failed for {section_key}, returning fallback.")
                return create_empty_individual_section(section_key)

            await asyncio.sleep(2 ** attempt + 0.5)

# --------------- MAIN BUSINESS PLAN GENERATOR ---------------


def validate_financial_data(section_key: str, data: List[Dict]) -> bool:
    """Add to services.py - call before returning from call_individual_section"""
    
    if section_key == "profitLossProjection":
        for item in data[0]["data"]:
            # Check basic accounting rules
            if item.get("revenue", 0) < item.get("cogs", 0):
                return False
            if item.get("gross_profit", 0) != (item.get("revenue", 0) - item.get("cogs", 0)):
                return False
            if item.get("net_income", 0) > item.get("revenue", 0):
                return False
    
    if section_key == "balanceSheet":
            return validate_balance_sheet(data)


    if section_key == "balanceSheet":
        for item in data[0]["data"]:
            # Assets must equal Liabilities + Equity
            assets = item.get("assets", 0)
            liabilities = item.get("liabilities", 0)
            equity = item.get("equity", 0)
            if abs(assets - (liabilities + equity)) > 1:  # Allow 1 unit rounding
                return False
    
    return True

# # In call_individual_section, BEFORE returning:
# if schema["type"] == "json":
#     if not validate_financial_data(section_key, section_content):
#         raise ValueError(f"Financial data validation failed for {section_key}")


async def generate_business_plan(
    uploaded_file: Optional[str] = None,
    user_input: List[Any] = None,
    user_id: str = None,
    language: str = "Italian",
    currency: str = "EUR"
) -> dict:
    """Generate complete business plan with all sections."""
    settings = get_settings()
    client = get_openai_client()

    # Process input data with smart summarization for large inputs
    business_context = []
    if user_input:
        for item in user_input:
            if isinstance(item, str):
                if len(item) > MAX_INPUT_LENGTH:
                    # Summarize large inputs instead of truncating
                    business_context.append(await summarize_large_input(client, item, settings.model_name))
                else:
                    business_context.append(item)
            else:
                business_context.append(str(item))

    # Build context
    context = "Business Plan Analysis:\n"
    if business_context:
        context += "\n".join([f"- {item}" for item in business_context])
    
    # Handle uploaded file
    if uploaded_file:
        if isinstance(uploaded_file, str):
            if len(uploaded_file) > MAX_INPUT_LENGTH:
                uploaded_file = await summarize_large_input(client, uploaded_file, settings.model_name)
            context += f"\nDocument Analysis:\n{uploaded_file}"
        elif isinstance(uploaded_file, list):
            # Handle multiple files
            for file_data in uploaded_file:
                if isinstance(file_data, dict):
                    file_str = json.dumps(file_data)
                    if len(file_str) > MAX_INPUT_LENGTH:
                        file_str = await summarize_large_input(client, file_str, settings.model_name)
                    context += f"\nDocument Analysis:\n{file_str}"

    # Parse uploaded data to extract financial information
    uploaded_json = {}
    if uploaded_file:
        try:
            if isinstance(uploaded_file, str):
                uploaded_json = json.loads(uploaded_file)
            elif isinstance(uploaded_file, list):
                # Merge multiple files
                for file_data in uploaded_file:
                    if isinstance(file_data, dict):
                        uploaded_json.update(file_data)
        except Exception as e:
            logger.warning(f"Could not parse uploaded file as JSON: {e}")

    # Extract financial data from uploaded files
    financial_context = {}
    if uploaded_json:
        for key, value in uploaded_json.items():
            if key == "uploaded_file" and isinstance(value, list):
                for doc in value:
                    if isinstance(doc, dict) and "financial_data" in doc:
                        financial_context["financial_data"] = doc["financial_data"]
                        break

    # Define section generation order (sequential for dependencies)
    section_order = [
        # Text sections first
        "executiveSummary",
        "businessOverview",
        "marketAnalysis",
        "businessModel",
        "marketingSalesStrategy",
        "managementTeam",
        
        # Financial sections in dependency order
        "profitLossProjection",  # Base financial data
        "balanceSheet",                # Uses P&L data
        "cashFlowAnalysis",           # Uses P&L + Balance Sheet
        "financialHighlights",         # Summary of above
        "netFinancialPosition",       # Uses Balance Sheet
        "debtStructure",               # Uses Balance Sheet
        "keyRatios",                   # Uses all financial data
        "financialAnalysis",           # Wayne SRL style analysis
        "ratiosAnalysis",              # Advanced ratios
        "productionSalesForecast"     # Sales projections
    ]

    # Generate sections sequentially with context passing
    merged_plan = {}
    
    for section_key in section_order:
        try:
            logger.info(f"Generating section: {section_key}")
            
            # Build recent_data with financial context and previous sections
            recent_data = {}
            if financial_context:
                recent_data.update(financial_context)
            
            # For financial sections, include previous financial sections as context
            if section_key in ["balanceSheet", "cashFlowAnalysis", "financialHighlights", 
                              "netFinancialPosition", "debtStructure", "keyRatios",
                               "financialAnalysis", 
                              "ratiosAnalysis", "productionSalesForecast"]:
                # Only pass previous sections that are structured (list/dict) to avoid strings
                recent_data["previous_sections"] = {
                    k: v for k, v in merged_plan.items()
                    if k in ["profitLossProjection", "balanceSheet", "cashFlowAnalysis"]
                    and isinstance(v, (dict, list))
                }
            
            # Generate section
            result = await call_individual_section(
                client, 
                section_key, 
                context, 
                settings.model_name,
                language=language, 
                currency=currency, 
                recent_data=recent_data
            )
            
            # Validate result
            if isinstance(result, dict) and section_key in result:
                section_content = result[section_key]
                
                # --- NORMALIZE localized outputs into expected schema ---
                section_content = normalize_localized_section(section_key, section_content)
                # --- END NORMALIZATION ---

                # Additional validation for financial sections
                schema = INDIVIDUAL_SECTION_SCHEMAS.get(section_key, {})
                if schema.get("type") == "json":
                    # Ensure proper structure
                    if not isinstance(section_content, list) or len(section_content) == 0:
                        logger.warning(f"Invalid structure for {section_key}, using fallback")
                        section_content = create_empty_individual_section(section_key)[section_key]
                    else:
                        # Validate financial consistency
                        if not validate_financial_section(section_key, section_content):
                            logger.warning(f"Financial validation failed for {section_key}, regenerating...")
                            # Retry once with stricter prompt
                            result = await call_individual_section(
                                client, 
                                section_key, 
                                context + "\n\nIMPORTANT: Ensure all financial calculations are mathematically correct.", 
                                settings.model_name,
                                language=language, 
                                currency=currency, 
                                recent_data=recent_data
                            )
                            section_content = result.get(section_key, create_empty_individual_section(section_key)[section_key])
                
                merged_plan[section_key] = section_content
                logger.info(f"Successfully generated {section_key}")
            else:
                logger.error(f"Invalid result structure for {section_key}")
                merged_plan[section_key] = create_empty_individual_section(section_key)[section_key]
            
            # Small delay between API calls to avoid rate limiting
            await asyncio.sleep(1.5)
            
        except Exception as e:
            logger.error(f"Failed to generate section {section_key}: {e}", exc_info=True)
            merged_plan[section_key] = create_empty_individual_section(section_key)[section_key]

    return merged_plan


async def summarize_large_input(client, text: str, model: str, max_length: int = 50000) -> str:
    """Summarize large input text while preserving key information"""
    if len(text) <= max_length:
        return text
    
    try:
        summary_prompt = """Summarize this business document for a business plan. 
Keep ALL numerical data, financial figures, dates, and key facts EXACTLY as stated.
Focus on: company info, products/services, market data, financials, team, goals.
Maximum 3000 words."""
        
        messages = [
            {"role": "system", "content": summary_prompt},
            {"role": "user", "content": text[:80000]}  # Limit to avoid token overflow
        ]
        
        response = await client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=0.1,
            max_tokens=4000
        )
        
        summary = response.choices[0].message.content.strip()
        logger.info(f"Summarized large input from {len(text)} to {len(summary)} characters")
        return summary
        
    except Exception as e:
        logger.error(f"Failed to summarize large input: {e}")
        # Fallback to truncation if summarization fails
        return text[:max_length] + "\n\n[Content truncated due to length]"


def validate_financial_section(section_key: str, section_content: List[Dict]) -> bool:
    """Enhanced validation with required fields check"""
    try:
        if not isinstance(section_content, list) or not section_content:
            return False
            
        required_fields = {
            'balanceSheet': ['assets', 'liabilities', 'equity'],
            'cashFlowAnalysis': ['operating', 'investing', 'financing', 'net_cash'],
            'financialHighlights': ['revenue', 'net_income', 'capex']
        }
        
        data = section_content[0].get('data', [])
        if not data:
            return False
            
        # Check required fields
        fields = required_fields.get(section_key, [])
        for item in data:
            if not all(field in item for field in fields):
                logger.warning(f"Missing required fields in {section_key}")
                return False
                
            # Ensure no None values
            if any(item.get(field) is None for field in fields):
                logger.warning(f"None values found in {section_key}")
                return False
                
        return True
        
    except Exception as e:
        logger.error(f"Validation error in {section_key}: {e}")
        return False


# Add to services.py after the validate_financial_section function

def validate_balance_sheet(data: List[Dict]) -> bool:
    """
    Validates balance sheet data ensuring:
    1. Assets = Liabilities + Equity
    2. All required fields are present and non-negative
    3. Sub-components add up correctly
    """
    try:
        if not isinstance(data, list) or not data:
            return False

        for item in data[0].get('data', []):
            # Check required fields existence
            required_fields = ['assets', 'liabilities', 'equity', 'year']
            if not all(field in item for field in required_fields):
                logger.warning(f"Missing required fields in balance sheet for year {item.get('year')}")
                return False

            # Ensure values are numbers and non-None
            for field in required_fields:
                if not isinstance(item.get(field), (int, float)):
                    logger.warning(f"Invalid {field} value in balance sheet: {item.get(field)}")
                    return False

            # Verify accounting equation: Assets = Liabilities + Equity
            assets = float(item['assets'])
            liabilities = float(item['liabilities'])
            equity = float(item['equity'])
            
            # Allow for small rounding differences (0.01 or 1% tolerance)
            tolerance = max(0.01, assets * 0.01)
            if abs(assets - (liabilities + equity)) > tolerance:
                logger.warning(f"Balance sheet equation doesn't balance for year {item['year']}")
                logger.warning(f"Assets: {assets}, Liabilities: {liabilities}, Equity: {equity}")
                logger.warning(f"Difference: {assets - (liabilities + equity)}")
                return False

            # Verify sub-components if present
            if 'current_assets' in item and 'non_current_assets' in item:
                total_assets = float(item['current_assets']) + float(item['non_current_assets'])
                if abs(total_assets - assets) > tolerance:
                    logger.warning(f"Assets components don't sum correctly in year {item['year']}")
                    return False

            if 'current_liabilities' in item and 'non_current_liabilities' in item:
                total_liabilities = float(item['current_liabilities']) + float(item['non_current_liabilities'])
                if abs(total_liabilities - liabilities) > tolerance:
                    logger.warning(f"Liabilities components don't sum correctly in year {item['year']}")
                    return False

    except Exception as e:
        logger.error(f"Balance sheet validation error: {e}")
        return False

    return True



# --------------- SUGGESTION FUNCTION ---------------

SUGGESTION_PROMPT = """
You are an expert business plan consultant. Generate 4 different possible professional answers for the following business plan question. 
Keep each answer concise (Less than 10 words).
MAKE SURE ALL IS IN ITALIAN LANGUAGE.
Return the answers in a clean JSON array format.

Question: {question}

Return ONLY a valid JSON array of strings, no additional text or explanations.
"""

async def generate_suggestions(question: str) -> List[str]:
    """Generate suggestion options for business plan questions."""
    settings = get_settings()
    client = get_openai_client()

    messages = [{"role": "system", "content": SUGGESTION_PROMPT.format(question=question)}]

    try:
        response = await client.chat.completions.create(
            messages=messages,
            model=settings.model_name,
            temperature=0.3,
            max_tokens=100
        )
        
        content = response.choices[0].message.content.strip()
        
        # Clean content
        if content.startswith("```"):
            content = re.sub(r"^```(json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
        
        suggestions = json.loads(content)
        
        if not isinstance(suggestions, list):
            raise ValueError("Expected a list of strings")
            
        return suggestions[:4]
        
    except Exception as e:
        logger.error(f"Error generating suggestions: {e}")
        return [
            "Bootstrapping with personal funds",
            "Seeking angel investment", 
            "Applying for business loans",
            "Crowdfunding campaign"
        ]

def normalize_localized_section(section_key: str, section_content: Any) -> Any:
    """Normalize localized/nested outputs into expected schema shapes."""
    if not section_content:
        return section_content

    # Normalize balanceSheet Italian nested structure to expected flat keys
    if section_key == "balanceSheet" and isinstance(section_content, list):
        try:
            obj = section_content[0]
            data = obj.get("data", [])
            new_data = []
            for item in data:
                if not isinstance(item, dict):
                    new_data.append(item); continue

                # If nested italian keys exist, map them
                # expected: assets, current_assets, non_current_assets, liabilities, current_liabilities, non_current_liabilities, equity
                mapped = {}
                mapped["year"] = item.get("year", item.get("anno", None))

                # handle nested "attivita" / "passivita" / "patrimonio_netto"
                att = item.get("attivita") or item.get("attività") or item.get("assets")
                if isinstance(att, dict):
                    mapped["current_assets"] = att.get("correnti") or att.get("corrente") or att.get("current_assets") or att.get("currentAsset")
                    mapped["non_current_assets"] = att.get("non_correnti") or att.get("nonCorrenti") or att.get("non_current_assets")
                    mapped["assets"] = att.get("totale") or att.get("totale_attivita") or att.get("totale") or att.get("assets")
                else:
                    # maybe already flat with Italian names
                    mapped["assets"] = item.get("totale") or item.get("assets") or att

                pas = item.get("passivita") or item.get("passività") or item.get("liabilities")
                if isinstance(pas, dict):
                    mapped["current_liabilities"] = pas.get("correnti") or pas.get("corrente") or pas.get("current_liabilities")
                    mapped["non_current_liabilities"] = pas.get("non_correnti") or pas.get("non_current_liabilities")
                    mapped["liabilities"] = pas.get("totale") or pas.get("totale_passivita") or pas.get("totale") or pas.get("liabilities")
                else:
                    mapped["liabilities"] = item.get("totale_passivita") or item.get("liabilities") or pas

                mapped["equity"] = item.get("patrimonio_netto") or item.get("patrimonio") or item.get("equity")

                # Fallbacks: copy over existing expected keys if present
                for k in ["assets", "current_assets", "non_current_assets", "liabilities", "current_liabilities", "non_current_liabilities", "equity"]:
                    if mapped.get(k) is None and k in item:
                        mapped[k] = item.get(k)

                # ensure numeric types remain numbers (attempt conversion)
                for k, v in list(mapped.items()):
                    if isinstance(v, str):
                        try:
                            mapped[k] = float(v.replace(',', '').replace(' ', ''))
                        except Exception:
                            pass

                new_data.append(mapped)
            return [{"data": new_data, "analysis": obj.get("analysis", "")}]
        except Exception:
            return section_content

    return section_content
