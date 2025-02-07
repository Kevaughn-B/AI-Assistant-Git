# Reads And Processes Text
from PyPDF2 import PdfReader
import re

class TextProcessor:
    def extract_text_from_pdf(self, pdf_path):
        try:
            reader = PdfReader(pdf_path)
            text = ""

            for page in reader.pages:
                raw_text = page.extract_text()
                if raw_text:
                    text += raw_text + "\n"

            cleaned_text = re.sub(r'\s+', ' ', text).strip()
            return cleaned_text
        except Exception as e:
            return f"Error processing PDF: {e}"

# Example use
if __name__ == "__main__":
    processor = TextProcessor()
    text = processor.extract_text_from_pdf("sample_document.pdf")
    print(text)
