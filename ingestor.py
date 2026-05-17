"""
Text extraction module for Corpus Forge.

This module provides functionality to extract text from various file types:
- PDF files (.pdf) using PyMuPDF (fitz)
- Plain text and markdown files (.txt, .md)
- Source code files (.py, .js)
"""

import fitz
from pathlib import Path


def extract_pdf(filepath):
    """
    Extract all text from a PDF file.
    
    Args:
        filepath (str): Path to the PDF file.
        
    Returns:
        str: Concatenated text from all pages of the PDF.
        
    Raises:
        Exception: If the PDF cannot be opened or read.
    """
    text_content = []
    
    with fitz.open(filepath) as pdf_document:
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            text = page.get_text()
            text_content.append(text)
    
    return "".join(text_content)


def extract_text_file(filepath):
    """
    Extract text from a plain text or markdown file.
    
    Args:
        filepath (str): Path to the text file (.txt or .md).
        
    Returns:
        str: Content of the file as UTF-8 text.
        
    Raises:
        UnicodeDecodeError: If the file cannot be decoded as UTF-8.
    """
    with open(filepath, "r", encoding="utf-8") as file:
        return file.read()


def extract_source_code(filepath):
    """
    Extract text from a source code file.
    
    Args:
        filepath (str): Path to the source code file (.py or .js).
        
    Returns:
        str: Content of the file as UTF-8 text.
        
    Raises:
        UnicodeDecodeError: If the file cannot be decoded as UTF-8.
    """
    with open(filepath, "r", encoding="utf-8") as file:
        return file.read()


def ingest_file(filepath):
    """
    Extract text from a file based on its type.
    
    Supports the following file types:
    - PDF files (.pdf)
    - Plain text files (.txt)
    - Markdown files (.md)
    - Python files (.py)
    - JavaScript files (.js)
    
    Args:
        filepath (str): Path to the file to ingest.
        
    Returns:
        str: Extracted text content from the file.
        
    Raises:
        ValueError: If the file type is not supported.
        FileNotFoundError: If the file does not exist.
        Exception: For other errors during extraction (e.g., corrupted PDFs).
    """
    # Convert to Path object for easier manipulation
    path = Path(filepath)
    
    # Check if file exists
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    # Get file extension (lowercase for case-insensitive comparison)
    extension = path.suffix.lower()
    
    # Route to appropriate extraction function
    if extension == ".pdf":
        return extract_pdf(filepath)
    elif extension in [".txt", ".md"]:
        return extract_text_file(filepath)
    elif extension in [".py", ".js"]:
        return extract_source_code(filepath)
    else:
        supported_types = [".pdf", ".txt", ".md", ".py", ".js"]
        raise ValueError(
            f"Unsupported file type: {extension}. "
            f"Supported types are: {', '.join(supported_types)}"
        )


if __name__ == "__main__":
    # Example usage
    sample_files = [
        "example.pdf",
        "readme.md",
        "script.py",
    ]
    
    for sample_file in sample_files:
        try:
            content = ingest_file(sample_file)
            print(f"Successfully ingested {sample_file}")
            print(f"Content length: {len(content)} characters\n")
        except FileNotFoundError:
            print(f"File not found: {sample_file}\n")
        except ValueError as e:
            print(f"Error: {e}\n")
        except Exception as e:
            print(f"Unexpected error processing {sample_file}: {e}\n")
