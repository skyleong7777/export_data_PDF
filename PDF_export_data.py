import os
import json
import time
import argparse
import sys
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
import streamlit as st
import tempfile
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Configuration - Securely loaded from environment
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if not GEMINI_API_KEY:
    raise ValueError(
        "⚠️ GEMINI_API_KEY not found in environment variables!\n"
        "Please create a .env file with your API key:\n"
        "  1. Copy .env.example to .env\n"
        "  2. Replace 'your_api_key_here' with your actual Gemini API key\n"
        "  3. Get your key from: https://aistudio.google.com/apikey"
    )

try:
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    # Handle config error gracefully if run in environments where st is not yet ready
    pass

# Use 2.5 Pro for best understanding of screenshots and long text
def get_model():
    return genai.GenerativeModel(
        model_name='gemini-2.5-pro',
        generation_config=GenerationConfig(
            response_mime_type="application/json", # Force JSON output
            temperature=0.1 # Low temperature for precision and low hallucinations
        )
    )

def process_single_pdf(file_path, status_container=None):
    if status_container:
        status_container.info(f"🚀 Deep analysis in progress: {os.path.basename(file_path)}")
    else:
        print(f"🚀 Deep analysis in progress: {file_path}")
    
    uploaded_file = None
    try:
        model = get_model()
        # 1. Upload File
        uploaded_file = genai.upload_file(file_path)
        
        # 2. Wait for processing (Crucial for large files)
        while uploaded_file.state.name == "PROCESSING":
            time.sleep(2)
            uploaded_file = genai.get_file(uploaded_file.name)
             
        if uploaded_file.state.name != "ACTIVE":
             raise Exception(f"File processing failed with state: {uploaded_file.state.name}")
             
        # 3. RAG-Optimized Prompt with Citation Requirements
        prompt = """
        You are an expert technical documentation analyst specializing in L&W casino systems. 
        
        CRITICAL INSTRUCTIONS FOR GROUNDED EXTRACTION:
        - You MUST extract information ONLY from what is explicitly written in the PDF
        - NEVER infer, assume, or make up information not present in the document
        - For EVERY piece of extracted information, you MUST cite the exact page number
        - Include direct quotes from the PDF as evidence
        
        Your task is to extract technical Q&A pairs following these dimensions:
        1. Operational Logic: How to configure features (Offers, Blackouts, mappings, etc.)
        2. Troubleshooting: Error messages, failure scenarios, and resolution steps
        3. UI Navigation: Menu paths, button locations, screen transitions
        4. Business Rules: Specific values, limits, calculations, currency rules
        
        REQUIRED OUTPUT FORMAT (JSON List):
        [
          {
            "instruction": "Clear technical question based on the document content",
            "input": "Context (system version, screen location, user scenario)",
            "output": "Step-by-step solution or explanation",
            "page_number": <integer>,
            "source_quote": "Exact text snippet from the PDF that backs up this Q&A pair",
            "section": "Section title or heading from the document"
          }
        ]
        
        VALIDATION RULES:
        - page_number: Must be a valid page number from the PDF
        - source_quote: Must be a verbatim quote of at least 10 words from the PDF
        - section: The heading/title of the section where this information was found
        - If you cannot find explicit information for a Q&A pair, DO NOT include it
        - Prioritize accuracy over quantity
        
        Extract as many high-quality, grounded Q&A pairs as possible from this document.
        """

        # 4. Generate Content (with spinner in status_container if possible, but st.spinner context is tricky inside function)
        # We rely on the caller to handle spinner or just log
        if status_container:
            status_container.info(f"🧠 analyzing content of {os.path.basename(file_path)}... (This may take up to a minute)")
        else:
            print(f"🧠 analyzing content...")
            
        response = model.generate_content([uploaded_file, prompt])
        
        
        # 5. Parse JSON and Validate Citations
        batch_data = json.loads(response.text)
        
        # Validation: Check for required citation fields
        validated_data = []
        warnings = []
        
        for idx, entry in enumerate(batch_data):
            missing_fields = []
            
            if 'page_number' not in entry or not isinstance(entry.get('page_number'), int):
                missing_fields.append('page_number')
            
            if 'source_quote' not in entry or not entry.get('source_quote') or len(entry.get('source_quote', '')) < 10:
                missing_fields.append('source_quote (min 10 chars)')
            
            if 'section' not in entry or not entry.get('section'):
                missing_fields.append('section')
            
            if missing_fields:
                warnings.append(f"Entry {idx+1}: Missing {', '.join(missing_fields)}")
            else:
                validated_data.append(entry)
        
        if status_container:
            if warnings:
                status_container.warning(f"⚠️ {len(warnings)} entries filtered out due to missing citations. Kept {len(validated_data)}/{len(batch_data)} entries.")
                for warning in warnings[:3]:  # Show first 3 warnings
                    status_container.text(f"  {warning}")
            status_container.success(f"✅ Successfully extracted {len(validated_data)} grounded technical conversation pairs from {os.path.basename(file_path)}")
        else:
            if warnings:
                print(f"⚠️ {len(warnings)} entries filtered out due to missing citations:")
                for warning in warnings[:5]:
                    print(f"  {warning}")
            print(f"✅ Successfully extracted {len(validated_data)} technical conversation pairs")
        
        return validated_data
        
    except Exception as e:
        msg = f"❌ Failed to parse {file_path}: {str(e)}"
        if status_container:
            status_container.error(msg)
        else:
            print(msg)
        return []
    finally:
        # Cleanup
        if uploaded_file:
            try:
                genai.delete_file(uploaded_file.name)
            except:
                pass

