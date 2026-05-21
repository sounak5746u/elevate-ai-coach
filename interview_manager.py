import os
import io
import re

try:
    import google.generativeai as genai
except ImportError:
    try:
        from google.ai import generative as genai
    except ImportError as exc:
        raise ImportError(
            "Missing Gemini client library. Please install `google-generativeai` in the Python environment used by Streamlit. "
            "For example: `pip install google-generativeai`") from exc

from pypdf import PdfReader
from gtts import gTTS

class InterviewManager:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        
        try:
            # Dynamically auto-detect an available model for your API key
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            model_name = next((m for m in available_models if 'flash' in m.lower()), None)
            if not model_name and available_models:
                model_name = available_models[-1] # Fallback to any valid model
                
            if model_name and model_name.startswith('models/'):
                model_name = model_name[7:]
        except Exception:
            # If the API key is invalid or network fails, fallback gracefully to prevent a crash
            model_name = 'gemini-1.5-flash'
            
        self.model = genai.GenerativeModel(model_name or 'gemini-1.5-flash')

    def extract_text_from_pdf(self, pdf_file) -> str:
        """Extracts text from an uploaded PDF file."""
        text = ""
        reader = PdfReader(pdf_file)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text

    def generate_questions(self, role: str, description: str, company: str, num_questions: int, resume_text: str = None, difficulty: str = "Intermediate", tone: str = "Professional") -> list:
        """Generates tailored interview questions."""
        prompt = f"Generate {num_questions} {difficulty}-level interview questions for the role of '{role}'."
        prompt += f"\nThe tone of the interviewer should be {tone}."
        if company:
            prompt += f" The target company is {company}."
        prompt += f"\nJob Description/Skills: {description}."
        
        if resume_text:
            prompt += f"\n\nTailor the questions based on the candidate's resume experience:\n{resume_text}"
            
        prompt += "\n\nIMPORTANT: Output only the questions, separated by exactly '|||'. Do not include any numbering, intro, or extra text."

        response = self.model.generate_content(prompt)
        
        # Parse the output
        questions = [q.strip() for q in response.text.split('|||') if q.strip()]
        
        # Fallback if the model didn't use the separator properly
        if len(questions) < num_questions:
            questions = [q.strip() for q in response.text.split('\n') if q.strip() and len(q.strip()) > 5]
            
        return questions[:num_questions]

    def evaluate_answer(self, question: str, text_answer: str = None, audio_bytes: bytes = None) -> str:
        """Evaluates the candidate's answer to a given question using text or audio."""
        prompt = f"You are a strict and highly experienced Technical Interviewer. The candidate was asked this interview question: '{question}'.\n"
        prompt += "Evaluate their response critically. Be an absolute perfectionist. If they miss core concepts, industry terminology, give vague answers, or lack depth, score them harshly (below 6).\n\n"
        prompt += "Provide a detailed, well-formatted review containing exactly these sections:\n"
        prompt += "- Score: (Rate out of 10. Be strict and realistic!)\n"
        prompt += "- Strengths: (Bullet points detailing what they did right)\n"
        prompt += "- Areas for Improvement: (MUST CONTAIN AT LEAST 10 highly specific bullet points detailing EXACTLY what they missed, inaccuracies, technical gaps, missing industry terms, and how to sound more senior/professional)\n"
        prompt += "- Exemplary Response: (Provide a perfect, 10/10 technical response that the candidate should strive for. CRITICAL: Make it sound natural, conversational, and realistic for a human to speak in a live interview. Keep it under 3-4 sentences max, do not write a massive robotic paragraph.)\n"
        prompt += "- Recommended Study Materials: (Provide 3-5 specific topics, documentations, or youtube search terms the candidate should review to master this concept)\n\n"
        prompt += "CRITICAL: Ensure the 'Score: X/10' format is strictly followed on its own line."
        
        contents = [prompt]
        if audio_bytes:
            # Send raw audio bytes to Gemini 1.5 Flash Native Multi-Modal
            contents.append({"mime_type": "audio/wav", "data": audio_bytes})
        elif text_answer:
            contents.append(f"Candidate's response: {text_answer}")
            
        response = self.model.generate_content(contents)
        return response.text

    def text_to_speech(self, text: str, is_question: bool = False) -> io.BytesIO:
        """Converts text to speech using gTTS and returns an in-memory buffer."""
        clean_text = text.replace('*', '').replace('#', '').replace('-', '')
        clean_text = re.sub(r'\s*\n+\s*', '. ', clean_text).strip()
        clean_text = re.sub(r'\.{2,}', '.', clean_text)
        clean_text = re.sub(r'\s{2,}', ' ', clean_text)

        if not is_question:
            # Speak a crisp summary of the evaluation rather than a long raw dump
            score_match = re.search(r'Score:\s*\d+(?:\.\d+)?\s*(?:/|out of)\s*10', clean_text, re.IGNORECASE)
            exemplary_match = re.search(r'Exemplary Response:\s*(.+?)(?:\.|$)', clean_text, re.IGNORECASE)
            summary_parts = []
            if score_match:
                summary_parts.append(score_match.group(0))
            if exemplary_match:
                exemplary_line = exemplary_match.group(1).strip()
                summary_parts.append(f"Exemplary response: {exemplary_line}")

            if summary_parts:
                clean_text = '. '.join(summary_parts)

            # Keep audio crisp and professional, avoid overly long feedback playback
            if len(clean_text) > 320:
                clean_text = clean_text[:320].rsplit('.', 1)[0] + '.'

        tts = gTTS(text=clean_text, lang='en', slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp

    def generate_final_report(self, qas: list) -> str:
        """Compiles a comprehensive Final Interview Report."""
        prompt = "You are an expert AI Interview Coach. Here is the transcript and evaluations of a completed interview:\n\n"
        for i, qa in enumerate(qas):
            prompt += f"Question {i+1}: {qa['question']}\nEvaluation Feedback: {qa['evaluation']}\n\n"
            
        prompt += "Compile a concise 'Final Interview Report' that breaks down the following:\n"
        prompt += "1. Overall Accuracy & Performance\n"
        prompt += "2. Core Flaws & Weaknesses\n"
        prompt += "3. Actionable Improvement Plan\n\n"
        prompt += "Use professional markdown formatting. CRITICAL: Keep this report highly summarized and brief. Use short bullet points and avoid long paragraphs."
        
        response = self.model.generate_content(prompt)
        return response.text

    def generate_study_materials(self, final_report: str) -> str:
        """Synthesizes a custom study guide based on the final report."""
        prompt = "Based on the following Final Interview Report, synthesize a custom study guide detailing:\n"
        prompt += "1. Key Concepts to Master\n"
        prompt += "2. Highly specific copy-pasteable YouTube Search terms\n"
        prompt += "3. Specific types of official documentation/PDF checklists to search for online.\n\n"
        prompt += f"Final Report:\n{final_report}\n\n"
        prompt += "Format this as an organized and encouraging action plan in markdown. CRITICAL: Keep the response extremely brief and summarized. Limit to 2-3 bullet points per section max."
        
        response = self.model.generate_content(prompt)
        return response.text

    def chat_about_evaluation(self, question: str, evaluation: str, user_message: str, chat_history: list) -> str:
        """Allows the candidate to ask follow-up questions about their evaluation."""
        prompt = f"You are a helpful AI Technical Interview Coach. The candidate was asked this question:\n'{question}'\n\n"
        prompt += f"They received this evaluation:\n{evaluation}\n\n"
        
        if chat_history:
            prompt += "Here is the chat history so far:\n"
            for msg in chat_history:
                prompt += f"{msg['role'].capitalize()}: {msg['content']}\n"
                
        prompt += f"\nCandidate's new question: {user_message}\n\n"
        prompt += "Answer the candidate's question clearly and encouragingly. If the candidate explicitly asks for the ideal answer, include a short polished example answer that directly addresses the original interview question in addition to your guidance. Give technical examples to help them understand their mistakes. CRITICAL: Keep your answer concise, conversational, and human-like (max 3-4 sentences). Do not give long elaborate explanations."
        
        response = self.model.generate_content(prompt)
        return response.text
