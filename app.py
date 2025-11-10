import gradio as gr
import re
import os
from datetime import datetime
from importlib import resources, util
from pathlib import Path
import google.generativeai as genai
from fpdf import FPDF  # For PDF generation

# Check if running in Google Colab
try:
    from google.colab import files
    IN_COLAB = True
    print("Running in Google Colab environment")
except ImportError:
    IN_COLAB = False
    print("Not running in Google Colab environment")

# Function for direct PDF download in Colab
def download_pdf_in_colab(pdf_path):
    if IN_COLAB and pdf_path and os.path.exists(pdf_path):
        files.download(pdf_path)
        return "PDF downloaded in Colab"
    return pdf_path

# --- Configuration ---
# Gemini API Model
GEMINI_MODEL_NAME = "gemini-2.5-flash-lite"  # Or "gemini-1.5-pro-latest"

# Language mapping for translation
LANG_CODES = {
    "English": "en", "Arabic": "ar", "German": "de", "Spanish": "es", "French": "fr",
    "Hindi": "hi", "Italian": "it", "Japanese": "ja", "Korean": "ko", "Portuguese": "pt",
    "Russian": "ru", "Chinese": "zh", "Bengali": "bn", "Tamil": "ta", "Telugu": "te", 
    "Thai": "th", "Ukrainian": "uk", "Turkish": "tr", "Vietnamese": "vi", "Kannada": "kn"
}

# --- API Initialization ---
# Get API key from environment variable or user input
import os
API_KEY = os.environ.get("GEMINI_API_KEY", "")

# If no API key in environment, prompt user
if not API_KEY:
    print("\n" + "="*50)
    print("No Gemini API key found in environment variables.")
    print("You can set it permanently with: export GEMINI_API_KEY='your-key-here'")
    API_KEY = input("Please enter your Gemini API key: ").strip()
    print("="*50 + "\n")

gemini_client = None
try:
    genai.configure(api_key=API_KEY)
    gemini_client = genai.GenerativeModel(GEMINI_MODEL_NAME)
    print(f"Gemini API client initialized with model: {GEMINI_MODEL_NAME}")
except Exception as e:
    print(f"Error initializing Gemini model: {e}")
    print("Please check if the model name is correct and your API key is valid.")

# --- Helper Functions ---
def gemini_translate(text, src_lang_code, tgt_lang_code, temp=0.1):
    """Translates text using Gemini."""
    if gemini_client is None:
        print("Gemini client not available for translation.")
        return text  # Return original text if Gemini client fails

    if not text or text.strip() == "":
        return ""

    # Handle cases where lang code might be None
    effective_src_lang_code = src_lang_code if src_lang_code in LANG_CODES.values() else "auto"
    effective_tgt_lang_code = tgt_lang_code if tgt_lang_code in LANG_CODES.values() else "en"

    if effective_src_lang_code != "auto" and effective_src_lang_code == effective_tgt_lang_code:
        return text  # Skip translation if source equals target

    # Get language name from code
    tgt_lang_name = next((name for name, code in LANG_CODES.items() if code == effective_tgt_lang_code), effective_tgt_lang_code)
    prompt = f"Translate the following text to {tgt_lang_name}:\n\n{text}"
    
    if effective_src_lang_code != "auto":
        src_lang_name = next((name for name, code in LANG_CODES.items() if code == effective_src_lang_code), effective_src_lang_code)
        prompt = f"Translate the following text from {src_lang_name} to {tgt_lang_name}:\n\n{text}"

    try:
        response = gemini_client.generate_content(prompt, generation_config=genai.GenerationConfig(temperature=temp))
        return response.text.strip()
    except Exception as e:
        print(f"Translation error: {e}")
        return text

