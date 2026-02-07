# Implementation Plan: Enhanced PDF Data Extraction for RAG

## Objective
Upgrade the existing `PDF_export_data.py` system to produce high-quality, grounded data suitable for Retrieval-Augmented Generation (RAG). The focus is on traceability (citations, page numbers) and reliability (reduced hallucinations).

## Core Improvements

### 1. Enhanced Metadata & Schema
We will move from a simple list of Q&A pairs to a structured schema including:
- **`page_number`**: The specific page(s) where the information is found.
- **`citation_quote`**: Verbatim text from the document supporting the extraction.
- **`confidence_score`**: Self-assessed confidence (0.0-1.0).
- **`category`**: Semantic category (Operational, Troubleshooting, etc.).
- **`source_file`**: Filename hash or identifier.

### 2. Dual Extraction Modes
We will implement two distinct processing strategies:

*   **Mode A: Synthesis (Q&A Pairs)**
    *   *Goal*: Generate training data or FAQ style output.
    *   *Method*: Similar to current approach but enforces a "Proof" field requiring a direct quote.
    
*   **Mode B: Grounded Extraction (Fact-based)**
    *   *Goal*: Build a knowledge base for RAG.
    *   *Method*: Segment-level processing. Extracts atomic facts with strict location pointers.

### 3. Prompt Engineering
Refine the Gemini prompt to:
- Use **JSON Schema** enforcement (if supported by the model version) or strict one-shot examples.
- Explicitly penalize hallucinated page numbers.
- Require `citation_quote` for every claim.

### 4. Validation Pipeline
Integrate a local PDF text extractor (using `pdfplumber` or `pypdf`) to validat extraction:
- **Verification Step**: For every extracted item, search for the `citation_quote` in the local PDF text.
- **Flagging**: Mark items where the quote is not found or the page number does not match the text location.

## Technical Architecture

### New Dependencies
- `pdfplumber`: For accurate local text/page mapping to verify AI output.
- `pydantic`: For robust schema validation (optional but recommended).

### Workflow
1.  **Ingest**: Load PDF.
2.  **Pre-process**: Extract text map (Page N -> Text Content) locally using `pdfplumber`.
3.  **AI Process**: Upload PDF to Gemini (multimodal) for understanding charts/images.
4.  **Extract**: Run prompt asking for JSON with `page_number` and `citation`.
5.  **Post-process (Validation)**:
    -   Iterate through AI results.
    -   Fuzzy match `citation` against `Page N` text from step 2.
    -   Update `verification_status` (Verified/Hallucinated/Modified).
6.  **Export**: Save as JSONL with full metadata.

## Execution Steps
1.  **Environment Setup**: Install `pdfplumber`.
2.  **Script Refactoring**:
    -   Create `class PDFProcessor` to handle state.
    -   Add `verify_citation(page, quote)` method.
3.  **Prompt Update**: Rewrite the system prompt.
4.  **Testing**: Run on `my_casino_pdfs` and manually inspect "Verified" vs "Unverified" outputs.
