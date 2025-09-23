from fastapi import FastAPI, HTTPException, Request, File, UploadFile, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from app.pdf_service import extract_from_multiple_pdfs, extract_text_from_pdf

from app.models import (
    BusinessIdeaInput,
    BusinessPlan,
    PDFExtraction,
    SuggestionRequest,
    SuggestionResponse,
    DocumentExtraction,
    FinancialExtraction
)

from app.services import generate_business_plan, generate_suggestions
from app.pdf_service import extract_text_from_pdf

app = FastAPI(
    title="Business Plan Generator API",
    version="1.0.0",
    description="Generates a comprehensive JSON business plan"
)


import re

def clean_text(text: str) -> str:
    """Remove control characters that break JSON parsing."""
    if not text:
        return text
    return re.sub(r"[\x00-\x1f]", " ", text)

# ---------------- CORS ----------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Endpoints ----------------

@app.post("/generate", response_model=dict)
async def create_business_plan(payload: BusinessIdeaInput):
    """
    Generate a business plan from user input and optional PDF text
    """
    try:
        plan_dict = await generate_business_plan(
            uploaded_file=payload.uploaded_file,
            user_input=payload.user_input,
            user_id=payload.user_id
        )

        # Clean all string fields in the returned plan
        for key, value in plan_dict.items():
            if isinstance(value, str):
                plan_dict[key] = clean_text(value)

        return plan_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate business plan: {str(e)}")


@app.post("/extract-pdf", response_model=DocumentExtraction)
async def extract_pdf(
    files: List[UploadFile] = File(...),
    document_type: str = Query(..., description="Type of document: 'balance_sheet' or 'company_extract'")
):
    """Extract and merge text and financial data from multiple PDF files"""
    files_content = []
    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"File {file.filename} must be a PDF")
        content = await file.read()
        files_content.append(content)

    merged_results = extract_from_multiple_pdfs(files_content, document_type, merge=True)
    text, pages, metadata, financial_data = merged_results[0]

    return DocumentExtraction(
        text_content=text,
        page_count=pages,
        metadata=metadata,
        financial_data=FinancialExtraction(**financial_data) if financial_data else None,
        document_type=document_type
    )

@app.post("/suggestions", response_model=SuggestionResponse)
async def get_suggestions(request: SuggestionRequest):
    """
    Generate multiple concise suggestions for a business plan question
    """
    try:
        suggestions = await generate_suggestions(
            question=request.question
        )
        return SuggestionResponse(
            question=request.question,
            suggestions=suggestions
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate suggestions: {str(e)}")


@app.get("/health")
def health():
    """
    Health check endpoint
    """
    return {"status": "ok"}


# ---------------- Global Exception Handler ----------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )
