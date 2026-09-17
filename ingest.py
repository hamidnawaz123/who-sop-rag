import argparse
from pathlib import Path
import  fitz
import pdfplumber
import chromadb
from sentence_transformers import SentenceTransformer

def extract_structure_and_tables(pdf_path):
    pdf_tables = {}
    with pdfplumber.open(pdf_path) as plumber_pdf:
        for page_idx, page in enumerate(plumber_pdf.pages):
            tables = page.extract_tables()
            if tables:
                pdf_tables[page_idx] = tables

    doc = fitz.open(pdf_path)
    chunks = []
    current_section = "General"
    current_text = ""

    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    font_size = span["size"]
                    
                    if font_size > 14 and len(text) > 3:
                        if current_text:
                            chunks.append({"section": current_section, "content": current_text, "page": page_num})
                            current_text = ""
                        current_section = text
                    else:
                        current_text += " " + text

        if page_num in pdf_tables:
            for table in pdf_tables[page_num]:
                table_str = "\n".join([" | ".join([str(cell) for cell in row if cell]) for row in table])
                current_text += f"\n[TABLE DATA]:\n{table_str}\n"

    if current_text:
        chunks.append({"section": current_section, "content": current_text, "page": len(doc)})

    return chunks

def build_vector_store(chunks):
    model = SentenceTransformer("BAAI/bge-m3")
    client = chromadb.PersistentClient(path="./chroma_db")
    collection = client.get_or_create_collection(name="sop_chunks")

    for i, chunk in enumerate(chunks):
        embedding = model.encode(chunk["content"]).tolist()
        collection.add(
            ids=[f"chunk_{i}"],
            embeddings=[embedding],
            documents=[chunk["content"]],
            metadatas=[{"section": chunk["section"], "page": chunk["page"]}]
        )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest a SOP PDF into the vector store.")
    parser.add_argument(
        "pdf_path",
        type=Path,
        nargs="?",
        default=Path("REPORT_SOP_english_low.pdf"),
        help="Path to the PDF file to ingest"
    )
    args = parser.parse_args()

    if not args.pdf_path.is_file():
        parser.error(f"PDF file not found: {args.pdf_path}")

    extracted_chunks = extract_structure_and_tables(args.pdf_path)
    build_vector_store(extracted_chunks)