def get_gemini_response(prompt_text, chat_history=None, temp=0.7):
    """Gets a response from the Gemini API."""
    if gemini_client is None:
        return "Error: Gemini API not available. Cannot provide medical information."

    try:
        # Format chat history for Gemini
        formatted_history = []
        if chat_history:
            for turn in chat_history:
                if isinstance(turn, dict) and "role" in turn and "parts" in turn:
                    formatted_history.append({"role": turn["role"], "parts": [{"text": turn["parts"][0]["text"]}]})

        if formatted_history:
            chat_session = gemini_client.start_chat(history=formatted_history)
            response = chat_session.send_message(prompt_text)
        else:
            response = gemini_client.generate_content(prompt_text, generation_config=genai.GenerationConfig(temperature=temp))

        return response.text
    except Exception as e:
        print(f"Gemini API error: {e}")
        error_detail = str(e).lower()
        if "401" in error_detail or "unauthorized" in error_detail:
            return f"Error: Unauthorized. Check your API key. {e}"
        if "429" in error_detail or "quota" in error_detail:
            return f"Error: Rate limit exceeded. Try again later. {e}"
        return f"Error communicating with Gemini API: {e}"

UNIFIED_FONT_FAMILY = "PharmaSans"
FONT_FILE_CANDIDATES = [
    "DejaVuSansCondensed.ttf",
    "NotoSans-Regular.ttf",
    "NotoSansCJK-Regular.ttc",
    "unifont-13.0.06.ttf",
]
SYSTEM_FONT_CANDIDATES = [
    "C:/Windows/Fonts/arialuni.ttf",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/NotoSans-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/opentype/noto/NotoSans-Regular.otf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
]

def _resolve_font_path():
    # Look inside the installed fpdf package for bundled unicode fonts
    try:
        fonts_root = resources.files("fpdf") / "fonts" / "ttfonts"
        if fonts_root.is_dir():
            for font_name in FONT_FILE_CANDIDATES:
                font_path = fonts_root / font_name
                if font_path.is_file():
                    return str(font_path)
    except (ModuleNotFoundError, AttributeError, FileNotFoundError):
        pass

    try:
        spec = util.find_spec("fpdf")
        if spec and spec.origin:
            base_path = Path(spec.origin).resolve().parent
            candidate_root = base_path / "fonts" / "ttfonts"
            if candidate_root.is_dir():
                for font_name in FONT_FILE_CANDIDATES:
                    font_path = candidate_root / font_name
                    if font_path.is_file():
                        return str(font_path)
    except Exception:
        pass

    for path_str in SYSTEM_FONT_CANDIDATES:
        if os.path.isfile(path_str):
            return path_str
    return None

PDF_UNICODE_FONT_PATH = _resolve_font_path()

