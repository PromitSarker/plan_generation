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
    "executive_summary": {
        "type": "string",
        "description": "Summarize the overall business opportunity in 300+ words: include the core product or service, the market need it addresses, key team strengths, business traction (if any), and the long-term vision. Highlight why this business matters now.",
        "min_words": 300
    },
    "business_overview": {
        "type": "string", 
        "description": "Describe the company's mission, vision, and founding story. Include when and why it was started, what goals it seeks to achieve, where it is currently based, and what motivates the team behind it.",
        "min_words": 500
    },
    "market_analysis": {
        "type": "string",
        "description": "Provide an analysis of the market: total addressable market (TAM), serviceable available market (SAM), and obtainable market (SOM). Identify competitors, customer segments, market trends, and why the timing is right for this solution.",
        "min_words": 700
    },
    "business_model": {
        "type": "string",
        "description": "Explain how the business makes money. Describe primary and secondary revenue streams, customer acquisition strategy, pricing model, cost structure, margins, and how the model scales over time.",
        "min_words": 500
    },
    "marketing_and_sales_strategy": {
        "type": "string",
        "description": "Describe how the business plans to go to market. Include positioning, target customers, sales channels (online/offline), customer acquisition cost (CAC) strategies, conversion funnels, and how growth will be driven operationally.",
        "min_words": 500
    },
    "financial_highlights": {
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
    "cash_flow_analysis": {
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
    "profit_and_loss_projection": {
        "type": "json",
        "description": "6 years of profit & loss statement (Year 0 = current data, Years 1-5 = projections) with detailed breakdown following Italian accounting principles.",
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
    "balance_sheet": {
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
                    {"year": 1, "assets": 300000, "current_assets": 150000, "non_current_assets": 150000, "liabilities": 200000, "current_liabilities": 100000, "non_current_liabilities": 100000, "equity": 100000},
                    {"year": 2, "assets": 450000, "current_assets": 200000, "non_current_assets": 250000, "liabilities": 280000, "current_liabilities": 130000, "non_current_liabilities": 150000, "equity": 170000}
                ],
                "analysis": "Il patrimonio netto mostra un rafforzamento progressivo e il rapporto debito/capitale si riduce, segnalando maggiore solidità finanziaria. Gli investimenti in immobilizzazioni aumentano la capacità produttiva."
            }
        ]
    },
    "net_financial_position": {
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
    "debt_structure": {
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
    "key_ratios": {
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
    "financial_analysis": {
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
    "ratios_analysis": {
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
                "analysis": "Provide a full analysis of the datas within 200 words"
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
    "production_sales_forecast": {
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
    "management_team": {
        "type": "string",
        "description": "Detailed description of the management team following Italian business standards. Include roles, experience, and responsibilities of each key team member.",
        "min_words": 800
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
    # Remove trailing commas before } or ]
    text = re.sub(r',\s*([}\]])', r'\1', text)
    # Fix unescaped quotes within strings
    text = re.sub(r'([^\\])"([^"]*?)([^\\])"', r'\1"\2\3"', text)
    # Fix missing quotes around keys
    text = re.sub(r'(\w+)\s*:', r'"\1":', text)
    # Fix boolean values
    text = text.replace(': true', ': true').replace(': false', ': false').replace(': null', ': null')
    # Ensure proper array formatting
    text = re.sub(r',\s*]', ']', text)
    text = re.sub(r',\s*}', '}', text)
    return text

def robust_json_load(text: str) -> dict:
    """Robust JSON parsing with multiple fallback strategies."""
    if not text or not text.strip():
        return {}
    
    text = clean_json_response(text)
    
    strategies = [
        lambda: json.loads(text),
        lambda: json.loads(re.search(r'\{.*\}', text, re.DOTALL).group(0)),
        lambda: json.loads(re.search(r'\[.*\]', text, re.DOTALL).group(0)),
        lambda: json.loads(fix_common_json_issues(text)),
        lambda: json.loads(text.replace("'", '"')),
    ]
    
    for i, strategy in enumerate(strategies):
        try:
            result = strategy()
            logger.info(f"JSON parsing successful with strategy {i + 1}")
            return result
        except (json.JSONDecodeError, AttributeError, ValueError) as e:
            logger.warning(f"Strategy {i + 1} failed: {e}")
            continue
    
    # Final fallback
    try:
        start_brace = text.find('{')
        start_bracket = text.find('[')
        
        if start_brace != -1 and (start_bracket == -1 or start_brace < start_bracket):
            end_brace = text.rfind('}')
            if end_brace != -1 and end_brace > start_brace:
                json_str = text[start_brace:end_brace + 1]
                return json.loads(fix_common_json_issues(json_str))
        elif start_bracket != -1:
            end_bracket = text.rfind(']')
            if end_bracket != -1 and end_bracket > start_bracket:
                json_str = text[start_bracket:end_bracket + 1]
                return {list(INDIVIDUAL_SECTION_SCHEMAS.keys())[0]: json.loads(fix_common_json_issues(json_str))}
    except Exception as e:
        logger.error(f"Final JSON parsing fallback failed: {e}")
    
    raise ValueError(f"Could not parse JSON from response: {text[:200]}...")

def ensure_6_years(section_content: List[Dict], recent_data: Dict = None) -> List[Dict]:
    """Ensure exactly 6 years of data for numerical sections."""
    if not isinstance(section_content, list):
        section_content = []

    # Override Year 0 with recent_data if provided
    if recent_data and section_content:
        if isinstance(section_content[0], dict):
            section_content[0].update(recent_data)
    elif recent_data and not section_content:
        section_content.append({**recent_data, "year": 0})

    # Fill remaining years
    while len(section_content) < 6:
        last_year = section_content[-1].copy() if section_content else {"year": len(section_content)}
        last_year["year"] = len(section_content)
        section_content.append(last_year)

    return section_content[:6]

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

ISTRUZIONI CRITICHE:
- Mantieni tutte le chiavi JSON in INGLESE
- Output SOLAMENTE JSON valido
- Anno 0 DEVE riflettere i dati correnti
- Numeri consistenti e realistici
- Nessun testo fuori dal JSON
- Priorità mercato italiano
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
                max_tokens=8000
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
                if not isinstance(section_content, str) or len(section_content.strip()) < 50:
                    raise ValueError(f"Invalid string content for {section_key}")
            else:
                section_content = ensure_6_years(section_content, recent_data)
                result[section_key] = section_content

            return result

        except Exception as e:
            logger.warning(f"Attempt {attempt+1} failed for {section_key}: {e}")
            if attempt == max_retries - 1:
                logger.error(f"All retries failed for {section_key}, returning fallback.")
                return create_empty_individual_section(section_key)

            await asyncio.sleep(2 ** attempt + 0.5)

# --------------- MAIN BUSINESS PLAN GENERATOR ---------------

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

    # Process input data
    business_context = []
    if user_input:
        for item in user_input:
            if isinstance(item, str) and len(item) > MAX_INPUT_LENGTH:
                business_context.append(item[:MAX_INPUT_LENGTH] + "...")
            else:
                business_context.append(str(item))

    context = "Business Plan Analysis:\n"
    if business_context:
        context += "\n".join([f"- {item}" for item in business_context])
    if uploaded_file:
        if len(uploaded_file) > MAX_INPUT_LENGTH:
            uploaded_file = uploaded_file[:MAX_INPUT_LENGTH] + "..."
        context += f"\nDocument Analysis:\n{uploaded_file}"

    # Parse uploaded data
    uploaded_json = {}
    if uploaded_file:
        try:
            uploaded_json = json.loads(uploaded_file)
        except:
            logger.warning("Could not parse uploaded file as JSON")

    # Generate sections concurrently
    tasks = []
    for section_key in INDIVIDUAL_SECTION_SCHEMAS.keys():
        recent_data = uploaded_json.get(section_key)
        task = call_individual_section(
            client, section_key, context, settings.model_name,
            language=language, currency=currency, recent_data=recent_data
        )
        tasks.append((section_key, task))

    # Execute tasks with controlled concurrency
    merged_plan = {}
    for section_key, task in tasks:
        try:
            result = await task
            if isinstance(result, dict) and section_key in result:
                merged_plan[section_key] = result[section_key]
            else:
                merged_plan[section_key] = create_empty_individual_section(section_key)[section_key]
            
            # Small delay between API calls to avoid rate limiting
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Failed section {section_key}: {e}")
            merged_plan[section_key] = create_empty_individual_section(section_key)[section_key]

    return merged_plan

# --------------- SUGGESTION FUNCTION ---------------

SUGGESTION_PROMPT = """
You are an expert business plan consultant. Generate 4 different possible professional answers for the following business plan question. 
Keep each answer concise (Less than 10 words).
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