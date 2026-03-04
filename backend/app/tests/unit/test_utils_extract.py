from app.services.utils.extract import extract_content_from_uploaded_pdf
from unittest.mock import patch
import io


class FakeUpload:
    def __init__(self, content: bytes):
        self.file = io.BytesIO(content)


@patch("app.services.utils.extract._extract_with_pdfplumber")
def test_extract_content_from_uploaded_pdf(mock_pdfplumber):
    """Default path: no API key → uses pdfplumber."""
    mock_pdfplumber.return_value = ["Page 1", "Page 2"]

    fake_file = FakeUpload(b"fake pdf content")

    result = extract_content_from_uploaded_pdf(fake_file)

    assert result == ["Page 1", "Page 2"]
    mock_pdfplumber.assert_called_once()


@patch.dict("os.environ", {"LLAMA_CLOUD_API_KEY": "real-api-key-123"})
@patch("app.services.utils.extract._extract_with_llamaparse")
def test_extract_with_llamaparse_when_key_set(mock_llamaparse):
    """When a valid API key is set, LlamaParse path is used."""
    mock_llamaparse.return_value = ["Page A", "Page B"]

    fake_file = FakeUpload(b"fake pdf content")

    result = extract_content_from_uploaded_pdf(fake_file)

    assert result == ["Page A", "Page B"]
    mock_llamaparse.assert_called_once()