class PDFReport(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_auto_page_break(auto=True, margin=15)
        self._font_family = 'Arial'
        if PDF_UNICODE_FONT_PATH:
            try:
                self.add_font(UNIFIED_FONT_FAMILY, "", PDF_UNICODE_FONT_PATH, uni=True)
                self.add_font(UNIFIED_FONT_FAMILY, "B", PDF_UNICODE_FONT_PATH, uni=True)
                self.add_font(UNIFIED_FONT_FAMILY, "I", PDF_UNICODE_FONT_PATH, uni=True)
                self._font_family = UNIFIED_FONT_FAMILY
            except RuntimeError as font_error:
                print(f"Warning: Failed to load unicode font ({PDF_UNICODE_FONT_PATH}): {font_error}")
        else:
            print("Warning: Unicode font not found. Falling back to Arial - some characters may not render.")

    def header(self):
        self.set_font(self._font_family, 'B', 14)
        self.cell(0, 10, 'PharmaGPT Medical Report', 0, 1, 'C')
        self.ln(4)

    def footer(self):
        self.set_y(-20)
        self.set_font(self._font_family, '', 8)
        self.cell(0, 8, f'Page {self.page_no()}/{{nb}}', 0, 1, 'C')
        self.set_font(self._font_family, 'I', 7)
        disclaimer = 'Disclaimer: This is an AI-generated report for conceptual purposes only.'
        self.multi_cell(0, 4, disclaimer, align='C')

    def chapter_title(self, title):
        self.set_font(self._font_family, 'B', 12)
        self.set_text_color(40, 62, 90)
        self.cell(0, 8, title, 0, 1, 'L')
        self.set_text_color(0, 0, 0)

    def chapter_body(self, body):
        self.set_font(self._font_family, '', 10)
        text = body if isinstance(body, str) else str(body)
        self.multi_cell(0, 6, text)
        self.ln(2)

def _clean_summary_blocks(translated_summary):
    sections = []
    parts = translated_summary.split("###")
    for raw_section in parts:
        section = raw_section.strip()
        if not section:
            continue
        if ":" in section:
            title, content = section.split(":", 1)
            sections.append((title.strip(), content.strip()))
        else:
            sections.append(("", section))
    return sections

def generate_pdf_report(chat_state):
    """Generates a PDF report using unicode-aware fonts."""
    print("Generating PDF report...")
    state_data = chat_state.copy() if isinstance(chat_state, dict) else {}

    translated_summary = state_data.get("translated_summary", "")
    user_language = state_data.get("language", "English")

    if not translated_summary:
        print("No summary available to generate PDF")
        return None

    report_dir = Path.cwd() / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_filename = f"pharma_gpt_report_{timestamp}.pdf"
    pdf_output_path = str((report_dir / pdf_filename).resolve())

    try:
        pdf = PDFReport(format="A4")
        pdf.alias_nb_pages()
        pdf.add_page()

        # Title block
        pdf.set_font(pdf._font_family, 'B', 16)
        pdf.cell(0, 12, "PharmaGPT Medical Report", 0, 1, 'C')
        pdf.set_font(pdf._font_family, 'I', 10)
        pdf.cell(0, 8, f"Report language: {user_language}", 0, 1, 'C')
        pdf.ln(4)

        for title, content in _clean_summary_blocks(translated_summary):
            if title:
                pdf.chapter_title(f"{title}:")
            pdf.chapter_body(content)

        pdf.chapter_title("Disclaimer:")
        pdf.chapter_body("This is an AI-generated report for conceptual purposes only. Consult a medical professional.")

        pdf.output(pdf_output_path)
        print(f"PDF report saved to {pdf_output_path}")
        return pdf_output_path
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return None

def prepare_pdf_ui(pdf_path):
    if not pdf_path:
        return (
            gr.update(value=None, visible=True, label="📥 Download PDF Report"),
            gr.update(value=None, visible=False),
        )
    file_name = os.path.basename(pdf_path)
    return (
        gr.update(value=pdf_path, visible=True, label=f"📥 Download PDF Report ({file_name})"),
        gr.update(value=pdf_path, visible=True),
    )

# --- Chat Stages ---
CHAT_STAGE_ASK_LANGUAGE = "ask_language"
CHAT_STAGE_ASK_SYMPTOMS = "ask_symptoms"
CHAT_STAGE_ASK_ALLERGIES = "ask_allergies"
CHAT_STAGE_GENERATE_RESPONSE = "generate_response"
CHAT_STAGE_GENERAL_QNA = "general_qna"

# Initialize chat state
def initialize_chat_state():
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
        "gemini_chat_history_manual": []
    }

def _normalize_chat_history(history):
    """Convert incoming chat history entries to mutable lists."""
    if not history:
        return []
    normalized = []
    for entry in history:
        if isinstance(entry, tuple):
            normalized.append([entry[0], entry[1]])
        elif isinstance(entry, list):
            if len(entry) >= 2:
                normalized.append([entry[0], entry[1]])
            elif len(entry) == 1:
                normalized.append([entry[0], ""])
            else:
                normalized.append(["", ""])
        else:
            normalized.append([str(entry), ""])
    return normalized

def _prepare_history_for_return(history):
    """Convert mutable history entries back to tuples for Gradio."""
    return [tuple(item) for item in history]

