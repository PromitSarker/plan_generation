# services.py
import json
import logging
import re
from typing import Dict, List, Optional, Any
from app.config import get_openai_client
from app.pdf_service import extract_text_from_pdf

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------------------------------
# 1.  SECTION SCHEMAS (unchanged – only shown for completeness)
# -------------------------------------------------
INDIVIDUAL_SECTION_SCHEMAS = {
    "executiveSummary": {
        "type": "string",
        "description": "Summarize the overall business opportunity in 300+ words",
        "min_words": 300
    },
    "businessOverview": {
        "type": "string",
        "description": "Describe the company's mission, vision, and founding story. Include when and why it was started, what goals it seeks to achieve, where it is currently based, and what motivates the team behind it.",
        "min_words": 300
    },
    "marketAnalysis": {
        "type": "string",
        "description": "Provide an analysis of the market that consist total addressable market (TAM), serviceable available market (SAM), and obtainable market (SOM). Make sure to Identify competitors, customer segments, market trends, and why the timing is right for this solution. Do not create any sub catagory.",
        "min_words": 300
    },
    "businessModel": {
        "type": "string",
        "description": "Explain how the business makes money. Describe primary and secondary revenue streams, customer acquisition strategy, pricing model, cost structure, margins, and how the model scales over time. DO NOT ADD SUBSECTIONS OF IT.",
        "min_words": 300
    },
    "marketingSalesStrategy": {
        "type": "string",
        "description": "Describe how the business plans to go to market. Include positioning, target customers, sales channels (online/offline), customer acquisition cost (CAC) strategies, conversion funnels, and how growth will be driven operationally.",
        "min_words": 300
    },
    "financialHighlights": {
        "type": "json",
        "description": "6 years of key financial metrics (Year 0 = current/recent data, Years 1-5 = projections) following Italian accounting standards (OIC). Provide realistic numerical data with interpretive commentary on trends and performance indicators. MUST INCLUDE ALL 6 YEARS: Year 0, 1, 2, 3, 4, 5.",
        "schema": {
            "data": [{"year": "int", "revenue": "float", "net_income": "float", "capex": "float", "debt_repayment": "float"}],
            "analysis": "string"
        },
        "example": {
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
    },
    "cashFlowAnalysis": {
    "type": "json",
    "description": "6 years of cash flow statement (Anno 0 = current data, Anni 1-5 = projections) following Italian accounting standards with proper Italian terminology. Include operating, investing, and financing activities with net cash position.",
    "schema": {
        "data": [{"year": "int", "operating": "float", "investing": "float", "financing": "float", "net_cash": "float"}],
        "analysis": "string"
    },
    "example": {
        "data": [
            {"year": 0, "operating": 60000.0, "investing": -50000.0, "financing": 10000.0, "net_cash": 20000.0},
            {"year": 1, "operating": 69000.0, "investing": -57500.0, "financing": 11000.0, "net_cash": 22500.0},
            {"year": 2, "operating": 79350.0, "investing": -66125.0, "financing": 12100.0, "net_cash": 25325.0},
            {"year": 3, "operating": 91252.0, "investing": -76000.0, "financing": 13310.0, "net_cash": 28562.0},
            {"year": 4, "operating": 104944.0, "investing": -87375.0, "financing": 14641.0, "net_cash": 31410.0},
            {"year": 5, "operating": 120684.0, "investing": -100000.0, "financing": 16100.0, "net_cash": 36684.0}
        ],
        "analysis": "Analisi del flusso di cassa: I flussi operativi mostrano una crescita costante del 15% annuo, sostenuta dalla redditività del business. Gli investimenti rimangono consistenti per lo sviluppo delle immobilizzazioni. I flussi finanziari riflettono il piano di rimborso del debito. La posizione di cassa netta migliora progressivamente ogni anno."
    }
},
    "profitLossProjection": {
        "type": "json",
        "description": "6 years of profit & loss statement (Year 0 = current data from the provided input, Years 1-5 = projections) following the exact Italian accounting format with detailed breakdown. MUST INCLUDE ALL 6 YEARS: Year 0, 1, 2, 3, 4, 5.",
        "schema": {
        "data": [{"year": "int",
                "ricavi_vendite_prestazioni": "float",
                "acquisti_merci": "float",
                "acquisti_servizi": "float", 
                "godimento_beni_terzi": "float",
                "valore_aggiunto": "float",
                "costi_personale": "float",
                "margine_operativo_lordo": "float",
                "ammortamenti_immateriali": "float",
                "ammortamenti_materiali": "float",
                "risultato_operativo": "float",
                "oneri_finanziari": "float",
                "risultato_prima_imposte": "float",
                "imposte_reddito": "float",
                "utile_netto": "float"}],
        "analysis": "string"
    },
    "example": {
        "data": [
            {"year": 0, "ricavi_vendite_prestazioni": 0.0, "acquisti_merci": 0.0, "acquisti_servizi": 0.0, "godimento_beni_terzi": 0.0, "valore_aggiunto": 0.0, "costi_personale": 0.0, "margine_operativo_lordo": 0.0, "ammortamenti_immateriali": 0.0, "ammortamenti_materiali": 0.0, "risultato_operativo": 0.0, "oneri_finanziari": 0.0, "risultato_prima_imposte": 0.0, "imposte_reddito": 0.0, "utile_netto": 0.0},
            {"year": 1, "ricavi_vendite_prestazioni": 1500000.0, "acquisti_merci": 450000.0, "acquisti_servizi": 120000.0, "godimento_beni_terzi": 15000.0, "valore_aggiunto": 915000.0, "costi_personale": 300000.0, "margine_operativo_lordo": 615000.0, "ammortamenti_immateriali": 6000.0, "ammortamenti_materiali": 25800.0, "risultato_operativo": 583200.0, "oneri_finanziari": 5000.0, "risultato_prima_imposte": 578200.0, "imposte_reddito": 140208.0, "utile_netto": 437992.0}
        ],
        "analysis": "Analisi del conto economico: L'anno 0 rappresenta la situazione corrente. I ricavi mostrano una crescita costante del 15% annuo. Il valore aggiunto si mantiene stabile attorno al 60-61% dei ricavi, indicando una buona efficienza operativa."
    }
    },
    "balanceSheet": {
    "type": "json",
    "description": "6 years of balance sheet following Italian accounting standards (Stato Patrimoniale) with proper Italian structure matching the exact table format: Attività (Fixed/Current), Passività e Patrimonio Netto (Equity/Non-Current/Current Liabilities).",
    "schema": {
        "data": [{"year": "int",
            # ATTIVO - FIXED ASSETS
            "immobilizzazioni_immateriali": "float",
            "tot_immob_immateriali_nette": "float",
            "terreni_e_fabbricati": "float",
            "impianti_e_macchinari": "float",
            "attrezzature_arredi_altri_beni": "float",
            "tot_immob_materiali_nette": "float",
            "tot_immob_finanziarie": "float",
            "totale_attivo_fisso": "float",
            
            # ATTIVO - CURRENT ASSETS
            "crediti_commerciali": "float",
            "disponibilita_liquide": "float",
            "ratei_risconti_attivi": "float",
            "totale_attivo_circolante": "float",
            "totale_attivo": "float",
            
            # PASSIVO E PATRIMONIO NETTO
            "capitale_sociale": "float",
            "riserve_utili_accantonati": "float",
            "utile_perdita_esercizio": "float",
            "patrimonio_netto": "float",
            "fondo_tfr": "float",
            "fondi": "float",
            "debiti_ml_termine_mutuo": "float",
            "passivita_consolidate": "float",
            "debiti_vs_fornitori": "float",
            "debiti_vs_soci": "float",
            "debiti_vs_erario": "float",
            "debiti_vs_banche": "float",
            "totale_debiti_breve_termine": "float",
            "ratei_risconti_passivi": "float",
            "passivita_correnti": "float",
            "totale_passivo": "float"
        }],
        "analysis": "string"
    },
    "example": {
        "data": [
            {
                "year": 0,
                "immobilizzazioni_immateriali": 0.0,
                "tot_immob_immateriali_nette": 0.0,
                "terreni_e_fabbricati": 0.0,
                "impianti_e_macchinari": 0.0,
                "attrezzature_arredi_altri_beni": 0.0,
                "tot_immob_materiali_nette": 0.0,
                "tot_immob_finanziarie": 0.0,
                "totale_attivo_fisso": 0.0,
                "crediti_commerciali": 0.0,
                "disponibilita_liquide": 0.0,
                "ratei_risconti_attivi": 0.0,
                "totale_attivo_circolante": 0.0,
                "totale_attivo": 0.0,
                "capitale_sociale": 0.0,
                "riserve_utili_accantonati": 0.0,
                "utile_perdita_esercizio": 0.0,
                "patrimonio_netto": 0.0,
                "fondo_tfr": 0.0,
                "fondi": 0.0,
                "debiti_ml_termine_mutuo": 0.0,
                "passivita_consolidate": 0.0,
                "debiti_vs_fornitori": 0.0,
                "debiti_vs_soci": 0.0,
                "debiti_vs_erario": 0.0,
                "debiti_vs_banche": 0.0,
                "totale_debiti_breve_termine": 0.0,
                "ratei_risconti_passivi": 0.0,
                "passivita_correnti": 0.0,
                "totale_passivo": 0.0
            }
        ],
        "analysis": "Analisi dello stato patrimoniale: L'anno 0 rappresenta la situazione iniziale. Il patrimonio netto mostra una crescita costante supportata dalla redditività operativa."
    }
},
    "debtStructure": {
    "type": "json", 
    "description": "6 years of debt structure and repayment schedule following Italian banking standards with Italian formatting. Include repayment amounts, interest rates, and outstanding debt balance for each year.",
    "schema": {
        "data": [{"year": "int", "repayment": "float", "interest_rate": "float", "outstanding_debt": "float"}],
        "analysis": "string"
    },
    "example": {
        "data": [
            {"year": 0, "repayment": 10000.0, "interest_rate": 4.5, "outstanding_debt": 36500.0},
            {"year": 1, "repayment": 11000.0, "interest_rate": 4.2, "outstanding_debt": 25500.0},
            {"year": 2, "repayment": 12100.0, "interest_rate": 4.0, "outstanding_debt": 13400.0},
            {"year": 3, "repayment": 13310.0, "interest_rate": 3.8, "outstanding_debt": 0.0},
            {"year": 4, "repayment": 0.0, "interest_rate": 0.0, "outstanding_debt": 0.0},
            {"year": 5, "repayment": 0.0, "interest_rate": 0.0, "outstanding_debt": 0.0}
        ],
        "analysis": "La struttura del debito mostra un piano di ammortamento progressivo con tassi di interesse decrescenti. Il debito viene completamente estinto entro il terzo anno, riducendo gli oneri finanziari e migliorando la posizione finanziaria netta."
    }
},

    "ratiosAnalysis": {
        "type": "json",
        "description": "Detailed Italian financial ratios analysis following Wayne SRL example with Italian financial indicators and interpretive commentary on ratio performance.",
        "schema": {
            "data": [{"year": "int", "roi": "float", "roe": "float", "ros": "float", "ebit_margin": "float", "net_debt_to_ebitda": "float", "net_debt_to_equity": "float", "net_debt_to_revenue": "float", "current_ratio": "float", "quick_ratio": "float", "debt_to_equity": "float", "treasury_margin": "float", "structural_margin": "float", "net_working_capital": "float", "altman_z_score": "float"}],
            "analysis": "string"
        },
        "example": {
            "data": [
                {"year": 0, "roi": 12.5, "roe": 15.0, "ros": 8.5, "ebit_margin": 10.0, "net_debt_to_ebitda": 3.5, "net_debt_to_equity": 0.55, "net_debt_to_revenue": 0.3, "current_ratio": 1.5, "quick_ratio": 1.2, "debt_to_equity": 0.55, "treasury_margin": 0.25, "structural_margin": 0.45, "net_working_capital": 35000, "altman_z_score": 2.5},
                {"year": 1, "roi": 15.8, "roe": 18.5, "net_debt_to_equity": 1.65, "gross_margin": 60.0, "ebitda_margin": 20.0, "net_margin": 15.0, "current_ratio": 1.54, "quick_ratio": 1.25, "asset_turnover": 0.89}
            ],
            "analysis": "Trend positivo dei principali indici: ROI e ROE in aumento, riduzione della leva finanziaria e miglioramento della liquidità."
        }
    },
    "managementTeam": {
        "type": "string",
        "description": "Detailed description about how management team should run. Do not add any sub secttions to it.",
        "min_words": 400
    }
}



class FinancialValidator:
    """Validator to force-correct financial calculations according to Italian accounting standards"""
    
    def __init__(self):
        self.ires_tax_rate = 0.24  # 24% Italian corporate tax rate


    def validate_and_fix_financial_analysis(self, financial_analysis_data: Dict) -> Dict:
        """Validate and fix financial analysis calculations according to Italian cash flow standards"""
        try:
            if "data" not in financial_analysis_data:
                return financial_analysis_data
                
            fixed_data = []
            previous_cash = 0  # Track cumulative cash position
            
            for record in financial_analysis_data["data"]:
                fixed_record = self._fix_single_financial_analysis_record(record, previous_cash)
                fixed_data.append(fixed_record)
                previous_cash = fixed_record.get("cash_and_banks", 0)
            
            return {
                "data": fixed_data,
                "analysis": financial_analysis_data.get("analysis", "Analisi finanziaria corretta con validazione")
            }
        except Exception as e:
            logger.error(f"Error validating financial analysis: {str(e)}")
            return financial_analysis_data

    def _fix_single_financial_analysis_record(self, record: Dict, previous_cash: float) -> Dict:
        """Fix calculations for a single financial analysis record"""
        record = record.copy()
        
        # 1. Calculate NOPAT (if EBIT and taxes are provided)
        if all(k in record for k in ["ebit", "net_income"]):
            # NOPAT ≈ EBIT - Taxes (simplified)
            nopat = record["ebit"] - abs(record.get("imposte_reddito", 0))
            record["gross_operating_margin"] = round(nopat, 2)
        
        # 2. Calculate Gross Operating Cash Flow
        gross_operating_cash_flow = (
            record.get("gross_operating_margin", 0) +
            record.get("ammortamenti", 0)  # Assuming amortization is included here
        )
        record["gross_operating_cash_flow"] = round(gross_operating_cash_flow, 2)
        
        # 3. Calculate Current Management Cash Flow
        current_management_cash_flow = (
            record["gross_operating_cash_flow"] +
            record.get("working_capital_change", 0)
        )
        record["current_management_cash_flow"] = round(current_management_cash_flow, 2)
        
        # 4. Calculate Operating Cash Flow
        operating_cash_flow = (
            record["current_management_cash_flow"] +
            record.get("investing", 0)  # Using 'investing' from cashFlowAnalysis schema
        )
        record["operating_cash_flow"] = round(operating_cash_flow, 2)
        
        # 5. Calculate Net Cash Flow (simplified)
        net_cash_flow = (
            record.get("operating", 0) +
            record.get("investing", 0) +
            record.get("financing", 0)
        )
        record["net_cash_flow"] = round(net_cash_flow, 2)
        
        # 6. Calculate Cumulative Cash Position
        cash_and_banks = previous_cash + record["net_cash_flow"]
        record["cash_and_banks"] = round(cash_and_banks, 2)
        
        # 7. Ensure debt service and shareholder flows are consistent
        if "debt_service_cash_flow" not in record:
            record["debt_service_cash_flow"] = round(record["operating_cash_flow"], 2)
        
        if "shareholders_cash_flow" not in record:
            record["shareholders_cash_flow"] = round(record["net_cash_flow"], 2)
        
        return record


    
    def validate_and_fix_profit_loss(self, profit_loss_data: Dict) -> Dict:
        """Validate and fix profit & loss calculations according to Italian standards"""
        try:
            if "data" not in profit_loss_data:
                return profit_loss_data
                
            fixed_data = []
            for record in profit_loss_data["data"]:
                fixed_record = self._fix_single_profit_loss_record(record)
                fixed_data.append(fixed_record)
            
            return {
                "data": fixed_data,
                "analysis": profit_loss_data.get("analysis", "Analisi corretta con validazione finanziaria")
            }
        except Exception as e:
            logger.error(f"Error validating profit loss: {str(e)}")
            return profit_loss_data
    
    def _fix_single_profit_loss_record(self, record: Dict) -> Dict:
        """Fix calculations for a single profit & loss record using exact table structure"""
        record = record.copy()
        
        # Calculate valore_aggiunto (exact from your table)
        valore_aggiunto = (
            record.get("ricavi_vendite_prestazioni", 0) -
            record.get("acquisti_merci", 0) -
            record.get("acquisti_servizi", 0) -
            record.get("godimento_beni_terzi", 0)
        )
        record["valore_aggiunto"] = round(valore_aggiunto, 2)
        
        # Calculate margine_operativo_lordo (EBITDA)
        mol = record["valore_aggiunto"] - record.get("costi_personale", 0)
        record["margine_operativo_lordo"] = round(mol, 2)
        
        # Calculate risultato_operativo (EBIT)
        risultato_operativo = (
            record["margine_operativo_lordo"] -
            record.get("ammortamenti_immateriali", 0) -
            record.get("ammortamenti_materiali", 0)
        )
        record["risultato_operativo"] = round(risultato_operativo, 2)
        
        # Calculate risultato_prima_imposte (EBT)
        ebt = record["risultato_operativo"] - record.get("oneri_finanziari", 0)
        record["risultato_prima_imposte"] = round(ebt, 2)
        
        # Calculate taxes (IRES 24%)
        if record["risultato_prima_imposte"] > 0:
            imposte_reddito = -abs(record["risultato_prima_imposte"] * self.ires_tax_rate)
        else:
            imposte_reddito = 0
        record["imposte_reddito"] = round(imposte_reddito, 2)
        
        # Calculate utile_netto
        utile_netto = record["risultato_prima_imposte"] + record["imposte_reddito"]
        record["utile_netto"] = round(utile_netto, 2)
        
        return record
        
    def validate_and_fix_balance_sheet(self, balance_sheet_data: Dict) -> Dict:
        """Validate and fix balance sheet calculations using exact PDF formulas"""
        try:
            if "data" not in balance_sheet_data:
                return balance_sheet_data
                
            fixed_data = []
            for record in balance_sheet_data["data"]:
                fixed_record = self._fix_single_balance_sheet_record(record)
                fixed_data.append(fixed_record)
            
            return {
                "data": fixed_data,
                "analysis": balance_sheet_data.get("analysis", "Bilancio corretto con validazione")
            }
        except Exception as e:
            logger.error(f"Error validating balance sheet: {str(e)}")
            return balance_sheet_data
    
    def _fix_single_balance_sheet_record(self, record: Dict) -> Dict:
        """Fix calculations for a single balance sheet record using exact PDF formulas"""
        record = record.copy()
        
        # 1. Calculate total_fixed_assets (ATTIVO FISSO NETTO)
        total_fixed_assets = (
            record.get("intangible_fixed_assets", 0) +
            record.get("tangible_fixed_assets", 0) +
            record.get("financial_fixed_assets", 0)
        )
        record["total_fixed_assets"] = round(total_fixed_assets, 2)
        
        # 2. Calculate net_operating_current_assets (ATTIVO CIRCOLANTE OPERATIVO NETTO)
        # Using exact formula from PDF
        net_operating_current_assets = (
            record.get("inventory", 0) +
            record.get("net_receivables_from_clients", 0) +
            record.get("other_operating_receivables", 0) +
            record.get("accruals_prepayments_assets", 0) +
            record.get("suppliers_payables", 0) +  # This is negative in PDF
            record.get("related_party_payables", 0) +  # This is negative in PDF  
            record.get("other_operating_payables", 0)  # This is negative in PDF
        )
        record["net_operating_current_assets"] = round(net_operating_current_assets, 2)
        
        # 3. Calculate total_invested_capital (CAPITALE INVESTITO)
        total_invested_capital = record["total_fixed_assets"] + record["net_operating_current_assets"]
        record["total_invested_capital"] = round(total_invested_capital, 2)
        
        # 4. Calculate net_invested_capital (CAPITALE INVESTITO NETTO)
        net_invested_capital = (
            record["total_invested_capital"] +
            record.get("tfr_provision", 0) +  # Negative in PDF
            record.get("other_provisions", 0) +  # Negative in PDF
            record.get("non_current_operating_liabilities", 0)  # Negative in PDF
        )
        record["net_invested_capital"] = round(net_invested_capital, 2)
        
        # 5. Calculate total_equity (PATRIMONIO NETTO)
        total_equity = (
            record.get("share_capital", 0) +
            record.get("reserves", 0) +
            record.get("profit_loss", 0)
        )
        record["total_equity"] = round(total_equity, 2)
        
        # 6. Calculate net_financial_debt (INDEBITAMENTO FINANZIARIO NETTO)
        # Using exact formula from PDF
        net_financial_debt = (
            record.get("short_term_bank_debt", 0) +
            record.get("other_short_term_financial_debt", 0) +
            record.get("long_term_bank_debt", 0) +
            record.get("other_long_term_financial_debt", 0) +
            record.get("shareholder_financing", 0) +
            record.get("leasing_debt", 0) +
            record.get("financial_receivables", 0) +  # This subtracts in calculation
            record.get("cash_bank_accounts", 0)  # This subtracts in calculation (negative in PDF)
        )
        record["net_financial_debt"] = round(net_financial_debt, 2)
        
        # 7. Calculate total_funding_sources (FONTI DI FINANZIAMENTO)
        total_funding_sources = record["total_equity"] + record["net_financial_debt"]
        record["total_funding_sources"] = round(total_funding_sources, 2)
        
        # 8. Force balance: total_funding_sources should equal net_invested_capital
        if abs(record["total_funding_sources"] - record["net_invested_capital"]) > 1.0:
            # Adjust reserves to balance the equation
            adjustment = record["net_invested_capital"] - record["total_funding_sources"]
            record["reserves"] = round(record.get("reserves", 0) + adjustment, 2)
            # Recalculate equity and funding sources
            record["total_equity"] = round(
                record.get("share_capital", 0) + 
                record["reserves"] + 
                record.get("profit_loss", 0), 2
            )
            record["total_funding_sources"] = round(record["total_equity"] + record["net_financial_debt"], 2)
        
        return record
    

    def _fix_single_balance_sheet_record(self, record: Dict) -> Dict:
        """Fix calculations for balance sheet using exact table structure"""
        record = record.copy()
        
        # Calculate total intangible fixed assets
        tot_immob_immateriali = record.get("immobilizzazioni_immateriali", 0)
        record["tot_immob_immateriali_nette"] = round(tot_immob_immateriali, 2)
        
        # Calculate total tangible fixed assets
        tot_immob_materiali = (
            record.get("terreni_e_fabbricati", 0) +
            record.get("impianti_e_macchinari", 0) +
            record.get("attrezzature_arredi_altri_beni", 0)
        )
        record["tot_immob_materiali_nette"] = round(tot_immob_materiali, 2)
        
        # Calculate total fixed assets
        totale_attivo_fisso = (
            record["tot_immob_immateriali_nette"] +
            record["tot_immob_materiali_nette"] +
            record.get("tot_immob_finanziarie", 0)
        )
        record["totale_attivo_fisso"] = round(totale_attivo_fisso, 2)
        
        # Calculate total current assets
        totale_attivo_circolante = (
            record.get("crediti_commerciali", 0) +
            record.get("disponibilita_liquide", 0) +
            record.get("ratei_risconti_attivi", 0)
        )
        record["totale_attivo_circolante"] = round(totale_attivo_circolante, 2)
        
        # Calculate total assets
        totale_attivo = record["totale_attivo_fisso"] + record["totale_attivo_circolante"]
        record["totale_attivo"] = round(totale_attivo, 2)
        
        # Calculate equity
        patrimonio_netto = (
            record.get("capitale_sociale", 0) +
            record.get("riserve_utili_accantonati", 0) +
            record.get("utile_perdita_esercizio", 0)
        )
        record["patrimonio_netto"] = round(patrimonio_netto, 2)
        
        # Calculate funds
        record["fondi"] = round(record.get("fondo_tfr", 0), 2)
        
        # Calculate non-current liabilities
        record["passivita_consolidate"] = round(record.get("debiti_ml_termine_mutuo", 0), 2)
        
        # Calculate short-term debts
        totale_debiti_breve_termine = (
            record.get("debiti_vs_fornitori", 0) +
            record.get("debiti_vs_soci", 0) +
            record.get("debiti_vs_erario", 0) +
            record.get("debiti_vs_banche", 0)
        )
        record["totale_debiti_breve_termine"] = round(totale_debiti_breve_termine, 2)
        
        # Calculate current liabilities
        passivita_correnti = (
            record["totale_debiti_breve_termine"] +
            record.get("ratei_risconti_passivi", 0)
        )
        record["passivita_correnti"] = round(passivita_correnti, 2)
        
        # Calculate total liabilities and equity
        totale_passivo = (
            record["patrimonio_netto"] +
            record["fondi"] +
            record["passivita_consolidate"] +
            record["passivita_correnti"]
        )
        record["totale_passivo"] = round(totale_passivo, 2)
        
        # Force balance: total assets should equal total liabilities + equity
        if abs(record["totale_attivo"] - record["totale_passivo"]) > 1.0:
            # Adjust retained earnings to balance
            adjustment = record["totale_attivo"] - record["totale_passivo"]
            record["riserve_utili_accantonati"] = round(record.get("riserve_utili_accantonati", 0) + adjustment, 2)
            # Recalculate equity and total liabilities
            record["patrimonio_netto"] = round(
                record.get("capitale_sociale", 0) + 
                record["riserve_utili_accantonati"] + 
                record.get("utile_perdita_esercizio", 0), 2
            )
            record["totale_passivo"] = round(
                record["patrimonio_netto"] +
                record["fondi"] +
                record["passivita_consolidate"] +
                record["passivita_correnti"], 2
            )
        
        return record

    
    def validate_and_fix_cash_flow(self, cash_flow_data: Dict) -> Dict:
        """Validate and fix cash flow calculations with enhanced logic"""
        try:
            if "data" not in cash_flow_data:
                return cash_flow_data
                
            fixed_data = []
            cumulative_cash = 0  # Track cumulative cash position
            
            for record in cash_flow_data["data"]:
                fixed_record = record.copy()
                year = fixed_record.get("year", 0)
                
                # Ensure investing is typically negative (cash outflow)
                if fixed_record.get("investing", 0) > 0:
                    # Unless there are disposals of assets, investing should be negative
                    fixed_record["investing"] = -abs(fixed_record["investing"])
                
                # Calculate net cash from components
                calculated_net_cash = (
                    fixed_record.get("operating", 0) +
                    fixed_record.get("investing", 0) +
                    fixed_record.get("financing", 0)
                )
                
                # If provided net_cash doesn't match calculation, use calculated value
                if abs(fixed_record.get("net_cash", 0) - calculated_net_cash) > 1.0:
                    fixed_record["net_cash"] = round(calculated_net_cash, 2)
                
                # Calculate cumulative cash position
                cumulative_cash += fixed_record["net_cash"]
                fixed_record["cumulative_cash"] = round(cumulative_cash, 2)  # Optional: add cumulative tracking
                
                fixed_data.append(fixed_record)
            
            return {
                "data": fixed_data,
                "analysis": cash_flow_data.get("analysis", "Analisi del flusso di cassa validata e corretta")
            }
        except Exception as e:
            logger.error(f"Error validating cash flow: {str(e)}")
            return cash_flow_data
    
    def validate_financial_consistency(self, all_financial_data: Dict) -> Dict:
        """Validate consistency across all financial statements"""
        try:
            # Extract key data for consistency checks with defensive programming
            profit_loss_section = all_financial_data.get("profitLossProjection", {})
            balance_sheet_section = all_financial_data.get("balanceSheet", {})
            cash_flow_section = all_financial_data.get("cashFlowAnalysis", {})
            
            # FIX: Check if sections are dictionaries before accessing .get()
            profit_loss_data = profit_loss_section.get("data", []) if isinstance(profit_loss_section, dict) else []
            balance_sheet_data = balance_sheet_section.get("data", []) if isinstance(balance_sheet_section, dict) else []
            cash_flow_data = cash_flow_section.get("data", []) if isinstance(cash_flow_section, dict) else []
            
            # Ensure we have data for all years
            years = set()
            for data in [profit_loss_data, balance_sheet_data, cash_flow_data]:
                if isinstance(data, list):
                    for record in data:
                        if isinstance(record, dict):
                            years.add(record.get("year", 0))
            
            # Check net income consistency between P&L and Balance Sheet
            for year in sorted(years):
                pl_net_income = self._get_value_for_year(profit_loss_data, year, "utile_netto")  # Fixed field name
                bs_profit_loss = self._get_value_for_year(balance_sheet_data, year, "utile_perdita_esercizio")
                
                # If there's a significant discrepancy, log it
                if pl_net_income is not None and bs_profit_loss is not None:
                    if abs(pl_net_income - bs_profit_loss) > 100:  # Allow small rounding differences
                        logger.warning(f"Net income inconsistency in year {year}: P&L={pl_net_income}, BS={bs_profit_loss}")
            
            return all_financial_data
            
        except Exception as e:
            logger.error(f"Error in financial consistency check: {str(e)}")
            return all_financial_data
    

    def _get_value_for_year(self, data: List[Dict], year: int, field: str) -> Optional[float]:
        """Get value for specific year and field"""
        for record in data:
            if record.get("year") == year and field in record:
                return record[field]
        return None

# -------------------------------------------------
# ENHANCED BUSINESS PLAN SERVICE WITH VALIDATION
# -------------------------------------------------
class BusinessPlanService:
    def __init__(self):
        self.client = get_openai_client()
        self.section_schemas = INDIVIDUAL_SECTION_SCHEMAS
        self.validator = FinancialValidator()
        self.max_retries = 3

    async def generate_business_plan(
    self,
    uploaded_file: Optional[List[Any]] = None,
    user_input: List[Any] = None,
    user_id: str = None
) -> Dict:
        """Orchestrate generation of the full business plan and return structured result."""
        try:
            # Convert tuples to lists if necessary
            if uploaded_file and isinstance(uploaded_file, tuple):
                uploaded_file = list(uploaded_file)
            if user_input and isinstance(user_input, tuple):
                user_input = list(user_input)
                
            # Build context
            context: Dict[str, Any] = {}
            files_data = await self._process_uploaded_files(uploaded_file)
            context["extracted_text"] = files_data.get("text", "")
            context["extracted_financial_data"] = files_data.get("financial_data", {})
            context["user_input"] = self._process_user_input(user_input or [])

            previous_sections: Dict[str, Any] = {}
            business_plan_data: Dict[str, Any] = {}

            # Generate sections in defined order
            for section_key, schema in self.section_schemas.items():
                try:
                    if schema.get("type") == "string":
                        content = await self._generate_section(section_key, context, previous_sections)
                        business_plan_data[section_key] = content
                        previous_sections[section_key] = content
                    else:
                        content = await self._generate_financial_section(section_key, context, previous_sections)
                        business_plan_data[section_key] = content
                        previous_sections[section_key] = content
                except Exception as e:
                    logger.error(f"Error generating section {section_key}: {str(e)}")
                    # FIX: Return proper structure instead of string for financial sections
                    if schema.get("type") == "string":
                        business_plan_data[section_key] = f"Error generating {section_key}: {str(e)}"
                    else:
                        # For financial sections, return proper dictionary structure
                        business_plan_data[section_key] = self._get_fallback_financial_data(section_key, schema)

            # Final structure and consistency checks
            structured = await self._validate_and_structure_plan(business_plan_data, context)
            
            # Run final consistency check (but don't fail if it errors)
            try:
                self.validator.validate_financial_consistency(business_plan_data)
            except Exception as e:
                logger.warning(f"Final consistency validation warning: {str(e)}")

            return structured

        except Exception as e:
            logger.error(f"Error in generate_business_plan orchestration: {e}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Error details: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {"error": "Unable to generate business plan at this time."}

    # ... [keep all existing methods until _generate_financial_section] ...

    async def _generate_financial_section(
        self,
        section_key: str,
        context: Dict,
        previous_sections: Dict
    ) -> Dict:
        """Generate financial section with validation and retries"""
        schema = self.section_schemas[section_key]
        
        for attempt in range(self.max_retries):
            try:
                prompt = self._build_financial_prompt(section_key, schema, context, previous_sections)
                
                response = await self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "Sei un analista finanziario esperto in principi contabili italiani (OIC). Genera proiezioni finanziarie realistiche e analisi accurate in italiano. Rispondi SOLO con un oggetto JSON valido che corrisponde esattamente allo schema richiesto."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=3000,
                    response_format={"type": "json_object"}
                )

                content = response.choices[0].message.content.strip()
                financial_data = json.loads(content)
                self._validate_financial_structure(financial_data, schema)
                
                # Apply validation and fixes
                validated_data = await self._apply_financial_validation(section_key, financial_data)
                
                # Check if we need to retry
                if attempt < self.max_retries - 1 and self._needs_retry(section_key, validated_data):
                    logger.warning(f"Retrying {section_key} generation, attempt {attempt + 2}")
                    continue
                
                return validated_data
                
            except Exception as e:
                logger.error(f"Error generating {section_key} (attempt {attempt + 1}): {str(e)}")
                if attempt == self.max_retries - 1:
                    # Return fallback data on final attempt
                    return self._get_fallback_financial_data(section_key, schema)
        
        return self._get_fallback_financial_data(section_key, schema)
    
    async def _apply_financial_validation(self, section_key: str, financial_data: Dict) -> Dict:
        """Apply appropriate validation based on section type"""
        if section_key == "profitLossProjection":
            return self.validator.validate_and_fix_profit_loss(financial_data)
        elif section_key == "balanceSheet":
            return self.validator.validate_and_fix_balance_sheet(financial_data)
        elif section_key == "cashFlowAnalysis":
            return self.validator.validate_and_fix_cash_flow(financial_data)

        elif section_key == "debtStructure":  # ADD THIS
            return self.validator.validate_and_fix_debt_structure(financial_data)
        else:
            return financial_data
    
    def _needs_retry(self, section_key: str, validated_data: Dict) -> bool:
        """Determine if we need to retry generation due to data issues"""
        if "data" not in validated_data or not validated_data["data"]:
            return True
            
        # Check for obvious data issues that require regeneration
        if section_key == "profitLossProjection":
            for record in validated_data["data"]:
                # If net income is negative for all years, might need retry
                if record.get("risultato_netto", 0) < -100000:  # Large negative values
                    return True
                    
        return False
    
    def _get_fallback_financial_data(self, section_key: str, schema: Dict) -> Dict:
        """Provide fallback data when generation fails"""
        logger.warning(f"Using fallback data for {section_key}")
        
        if "example" in schema:
            return schema["example"]
        
        # Basic fallback structure
        return {
            "data": [],
            "analysis": "Dati non disponibili a causa di errori di generazione."
        }

    # Modify the final structuring to include cross-statement validation
    async def _validate_and_structure_plan(self, business_plan_data: Dict, context: Dict) -> Dict:
        """Convert every financial section to the requested wrapper format with final validation"""
        structured_plan = {
            "executiveSummary": business_plan_data.get("executiveSummary", ""),
            "businessOverview": business_plan_data.get("businessOverview", ""),
            "marketAnalysis": business_plan_data.get("marketAnalysis", ""),
            "businessModel": business_plan_data.get("businessModel", ""),
            "marketingSalesStrategy": business_plan_data.get("marketingSalesStrategy", ""),
            "managementTeam": business_plan_data.get("managementTeam", ""),
        }

        # Helper to wrap a financial section
        def wrap(section_data: Any) -> List[Dict[str, Any]]:
            if isinstance(section_data, dict) and "data" in section_data and "analysis" in section_data:
                return [section_data]
            return [{"data": [], "analysis": "Dati non disponibili."}]

        # Apply final cross-statement validation
        financial_sections = [
            #"financialHighlights", 
            "cashFlowAnalysis", "profitLossProjection",
            "balanceSheet", #"netFinancialPosition", 
            "debtStructure",
            #"keyRatios", 
            #"financialAnalysis", 
            "ratiosAnalysis"
        ]
        
        financial_data_dict = {}
        for section_key in financial_sections:
            section_data = business_plan_data.get(section_key)
            financial_data_dict[section_key] = section_data
            structured_plan[section_key] = wrap(section_data)
        
        # Run final consistency check
        self.validator.validate_financial_consistency(financial_data_dict)
        
        return structured_plan


    # -------------------------------------------------
    # 3.  SECTION GENERATORS
    # -------------------------------------------------
    async def _generate_section(
        self,
        section_key: str,
        context: Dict,
        previous_sections: Dict
    ) -> str:
        schema = self.section_schemas[section_key]
        prompt = self._build_section_prompt(section_key, schema, context, previous_sections)

        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Sei un esperto consulente aziendale italiano. Genera contenuti professionali e accurati per business plan in italiano. Rispondi solo con il contenuto richiesto senza introduzioni."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=2000
        )

        content = response.choices[0].message.content.strip()

        # Optional word-count re-generation
        if "min_words" in schema:
            word_count = len(content.split())
            if word_count < schema["min_words"]:
                content = await self._regenerate_with_word_count(section_key, schema, content, prompt)
        return content

    async def _generate_financial_section(
        self,
        section_key: str,
        context: Dict,
        previous_sections: Dict
    ) -> Dict:
        schema = self.section_schemas[section_key]
        prompt = self._build_financial_prompt(section_key, schema, context, previous_sections)

        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Sei un analista finanziario esperto in principi contabili italiani (OIC). Genera proiezioni finanziarie realistiche e analisi accurate in italiano. Rispondi SOLO con un oggetto JSON valido che corrisponde esattamente allo schema richiesto."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=3000,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content.strip()
        financial_data = json.loads(content)
        self._validate_financial_structure(financial_data, schema)
        return financial_data

    # -------------------------------------------------
    # 5.  PROMPT BUILDERS
    # -------------------------------------------------
    def _build_section_prompt(
        self,
        section_key: str,
        schema: Dict,
        context: Dict,
        previous_sections: Dict
    ) -> str:
        prompt_parts = [
            f"Genera la sezione '{section_key}' per un business plan.",
            f"DESCRIZIONE: {schema['description']}",
            "LINGUA: Italiano",
            "VALUTA: Euro",
            f"MINIMO PAROLE: {schema.get('min_words', 300)}"
        ]

        if context.get("user_input"):
            prompt_parts.append(f"INPUT UTENTE: {context['user_input']}")

        if context.get("extracted_financial_data"):
            fin_data = context['extracted_financial_data']
            prompt_parts.append(f"DATI FINANZIARI ESTRATTI: {json.dumps(fin_data, indent=2)}")

        if context.get("extracted_text"):
            prompt_parts.append(f"TESTO ESTRATTO DA DOCUMENTI: {context['extracted_text'][:1000]}...")

        for prev_key, prev_content in previous_sections.items():
            if isinstance(prev_content, str) and prev_content:
                preview = prev_content[:500] + "..." if len(prev_content) > 500 else prev_content
                prompt_parts.append(f"CONTESTO DA {prev_key.upper()}: {preview}")

        prompt_parts.extend([
            "ISTRUZIONI IMPORTANTI:",
            "1. Genera solo il contenuto della sezione richiesta",
            "2. Non aggiungere introduzioni, titoli o note",
            "3. Mantieni un tono professionale",
            "4. Assicurati di raggiungere il numero minimo di parole",
            "5. Basati sul contesto fornito ma non ripetere informazioni"
        ])
        return "\n\n".join(prompt_parts)

    def _build_financial_prompt(self, section_key: str, schema: Dict, context: Dict, previous_sections: Dict) -> str:
        prompt_parts = [
            f"Genera la sezione finanziaria '{section_key}' in formato JSON.",
            f"DESCRIZIONE: {schema['description']}",
            f"SCHEMA RICHIESTO: {json.dumps(schema['schema'], indent=2)}",
            "LINGUA per l'analisi: Italiano",
            "VALUTA: Euro",
            "PRINCIPI CONTABILI: Standard Italiani (OIC)",
            "**IMPORTANTE: DEVI GENERARE ESATTAMENTE 6 ANNI DI DATI**",
            "ANNI RICHIESTI: Anno 0 (situazione corrente) + Anni 1, 2, 3, 4, 5 (proiezioni)",
            "**NON OMETTERE NESSUN ANNO. TUTTI I 6 ANNI DEVONO ESSERE PRESENTI.**"
        ]

        if section_key == "cashFlowAnalysis":
            prompt_parts.extend([
                "ISTRUZIONI SPECIFICHE PER ANALISI FLUSSO DI CASSA:",
                "1. Operating = Flusso di cassa operativo (solitamente positivo)",
                "2. Investing = Flusso di cassa per investimenti (solitamente negativo)",
                "3. Financing = Flusso di cassa finanziario (può essere positivo o negativo)",
                "4. Net Cash = Somma dei tre flussi (Operating + Investing + Financing)",
                "5. Anno 0 = situazione corrente basata sui dati forniti",
                "6. Anni 1-5 = proiezioni realistiche e coerenti"
            ]),
        
        if section_key == "profitLossProjection":
            prompt_parts.extend([
                "ISTRUZIONI SPECIFICHE CONTO ECONOMICO:",
                "1. Anno 0 = dati correnti (se disponibili) o valori di partenza",
                "2. Anni 1-5 = proiezioni con crescita realistica",
                "3. Tutti i calcoli devono essere matematicamente coerenti",
                "4. Le imposte devono essere calcolate al 24% sull'EBIT positivo"
            ])
        if section_key == "balanceSheet":
            prompt_parts.extend([
                "ISTRUZIONI SPECIFICHE STATO PATRIMONIALE:",
                "1. Anno 0 = situazione patrimoniale iniziale",
                "2. Attivo = Passivo + Patrimonio Netto per ogni anno",
                "3. Gli utili accumulati devono crescere coerentemente con il conto economico"
                ])

        if section_key == "debtStructure":
            prompt_parts.extend([
                "ISTRUZIONI SPECIFICHE PER STRUTTURA DEL DEBITO:",
                "1. Anno 0 = situazione corrente",
                "2. Anni 1-5 = proiezioni",
                "3. Interest rate in percentuale (es. 4.5 per 4.5%)",
                "4. Outstanding debt deve diminuire progressivamente",
                "5. Se il debito viene estinto prima dell'anno 5, impostare i valori successivi a 0"
            ])

        if context.get("extracted_financial_data"):
            fin_data = context['extracted_financial_data']
            prompt_parts.append(f"DATI FINANZIARI ESTRATTI (usare come base per Anno 0): {json.dumps(fin_data, indent=2)}")

        if context.get("user_input"):
            prompt_parts.append(f"IDEA BUSINESS: {context['user_input']}")

        financial_context = {}
        for prev_key, prev_content in previous_sections.items():
            if any(k in prev_key.lower() for k in ['financial', 'ratio', 'cash', 'debt', 'balance', 'profit']):
                financial_context[prev_key] = prev_content
        if financial_context:
            prompt_parts.append(f"CONTESTO FINANZIARIO PRECEDENTE: {json.dumps(financial_context, indent=2)}")

        business_context = {}
        for prev_key, prev_content in previous_sections.items():
            if isinstance(prev_content, str) and not any(k in prev_key.lower() for k in ['financial', 'ratio', 'cash', 'debt', 'balance']):
                business_context[prev_key] = prev_content[:500] + "..." if len(prev_content) > 500 else prev_content
        if business_context:
            prompt_parts.append(f"CONTESTO BUSINESS: {json.dumps(business_context, indent=2)}")

        prompt_parts.extend([
            "ISTRUZIONI CRITICHE:",
            "1. Usa i dati estratti per l'Anno 0 (se disponibili)",
            "2. Le proiezioni per gli anni 1-5 devono essere realistiche e coerenti",
            "3. Tutti i valori finanziari devono essere in Euro",
            "4. Includi sia i dati che l'analisi testuale nel formato JSON specificato",
            "5. Assicurati che i calcoli siano matematicamente corretti",
            "6. Mantieni coerenza con le sezioni finanziarie precedenti",
            "7. Per l'analisi, fornisci un commento interpretativo in italiano",
            "8. RESTITUISCI SOLO JSON VALIDO, NESSUN ALTRO TESTO"
        ])
        return "\n\n".join(prompt_parts)

    # -------------------------------------------------
    # 6.  FILE & INPUT HELPERS
    # -------------------------------------------------
    async def _process_uploaded_files(self, uploaded_files: Optional[List[Any]]) -> Dict:
        extracted_data = {"text": "", "financial_data": {}}
        if not uploaded_files:
            return extracted_data

        try:
            for file_data in uploaded_files:
                if hasattr(file_data, 'read') and hasattr(file_data, 'filename'):
                    file_content = await file_data.read()
                    if file_data.filename.lower().endswith('.pdf'):
                        text, pages, metadata, financial_data = extract_text_from_pdf(file_content, "company_extract")
                        extracted_data["text"] += f"\n\n{text}"
                        if financial_data:
                            extracted_data["financial_data"].update(financial_data)
                elif isinstance(file_data, dict):
                    if 'content' in file_data:
                        extracted_data["text"] += f"\n\n{file_data['content']}"
                    if 'financial_data' in file_data:
                        extracted_data["financial_data"].update(file_data['financial_data'])
            logger.info(f"Extracted {len(extracted_data['text'])} chars and {len(extracted_data['financial_data'])} financial data points")
        except Exception as e:
            logger.error(f"Error processing uploaded files: {str(e)}")

        return extracted_data

    def _process_user_input(self, user_input: List[Any]) -> str:
        if not user_input:
            return ""
        processed = []
        for item in user_input:
            if isinstance(item, str):
                processed.append(item)
            elif isinstance(item, dict):
                if 'description' in item:
                    processed.append(item['description'])
                elif 'content' in item:
                    processed.append(item['content'])
                else:
                    processed.append(json.dumps(item, ensure_ascii=False))
            else:
                processed.append(str(item))
        return " ".join(processed)


    def validate_and_fix_debt_structure(self, debt_data: Dict) -> Dict:
        """Validate and fix debt structure calculations"""
        try:
            if "data" not in debt_data:
                return debt_data
                
            fixed_data = []
            previous_debt = 0
            
            for record in debt_data["data"]:
                fixed_record = record.copy()
                year = fixed_record.get("year", 0)
                
                # Validate debt reduction logic
                if year == 0:
                    previous_debt = fixed_record.get("outstanding_debt", 0)
                else:
                    # Outstanding debt should equal previous debt minus repayment
                    expected_debt = max(0, previous_debt - fixed_record.get("repayment", 0))
                    if abs(fixed_record.get("outstanding_debt", 0) - expected_debt) > 100:
                        # Auto-correct if discrepancy is significant
                        fixed_record["outstanding_debt"] = round(expected_debt, 2)
                    
                    previous_debt = fixed_record.get("outstanding_debt", 0)
                
                fixed_data.append(fixed_record)
            
            return {
                "data": fixed_data,
                "analysis": debt_data.get("analysis", "Struttura del debito validata e corretta")
            }
        except Exception as e:
            logger.error(f"Error validating debt structure: {str(e)}")
            return debt_data
    
    def _validate_financial_structure(self, financial_data: Dict, schema: Dict):
        """Validate that financial data matches the expected schema"""
        if not isinstance(financial_data, dict):
            raise ValueError("Financial data must be a dictionary")
            
        if "data" not in financial_data or "analysis" not in financial_data:
            raise ValueError("Financial data must contain 'data' and 'analysis' keys")
            
        if not isinstance(financial_data["analysis"], str):
            raise ValueError("Analysis must be a string")
            
        if not isinstance(financial_data["data"], list):
            raise ValueError("Data must be a list")
            
        if financial_data["data"] and not isinstance(financial_data["data"][0], dict):
            raise ValueError("Data items must be dictionaries")
            
        if financial_data["data"] and "year" not in financial_data["data"][0]:
            raise ValueError("Data items must contain 'year' field")

    async def _regenerate_with_word_count(self, section_key: str, schema: Dict, current_content: str, original_prompt: str) -> str:
        try:
            enhancement_prompt = f"""
{original_prompt}

CONTENUTO ATTUALMENTE GENERATO (insufficiente):
{current_content}

Il contenuto sopra ha solo {len(current_content.split())} parole, ma ne servono almeno {schema['min_words']}.
Per favore, espandi significativamente il contenuto mantenendo qualità e rilevanza.
"""
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Espandi il contenuto per raggiungere il numero minimo di parole richiesto, mantenendo qualità e coerenza."
                    },
                    {"role": "user", "content": enhancement_prompt}
                ],
                temperature=0.7,
                max_tokens=2500
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error regenerating section {section_key}: {str(e)}")
            return current_content

    # -------------------------------------------------
    # 7.  FINAL STRUCTURING – NEW WRAPPER FORMAT
    # -------------------------------------------------
    async def _validate_and_structure_plan(self, business_plan_data: Dict, context: Dict) -> Dict:
        """
        Convert every financial section to the requested wrapper format:
        "sectionName": [ { "data": [...], "analysis": "..." } ]
        """
        structured_plan: Dict[str, Any] = {
            "executiveSummary": business_plan_data.get("executiveSummary", ""),
            "businessOverview": business_plan_data.get("businessOverview", ""),
            "marketAnalysis": business_plan_data.get("marketAnalysis", ""),
            "businessModel": business_plan_data.get("businessModel", ""),
            "marketingSalesStrategy": business_plan_data.get("marketingSalesStrategy", ""),
            "managementTeam": business_plan_data.get("managementTeam", ""),
            # "sector_strategy": business_plan_data.get("marketAnalysis", ""),
            # "funding_sources": "Da definire in base alle necessità di finanziamento"
        }

        # Helper to wrap a financial section
        def wrap(section_data: Any) -> List[Dict[str, Any]]:
            if isinstance(section_data, dict) and "data" in section_data and "analysis" in section_data:
                return [section_data]
            return [{"data": [], "analysis": "Dati non disponibili."}]


        structured_plan["cashFlowAnalysis"] = wrap(business_plan_data.get("cashFlowAnalysis"))
        structured_plan["profitLossProjection"] = wrap(business_plan_data.get("profitLossProjection"))
        structured_plan["balanceSheet"] = wrap(business_plan_data.get("balanceSheet"))

        structured_plan["debtStructure"] = wrap(business_plan_data.get("debtStructure"))

        structured_plan["ratiosAnalysis"] = wrap(business_plan_data.get("ratiosAnalysis"))
        # structured_plan.setdefault("operating_cost_breakdown", [])

        return structured_plan

# -------------------------------------------------
# 8.  FAST-API ENTRY-POINT FUNCTIONS (unchanged)
# -------------------------------------------------
async def generate_business_plan(
    uploaded_file: Optional[List[Any]] = None,
    user_input: List[Any] = None,
    user_id: str = None
) -> Dict:
    service = BusinessPlanService()
    return await service.generate_business_plan(uploaded_file, user_input, user_id)

SUGGESTION_PROMPT = """
You are an expert business plan consultant. Generate 4 different possible professional answers for the following business plan question. 
Keep each answer concise (Less than 10 words).
ALWAYS MAKE SURE THAT THE SUGGESTION WILL BE IN ITALIAN LANGUAGE.
Return the answers in a clean JSON array format.

Question: {question}

Return ONLY a valid JSON array of strings, no additional text or explanations.
"""



async def generate_suggestions(question: str) -> List[str]:
    """Generate suggestion options for business plan questions."""
    client = get_openai_client()

    messages = [{"role": "system", "content": SUGGESTION_PROMPT.format(question=question)}]

    try:
        response = await client.chat.completions.create(
            messages=messages,
            model="gpt-4o-mini",
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
