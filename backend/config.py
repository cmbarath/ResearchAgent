import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Settings:
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2:latest")
    MAX_STEPS: int = int(os.getenv("MAX_STEPS", "8"))
    MAX_TOTAL_TOKENS: int = int(os.getenv("MAX_TOTAL_TOKENS", "6000"))
    PAGE_FETCH_TIMEOUT: float = float(os.getenv("PAGE_FETCH_TIMEOUT", "10.0"))
    MAX_PAGE_CHARS: int = int(os.getenv("MAX_PAGE_CHARS", "4000"))
    MAX_SEARCH_RESULTS: int = int(os.getenv("MAX_SEARCH_RESULTS", "5"))

settings = Settings()
