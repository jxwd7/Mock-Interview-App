#############################################################################
# mock_interview_app.py – Streamlit + Groq mock-interview demo              #
# Flow: API-Key → Landing (template buttons) → Setup → Profile → Interview  #
# Fix: interviewer gets a real name; no “[Interviewer’s Name]” placeholders #
#############################################################################
import os
import time
import textwrap
from typing import Dict, List

import streamlit as st
from dotenv import load_dotenv
from groq import Groq, GroqError

# or "mixtral-8x7b-32768"
MODEL_NAME = "meta-llama/llama-4-maverick-17b-128e-instruct"
load_dotenv()

# ───────────────────────── Templates ───────────────────────── #
PRELOADED_TEMPLATES: Dict[str, Dict] = {
    "Full-Stack Developer": {
        "company_name": "Tech Corp",
        "job_title": "Senior Full-Stack Developer",
        "company_desc": "A product-led SaaS scale-up delivering web & mobile solutions.",
        "job_desc": "Own the end-to-end SDLC, design scalable REST/GraphQL APIs, and coach juniors.",
        "round": "Technical",
        "tech_stack": "Python, TypeScript, React, Node.js, AWS",
        "criteria": "System-design depth, code quality, mentorship mindset."
    },
    "Machine-Learning Engineer": {
        "company_name": "Vision AI Labs",
        "job_title": "ML Engineer",
        "company_desc": "We build computer-vision products for logistics.",
        "job_desc": "Prototype & ship deep-learning models, own MLOps pipeline.",
        "round": "Technical",
        "tech_stack": "Python, PyTorch, TensorFlow, Kubeflow",
        "criteria": "Model-building, data-centric mindset, deployment chops."
    },
    "DevOps Engineer": {
        "company_name": "CloudOps Inc.",
        "job_title": "DevOps Engineer (AWS / K8s)",
        "company_desc": "Managed-services provider focused on high-availability platforms.",
        "job_desc": "Automate IaC, CI/CD, observability and incident response.",
        "round": "Technical",
        "tech_stack": "AWS, Terraform, Docker, Kubernetes, Go",
        "criteria": "Resilience patterns, IaC best-practices, SRE thinking."
    },
    "Product Manager": {
        "company_name": "FinTech Neo",
        "job_title": "Product Manager – Payments",
        "company_desc": "Digital bank building next-gen payments experience.",
        "job_desc": "Define roadmap, own KPIs, collaborate with design & engineering.",
        "round": "Behavioral",
        "tech_stack": "",
        "criteria": "Stakeholder comms, metrics-driven decisions, user empathy."
    },
}

# ───────────────────── Session defaults ───────────────────── #


