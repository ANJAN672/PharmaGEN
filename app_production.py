"""
PharmaGEN - Improved UI/UX Version
Enhanced with modern design, better user experience, and fully configurable settings
"""
import gradio as gr
import re
import os
import logging
import time
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
import google.generativeai as genai
from fpdf import FPDF
import webbrowser
from config import Config

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Optional Redis for caching and rate limiting
redis_client = None
if Config.REDIS_ENABLED:
    try:
        import redis
        redis_client = redis.Redis(
            host=Config.REDIS_HOST,
            port=Config.REDIS_PORT,
            db=Config.REDIS_DB,
            password=Config.REDIS_PASSWORD,
            decode_responses=True
        )
        redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Falling back to in-memory storage.")
        redis_client = None

# In-memory cache and rate limiting (fallback)
memory_cache = {}
rate_limit_store = {}

# Check if running in Google Colab
try:
    from google.colab import files
    IN_COLAB = True
    logger.info("Running in Google Colab environment")
except ImportError:
    IN_COLAB = False
    logger.info("Running in standard environment")

# Language mapping for translation
LANG_CODES = {
    "English": "en", "Arabic": "ar", "German": "de", "Spanish": "es", "French": "fr",
    "Hindi": "hi", "Italian": "it", "Japanese": "ja", "Korean": "ko", "Portuguese": "pt",
    "Russian": "ru", "Chinese": "zh", "Bengali": "bn", "Tamil": "ta", "Telugu": "te", 
    "Thai": "th", "Ukrainian": "uk", "Turkish": "tr", "Vietnamese": "vi", "Kannada": "kn"
}

# --- Rate Limiting ---
def check_rate_limit(user_id: str) -> bool:
    """Check if user has exceeded rate limit"""
    if not Config.RATE_LIMIT_ENABLED:
        return True
    
    current_time = time.time()
    minute_key = f"rate_limit:{user_id}:minute"
    hour_key = f"rate_limit:{user_id}:hour"
    
    if redis_client:
        try:
            minute_count = redis_client.incr(minute_key)
            if minute_count == 1:
                redis_client.expire(minute_key, 60)
            
            hour_count = redis_client.incr(hour_key)
            if hour_count == 1:
                redis_client.expire(hour_key, 3600)
            
            if minute_count > Config.RATE_LIMIT_PER_MINUTE:
                logger.warning(f"Rate limit exceeded for user {user_id}: {minute_count} requests/minute")
                return False
            
            if hour_count > Config.RATE_LIMIT_PER_HOUR:
                logger.warning(f"Rate limit exceeded for user {user_id}: {hour_count} requests/hour")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
    
    # In-memory rate limiting
    if user_id not in rate_limit_store:
        rate_limit_store[user_id] = {"minute": [], "hour": []}
    
    rate_limit_store[user_id]["minute"] = [
        t for t in rate_limit_store[user_id]["minute"] if current_time - t < 60
    ]
    rate_limit_store[user_id]["hour"] = [
        t for t in rate_limit_store[user_id]["hour"] if current_time - t < 3600
    ]
    
    if len(rate_limit_store[user_id]["minute"]) >= Config.RATE_LIMIT_PER_MINUTE:
        logger.warning(f"Rate limit exceeded for user {user_id}")
        return False
    
    if len(rate_limit_store[user_id]["hour"]) >= Config.RATE_LIMIT_PER_HOUR:
        logger.warning(f"Rate limit exceeded for user {user_id}")
        return False
    
    rate_limit_store[user_id]["minute"].append(current_time)
    rate_limit_store[user_id]["hour"].append(current_time)
    
    return True

# --- Caching ---
def get_cache(key: str) -> Optional[str]:
    """Get cached value"""
    if not Config.CACHE_ENABLED:
        return None
    
    if redis_client:
        try:
            return redis_client.get(f"cache:{key}")
        except Exception as e:
            logger.error(f"Redis cache get failed: {e}")
    
    if key in memory_cache:
        value, expiry = memory_cache[key]
        if time.time() < expiry:
            return value
        else:
            del memory_cache[key]
    
    return None

def set_cache(key: str, value: str, ttl: int = None):
    """Set cached value"""
    if not Config.CACHE_ENABLED:
        return
    
    if ttl is None:
        ttl = Config.CACHE_TTL
    
    if redis_client:
        try:
            redis_client.setex(f"cache:{key}", ttl, value)
            return
        except Exception as e:
            logger.error(f"Redis cache set failed: {e}")
    
    memory_cache[key] = (value, time.time() + ttl)