# Process chat messages
def process_chat(message, history, state):
    """Process user messages and generate responses."""
    if history is None:
        history = []
    else:
        history = _normalize_chat_history(history)
    
    # Add user message to history
    history.append([message, ""])
    
    try:
        current_stage = state["stage"]
        user_lang_code = state.get("lang_code", "en")
        
        # Translate user message to English if needed
        user_message_en = message
        if user_lang_code != "en" and user_lang_code is not None and message.strip():
            user_message_en = gemini_translate(message, user_lang_code, 'en')
        
        bot_response_en = ""
        bot_response_user_lang = ""
        
        # Initialize summary outputs
        english_summary = "Report summary will appear here after diagnosis."
        translated_summary = "Translated report summary will appear here."
        
        # Preserve previous summary if available
        if state.get("drug_concept_full_en"):
            full_response = state["drug_concept_full_en"]
            
            # Extract sections using regex
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
            
            # Create English summary
            english_summary = f"**Symptoms:** {state.get('symptoms_en', 'N/A')}\n\n"
            english_summary += f"**Allergies:** {state.get('allergies_en', 'N/A')}\n\n"
            english_summary += f"**Diagnosis:** {diagnosis}\n\n"
            english_summary += f"**Drug Concept:** {drug_concept}\n\n"
            english_summary += f"**Dosage:** {dosage}\n\n"
            english_summary += f"**Safety:** {safety}\n\n"
            
            # Create translated summary
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
        
        # Process based on current stage
        if current_stage == CHAT_STAGE_ASK_LANGUAGE:
            selected_language = message.strip().title()
            
            if selected_language in LANG_CODES:
                state["language"] = selected_language
                state["lang_code"] = LANG_CODES[selected_language]
                state["stage"] = CHAT_STAGE_ASK_SYMPTOMS
                user_lang_code = state["lang_code"]
                
                # First create the English version for our records
                welcome_message_en = f"Thank you. Your selected language is {selected_language}."
                next_prompt_en = "Please describe your symptoms."
                bot_response_en = f"{welcome_message_en}\n\n{next_prompt_en}"
                
                # Then translate to user's language
                welcome_message = gemini_translate(welcome_message_en, "en", user_lang_code)
                next_prompt = gemini_translate(next_prompt_en, "en", user_lang_code)
                bot_response_user_lang = f"{welcome_message}\n\n{next_prompt}"
                
                # Add to chat history
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
                error_message_en = f"Sorry, '{message}' is not a supported language. Please select from: {available_languages}"
                bot_response_en = error_message_en
                # Don't translate error messages about language selection
                bot_response_user_lang = error_message_en
        
        elif current_stage == CHAT_STAGE_ASK_SYMPTOMS:
            if not user_lang_code:
                bot_response_en = "Error: Language not set. Please start over."
                bot_response_user_lang = bot_response_en
                state = initialize_chat_state()
            elif not message.strip():
                bot_response_en = "Please describe your symptoms so I can assist you."
                bot_response_user_lang = gemini_translate(bot_response_en, "en", user_lang_code)
            else:
                state["symptoms_user_lang"] = message.strip()
                state["symptoms_en"] = user_message_en
                state["stage"] = CHAT_STAGE_ASK_ALLERGIES
                
                bot_response_en = "Thank you for sharing your symptoms. Do you have any known allergies? If none, please say 'None'."
                bot_response_user_lang = gemini_translate(bot_response_en, "en", user_lang_code)
                
                # Add to chat history
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
                bot_response_en = "Error: Language not set. Please start over."
                bot_response_user_lang = bot_response_en
                state = initialize_chat_state()
            else:
                state["allergies_user_lang"] = message.strip()
                state["allergies_en"] = user_message_en
                state["stage"] = CHAT_STAGE_GENERATE_RESPONSE
                
                # Add to chat history
                state["gemini_chat_history_manual"].append({
                    "role": "user", 
                    "parts": [{"text": f"Allergies: {user_message_en}"}]
                })
                
                # Show a processing message in the user's language while generating the response
                processing_message_en = "Thank you. I'm analyzing your symptoms and allergies to generate a diagnosis and drug concept. This may take a moment..."
                processing_message = gemini_translate(processing_message_en, "en", user_lang_code)
                
                # Update history with processing message
                if history and len(history) > 0:
                    if isinstance(history[-1], list) and len(history[-1]) >= 2:
                        history[-1][1] = processing_message
                    else:
                        history.append([message, processing_message])
                else:
                    history = [[message, processing_message]]
                
                # Generate diagnosis and drug concept
                symptoms = state["symptoms_en"]
                allergies = state["allergies_en"]
                
                prompt = f"""Based on the following symptoms and allergies, provide:
                1. A potential diagnosis
                2. A hypothetical new drug concept that could treat this condition
                3. Hypothetical dosage instructions
                4. Safety considerations related to the patient's allergies

                Symptoms: {symptoms}
                Allergies: {allergies}

                Format your response with these exact headings:
                Diagnosis:
                Proposed New Drug:
                Hypothetical Dosage/Instructions:
                Allergy/Safety Note:
                """
                
                diagnosis_response = get_gemini_response(prompt)
                state["drug_concept_full_en"] = diagnosis_response
                state["stage"] = CHAT_STAGE_GENERAL_QNA
                
                bot_response_en = diagnosis_response
                bot_response_user_lang = gemini_translate(diagnosis_response, "en", user_lang_code)
                
                # Add to chat history
                state["gemini_chat_history_manual"].append({
                    "role": "model", 
                    "parts": [{"text": bot_response_en}]
                })
                
                # Update summaries
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
                
                # Create simplified bullet point summaries for better readability
                diagnosis_simplified_prompt = "Simplify this medical diagnosis into 2-3 short bullet points: " + diagnosis
                drug_simplified_prompt = "Simplify this drug concept into 2-3 short bullet points about what it is and how it works: " + drug_concept
                dosage_simplified_prompt = "Simplify this dosage information into 2-3 short bullet points about dosage amount, frequency, and how to take it: " + dosage
                safety_simplified_prompt = "Simplify this safety information into 2-3 short bullet points about allergies and side effects: " + safety
                
                diagnosis_simplified = get_gemini_response(diagnosis_simplified_prompt)
                drug_concept_simplified = get_gemini_response(drug_simplified_prompt)
                dosage_simplified = get_gemini_response(dosage_simplified_prompt)
                safety_simplified = get_gemini_response(safety_simplified_prompt)
                
                # Create English summary with simplified text
                english_summary = f"**Symptoms:** {symptoms}\n\n"
                english_summary += f"**Allergies:** {allergies}\n\n"
                english_summary += f"**Diagnosis:** {diagnosis_simplified}\n\n"
                english_summary += f"**Medicine:** {drug_concept_simplified}\n\n"
                english_summary += f"**Dosage:** {dosage_simplified}\n\n"
                english_summary += f"**Safety Notes:** {safety_simplified}\n\n"
                
                # Translate the simplified text to user's language
                symptoms_title = gemini_translate("Symptoms", "en", user_lang_code)
                allergies_title = gemini_translate("Allergies", "en", user_lang_code)
                diagnosis_title = gemini_translate("Diagnosis", "en", user_lang_code)
                drug_title = gemini_translate("Medicine", "en", user_lang_code)
                dosage_title = gemini_translate("Dosage", "en", user_lang_code)
                safety_title = gemini_translate("Safety Notes", "en", user_lang_code)
                
                translated_diagnosis = gemini_translate(diagnosis_simplified, "en", user_lang_code)
                translated_drug = gemini_translate(drug_concept_simplified, "en", user_lang_code)
                translated_dosage = gemini_translate(dosage_simplified, "en", user_lang_code)
                translated_safety = gemini_translate(safety_simplified, "en", user_lang_code)
                
                # Only show the translated summary in the user's language with clear formatting
                translated_summary = f"### {symptoms_title}:\n{state['symptoms_user_lang']}\n\n"
                translated_summary += f"### {allergies_title}:\n{state['allergies_user_lang']}\n\n"
                translated_summary += f"### {diagnosis_title}:\n{translated_diagnosis}\n\n"
                translated_summary += f"### {drug_title}:\n{translated_drug}\n\n"
                translated_summary += f"### {dosage_title}:\n{translated_dosage}\n\n"
                translated_summary += f"### {safety_title}:\n{translated_safety}\n\n"
                
                # Store the translated summary in the state for PDF generation
                state["translated_summary"] = translated_summary
        
        elif current_stage == CHAT_STAGE_GENERAL_QNA:
            # Add user question to history
            state["gemini_chat_history_manual"].append({
                "role": "user", 
                "parts": [{"text": user_message_en}]
            })
            
            # Show a processing message in the user's language while generating the response
            processing_message_en = "I'm thinking about your question..."
            processing_message = gemini_translate(processing_message_en, "en", user_lang_code)
            
            # Update history with processing message
            if history and len(history) > 0:
                if isinstance(history[-1], list) and len(history[-1]) >= 2:
                    history[-1][1] = processing_message
                else:
                    history.append([message, processing_message])
            else:
                history = [[message, processing_message]]
            
            # Generate response to follow-up question
            context = f"""
            Previous symptoms: {state.get('symptoms_en', 'None')}
            Previous allergies: {state.get('allergies_en', 'None')}
            Previous diagnosis and drug concept: {state.get('drug_concept_full_en', 'None')}
            
            User question: {user_message_en}
            
            Respond in a clear, concise way that would be easy to translate to another language.
            """
            
            qna_response = get_gemini_response(context)
            
            bot_response_en = qna_response
            bot_response_user_lang = gemini_translate(qna_response, "en", user_lang_code)
            
            # Add to chat history
            state["gemini_chat_history_manual"].append({
                "role": "model", 
                "parts": [{"text": bot_response_en}]
            })
        
        # Always use the translated response in the user's language for the chat interface
        # This ensures all bot responses appear in the user's chosen language
        if history and len(history) > 0:
            if isinstance(history[-1], list) and len(history[-1]) >= 2:
                history[-1][1] = bot_response_user_lang
            else:
                history.append([message, bot_response_user_lang])
        else:
            history = [[message, bot_response_user_lang]]
        
        return _prepare_history_for_return(history), english_summary, translated_summary, state
    
    except Exception as e:
        print(f"Error in chat processing: {e}")
        error_message = f"An error occurred: {e}. Please try again or restart the conversation."
        
        # Update history with error message
        if history and len(history) > 0:
            if isinstance(history[-1], list) and len(history[-1]) >= 2:
                history[-1][1] = error_message
            else:
                history.append([message, error_message])
        else:
            history = [[message, error_message]]
        
        return _prepare_history_for_return(history), f"Error: {error_message}", f"Error: {error_message}", initialize_chat_state()