def main_cli():
    parser = argparse.ArgumentParser(description="Extract expert data from PDF files using Gemini.")
    parser.add_argument("input_path", help="Path to a PDF file or a directory containing PDF files.")
    parser.add_argument("--output", default="casino_expert_train.jsonl", help="Output JSONL file path.")
    
    args = parser.parse_args()
    
    all_data = []
    files_to_process = []

    if os.path.isfile(args.input_path):
        if args.input_path.lower().endswith(".pdf"):
            files_to_process.append(args.input_path)
    elif os.path.isdir(args.input_path):
        for filename in sorted(os.listdir(args.input_path)):
            if filename.lower().endswith(".pdf"):
                files_to_process.append(os.path.join(args.input_path, filename))
    
    if not files_to_process:
        print(f"⚠️ No PDF files found in {args.input_path}")
        return

    for file_path in files_to_process:
        batch_data = process_single_pdf(file_path)
        all_data.extend(batch_data)

    if all_data:
        # Append mode
        mode = 'a' if os.path.exists(args.output) else 'w'
        with open(args.output, mode, encoding='utf-8') as f:
            for entry in all_data:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        print(f"🎊 Task Complete! Collected {len(all_data)} Casino IT expert data entries.")
        print(f"Saved to: {args.output}")
    else:
        print("⚠️ No data extracted.")

def main_streamlit():
    st.set_page_config(page_title="Casino PDF Expert Extractor", layout="wide")
    st.title("🎰 Casino PDF Expert Data Extractor")
    st.markdown("Upload PDF manuals to extract technical Q&A pairs for model training.")

    uploaded_files = st.file_uploader("Choose PDF files", type="pdf", accept_multiple_files=True)
    
    if st.button("Start Extraction"):
        if not uploaded_files:
            st.warning("Please upload at least one PDF file.")
            return

        all_data = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        with st.spinner('Starting extraction...'):
            for i, uploaded_file in enumerate(uploaded_files):
                status_text.text(f"Processing {uploaded_file.name} ({i+1}/{len(uploaded_files)})")
                
                # Save uploaded file to temp
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                try:
                    # status_container=st because we want inline updates inside the function as well
                    batch_data = process_single_pdf(tmp_path, status_container=st)
                    all_data.extend(batch_data)
                finally:
                    os.unlink(tmp_path)
                
                progress_bar.progress((i + 1) / len(uploaded_files))
        
        status_text.empty()

        if all_data:
            st.success(f"🎊 Task Complete! Collected {len(all_data)} Casino IT expert data entries.")
            
            # Show enhanced preview with citation details
            st.subheader("📊 Data Preview with Citations")
            
            if len(all_data) > 0:
                # Display first 3 entries in a more readable format
                for idx, entry in enumerate(all_data[:3], 1):
                    with st.expander(f"Entry {idx}: {entry.get('instruction', 'N/A')[:80]}..."):
                        st.markdown(f"**Question:** {entry.get('instruction', 'N/A')}")
                        st.markdown(f"**Context:** {entry.get('input', 'N/A')}")
                        st.markdown(f"**Answer:** {entry.get('output', 'N/A')}")
                        st.divider()
                        st.markdown("**🔍 Citation Info (RAG Grounding)**")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Page Number", entry.get('page_number', 'N/A'))
                        with col2:
                            st.text(f"Section: {entry.get('section', 'N/A')}")
                        st.info(f"**Source Quote:** {entry.get('source_quote', 'N/A')}")
            
            # Show full JSON for technical users
            with st.expander("View Raw JSON (all entries)"):
                st.json(all_data)
            
            # Download button
            jsonl_str = ""
            for entry in all_data:
                jsonl_str += json.dumps(entry, ensure_ascii=False) + '\n'
            
            st.download_button(
                label="Download JSONL Data",
                data=jsonl_str,
                file_name="casino_expert_train.jsonl",
                mime="application/jsonl"
            )
            
            # Also save locally for convenience if running locally
            try:
                mode = 'a' if os.path.exists("casino_expert_train.jsonl") else 'w'
                with open("casino_expert_train.jsonl", mode, encoding='utf-8') as f:
                    f.write(jsonl_str)
                st.info("Also saved to local file: casino_expert_train.jsonl")
            except:
                pass

        else:
            st.warning("⚠️ No data extracted from the uploaded files.")

if __name__ == "__main__":
    # Check if running via streamlit
    # Streamlit sets specific environment variables or modifying sys.argv mostly works,
    # but the reliable way is to check if we are in the main execution or imported by streamlit.
    # Actually, simpler: check if header is present or just try to import streamlit runtime?
    # No, 'streamlit run' executes the script. 'python script.py' executes the script.
    # If run with python, st.runtime.exists() is False (usually).
    
    # Simple heuristic: If arguments are passed, use CLI. If not, and running under streamlit, use GUI.
    # But if user runs "python script.py" without args, they might expect GUI.
    # We can detect if run via 'streamlit run' by checking sys.modules or environment.
    
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        if get_script_run_ctx():
            main_streamlit()
        else:
            if len(sys.argv) > 1:
                main_cli()
            else:
                print("To run with GUI, please use command:")
                print("streamlit run PDF_export_data.py")
                print("\nOr provide arguments for CLI mode:")
                print("python PDF_export_data.py <input_path>")
    except ImportError:
        # Fallback if streamlit is not installed or different version
        if len(sys.argv) > 1:
            main_cli()
        else:
            print("To run with GUI, install streamlit and run:")
            print("streamlit run PDF_export_data.py")