def cache_key(text: str, src_lang: str, tgt_lang: str) -> str:
    """Generate cache key for translation"""
    content = f"{text}:{src_lang}:{tgt_lang}"
    return hashlib.md5(content.encode()).hexdigest()

# --- API Initialization ---
def initialize_gemini():
    """Initialize Gemini API client"""
    try:
        errors = Config.validate()
        if errors:
            for error in errors:
                logger.error(f"Configuration error: {error}")
            if not Config.GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY is required. Please set it in your .env file")
        
        genai.configure(api_key=Config.GEMINI_API_KEY)
        client = genai.GenerativeModel(Config.GEMINI_MODEL_NAME)
        logger.info(f"Gemini API client initialized with model: {Config.GEMINI_MODEL_NAME}")
        return client
    except Exception as e:
        logger.error(f"Error initializing Gemini model: {e}")
        raise

gemini_client = initialize_gemini()

# --- Helper Functions ---
def sanitize_input(text: str) -> str:
    """Sanitize user input"""
    if not text:
        return ""
    text = text[:Config.MAX_MESSAGE_LENGTH]
    text = text.strip()
    return text

def gemini_translate(text: str, src_lang_code: str, tgt_lang_code: str, temp: float = None) -> str:
    """Translates text using Gemini with caching"""
    if temp is None:
        temp = Config.GEMINI_TRANSLATION_TEMP
    
    if not text or text.strip() == "":
        return ""
    
    cache_k = cache_key(text, src_lang_code, tgt_lang_code)
    cached_result = get_cache(cache_k)
    if cached_result:
        logger.debug(f"Translation cache hit for key: {cache_k}")
        return cached_result
    
    effective_src_lang_code = src_lang_code if src_lang_code in LANG_CODES.values() else "auto"
    effective_tgt_lang_code = tgt_lang_code if tgt_lang_code in LANG_CODES.values() else "en"
    
    if effective_src_lang_code != "auto" and effective_src_lang_code == effective_tgt_lang_code:
        return text
    
    tgt_lang_name = next((name for name, code in LANG_CODES.items() if code == effective_tgt_lang_code), effective_tgt_lang_code)
    
    # Create a strict translation prompt
    if effective_src_lang_code != "auto":
        src_lang_name = next((name for name, code in LANG_CODES.items() if code == effective_src_lang_code), effective_src_lang_code)
        prompt = f"""You are a professional translator. Translate the following text from {src_lang_name} to {tgt_lang_name}.

CRITICAL RULES:
1. Translate EVERYTHING to {tgt_lang_name}
2. Do NOT leave any English words
3. Do NOT add explanations or notes
4. Output ONLY the translated text

Text: {text}

{tgt_lang_name} Translation:"""
    else:
        prompt = f"""You are a professional translator. Translate the following text to {tgt_lang_name}.

CRITICAL RULES:
1. Translate EVERYTHING to {tgt_lang_name}
2. Do NOT leave any English words
3. Do NOT add explanations or notes
4. Output ONLY the translated text

Text: {text}

{tgt_lang_name} Translation:"""
    
    try:
        response = gemini_client.generate_content(
            prompt, 
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                max_output_tokens=1000
            )
        )
        result = response.text.strip()
        
        # Check if translation actually happened (not just returning English)
        # If result is too similar to input and target is not English, retry with stronger prompt
        if tgt_lang_code != 'en' and len(result) > 0:
            # If result contains mostly English characters and target is non-Latin, it failed
            english_chars = sum(1 for c in result if ord(c) < 128)
            total_chars = len(result)
            if total_chars > 0 and (english_chars / total_chars) > 0.8:
                # Translation failed, try again with even stronger prompt
                logger.warning(f"Translation may have failed (too much English), retrying...")
                retry_prompt = f"""TRANSLATE TO {tgt_lang_name.upper()} ONLY. NO ENGLISH ALLOWED.

English text: {text}

Your {tgt_lang_name} translation (MUST be in {tgt_lang_name} script):"""
                
                retry_response = gemini_client.generate_content(
                    retry_prompt,
                    generation_config=genai.GenerationConfig(temperature=0.1, max_output_tokens=1000)
                )
                result = retry_response.text.strip()
        
        # Clean up any extra explanations
        if '\n' in result and len(result.split('\n')) > 5:
            # If too many lines, probably has explanations
            lines = result.split('\n')
            # Take the longest line as it's likely the translation
            result = max(lines, key=len).strip()
        
        set_cache(cache_k, result)
        return result
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return text

