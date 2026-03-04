import os
import tempfile
import mlflow


def _extract_with_pdfplumber(tmp_path: str) -> list[str]:
    import pdfplumber

    pages = []
    with pdfplumber.open(tmp_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text and text.strip():
                pages.append(text.strip())
    print(f"Pages parsed (pdfplumber): {len(pages)}")
    return pages


def _extract_with_llamaparse(tmp_path: str) -> list[str]:
    from llama_parse import LlamaParse

    parser = LlamaParse(
        result_type="markdown",
        language="fr",
        verbose=True,
        premium_mode=True,
    )
    documents = parser.load_data(tmp_path, extra_info={"invalidate_cache": True})
    print(f"Pages parsed (LlamaParse): {len(documents)}")
    return list(map(lambda d: d.text, documents)) if documents else []


@mlflow.trace
def extract_content_from_uploaded_pdf(uploaded_file):
    # Save uploaded file to a temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.file.read())
        tmp_path = tmp.name

    api_key = os.environ.get("LLAMA_CLOUD_API_KEY", "")
    use_llamaparse = api_key and api_key not in (
        "",
        "your_llama_cloud_api_key_here",
        "your_secret_key",
    )

    if use_llamaparse:
        try:
            return _extract_with_llamaparse(tmp_path)
        except Exception as e:
            print(f"LlamaParse failed ({e}), falling back to pdfplumber")

    return _extract_with_pdfplumber(tmp_path)
