# PDF Expert Data Extractor

A RAG-optimized PDF extraction tool that extracts grounded Q&A pairs from technical documentation with citations to prevent hallucination.

## Features

- ✅ **Citation-Backed Extraction**: Every Q&A pair includes page numbers, source quotes, and section headers
- ✅ **Validation Filtering**: Automatically rejects entries without proper citations
- ✅ **Streamlit Web Interface**: User-friendly drag-and-drop file upload
- ✅ **Command-Line Support**: Batch processing for automation
- ✅ **RAG-Ready Output**: JSONL format optimized for Retrieval-Augmented Generation

## Output Format

```json
{
  "instruction": "Question based on PDF content",
  "input": "Context information",
  "output": "Step-by-step answer",
  "page_number": 5,
  "source_quote": "Direct quote from PDF that supports this answer",
  "section": "Section title from PDF"
}
```

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd export-data-from-PDF
```

2. Create a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. **Set up your Google Gemini API key (IMPORTANT)**:

   a. Get an API key from [Google AI Studio](https://aistudio.google.com/apikey)
   
   b. Create a `.env` file in the project root:
   ```bash
   cp .env.example .env
   ```
   
   c. Edit `.env` and add your API key:
   ```
   GEMINI_API_KEY=your_actual_api_key_here
   ```
   
   ⚠️ **NEVER commit your `.env` file to GitHub** - it's already in `.gitignore`

## Usage

### Web Interface (Recommended)

```bash
streamlit run PDF_export_data.py
```

Then open http://localhost:8501 in your browser and upload your PDFs.

### Command Line

Process a single PDF:
```bash
python PDF_export_data.py "path/to/document.pdf" --output output.jsonl
```

Process all PDFs in a directory:
```bash
python PDF_export_data.py "path/to/pdf_folder/" --output output.jsonl
```

## Requirements

- Python 3.9+ (3.10+ recommended)
- Google Gemini API key
- See `requirements.txt` for full dependency list

## Project Structure

```
export-data-from-PDF/
├── PDF_export_data.py       # Main extraction script
├── requirements.txt          # Python dependencies
├── .gitignore               # Git ignore rules
├── README.md                # This file
└── my_pdfs/          # Sample PDFs directory (ignored by git)
```

## How It Works

1. **Upload**: PDFs are uploaded via Gemini's file API
2. **Prompt**: RAG-optimized prompt requires citations for all extractions
3. **Validation**: Filters out entries without page numbers/source quotes
4. **Export**: Saves to JSONL with full citation metadata

## Citation Quality

The system enforces:
- ✅ Valid integer page numbers
- ✅ Source quotes (minimum 10 characters, verbatim from PDF)
- ✅ Section headers/titles
- ✅ No hallucinated or inferred information

## Use Cases

- **RAG Training Data**: Create grounded Q&A pairs for model fine-tuning
- **Documentation Search**: Build citation-backed knowledge bases
- **Compliance**: Ensure AI responses can be traced to source documents

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

MIT License - See LICENSE file for details

## Security Note

⚠️ **Important**: Never commit API keys to version control. Use environment variables for production deployments.

## Support

For issues or questions, please open a GitHub issue.