def get_gemini_response(prompt_text: str, chat_history: list = None, temp: float = None) -> str:
    """Gets a response from the Gemini API with error handling"""
    if temp is None:
        temp = Config.GEMINI_TEMPERATURE
    
    try:
        formatted_history = []
        if chat_history:
            for turn in chat_history:
                if isinstance(turn, dict) and "role" in turn and "parts" in turn:
                    formatted_history.append({
                        "role": turn["role"], 
                        "parts": [{"text": turn["parts"][0]["text"]}]
                    })
        
        if formatted_history:
            chat_session = gemini_client.start_chat(history=formatted_history)
            response = chat_session.send_message(prompt_text)
        else:
            response = gemini_client.generate_content(
                prompt_text, 
                generation_config=genai.GenerationConfig(temperature=temp)
            )
        
        return response.text
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        error_detail = str(e).lower()
        
        if "401" in error_detail or "unauthorized" in error_detail or "api key not valid" in error_detail:
            return "❌ Error: Invalid API key. Please check your GEMINI_API_KEY in the .env file."
        elif "429" in error_detail or "quota" in error_detail or "rate" in error_detail:
            return "⏳ Error: Rate limit exceeded. Please try again in a few moments."
        elif "400" in error_detail or "invalid" in error_detail:
            return "⚠️ Error: Invalid request. Please try rephrasing your message."
        else:
            return f"❌ Error: Unable to process your request. Please try again later."