# --- Gradio Interface ---
def create_interface():
    with gr.Blocks(theme=gr.themes.Soft(primary_hue="indigo", secondary_hue="cyan"), 
                  css="""
                  .gradio-container {
                      background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
                      color: white;
                      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                  }
                  .chatbot-container {
                      border-radius: 20px;
                      box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
                      backdrop-filter: blur(8px);
                      border: 1px solid rgba(255, 255, 255, 0.18);
                      padding: 20px;
                      background: rgba(255, 255, 255, 0.05);
                  }
                  .summary-container {
                      background: rgba(255, 255, 255, 0.05);
                      border-radius: 20px;
                      padding: 20px;
                      box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
                      backdrop-filter: blur(8px);
                      border: 1px solid rgba(255, 255, 255, 0.18);
                  }
                  .button-row {
                      display: flex;
                      justify-content: space-between;
                      margin-top: 15px;
                  }
                  .chat-header {
                      text-align: center;
                      margin-bottom: 30px;
                      animation: glow 2s ease-in-out infinite alternate;
                  }
                  @keyframes glow {
                      from {
                          text-shadow: 0 0 10px rgba(66, 153, 225, 0.5), 0 0 20px rgba(66, 153, 225, 0.3);
                      }
                      to {
                          text-shadow: 0 0 20px rgba(66, 153, 225, 0.8), 0 0 30px rgba(66, 153, 225, 0.5);
                      }
                  }
                  .send-btn {
                      background: linear-gradient(90deg, #4299e1, #667eea);
                      border: none;
                      border-radius: 50px;
                      transition: all 0.3s ease;
                  }
                  .send-btn:hover {
                      transform: translateY(-2px);
                      box-shadow: 0 5px 15px rgba(66, 153, 225, 0.4);
                  }
                  .download-btn {
                      background: linear-gradient(90deg, #00c6fb, #005bea);
                      border: none;
                      border-radius: 50px;
                      transition: all 0.3s ease;
                  }
                  .download-btn:hover {
                      transform: translateY(-2px);
                      box-shadow: 0 5px 15px rgba(0, 198, 251, 0.4);
                  }
                  .clear-btn {
                      background: linear-gradient(90deg, #ff9a9e, #fad0c4);
                      border: none;
                      border-radius: 50px;
                      transition: all 0.3s ease;
                  }
                  .clear-btn:hover {
                      transform: translateY(-2px);
                      box-shadow: 0 5px 15px rgba(255, 154, 158, 0.4);
                  }
                  .chatbot-message {
                      border-radius: 18px !important;
                      padding: 12px 18px !important;
                      margin-bottom: 10px !important;
                  }
                  .user-message {
                      background: linear-gradient(90deg, #4299e1, #667eea) !important;
                      color: white !important;
                  }
                  .bot-message {
                      background: rgba(255, 255, 255, 0.1) !important;
                      backdrop-filter: blur(5px) !important;
                      border: 1px solid rgba(255, 255, 255, 0.1) !important;
                  }
                  .summary-title {
                      font-size: 1.5em;
                      font-weight: 600;
                      margin-bottom: 15px;
                      color: #4cc9f0;
                      text-shadow: 0 0 10px rgba(76, 201, 240, 0.3);
                  }
                  .textbox-container {
                      margin-top: 15px;
                      border-radius: 50px;
                      overflow: hidden;
                      box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
                  }
                  """) as demo:
        
        # Header with animated glow effect
        gr.HTML("""
        <div class="chat-header">
            <h1 style="color: #4cc9f0; font-size: 3em; font-weight: 700; letter-spacing: 2px;">
                🧬 PharmaGPT 🧬
            </h1>
            <h3 style="color: #f72585; margin-top: -10px; font-style: italic; letter-spacing: 1px;">
                Next-Gen Medical Assistant & Drug Concept Generator
            </h3>
        </div>
        """)
        
        # Language selector with visual indicators
        gr.HTML("""
        <div style="text-align: center; margin-bottom: 20px;">
            <p style="color: #4cc9f0; font-size: 1.2em;">
                Start by typing your preferred language below
            </p>
            <div style="display: flex; justify-content: center; gap: 10px; flex-wrap: wrap; margin-top: 10px;">
                <span style="background: rgba(255,255,255,0.1); padding: 5px 10px; border-radius: 20px; font-size: 0.9em;">English</span>
                <span style="background: rgba(255,255,255,0.1); padding: 5px 10px; border-radius: 20px; font-size: 0.9em;">Hindi</span>
                <span style="background: rgba(255,255,255,0.1); padding: 5px 10px; border-radius: 20px; font-size: 0.9em;">Spanish</span>
                <span style="background: rgba(255,255,255,0.1); padding: 5px 10px; border-radius: 20px; font-size: 0.9em;">Kannada</span>
                <span style="background: rgba(255,255,255,0.1); padding: 5px 10px; border-radius: 20px; font-size: 0.9em;">+16 more</span>
            </div>
        </div>
        """)
        
        # Chat state
        chat_state = gr.State(initialize_chat_state())
        
        with gr.Row():
            # Main chat area
            with gr.Column(scale=3, elem_classes="chatbot-container"):
                chatbot = gr.Chatbot(
                    height=500,
                    bubble_full_width=False,
                    show_label=False,
                    elem_id="pharma-chat",
                    elem_classes="chatbot-message"
                )
                
                with gr.Row(elem_classes="textbox-container"):
                    txt = gr.Textbox(
                        placeholder="Type your message here...",
                        container=False,
                        scale=8,
                        show_label=False
                    )
                    send_btn = gr.Button("Send", variant="primary", scale=1, elem_classes="send-btn")
            
            # Side panel - Only show translated summary
            with gr.Column(scale=2, elem_classes="summary-container"):
                gr.HTML('<div class="summary-title">📊 Your Medical Report</div>')
                
                # Hide the English summary and only show the translated one
                english_summary = gr.Markdown(
                    value="",
                    label="English Summary",
                    visible=False  # Hide this component
                )
                
                translated_summary = gr.Markdown(
                    value="Your report will appear here after diagnosis in your chosen language.",
                    label=""  # Remove label as it's redundant
                )
                
                with gr.Row(elem_classes="button-row"):
                    download_btn = gr.DownloadButton("📥 Download PDF Report", variant="secondary", elem_classes="download-btn")
                    clear_btn = gr.Button("🔄 New Consultation", variant="stop", elem_classes="clear-btn")

                pdf_preview = gr.File(label="Report Preview", visible=False, interactive=False)
                colab_status = gr.Textbox(visible=False)
                pdf_path_state = gr.State(value=None)
        
        # Disclaimer with improved styling
        with gr.Accordion("⚠️ Important Medical Disclaimer", open=False):
            gr.HTML("""
            <div style="color: #f72585; font-size: 0.9em; padding: 15px; background: rgba(247, 37, 133, 0.1); border-radius: 15px;">
                <p style="font-weight: 600; font-size: 1.1em;">This application is for informational and conceptual purposes only.</p>
                <ul style="list-style-type: none; padding-left: 10px;">
                    <li style="margin-bottom: 10px; display: flex; align-items: flex-start;">
                        <span style="margin-right: 10px; font-size: 1.2em;">⚕️</span>
                        <span><b>AI-Generated Diagnosis:</b> The diagnosis provided is AI-generated and may not be accurate. 
                        <strong>Always consult a qualified medical professional for any health concerns.</strong></span>
                    </li>
                    <li style="margin-bottom: 10px; display: flex; align-items: flex-start;">
                        <span style="margin-right: 10px; font-size: 1.2em;">🧪</span>
                        <span><b>Hypothetical Drug Concepts:</b> The drug compounds suggested are NEW, HYPOTHETICAL CONCEPTS 
                        generated by AI. <strong>They are not real, tested, safe, or approved medications.</strong></span>
                    </li>
                    <li style="margin-bottom: 10px; display: flex; align-items: flex-start;">
                        <span style="margin-right: 10px; font-size: 1.2em;">⚠️</span>
                        <span><b>Safety Notes:</b> Allergy and side effect notes are theoretical AI assessments. 
                        <strong>They are not a substitute for professional medical advice.</strong></span>
                    </li>
                </ul>
            </div>
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
        
        download_btn.click(
            fn=generate_pdf_report,
            inputs=[chat_state],
            outputs=[pdf_path_state]
        )

        download_btn.click(
            fn=prepare_pdf_ui,
            inputs=[pdf_path_state],
            outputs=[download_btn, pdf_preview]
        )

        if IN_COLAB:
            download_btn.click(
                fn=download_pdf_in_colab,
                inputs=[pdf_path_state],
                outputs=[colab_status]
            )

        clear_btn.click(
            fn=lambda: ([], "", 
                       "Your report will appear here after diagnosis in your chosen language.", 
                       initialize_chat_state(),
                       gr.update(value=None, visible=True, label="📥 Download PDF Report"),
                       gr.update(value=None, visible=False),
                       None,
                       ""),
            inputs=None,
            outputs=[chatbot, english_summary, translated_summary, chat_state, download_btn, pdf_preview, pdf_path_state, colab_status]
        )
        
        # Footer with animated effect
        gr.HTML("""
        <div style="text-align: center; margin-top: 30px; padding: 15px; background: rgba(255,255,255,0.05); 
                    border-radius: 15px; backdrop-filter: blur(5px);">
            <p style="color: #4cc9f0; font-size: 0.9em; margin-bottom: 5px;">
                Powered by Google Gemini AI
            </p>
            <p style="color: #aaa; font-size: 0.8em;">
                Created for educational and conceptual purposes only
            </p>
        </div>
        """)
    
    return demo

# Launch the app
if __name__ == "__main__":
    demo = create_interface()
    if IN_COLAB:
        # In Colab, always use share=True to get a public URL
        demo.launch(share=True, debug=True)
    else:
        # For local development
        demo.launch(share=True)