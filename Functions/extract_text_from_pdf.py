import fitz  # PyMuPDF

# Helper function to extract text from PDF bytes
def extract_text_from_bytes(pdf_bytes: bytes) -> str:
    text_content = ""
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            text_content += page.get_text()
    return text_content