def generate_pdf_report(chat_state: Dict[str, Any]) -> Optional[str]:
    """Generates HTML report and opens in browser for printing"""
    if not Config.ENABLE_PDF_DOWNLOAD:
        logger.warning("PDF download is disabled")
        return None
    
    try:
        logger.info("Generating HTML report...")
        state_data = chat_state.copy()
        
        user_language = state_data.get("language", "English")
        translated_summary = state_data.get("translated_summary", "")
        
        if not translated_summary:
            logger.warning("No summary available to generate report")
            return None
        
        os.makedirs(Config.PDF_OUTPUT_DIR, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_filename = f"PharmaGEN_Report_{timestamp}.html"
        html_output_path = os.path.join(Config.PDF_OUTPUT_DIR, html_filename)
        
        # Clean up the summary and format as HTML
        clean_summary = translated_summary.replace("###", "<h3>").replace(":", ":</h3>", 1)
        
        # Create HTML with proper Unicode support
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{Config.APP_TITLE} - Medical Report</title>
    <style>
        @page {{
            size: A4;
            margin: 2cm;
        }}
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            text-align: center;
            border-bottom: 3px solid #667eea;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            color: #667eea;
            margin: 0;
            font-size: 28px;
        }}
        .meta {{
            color: #666;
            font-size: 14px;
            margin-top: 10px;
        }}
        h3 {{
            color: #667eea;
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 8px;
            margin-top: 25px;
        }}
        .content {{
            margin: 20px 0;
        }}
        .disclaimer {{
            background: #fff3cd;
            border: 2px solid #ffc107;
            border-radius: 8px;
            padding: 15px;
            margin-top: 30px;
        }}
        .disclaimer h3 {{
            color: #856404;
            margin-top: 0;
        }}
        .disclaimer p {{
            margin: 5px 0;
            color: #856404;
        }}
        @media print {{
            body {{
                margin: 0;
                padding: 15mm;
            }}
            .no-print {{
                display: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧬 {Config.APP_TITLE}</h1>
        <h2>Medical Report</h2>
        <div class="meta">
            <p><strong>Report Language:</strong> {user_language}</p>
            <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
    
    <div class="content">
        {clean_summary}
    </div>
    
    <div class="disclaimer">
        <h3>⚠️ DISCLAIMER</h3>
        <p><strong>This is an AI-generated report for conceptual purposes only.</strong></p>
        <p>• Always consult a qualified medical professional for health concerns.</p>
        <p>• Hypothetical drugs mentioned are NOT real medications.</p>
        <p>• This report is for educational purposes only.</p>
    </div>
    
    <div class="no-print" style="margin-top: 30px; text-align: center;">
        <button onclick="window.print()" style="background: #667eea; color: white; border: none; padding: 12px 30px; font-size: 16px; border-radius: 5px; cursor: pointer;">
            Print / Save as PDF
        </button>
    </div>
</body>
</html>"""
        
        # Write HTML file
        with open(html_output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML report saved to {html_output_path}")
        
        # Auto-open in browser
        try:
            webbrowser.open(f'file:///{os.path.abspath(html_output_path)}')
            logger.info(f"Opened report in browser")
        except Exception as browser_error:
            logger.warning(f"Could not auto-open browser: {browser_error}")
        
        return html_output_path
        
    except Exception as e:
        logger.error(f"Error generating report: {e}", exc_info=True)
        return None

# --- Chat Stages ---
CHAT_STAGE_ASK_LANGUAGE = "ask_language"
CHAT_STAGE_ASK_SYMPTOMS = "ask_symptoms"
CHAT_STAGE_ASK_ALLERGIES = "ask_allergies"
CHAT_STAGE_GENERATE_RESPONSE = "generate_response"
CHAT_STAGE_GENERAL_QNA = "general_qna"

def initialize_chat_state():
    """Initialize chat state"""
    return {
        "stage": CHAT_STAGE_ASK_LANGUAGE,
        "language": None,
        "lang_code": None,
        "symptoms_user_lang": None,
        "symptoms_en": None,
        "allergies_user_lang": None,
        "allergies_en": None,
        "diagnosis_en": None,
        "drug_concept_full_en": None,
        "gemini_chat_history_manual": [],
        "user_id": hashlib.md5(str(time.time()).encode()).hexdigest()[:8],
        "session_start": time.time()
    }

def process_chat(message: str, history: list, state: Dict[str, Any]):
    """Process user messages with rate limiting and error handling"""
    try:
        message = sanitize_input(message)
        
        if not message:
            return history, "", "", state
        
        user_id = state.get("user_id", "anonymous")
        if not check_rate_limit(user_id):
            error_msg = "⏳ Rate limit exceeded. Please wait a moment before sending another message."
            if history:
                history[-1] = [message, error_msg]
            else:
                history = [[message, error_msg]]
            return history, "", "", state
        
        if history is None:
            history = []
        
        history.append([message, ""])
        
        current_stage = state["stage"]
        user_lang_code = state.get("lang_code", "en")
        
        user_message_en = message
        if user_lang_code != "en" and user_lang_code is not None and message.strip():
            user_message_en = gemini_translate(message, user_lang_code, 'en')
        
        bot_response_en = ""
        bot_response_user_lang = ""
        
        english_summary = "📊 Report summary will appear here after diagnosis."
        translated_summary = "📋 Translated report summary will appear here."
        
        if current_stage == CHAT_STAGE_ASK_LANGUAGE:
            selected_language = message.strip().title()
            
            if selected_language in LANG_CODES:
                state["language"] = selected_language
                state["lang_code"] = LANG_CODES[selected_language]
                state["stage"] = CHAT_STAGE_ASK_SYMPTOMS
                user_lang_code = state["lang_code"]
                
                welcome_message_en = f"✅ Thank you! Your selected language is {selected_language}."
                next_prompt_en = "Please describe your symptoms in detail."
                bot_response_en = f"{welcome_message_en}\n\n{next_prompt_en}"
                
                welcome_message = gemini_translate(welcome_message_en, "en", user_lang_code)
                next_prompt = gemini_translate(next_prompt_en, "en", user_lang_code)
                bot_response_user_lang = f"{welcome_message}\n\n{next_prompt}"
                
                state["gemini_chat_history_manual"].append({
                    "role": "user", 
                    "parts": [{"text": f"User selected language: {selected_language}"}]
                })
                state["gemini_chat_history_manual"].append({
                    "role": "model", 
                    "parts": [{"text": bot_response_en}]
                })
            else:
                available_languages = ", ".join(sorted(LANG_CODES.keys()))
                error_message_en = f"❌ Sorry, '{message}' is not supported. Please select from:\n{available_languages}"
                bot_response_en = error_message_en
                bot_response_user_lang = error_message_en
        
        elif current_stage == CHAT_STAGE_ASK_SYMPTOMS:
            if not user_lang_code:
                bot_response_en = "❌ Error: Language not set. Please start over."
                bot_response_user_lang = bot_response_en
                state = initialize_chat_state()
            elif not message.strip():
                bot_response_en = "Please describe your symptoms so I can assist you."
                bot_response_user_lang = gemini_translate(bot_response_en, "en", user_lang_code)
            else:
                state["symptoms_user_lang"] = message.strip()
                state["symptoms_en"] = user_message_en
                state["stage"] = CHAT_STAGE_ASK_ALLERGIES
                
                bot_response_en = "✅ Thank you for sharing your symptoms. Do you have any known allergies? If none, please say 'None'."
                bot_response_user_lang = gemini_translate(bot_response_en, "en", user_lang_code)
                
                state["gemini_chat_history_manual"].append({
                    "role": "user", 
                    "parts": [{"text": f"Symptoms: {user_message_en}"}]
                })
                state["gemini_chat_history_manual"].append({
                    "role": "model", 
                    "parts": [{"text": bot_response_en}]
                })
        
        elif current_stage == CHAT_STAGE_ASK_ALLERGIES:
            if not user_lang_code:
                bot_response_en = "❌ Error: Language not set. Please start over."
                bot_response_user_lang = bot_response_en
                state = initialize_chat_state()
            else:
                state["allergies_user_lang"] = message.strip()
                state["allergies_en"] = user_message_en
                state["stage"] = CHAT_STAGE_GENERATE_RESPONSE
                
                state["gemini_chat_history_manual"].append({
                    "role": "user", 
                    "parts": [{"text": f"Allergies: {user_message_en}"}]
                })
                
                processing_message_en = "⏳ Analyzing your symptoms and allergies... This may take a moment."
                processing_message = gemini_translate(processing_message_en, "en", user_lang_code)
                
                if history and len(history) > 0:
                    history[-1][1] = processing_message
                
                symptoms = state["symptoms_en"]
                allergies = state["allergies_en"]
                
                # Get user's language name
                user_lang_name = state.get("language", "English")
                
                prompt = f"""Based on the symptoms and allergies below, provide a concise medical assessment IN ENGLISH FIRST.

Symptoms: {symptoms}
Allergies: {allergies}

Provide your response in this EXACT format with brief, clear information:

Diagnosis:
[2-3 sentences about the likely condition]

Proposed New Drug:
[2-3 sentences about a hypothetical drug name and how it works]

Hypothetical Dosage/Instructions:
[2-3 sentences about dosage, frequency, and how to take it]

Allergy/Safety Note:
[2-3 sentences about safety considerations given the patient's allergies]

IMPORTANT: Keep each section brief and direct. No extra explanations or bullet point breakdowns.
Write EVERYTHING in simple English so it can be easily translated to {user_lang_name}."""
                
                diagnosis_response = get_gemini_response(prompt)
                state["drug_concept_full_en"] = diagnosis_response
                state["stage"] = CHAT_STAGE_GENERAL_QNA
                
                # Don't show the full diagnosis in chat - just a confirmation
                bot_response_en = "✅ Analysis complete! Your medical report is ready. Please check the Medical Report panel on the right."
                bot_response_user_lang = gemini_translate(bot_response_en, "en", user_lang_code)
                
                state["gemini_chat_history_manual"].append({
                    "role": "model", 
                    "parts": [{"text": bot_response_en}]
                })
                
                # Extract and create summaries
                diagnosis_match = re.search(r"Diagnosis:(.*?)(?:Proposed New Drug:|Hypothetical Dosage/Instructions:|Allergy/Safety Note:|$)", 
                                          diagnosis_response, re.DOTALL | re.IGNORECASE)
                drug_match = re.search(r"Proposed New Drug:(.*?)(?:Hypothetical Dosage/Instructions:|Allergy/Safety Note:|$)", 
                                      diagnosis_response, re.DOTALL | re.IGNORECASE)
                dosage_match = re.search(r"Hypothetical Dosage/Instructions:(.*?)(?:Allergy/Safety Note:|$)", 
                                        diagnosis_response, re.DOTALL | re.IGNORECASE)
                safety_match = re.search(r"Allergy/Safety Note:(.*)", 
                                        diagnosis_response, re.DOTALL | re.IGNORECASE)
                
                diagnosis = diagnosis_match.group(1).strip() if diagnosis_match else "Not found"
                drug_concept = drug_match.group(1).strip() if drug_match else "Not found"
                dosage = dosage_match.group(1).strip() if dosage_match else "Not found"
                safety = safety_match.group(1).strip() if safety_match else "Not found"
                
                # Use original content directly - no simplification needed
                diagnosis_simplified = diagnosis
                drug_concept_simplified = drug_concept
                dosage_simplified = dosage
                safety_simplified = safety
                
                english_summary = f"**Symptoms:** {symptoms}\n\n"
                english_summary += f"**Allergies:** {allergies}\n\n"
                english_summary += f"**Diagnosis:** {diagnosis_simplified}\n\n"
                english_summary += f"**Medicine:** {drug_concept_simplified}\n\n"
                english_summary += f"**Dosage:** {dosage_simplified}\n\n"
                english_summary += f"**Safety Notes:** {safety_simplified}\n\n"
                
                symptoms_title = gemini_translate("Symptoms", "en", user_lang_code)
                allergies_title = gemini_translate("Allergies", "en", user_lang_code)
                diagnosis_title = gemini_translate("Diagnosis", "en", user_lang_code)
                drug_title = gemini_translate("Medicine", "en", user_lang_code)
                dosage_title = gemini_translate("Dosage", "en", user_lang_code)
                safety_title = gemini_translate("Safety Notes", "en", user_lang_code)
                
                # ULTIMATE NUCLEAR OPTION: Word-by-word if needed
                def ultimate_translate(text, lang_code, section_name):
                    """Most aggressive translation possible"""
                    if not text or text == "Not found":
                        return text
                    
                    lang_name = next((name for name, code in LANG_CODES.items() if code == lang_code), "target language")
                    
                    # Multiple splitting strategies
                    import re
                    
                    # First try: Split by periods, commas, and line breaks
                    chunks = re.split(r'[.\n,]', text)
                    chunks = [chunk.strip() for chunk in chunks if chunk.strip()]
                    
                    translated_chunks = []
                    
                    for i, chunk in enumerate(chunks):
                        if not chunk:
                            continue
                        
                        # ULTRA AGGRESSIVE prompt
                        ultra_prompt = f"""TRANSLATE TO {lang_name.upper()} ONLY - NO MIXING ALLOWED

RULE: Every single word must be {lang_name}. No English words at all.

English text: {chunk}

Write the complete {lang_name} translation (use {lang_name} script only):"""
                        
                        max_attempts = 2
                        best_result = chunk
                        
                        for attempt in range(max_attempts):
                            try:
                                response = gemini_client.generate_content(
                                    ultra_prompt,
                                    generation_config=genai.GenerationConfig(
                                        temperature=0.0 if attempt == 0 else 0.1,
                                        max_output_tokens=300
                                    )
                                )
                                result = response.text.strip()
                                
                                # Clean up result
                                if '\n' in result:
                                    lines = result.split('\n')
                                    # Take the line with most non-English characters
                                    best_line = ""
                                    min_english = float('inf')
                                    
                                    for line in lines:
                                        if line.strip():
                                            english_count = sum(1 for c in line if ord(c) < 128 and c.isalpha())
                                            if english_count < min_english:
                                                min_english = english_count
                                                best_line = line.strip()
                                    
                                    result = best_line if best_line else result.split('\n')[0]
                                
                                # Check if this attempt is better
                                english_chars = sum(1 for c in result if ord(c) < 128 and c.isalpha())
                                total_chars = sum(1 for c in result if c.isalpha())
                                
                                if total_chars > 0:
                                    english_ratio = english_chars / total_chars
                                    if english_ratio < 0.2:  # Less than 20% English
                                        best_result = result
                                        logger.info(f"{section_name} chunk {i+1}: {english_ratio*100:.1f}% English - GOOD")
                                        break
                                    else:
                                        logger.warning(f"{section_name} chunk {i+1} attempt {attempt+1}: {english_ratio*100:.1f}% English - RETRY")
                                        best_result = result  # Keep trying
                                
                            except Exception as e:
                                logger.error(f"Translation attempt {attempt+1} failed: {e}")
                                continue
                        
                        translated_chunks.append(best_result)
                    
                    # Join with appropriate punctuation
                    result = '. '.join(translated_chunks)
                    logger.info(f"{section_name} final translation completed")
                    return result
                
                # Use ULTIMATE nuclear option for ALL sections
                translated_diagnosis = ultimate_translate(diagnosis_simplified, user_lang_code, "Diagnosis")
                translated_drug = ultimate_translate(drug_concept_simplified, user_lang_code, "Medicine")
                translated_dosage = ultimate_translate(dosage_simplified, user_lang_code, "Dosage")
                translated_safety = ultimate_translate(safety_simplified, user_lang_code, "Safety")
                
                # Log final results
                logger.info(f"Final translations completed for all sections")
                
                translated_summary = f"### {symptoms_title}:\n{state['symptoms_user_lang']}\n\n"
                translated_summary += f"### {allergies_title}:\n{state['allergies_user_lang']}\n\n"
                translated_summary += f"### {diagnosis_title}:\n{translated_diagnosis}\n\n"
                translated_summary += f"### {drug_title}:\n{translated_drug}\n\n"
                translated_summary += f"### {dosage_title}:\n{translated_dosage}\n\n"
                translated_summary += f"### {safety_title}:\n{translated_safety}\n\n"
                
                state["translated_summary"] = translated_summary
        
        elif current_stage == CHAT_STAGE_GENERAL_QNA:
            state["gemini_chat_history_manual"].append({
                "role": "user", 
                "parts": [{"text": user_message_en}]
            })
            
            processing_message_en = "💭 Thinking about your question..."
            processing_message = gemini_translate(processing_message_en, "en", user_lang_code)
            
            if history and len(history) > 0:
                history[-1][1] = processing_message
            
            context = f"""
            Previous symptoms: {state.get('symptoms_en', 'None')}
            Previous allergies: {state.get('allergies_en', 'None')}
            Previous diagnosis and drug concept: {state.get('drug_concept_full_en', 'None')}
            
            User question: {user_message_en}
            
            Respond in a clear, concise way.
            """
            
            qna_response = get_gemini_response(context)
            
            bot_response_en = qna_response
            bot_response_user_lang = gemini_translate(qna_response, "en", user_lang_code)
            
            state["gemini_chat_history_manual"].append({
                "role": "model", 
                "parts": [{"text": bot_response_en}]
            })
        
        if history and len(history) > 0:
            history[-1][1] = bot_response_user_lang
        else:
            history = [[message, bot_response_user_lang]]
        
        # Preserve previous summaries if available
        if state.get("drug_concept_full_en") and not translated_summary.startswith("###"):
            full_response = state["drug_concept_full_en"]
            
            diagnosis_match = re.search(r"Diagnosis:(.*?)(?:Proposed New Drug:|Hypothetical Dosage/Instructions:|Allergy/Safety Note:|$)", 
                                      full_response, re.DOTALL | re.IGNORECASE)
            drug_match = re.search(r"Proposed New Drug:(.*?)(?:Hypothetical Dosage/Instructions:|Allergy/Safety Note:|$)", 
                                  full_response, re.DOTALL | re.IGNORECASE)
            dosage_match = re.search(r"Hypothetical Dosage/Instructions:(.*?)(?:Allergy/Safety Note:|$)", 
                                    full_response, re.DOTALL | re.IGNORECASE)
            safety_match = re.search(r"Allergy/Safety Note:(.*)", 
                                    full_response, re.DOTALL | re.IGNORECASE)
            
            diagnosis = diagnosis_match.group(1).strip() if diagnosis_match else "Not found"
            drug_concept = drug_match.group(1).strip() if drug_match else "Not found"
            dosage = dosage_match.group(1).strip() if dosage_match else "Not found"
            safety = safety_match.group(1).strip() if safety_match else "Not found"
            
            english_summary = f"**Symptoms:** {state.get('symptoms_en', 'N/A')}\n\n"
            english_summary += f"**Allergies:** {state.get('allergies_en', 'N/A')}\n\n"
            english_summary += f"**Diagnosis:** {diagnosis}\n\n"
            english_summary += f"**Drug Concept:** {drug_concept}\n\n"
            english_summary += f"**Dosage:** {dosage}\n\n"
            english_summary += f"**Safety:** {safety}\n\n"
            
            translated_diagnosis = gemini_translate(diagnosis, "en", user_lang_code)
            translated_drug = gemini_translate(drug_concept, "en", user_lang_code)
            translated_dosage = gemini_translate(dosage, "en", user_lang_code)
            translated_safety = gemini_translate(safety, "en", user_lang_code)
            
            translated_summary = f"**{gemini_translate('Symptoms', 'en', user_lang_code)}:** {state.get('symptoms_user_lang', 'N/A')}\n\n"
            translated_summary += f"**{gemini_translate('Allergies', 'en', user_lang_code)}:** {state.get('allergies_user_lang', 'N/A')}\n\n"
            translated_summary += f"**{gemini_translate('Diagnosis', 'en', user_lang_code)}:** {translated_diagnosis}\n\n"
            translated_summary += f"**{gemini_translate('Drug Concept', 'en', user_lang_code)}:** {translated_drug}\n\n"
            translated_summary += f"**{gemini_translate('Dosage', 'en', user_lang_code)}:** {translated_dosage}\n\n"
            translated_summary += f"**{gemini_translate('Safety', 'en', user_lang_code)}:** {translated_safety}\n\n"
        
        logger.info(f"Chat processed for user {user_id}, stage: {current_stage}")
        return history, english_summary, translated_summary, state
    
    except Exception as e:
        logger.error(f"Error in chat processing: {e}", exc_info=True)
        error_message = "❌ An error occurred while processing your message. Please try again."
        
        if history and len(history) > 0:
            history[-1][1] = error_message
        else:
            history = [[message, error_message]]
        
        return history, "Error occurred", "Error occurred", state

# --- Gradio Interface ---
def create_interface():
    """Create minimal and clean Gradio interface"""
    
    # Clean and functional CSS
    custom_css = """
    .gradio-container {
        max-width: 100% !important;
        padding: 1rem;
    }
    .header-minimal {
        text-align: center;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .language-hint {
        text-align: center;
        padding: 0.5rem;
        font-size: 0.9em;
        color: #666;
        margin-bottom: 1rem;
    }
    #report-summary {
        min-height: 400px;
        padding: 1rem;
        background: #ffffff !important;
        border-radius: 8px;
        border: 1px solid #ddd;
    }
    #report-summary * {
        color: #000000 !important;
    }
    #report-summary h1, #report-summary h2, #report-summary h3 {
        color: #1a1a1a !important;
    }
    #report-summary p, #report-summary li, #report-summary span {
        color: #333333 !important;
    }
    """
    
    with gr.Blocks(
        theme=gr.themes.Soft(
            primary_hue=Config.THEME_PRIMARY_COLOR, 
            secondary_hue=Config.THEME_SECONDARY_COLOR
        ),
        css=custom_css,
        title=f"{Config.APP_EMOJI} {Config.APP_TITLE}"
    ) as demo:
        
        # Minimal Header
        gr.HTML(f"""
        <div class="header-minimal">
            <h1 style="margin: 0; font-size: 2em;">{Config.APP_EMOJI} {Config.APP_TITLE}</h1>
            <p style="margin: 0.5rem 0 0 0; color: #666; font-size: 0.9em;">{Config.APP_SUBTITLE}</p>
        </div>
        """)
        
        # Simple language hint
        if Config.SHOW_LANGUAGE_EXAMPLES:
            gr.HTML("""
            <div class="language-hint">
                💬 Start by typing your language: English, Hindi, Spanish, French, German, Kannada, etc.
            </div>
            """)
        
        # Chat state
        chat_state = gr.State(initialize_chat_state())
        
        # Main layout - chat takes most space
        with gr.Row():
            # Chat area - takes 70% of width
            with gr.Column(scale=7):
                chatbot = gr.Chatbot(
                    height=550,
                    show_label=False,
                    type="tuples",
                    bubble_full_width=False
                )
                
                with gr.Row():
                    txt = gr.Textbox(
                        placeholder="Type your message...",
                        container=False,
                        scale=10,
                        show_label=False,
                        max_lines=2
                    )
                    send_btn = gr.Button("Send", variant="primary", scale=1)
            
            # Report panel - takes 30% of width
            with gr.Column(scale=3):
                gr.Markdown("### 📊 Medical Report")
                
                english_summary = gr.Markdown(
                    value="",
                    visible=False
                )
                
                translated_summary = gr.Markdown(
                    value="*Report will appear after diagnosis*",
                    label="",
                    container=False,
                    elem_id="report-summary"
                )
                
                with gr.Row():
                    if Config.ENABLE_PDF_DOWNLOAD:
                        download_btn = gr.Button("📥 PDF", variant="secondary", scale=1)
                    clear_btn = gr.Button("🔄 New", variant="stop", scale=1)
                
                if Config.ENABLE_PDF_DOWNLOAD:
                    pdf_output = gr.File(label="📄 Download Report", visible=True, interactive=False)
        
        # Compact disclaimer
        if Config.SHOW_DISCLAIMER:
            with gr.Accordion("⚠️ Disclaimer", open=False):
                gr.Markdown("""
**For educational purposes only**
- AI-generated diagnosis - consult a doctor
- Hypothetical drugs - not real medications
- Not medical advice
                """)
        
        # Event handlers
        send_btn.click(
            fn=process_chat,
            inputs=[txt, chatbot, chat_state],
            outputs=[chatbot, english_summary, translated_summary, chat_state]
        ).then(
            fn=lambda: "",
            inputs=None,
            outputs=txt
        )
        
        txt.submit(
            fn=process_chat,
            inputs=[txt, chatbot, chat_state],
            outputs=[chatbot, english_summary, translated_summary, chat_state]
        ).then(
            fn=lambda: "",
            inputs=None,
            outputs=txt
        )
        
        if Config.ENABLE_PDF_DOWNLOAD:
            download_btn.click(
                fn=generate_pdf_report,
                inputs=[chat_state],
                outputs=[pdf_output]
            )
        
        clear_btn.click(
            fn=lambda: ([], "", 
                       "*Report will appear after diagnosis*", 
                       initialize_chat_state()),
            inputs=None,
            outputs=[chatbot, english_summary, translated_summary, chat_state]
        )
    
    return demo

# Launch the app
if __name__ == "__main__":
    try:
        logger.info("Starting PharmaGEN application...")
        demo = create_interface()
        
        if IN_COLAB:
            demo.launch(share=True, debug=Config.DEBUG_MODE)
        else:
            demo.launch(
                server_name=Config.SERVER_HOST,
                server_port=Config.SERVER_PORT,
                share=False,
                debug=Config.DEBUG_MODE,
                show_error=True
            )
    except Exception as e:
        logger.error(f"Failed to start application: {e}", exc_info=True)
        raise
