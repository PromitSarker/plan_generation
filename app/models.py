from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# --------------------
# Basic Input Model
# --------------------
class BusinessIdeaInput(BaseModel):
    uploaded_file: Optional[List[Any]] = Field(
        [],
        description="Base64-encoded PDF or plain-text document (≤ 10 MB)"
    )
    user_input: List[Any] = Field(
        [],
        description="List of strings / objects describing the business idea or requirements"
    )
    language: str = "Italian"
    currency: str = "Euro"
    user_id: str

# --------------------
# Section & SubSection Models
# --------------------
class Section(BaseModel):
    title: str
    content: str

class SubSection(BaseModel):
    title: str
    sections: List[Section]

# --------------------
# Financial Models
# --------------------
class FinancialHighlight(BaseModel):
    year: int
    revenue: float
    net_income: float
    capex: float
    debt_repayment: float

class CashFlow(BaseModel):
    year: int
    operating: float
    investing: float
    financing: float
    net_cash: float

class ProfitLoss(BaseModel):
    year: int
    revenue: float
    cogs: float
    gross_profit: float
    operating_expenses: float
    ebitda: Optional[float] = None
    depreciation_amortization: Optional[float] = None
    ebit: Optional[float] = None
    interest: Optional[float] = None
    taxes: Optional[float] = None
    net_income: float

class BalanceSheet(BaseModel):
    year: int
    assets: float
    current_assets: Optional[float] = None
    non_current_assets: Optional[float] = None
    liabilities: float
    current_liabilities: Optional[float] = None
    non_current_liabilities: Optional[float] = None
    equity: float

class NetPosition(BaseModel):
    year: int
    net_position: float

class DebtRepayment(BaseModel):
    year: int
    repayment: float
    interest_rate: Optional[float] = None
    outstanding_debt: Optional[float] = None

class KeyRatio(BaseModel):
    year: int
    roi: float
    roe: float
    debt_to_equity: float
    gross_margin: Optional[float] = None
    ebitda_margin: Optional[float] = None
    net_margin: Optional[float] = None
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    asset_turnover: Optional[float] = None

class QuarterlyBreakdown(BaseModel):
    q1_revenue: float
    q2_revenue: float
    q3_revenue: float
    q4_revenue: float
    q1_costs: float
    q2_costs: float
    q3_costs: float
    q4_costs: float

class EmployeeAnalytics(BaseModel):
    management_costs: float
    operations_staff: float
    sales_team: float
    avg_salary_per_employee: float
    total_headcount: int
    cost_per_employee: float
    productivity_ratio: float
    overtime_costs: float
    benefits_percentage: float

class MarketingAnalytics(BaseModel):
    digital_marketing: float
    traditional_marketing: float
    events_conferences: float
    content_creation: float
    paid_advertising: float
    cost_per_acquisition: float
    marketing_roi: float
    lead_generation_cost: float
    conversion_cost: float

class OperationalMetrics(BaseModel):
    cost_per_unit_sold: float
    variable_cost_ratio: float
    fixed_cost_coverage: float
    operational_leverage: float
    cost_efficiency_index: float
    break_even_units: int
    capacity_utilization: float

class CostPercentages(BaseModel):
    cogs_percent: float
    employee_percent: float
    marketing_percent: float
    rent_percent: float
    admin_percent: float
    other_percent: float

class VarianceAnalysis(BaseModel):
    budget_vs_actual_variance: float
    yoy_cost_growth_rate: float
    cost_inflation_impact: float
    efficiency_improvement: float
    cost_per_revenue_ratio: float

class BenchmarkingRatios(BaseModel):
    industry_avg_cogs: float
    employee_cost_benchmark: float
    marketing_spend_benchmark: float
    admin_cost_benchmark: float

class OperatingCostBreakdown(BaseModel):
    year: int
    revenue: float
    cogs: float
    employee_costs: float
    marketing: float
    rent: float
    administration: float
    amortization: float
    other_expenses: float
    interest_expenses: float
    tax: float
    quarterly_breakdown: QuarterlyBreakdown
    employee_analytics: EmployeeAnalytics
    marketing_analytics: MarketingAnalytics
    operational_metrics: OperationalMetrics
    cost_percentages: CostPercentages
    variance_analysis: VarianceAnalysis
    benchmarking_ratios: BenchmarkingRatios

# --------------------
# Wayne SRL Financial Analysis
# --------------------
class FinancialAnalysis(BaseModel):
    year: int
    gross_operating_cash_flow: float
    working_capital_change: float
    current_management_cash_flow: float
    operating_cash_flow: float
    debt_service_cash_flow: float
    shareholders_cash_flow: float
    net_cash_flow: float
    sales_revenue: float
    production_value: float
    gross_operating_margin: float
    ebit: float
    ebt: float
    net_income: float
    dividends: float
    net_tangible_assets: float
    net_intangible_assets: float
    financial_assets: float
    trade_assets: float
    inventory: float
    deferred_liquidity: float
    immediate_liquidity: float
    equity: float
    long_term_debt: float
    short_term_debt: float
    net_financial_position: float
    mortgage_loans: float
    other_financial_debts: float
    cash_and_banks: float

class RatiosAnalysis(BaseModel):
    year: int
    roi: float
    roe: float
    ros: float
    ebit_margin: float
    net_debt_to_ebitda: float
    net_debt_to_equity: float
    net_debt_to_revenue: float
    current_ratio: float
    quick_ratio: float
    debt_to_equity: float
    treasury_margin: float
    structural_margin: float
    net_working_capital: float
    altman_z_score: float

# --------------------
# Core Business Plan Model
# --------------------
class BusinessPlan(BaseModel):
    executive_summary: str
    business_overview: str
    market_analysis: str
    business_model: str
    marketing_and_sales_strategy: Optional[str] = None
    sector_strategy: Optional[str] = None
    operations_plan: Optional[str] = None
    funding_sources: Optional[str] = None

    financial_highlights: List[FinancialHighlight] = []
    cash_flow_analysis: List[CashFlow] = []
    profit_and_loss_projection: List[ProfitLoss] = []
    balance_sheet: List[BalanceSheet] = []
    net_financial_position: List[NetPosition] = []
    debt_structure: List[DebtRepayment] = []
    key_ratios: List[KeyRatio] = []
    operating_cost_breakdown: List[OperatingCostBreakdown] = []
    financial_analysis: List[FinancialAnalysis] = []
    ratios_analysis: List[RatiosAnalysis] = []
# --------------------
# PDF & Suggestion Models
# --------------------
class PDFExtraction(BaseModel):
    text_content: str
    page_count: int
    metadata: Dict

class FinancialExtraction(BaseModel):
    total_assets: Optional[float] = None
    total_revenue: Optional[float] = None
    net_income: Optional[float] = None
    total_liabilities: Optional[float] = None
    equity: Optional[float] = None
    year: Optional[int] = None
    currency: Optional[str] = "EUR"

class DocumentExtraction(PDFExtraction):
    financial_data: Optional[FinancialExtraction] = None
    document_type: str

class SuggestionRequest(BaseModel):
    question: str = Field(..., description="The business plan question to generate suggestions for")

class SuggestionResponse(BaseModel):
    question: str
    suggestions: List[str]