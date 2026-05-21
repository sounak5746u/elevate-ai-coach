import io
import json
import re
import streamlit as st
import os
from dotenv import load_dotenv
from streamlit.components.v1 import html as components_html
from interview_manager import InterviewManager

# Load environment variables if present
load_dotenv()

# Initialize Streamlit Page configuration
st.set_page_config(page_title="Elevate AI", page_icon="✨", layout="wide", initial_sidebar_state="expanded")

# --- Custom CSS for Premium UI ---
st.markdown("""
<style>
    /* Main Background & Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Gradient Text for Title */
    .gradient-text {
        background: linear-gradient(135deg, #00F2FE 0%, #4FACFE 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 4rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0px;
        padding-bottom: 0px;
        animation: fadeInDown 0.8s ease-out;
    }
    .sub-text {
        text-align: center;
        color: #A0AEC0;
        font-size: 1.3rem;
        font-weight: 400;
        margin-top: -10px;
        margin-bottom: 40px;
        animation: fadeInUp 1s ease-out;
    }
    
    /* Custom Card for Questions */
    .question-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 20px;
        padding: 35px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 10px 40px 0 rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        margin-bottom: 30px;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    .question-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 50px 0 rgba(0, 242, 254, 0.2);
        border: 1px solid rgba(0, 242, 254, 0.3);
    }
    
    .question-number {
        color: #00F2FE;
        font-weight: 700;
        font-size: 1.2rem;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-bottom: 15px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .question-text {
        font-size: 2rem;
        font-weight: 600;
        line-height: 1.5;
        color: #FFFFFF;
    }
    
    /* Styled Button overrides */
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #667EEA 0%, #764BA2 100%);
        color: white;
        border: none;
        border-radius: 12px;
        font-weight: 600;
        padding: 0.6rem 1.2rem;
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
        box-shadow: 0 4px 15px rgba(118, 75, 162, 0.4);
    }
    .stButton>button[kind="primary"]:hover {
        transform: translateY(-3px) scale(1.02);
        box-shadow: 0 8px 25px rgba(118, 75, 162, 0.6);
    }
    
    /* Animations */
    @keyframes fadeInDown {
        from { opacity: 0; transform: translateY(-20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="gradient-text">✨ Elevate AI</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-text">Experience a masterclass in interview preparation with real-time AI feedback.</p>', unsafe_allow_html=True)

# Sidebar API Key & Setup
with st.sidebar:
    api_key = os.getenv("GEMINI_API_KEY") or st.text_input("Enter Gemini API Key", type="password")

    if not api_key:
        st.warning("Please provide your Gemini API Key below to proceed.")
        st.stop()

# Initialize or Update Backend and State
try:
    if 'manager' not in st.session_state or st.session_state.get('current_api_key') != api_key or not hasattr(st.session_state.manager, 'chat_about_evaluation'):
        from interview_manager import InterviewManager
        st.session_state.manager = InterviewManager(api_key=api_key)
        st.session_state.current_api_key = api_key
except Exception as e:
        st.sidebar.error(f"Failed to initialize AI: {e}")
        st.stop()

if 'questions' not in st.session_state:
    st.session_state.questions = []
if 'current_q_idx' not in st.session_state:
    st.session_state.current_q_idx = 0
if 'evaluations' not in st.session_state:
    st.session_state.evaluations = {}
if 'final_report' not in st.session_state:
    st.session_state.final_report = None
if 'study_materials' not in st.session_state:
    st.session_state.study_materials = None

with st.sidebar:
    st.divider()
    st.header("🎯 Interview Setup")
    
    with st.expander("Role & Experience", expanded=True):
        role = st.text_input("Target Job Role", "Full-Stack Engineer")
        description = st.text_area("Job Description / Key Skills", "Python, React, System Design, REST APIs", height=100)
        company = st.text_input("Target Company (Optional)", "Google")
        num_questions = st.slider("Number of Questions", 1, 10, 3)
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            difficulty = st.selectbox("Difficulty", ["Beginner", "Intermediate", "Advanced", "Expert"], index=1)
        with col_s2:
            tone = st.selectbox("Tone", ["Professional", "Friendly", "Strict", "Conversational"], index=0)

    with st.expander("Resume Context", expanded=False):
        uploaded_resume = st.file_uploader("Upload Resume (PDF)", type=["pdf"])
        use_resume = False
        resume_text = None

        if uploaded_resume:
            resume_text = st.session_state.manager.extract_text_from_pdf(uploaded_resume)
            use_resume = st.checkbox("Tailor questions to my experience", value=True)

    st.write("") # spacing
    if st.button("Generate Interview Questions", type="primary", use_container_width=True):
        with st.spinner("Generating targeted questions..."):
            try:
                r_text = resume_text if use_resume else None
                questions = st.session_state.manager.generate_questions(role, description, company, num_questions, r_text, difficulty, tone)
                
                if not questions:
                    st.error("Failed to generate questions. Please try again.")
                else:
                    st.session_state.questions = questions
                    st.session_state.current_q_idx = 0
                    st.session_state.evaluations = {}
                    st.session_state.final_report = None
                    st.session_state.study_materials = None
                    st.toast("✅ Questions generated successfully!")
                    import time
                    time.sleep(0.5)
                    st.rerun()
            except Exception as e:
                st.error(f"API Error! Please check if your API key is valid. Details: {e}")

if not st.session_state.questions:
    st.info("👈 Fill out the setup on the sidebar and click **'Generate Interview Questions'** to begin.")
    st.stop()

# --- Main Interview Flow ---
if not st.session_state.final_report:
    total_q = len(st.session_state.questions)
    current_idx = st.session_state.current_q_idx
    current_q = st.session_state.questions[current_idx]
    
    # Progress Bar
    st.progress((current_idx) / total_q)
    
    # Styled Question Card
    st.markdown(f"""
    <div class="question-card">
        <div class="question-number">Question {current_idx + 1} of {total_q}</div>
        <div class="question-text">{current_q}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Navigation controls
    col_nav1, col_nav2, col_nav3 = st.columns([1, 1, 2])
    with col_nav1:
        if current_idx > 0:
            if st.button("⬅️ Previous", use_container_width=True):
                st.session_state.current_q_idx -= 1
                st.rerun()
    with col_nav2:
        if current_idx < total_q - 1:
            if st.button("Next ➡️", use_container_width=True):
                st.session_state.current_q_idx += 1
                st.rerun()
    with col_nav3:
        question_text_js = json.dumps(current_q)
        components_html(f"""
            <div style="display:flex;align-items:center;justify-content:center;height:100%;width:100%;">
                <button id="read-question-btn" style="width:100%;max-width:320px;padding:0.9rem 1rem;border:none;background:linear-gradient(135deg,#5B8CFF,#8C63FF);color:white;border-radius:14px;font-size:1rem;font-weight:600;cursor:pointer;box-shadow:0 10px 30px rgba(0,0,0,0.18);transition:transform 0.15s ease;">
                    🔊 Read Question
                </button>
            </div>
            <script>
                const questionText = {question_text_js};
                const synth = window.speechSynthesis;
                const getVoice = () => {{
                    const voices = synth.getVoices();
                    return voices.find(v => /female|woman|zira|samantha|alloy|uk english female|us english female/i.test(v.name))
                        || voices.find(v => v.lang.toLowerCase().startsWith('en'))
                        || voices[0];
                }};
                const speakQuestion = () => {{
                    if (!synth) return;
                    synth.cancel();
                    const utterance = new SpeechSynthesisUtterance(questionText);
                    utterance.lang = 'en-US';
                    utterance.rate = 0.95;
                    utterance.pitch = 1;
                    utterance.volume = 1;
                    const voice = getVoice();
                    if (voice) utterance.voice = voice;
                    synth.speak(utterance);
                }};
                const button = document.getElementById('read-question-btn');
                button.addEventListener('click', () => {{
                    if (!window.speechSynthesis) return;
                    if (!window.speechSynthesis.getVoices().length) {{
                        window.speechSynthesis.onvoiceschanged = speakQuestion;
                    }} else {{
                        speakQuestion();
                    }}
                    button.style.transform = 'scale(0.99)';
                    setTimeout(() => button.style.transform = 'scale(1)', 100);
                }});
            </script>
        """, height=100)

    st.write("")
    
    # Check if this question was already answered
    if current_idx in st.session_state.evaluations:
        st.success("✅ You have already answered this question.")
        with st.expander("🔍 View AI Detailed Feedback", expanded=True):
            eval_text = st.session_state.evaluations[current_idx]
            score_match = re.search(r'Score:\s*(\d+(?:\.\d+)?)\s*(?:/|out of)\s*10', eval_text, re.IGNORECASE)
            if score_match:
                score_val = float(score_match.group(1))
                if score_val >= 8:
                    delta_text = "Exceptional 🌟"
                    delta_color = "normal"
                elif score_val >= 6:
                    delta_text = "Good Effort 👍"
                    delta_color = "off"
                else:
                    delta_text = "Needs Improvement 💡"
                    delta_color = "inverse"
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.metric(label="Score", value=f"{score_val}/10", delta=delta_text, delta_color=delta_color)
                with col2:
                    st.markdown(eval_text)
            else:
                st.markdown(eval_text)

            if st.button("🔊 Play Evaluation Audio", key=f"play_audio_{current_idx}", use_container_width=True):
                try:
                    audio_buffer = st.session_state.manager.text_to_speech(eval_text)
                    st.session_state[f"feedback_audio_{current_idx}"] = audio_buffer.getvalue()
                except Exception as e:
                    st.error(f"Failed to generate audio: {e}")

            audio_bytes = st.session_state.get(f"feedback_audio_{current_idx}")
            if audio_bytes:
                st.audio(io.BytesIO(audio_bytes), format='audio/mp3')

        # --- AI Chat Assistant for Evaluation ---
        st.write("")
        st.markdown("### 💬 Elevate Chat")
        st.info("Still confused? Ask Elevate what exactly you did wrong and how to improve.")
        
        chat_key = f"chat_{current_idx}"
        if chat_key not in st.session_state:
            st.session_state[chat_key] = [{"role": "assistant", "content": "Hi! I'm Elevate. What would you like to clarify about your evaluation?"}]
            
        with st.container(border=True):
            chat_container = st.container(height=350)
            with chat_container:
                for msg in st.session_state[chat_key]:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])
                
                if st.session_state[chat_key] and st.session_state[chat_key][-1]["role"] == "user":
                    with st.chat_message("assistant"):
                        with st.spinner("Thinking..."):
                            user_msg = st.session_state[chat_key][-1]["content"]
                            ai_resp = st.session_state.manager.chat_about_evaluation(
                                current_q, eval_text, user_msg, st.session_state[chat_key][:-1]
                            )
                            st.markdown(ai_resp)
                    st.session_state[chat_key].append({"role": "assistant", "content": ai_resp})
                    st.rerun()

            if prompt := st.chat_input("Ask Elevate about your score..."):
                st.session_state[chat_key].append({"role": "user", "content": prompt})
                st.rerun()

    else:
        # Answering mechanism inside a nice container
        with st.container(border=True):
            st.subheader("🗣️ Your Response")
            
            tabs = st.tabs(["📝 Text Input", "🎙️ Audio Record"])
            
            text_answer = None
            audio_bytes = None
            
            with tabs[0]:
                text_answer = st.text_area("Type your detailed response here:", height=150, placeholder="I would approach this by...")
            with tabs[1]:
                st.info("Ensure your microphone is enabled. Click the microphone icon to start recording.")
                audio_input = st.audio_input("Record your spoken response (WAV format)")
                if audio_input:
                    audio_bytes = audio_input.getvalue()
                    
            st.write("") # spacing
            if st.button("Submit Answer & Evaluate ✨", type="primary"):
                # Clean text to prevent empty space submissions
                cleaned_text = text_answer.strip() if text_answer else None
                
                if not cleaned_text and not audio_bytes:
                    st.error("⚠️ Please provide an answer using text or audio before submitting.")
                else:
                    with st.spinner("🤖 AI is evaluating your response..."):
                        try:
                            # Prefer audio over text if both somehow exist
                            eval_text = st.session_state.manager.evaluate_answer(
                                current_q,
                                text_answer=cleaned_text if not audio_bytes else None,
                                audio_bytes=audio_bytes
                            )
                            st.session_state.evaluations[current_idx] = eval_text
                            st.session_state[f"feedback_audio_{current_idx}"] = None
                            st.success("Evaluation complete!")
                            st.toast("✅ Answer evaluated successfully!")

                            # Rerun to show the evaluation properly
                            import time
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error during evaluation: {e}")

    st.divider()
    # End Interview Loop
    if len(st.session_state.evaluations) == total_q:
        st.balloons()
        st.success("🎉 You have completed all questions!")
        if st.button("Complete Interview & Generate Report 📈", type="primary", use_container_width=True):
            with st.spinner("Compiling your comprehensive Final Report..."):
                try:
                    qas = []
                    for i, q in enumerate(st.session_state.questions):
                        qas.append({"question": q, "evaluation": st.session_state.evaluations[i]})
                    
                    report = st.session_state.manager.generate_final_report(qas)
                    st.session_state.final_report = report
                    st.toast("🎉 Final Report Generated!")
                    import time
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to generate report: {e}")

# --- Final Report & Study Guide ---
else:
    st.balloons()
    st.markdown('<h2 style="text-align:center; color:#00F2FE;">📋 Your Final Interview Report</h2>', unsafe_allow_html=True)
    
    with st.container(border=True):
        st.markdown(st.session_state.final_report)
    
    st.write("")
    
    if not st.session_state.study_materials:
        if st.button("Generate Personalized Study Materials 📚", type="primary", use_container_width=True):
            with st.spinner("Synthesizing your custom study guide..."):
                try:
                    study_materials = st.session_state.manager.generate_study_materials(st.session_state.final_report)
                    st.session_state.study_materials = study_materials
                    st.toast("📚 Study Materials Ready!")
                    import time
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to generate study materials: {e}")
    else:
        st.markdown('<h2 style="text-align:center; color:#4FACFE;">📚 Personalized Study Materials</h2>', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(st.session_state.study_materials)
        
    st.divider()
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("🔄 Start New Interview", use_container_width=True):
            st.session_state.questions = []
            st.session_state.current_q_idx = 0
            st.session_state.evaluations = {}
            st.session_state.final_report = None
            st.session_state.study_materials = None
            st.rerun()
