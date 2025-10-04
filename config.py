"""
Configuration file for PharmaGEN application
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration"""
    
    # API Configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash-latest")
    GEMINI_TEMPERATURE = float(os.getenv("GEMINI_TEMPERATURE", "0.7"))
    GEMINI_TRANSLATION_TEMP = float(os.getenv("GEMINI_TRANSLATION_TEMP", "0.1"))
    
    # Rate Limiting
    RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "True").lower() == "true"
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
    RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "100"))
    
    # Redis Configuration (for rate limiting and caching)
    REDIS_ENABLED = os.getenv("REDIS_ENABLED", "False").lower() == "true"
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
    
    # Cache Configuration
    CACHE_ENABLED = os.getenv("CACHE_ENABLED", "True").lower() == "true"
    CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour
    
    # Server Configuration
    SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT = int(os.getenv("SERVER_PORT", "7860"))
    DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"
    
    # Security
    MAX_MESSAGE_LENGTH = int(os.getenv("MAX_MESSAGE_LENGTH", "2000"))
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "pharmagen.log")
    
    # PDF Configuration
    PDF_OUTPUT_DIR = os.getenv("PDF_OUTPUT_DIR", "./reports")
    MAX_PDF_SIZE_MB = int(os.getenv("MAX_PDF_SIZE_MB", "10"))
    
    # Session Configuration
    SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))
    MAX_CONCURRENT_SESSIONS = int(os.getenv("MAX_CONCURRENT_SESSIONS", "100"))
    
    # UI/UX Configuration
    APP_TITLE = os.getenv("APP_TITLE", "PharmaGEN")
    APP_SUBTITLE = os.getenv("APP_SUBTITLE", "Next-Gen Medical Assistant & Drug Concept Generator")
    APP_EMOJI = os.getenv("APP_EMOJI", "🧬")
    THEME_PRIMARY_COLOR = os.getenv("THEME_PRIMARY_COLOR", "indigo")
    THEME_SECONDARY_COLOR = os.getenv("THEME_SECONDARY_COLOR", "cyan")
    CHATBOT_HEIGHT = int(os.getenv("CHATBOT_HEIGHT", "600"))
    ENABLE_QUEUE = os.getenv("ENABLE_QUEUE", "True").lower() == "true"
    MAX_QUEUE_SIZE = int(os.getenv("MAX_QUEUE_SIZE", "10"))
    
    # Language Configuration
    DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "English")
    SHOW_LANGUAGE_EXAMPLES = os.getenv("SHOW_LANGUAGE_EXAMPLES", "True").lower() == "true"
    
    # Feature Flags
    ENABLE_PDF_DOWNLOAD = os.getenv("ENABLE_PDF_DOWNLOAD", "True").lower() == "true"
    ENABLE_CHAT_HISTORY = os.getenv("ENABLE_CHAT_HISTORY", "True").lower() == "true"
    SHOW_DISCLAIMER = os.getenv("SHOW_DISCLAIMER", "True").lower() == "true"

    @classmethod
    def validate(cls):
        """Validate configuration"""
        errors = []
        
        if not cls.GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY is not set")
        
        if cls.RATE_LIMIT_PER_MINUTE <= 0:
            errors.append("RATE_LIMIT_PER_MINUTE must be positive")
        
        if cls.SERVER_PORT < 1 or cls.SERVER_PORT > 65535:
            errors.append("SERVER_PORT must be between 1 and 65535")
        
        return errors