def init_session():
    defaults = {
        "page": "apikey" if not os.getenv("GROQ_API_KEY") else "landing",
        "api_key": os.getenv("GROQ_API_KEY", ""),
        "client": None,
        "form": {
            "company_name": "", "job_title": "",
            "company_desc": "", "job_desc": "",
            "round": "Technical", "tech_stack": "", "criteria": ""
        },
        "profile_md": "", "history": [], "show_eval": True, "report_md": ""
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


init_session()

# ───────────────────── Groq helpers ──────────────────────── #


def get_client() -> Groq:
    if st.session_state.client:
        return st.session_state.client
    key = st.session_state.api_key
    if not key:
        st.session_state.page = "apikey"
        st.rerun()
    try:
        cli = Groq(api_key=key)
        cli.chat.completions.create(model=MODEL_NAME,
                                    messages=[
                                        {"role": "user", "content": "ping"}],
                                    max_tokens=1)
    except GroqError as e:
        st.error(f"API key error: {e.message}")
        st.stop()
    st.session_state.client = cli
    return cli


def groq_chat(msgs: List[Dict], temperature: float = 0.4) -> str:
    cli = get_client()
    for attempt in range(3):
        try:
            r = cli.chat.completions.create(model=MODEL_NAME,
                                            messages=msgs,
                                            temperature=temperature)
            return r.choices[0].message.content
        except GroqError as e:
            if e.status_code in (429, 500, 503):
                time.sleep(2 ** attempt)
            else:
                raise

# ───────────────────── Page: API-Key ─────────────────────── #


def page_apikey():
    st.title("🔑 Enter your Groq API Key")
    st.markdown("Get one at **https://console.groq.com** and paste it below.")
    key = st.text_input("Groq API Key", type="password",
                        value=st.session_state.api_key)
    if st.button("Save & continue", type="primary") and key:
        st.session_state.api_key = key
        st.session_state.page = "landing"
        st.rerun()

# ───────────────────── Page: Landing ─────────────────────── #


def page_landing():
    st.title("💼 AI Mock Interview Coach")
    st.subheader("Practice interviews tailored to **your** role.")
    st.markdown("### ⚡ Quick-start with a template")
    cols = st.columns(len(PRELOADED_TEMPLATES))
    for (name, tpl), col in zip(PRELOADED_TEMPLATES.items(), cols):
        with col:
            if st.button(name, use_container_width=True):
                st.session_state.form.update(tpl)
                st.session_state.profile_md = generate_profile(tpl)
                st.session_state.page = "profile"
                st.rerun()
    st.markdown("---")
    if st.button("🔧 Custom setup (fill your own details)", type="primary"):
        st.session_state.page = "setup"
        st.rerun()

# ───────────────────── Page: Setup ───────────────────────── #


def page_setup():
    st.header("Setup (1/3)")
    tpl_names = ["— choose template —"] + list(PRELOADED_TEMPLATES.keys())
    chosen = st.selectbox("Load a template", tpl_names, index=0)
    if chosen != tpl_names[0]:
        st.session_state.form.update(PRELOADED_TEMPLATES[chosen])

    with st.form("setup"):
        f = st.session_state.form
        f["company_name"] = st.text_input("Company name", f["company_name"])
        f["job_title"] = st.text_input("Job title",    f["job_title"])
        f["company_desc"] = st.text_area(
            "Company description", f["company_desc"], height=100)
        f["job_desc"] = st.text_area(
            "Job description",     f["job_desc"],   height=120)
        cols = st.columns(2)
        with cols[0]:
            f["round"] = st.selectbox(
                "Interview round",
                ["Technical", "Behavioral", "HR / Cultural Fit", "Case Study"],
                index=["Technical", "Behavioral", "HR / Cultural Fit", "Case Study"].index(f["round"]))
        with cols[1]:
            st.session_state.show_eval = st.checkbox("Show real-time evaluation",
                                                     value=st.session_state.show_eval)
        if f["round"] == "Technical":
            f["tech_stack"] = st.text_input(
                "Tech stack (comma-separated)", f["tech_stack"])
        else:
            f["tech_stack"] = ""
        f["criteria"] = st.text_area(
            "Evaluation criteria", f["criteria"], height=100)

        if st.form_submit_button("Generate interviewer profile", type="primary"):
            st.session_state.profile_md = generate_profile(f)
            st.session_state.page = "profile"
            st.rerun()


def generate_profile(form: Dict) -> str:
    tech_block = f"Tech Stack: {form['tech_stack']}\n" if form['tech_stack'] else ""
    prompt = textwrap.dedent(f"""
        You are an expert interviewer-profile generator.

        Produce a concise markdown profile including:
        1. **A realistic Name & Title** (e.g. “Jordan Lee – Senior Product Manager”) — **never use placeholders**
        2. Interview Style
        3. Core Focus Areas
        4. Typical Question Types
        5. Evaluation Rubric
        6. Culture-fit Signals
        7. Common Candidate Mistakes

        Company: {form['company_name']}
        Job title: {form['job_title']}
        Company description: {form['company_desc']}
        Job description: {form['job_desc']}
        Interview round: {form['round']}
        {tech_block}
        Evaluation criteria: {form['criteria']}
    """)
    with st.spinner("Crafting interviewer profile…"):
        return groq_chat([{"role": "system", "content": "You are an expert interview assistant"},
                          {"role": "user", "content": prompt}], 0.3)

# ───────────────────── Page: Profile ─────────────────────── #


def page_profile():
    st.header("Interviewer profile (2/3)")
    st.markdown(st.session_state.profile_md or "*No profile generated.*")
    c1, c2 = st.columns(2)
    if c1.button("🚀 Start interview", type="primary"):
        st.session_state.history, st.session_state.report_md = [], ""
        st.session_state.page = "interview"
        st.rerun()
    if c2.button("✏️ Edit setup"):
        st.session_state.page = "setup"
        st.rerun()

# ───────────────────── Page: Interview ───────────────────── #


def page_interview():
    st.header("Live interview (3/3)")

    # Generate interviewer greeting if history is empty
    if not st.session_state.history:
        greet_prompt = textwrap.dedent(f"""
            {st.session_state.profile_md}

            Start the mock interview with:
            • A brief professional greeting **using your own name** from the profile \
              (or invent one). **Do not write “[Interviewer’s Name]”.**
            • The first tailored question.
        """)
        greeting = groq_chat([{"role": "system", "content": "You are an interviewer."},
                              {"role": "user", "content": greet_prompt}], 0.5).strip()
        st.session_state.history.append({"role": "interviewer",
                                         "content": greeting, "eval": None})

    # render chat
    for msg in st.session_state.history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("eval") and st.session_state.show_eval:
                with st.expander("Evaluation"):
                    st.markdown(msg["eval"])

    # candidate reply
    if (user_txt := st.chat_input("Your answer…")):
        st.session_state.history.append({"role": "candidate",
                                         "content": user_txt, "eval": None})
        convo = "\n".join(
            f"{m['role']}: {m['content']}" for m in st.session_state.history)
        follow = textwrap.dedent(f"""
            {st.session_state.profile_md}

            Continue the interview.

            Provide exactly two lines:
            EVALUATION: <brief feedback>
            QUESTION: <specific follow-up question>

            Conversation so far:
            {convo}
        """)
        resp = groq_chat([{"role": "system", "content": "You are an interviewer."},
                          {"role": "user", "content": follow}], 0.5).strip()
        try:
            e_part, q_part = resp.split("QUESTION:", 1)
            eval_text = e_part.replace("EVALUATION:", "").strip()
            question = q_part.strip()
        except ValueError:
            eval_text, question = "", resp

        with st.chat_message("interviewer"):
            st.markdown(question)
            if st.session_state.show_eval and eval_text:
                with st.expander("Evaluation"):
                    st.markdown(eval_text)

        # last candidate message
        st.session_state.history[-2]["eval"] = eval_text
        st.session_state.history.append({"role": "interviewer",
                                         "content": question, "eval": None})

    # report
    if len(st.session_state.history) >= 4 and st.button("Generate interview report"):
        st.session_state.report_md = generate_report()
        st.rerun()
    if st.session_state.report_md:
        st.markdown("---")
        st.subheader("📄 Interview report")
        st.markdown(st.session_state.report_md)


def generate_report() -> str:
    convo = "\n".join(
        f"{m['role'].capitalize()}: {m['content']}"
        f"{'  [Eval: '+m['eval']+']' if m.get('eval') else ''}"
        for m in st.session_state.history)
    prompt = textwrap.dedent(f"""
        Role: interview evaluator. Write a detailed markdown report \
        (summary, assessments, recommendations).

        Profile:
        {st.session_state.profile_md}

        Conversation:
        {convo}
    """)
    with st.spinner("Generating report…"):
        return groq_chat([{"role": "system", "content": "You are an expert interview evaluator"},
                          {"role": "user", "content": prompt}], 0.25)


# ───────────────────── Router ───────────────────────────── #
router = {"apikey": page_apikey, "landing": page_landing,
          "setup": page_setup, "profile": page_profile, "interview": page_interview}
router[st.session_state.page]()
