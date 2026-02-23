import streamlit as st
import requests
import json
import os
import urllib.parse
import hmac

# ===============================
# 🔒 DEMO PASSWORD PROTECTION
# ===============================

DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "")

def require_demo_password():
    if not DEMO_PASSWORD:
        st.error("DEMO_PASSWORD is not set. Add it in Render → Environment Variables.")
        st.stop()

    # already authenticated this session
    if st.session_state.get("demo_authenticated"):
        return

    st.markdown("<h2 style='text-align:center;'>🔒 Demo Access Required</h2>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        password_input = st.text_input("Enter Password", type="password")
        if st.button("Continue"):
            if hmac.compare_digest(password_input, DEMO_PASSWORD):
                st.session_state["demo_authenticated"] = True
                st.rerun()
            else:
                st.error("Incorrect password.")

    # stop the app until password is correct
    st.stop()

require_demo_password()
API_URL = "http://localhost:8000"
DOMAIN = os.environ.get("REPLIT_DEV_DOMAIN", os.environ.get("REPLIT_DOMAINS", "localhost:5000"))
PUBLIC_URL = f"https://{DOMAIN}"

st.set_page_config(
    page_title="StackMind",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    .block-container { padding-top: 1rem; }
    div[data-testid="stSidebar"] { background-color: #1a1d24; }
    .pinned-card { background-color: #1e2130; padding: 10px; border-radius: 8px; margin: 5px 0; border-left: 3px solid #4CAF50; }
    .artifact-card { background-color: #1a1d24; padding: 15px; border-radius: 8px; margin: 8px 0; border: 1px solid #2d3140; }
    h1 { color: #e0e0e0; }
    .stButton>button { border-radius: 6px; }
    .post-card-blue { background: linear-gradient(135deg, #1a237e22, #0d47a122); border-left: 4px solid #2196F3; padding: 16px; border-radius: 8px; margin: 8px 0; }
    .post-card-green { background: linear-gradient(135deg, #1b5e2022, #2e7d3222); border-left: 4px solid #4CAF50; padding: 16px; border-radius: 8px; margin: 8px 0; }
    .post-card-orange { background: linear-gradient(135deg, #e65100 22, #ff6d0022); border-left: 4px solid #FF9800; padding: 16px; border-radius: 8px; margin: 8px 0; }
    .post-card-purple { background: linear-gradient(135deg, #4a148c22, #6a1b9a22); border-left: 4px solid #9C27B0; padding: 16px; border-radius: 8px; margin: 8px 0; }
    .post-card-red { background: linear-gradient(135deg, #b71c1c22, #c6282822); border-left: 4px solid #f44336; padding: 16px; border-radius: 8px; margin: 8px 0; }
    .post-card-teal { background: linear-gradient(135deg, #00695c22, #00897b22); border-left: 4px solid #009688; padding: 16px; border-radius: 8px; margin: 8px 0; }
    .series-number { display: inline-block; background: #ffffff15; padding: 4px 12px; border-radius: 20px; font-size: 0.8em; margin-bottom: 8px; color: #aaa; }
    .copy-ready { background: #1a1d24; padding: 12px; border-radius: 8px; border: 1px dashed #444; font-family: system-ui; white-space: pre-wrap; }
</style>
""", unsafe_allow_html=True)


def api_get(path):
    try:
        r = requests.get(f"{API_URL}{path}", timeout=30)
        return r.json() if r.status_code == 200 else []
    except Exception:
        return []


def api_post(path, data=None, files=None):
    try:
        if files:
            r = requests.post(f"{API_URL}{path}", data=data, files=files, timeout=120)
        else:
            r = requests.post(f"{API_URL}{path}", json=data, timeout=120)
        return r.json() if r.status_code in (200, 201) else {"error": r.text}
    except Exception as e:
        return {"error": str(e)}

def api_delete(path):
    try:
        r = requests.delete(f"{API_URL}{path}", timeout=30)
        return r.json() if r.status_code == 200 else {"error": r.text}
    except Exception as e:
        return {"error": str(e)}

def _persona_payload():
    p = st.session_state.get("active_persona")
    if not p:
        return {}
    return {"persona_context": {
        "name": p.get("name", ""), "role_title": p.get("role_title", ""),
        "industry": p.get("industry", ""), "preferred_tone": p.get("preferred_tone", ""),
        "preferred_cta_style": p.get("preferred_cta_style", ""),
        "pain_points": p.get("pain_points", []), "description": p.get("description", ""),
    }}


COLOR_MAP = {
    "blue": "#2196F3", "green": "#4CAF50", "orange": "#FF9800",
    "purple": "#9C27B0", "red": "#f44336", "teal": "#009688",
}
DEFAULT_COLORS = ["blue", "green", "orange", "purple", "red", "teal"]


def api_patch(path, data=None):
    try:
        r = requests.patch(f"{API_URL}{path}", json=data, timeout=30)
        return r.json() if r.status_code == 200 else {"error": r.text}
    except Exception as e:
        return {"error": str(e)}

page = st.sidebar.radio("Navigation", ["Workbench", "Libraries & Upload", "Identities", "Audience Personas", "Actions & Exports", "Content Calendar", "Archive", "Diagnostics"], index=0)

if page == "Workbench":
    st.title("StackMind Workbench")

    col_wizard, col_main, col_pins = st.columns([1.2, 2.5, 1.3])

    with col_wizard:
        st.subheader("Session Setup")

        identities = api_get("/identities")
        identity_map = {i["name"]: i["id"] for i in identities} if identities else {}
        if identity_map:
            selected_identity = st.selectbox("Choose Identity", list(identity_map.keys()))
        else:
            st.warning("No identities found. Create one in the Identities page.")
            selected_identity = None

        libraries = api_get("/libraries")
        lib_map = {l["name"]: l["id"] for l in libraries} if libraries else {}
        if lib_map:
            selected_library = st.selectbox("Choose Library", list(lib_map.keys()))
        else:
            st.warning("No libraries found. Create one in Libraries & Upload.")
            selected_library = None

        personas_list = api_get("/personas") or []
        persona_map = {p["name"]: p for p in personas_list} if personas_list else {}
        persona_options = ["None (no audience targeting)"] + list(persona_map.keys())
        selected_persona_name = st.selectbox("Audience Persona", persona_options, help="Who are you creating content for?")
        selected_persona = persona_map.get(selected_persona_name) if selected_persona_name != "None (no audience targeting)" else None
        if selected_persona:
            st.caption(f"{selected_persona.get('role_title', '')} | {selected_persona.get('industry', '')} | Tone: {selected_persona.get('preferred_tone', '')}")

        available_files = []
        selected_files = []
        file_map = {}
        if selected_library and selected_library in lib_map:
            lib_id = lib_map[selected_library]
            all_files = api_get(f"/files?library_id={lib_id}")
            available_files = [f for f in all_files if f.get("status") == "embedded"]

            if available_files:
                file_map = {f.get("display_name") or f["filename"]: f["id"] for f in available_files}
                use_all = st.checkbox("Use all files in library", value=True if len(available_files) <= 3 else False)
                if use_all:
                    selected_files = list(file_map.values())
                    st.caption(f"All {len(available_files)} file(s) selected")
                else:
                    chosen = st.multiselect("Select Files", list(file_map.keys()), default=list(file_map.keys())[:1] if file_map else [])
                    selected_files = [file_map[n] for n in chosen]
            else:
                not_ready = [f for f in all_files if f.get("status") != "embedded"]
                if not_ready:
                    st.warning(f"{len(not_ready)} file(s) still processing. Refresh shortly.")
                else:
                    st.info("No files in this library yet. Upload files in Libraries & Upload.")

        can_create = bool(selected_identity and identity_map and selected_library and lib_map and selected_files)

        if st.button("Create Session", type="primary", disabled=not can_create):
            result = api_post("/sessions", {
                "identity_id": identity_map[selected_identity],
                "library_id": lib_map[selected_library],
                "selected_file_ids": selected_files,
                "selection_mode": "all" if len(selected_files) == len(available_files) else "selected",
            })
            if "id" in result:
                st.session_state["active_session"] = result["id"]
                st.session_state["active_persona"] = selected_persona
                st.success("Session created!")
                st.rerun()
            else:
                st.error(f"Error: {result.get('error', 'Unknown')}")

        if "active_session" in st.session_state:
            st.divider()
            st.success("Session active")
            if st.button("End Session"):
                del st.session_state["active_session"]
                for k in list(st.session_state.keys()):
                    if k.startswith("last_result_") or k.startswith("post_image_") or k.startswith("ai_result_") or k.startswith("repurpose_") or k in ("show_action", "deck_result", "content_result", "email_result", "video_result", "blog_result", "consolidated_summary", "cross_doc_result", "post_scores"):
                        del st.session_state[k]
                st.rerun()

    with col_main:
        if "active_session" in st.session_state:
            session_id = st.session_state["active_session"]

            st.subheader("Analysis Modules")
            modules = ["summary", "signals", "claims", "evidence", "relevance", "durability", "leverage", "canon", "decision_memo", "market_trends"]
            module_labels = ["Summary", "Signals", "Claims", "Evidence", "Relevance", "Durability", "Leverage", "Canon", "Decision Memo", "Market Trends"]

            row1 = st.columns(5)
            row2 = st.columns(5)
            all_cols = row1 + row2
            for i, (mod, label) in enumerate(zip(modules, module_labels)):
                with all_cols[i]:
                    if st.button(label, key=f"mod_{mod}"):
                        with st.spinner(f"Running {label}..."):
                            result = api_post(f"/sessions/{session_id}/run/{mod}")
                            if "error" in result:
                                st.error(result.get("detail", result.get("error", "Unknown error")))
                            else:
                                st.session_state[f"last_result_{mod}"] = result
                                st.rerun()

            con_col1, con_col2, con_col3 = st.columns([1, 1, 2])
            with con_col1:
                if st.button("Consolidate All", type="secondary", help="Run multiple modules, then consolidate into one master summary"):
                    with st.spinner("Consolidating all analysis..."):
                        result = api_post(f"/sessions/{session_id}/consolidate_summary")
                        if "error" in result:
                            st.error(result.get("error", "Run some analysis modules first."))
                        else:
                            st.session_state["consolidated_summary"] = result
                            st.rerun()
            with con_col2:
                if st.button("Cross-Doc Insights", type="secondary", help="Find patterns and connections across all your documents"):
                    with st.spinner("Analyzing cross-document patterns..."):
                        result = api_post(f"/sessions/{session_id}/cross_document_insights")
                        if "error" in result:
                            st.error(result.get("error", "Need 2+ documents"))
                        else:
                            st.session_state["cross_doc_result"] = result
                            st.rerun()

            st.divider()

            if "consolidated_summary" in st.session_state:
                cs = st.session_state["consolidated_summary"]
                items = cs.get("items", [cs])
                if isinstance(items, list) and items:
                    item = items[0] if isinstance(items[0], dict) else items
                    if isinstance(item, dict):
                        with st.expander("CONSOLIDATED EXECUTIVE SUMMARY", expanded=True):
                            if item.get("executive_summary"):
                                st.markdown(item["executive_summary"])
                            for field in ["top_signals", "key_claims", "leverage_opportunities", "risks_and_gaps", "recommended_actions"]:
                                vals = item.get(field, [])
                                if vals:
                                    st.markdown(f"**{field.replace('_', ' ').title()}:**")
                                    for v in vals:
                                        st.markdown(f"- {v}")
                            for field in ["evidence_quality", "relevance_verdict", "durability_assessment"]:
                                val = item.get(field, "")
                                if val:
                                    st.markdown(f"**{field.replace('_', ' ').title()}:** {val}")
                            if item.get("confidence_score"):
                                st.progress(float(item["confidence_score"]), text=f"Confidence: {item['confidence_score']}")
                st.divider()

            if "cross_doc_result" in st.session_state:
                cdr = st.session_state["cross_doc_result"]
                with st.expander("CROSS-DOCUMENT INSIGHTS", expanded=True):
                    if cdr.get("summary"):
                        st.markdown(f"**Summary:** {cdr['summary']}")
                    patterns = cdr.get("patterns", [])
                    if patterns:
                        st.markdown("**Patterns Found:**")
                        for pt in patterns:
                            conf = pt.get("confidence", 0)
                            docs = ", ".join(pt.get("documents_involved", []))
                            st.markdown(f"- **{pt.get('pattern', '')}** (confidence: {conf:.0%}) — {pt.get('significance', '')} _{docs}_")
                    contradictions = cdr.get("contradictions", [])
                    if contradictions:
                        st.markdown("**Contradictions:**")
                        for ct in contradictions:
                            st.markdown(f"- **{ct.get('topic', '')}**: _{ct.get('position_a', '')}_ vs _{ct.get('position_b', '')}_")
                    threads = cdr.get("story_threads", [])
                    if threads:
                        st.markdown("**Story Threads:**")
                        for th in threads:
                            st.markdown(f"- **{th.get('thread_title', '')}**: {th.get('narrative', '')} — *Best as: {th.get('content_angle', '')}*")
                    angles = cdr.get("unique_angles", [])
                    if angles:
                        st.markdown("**Unique Angles:**")
                        for a in angles:
                            st.markdown(f"- **{a.get('angle', '')}**: {a.get('why_unique', '')} — *Format: {a.get('recommended_format', '')}*")
                st.divider()

            session_data = api_get(f"/sessions/{session_id}")
            artifacts = session_data.get("artifacts", []) if isinstance(session_data, dict) else []

            has_results = False
            for mod in modules:
                rk = f"last_result_{mod}"
                if rk in st.session_state:
                    has_results = True
                    items = st.session_state[rk].get("items", [])
                    with st.expander(f"{mod.replace('_', ' ').title()} — {len(items)} items", expanded=True):
                        for idx, item in enumerate(items):
                            content = item.get("content", {})
                            if isinstance(content, dict):
                                for k, v in content.items():
                                    if k == "citations":
                                        continue
                                    if isinstance(v, list):
                                        st.markdown(f"**{k.replace('_', ' ').title()}:**")
                                        for li in v:
                                            if isinstance(li, dict):
                                                st.json(li)
                                            else:
                                                st.markdown(f"- {li}")
                                    elif isinstance(v, dict):
                                        st.markdown(f"**{k.replace('_', ' ').title()}:**")
                                        st.json(v)
                                    else:
                                        st.markdown(f"**{k.replace('_', ' ').title()}:** {v}")

                            item_id = item.get("id", "")
                            vcol1, vcol2, vcol3, vcol4, vcol5 = st.columns(5)
                            with vcol1:
                                if st.button("Useful", key=f"useful_{mod}_{idx}"):
                                    api_post(f"/sessions/{session_id}/vote", {"artifact_item_id": item_id, "vote": "useful"})
                                    st.toast("Voted useful")
                            with vcol2:
                                if st.button("Not useful", key=f"not_{mod}_{idx}"):
                                    api_post(f"/sessions/{session_id}/vote", {"artifact_item_id": item_id, "vote": "not"})
                                    st.toast("Voted not useful")
                            with vcol3:
                                if st.button("Partial", key=f"partial_{mod}_{idx}"):
                                    api_post(f"/sessions/{session_id}/vote", {"artifact_item_id": item_id, "vote": "partial"})
                                    st.toast("Voted partial")
                            with vcol4:
                                if st.button("Pin", key=f"pin_{mod}_{idx}"):
                                    api_post(f"/sessions/{session_id}/pin", {"artifact_item_id": item_id})
                                    st.toast("Pinned!")
                                    st.rerun()
                            with vcol5:
                                if item.get("citations"):
                                    with st.popover("Citations"):
                                        st.json(item["citations"])

                            st.divider()

            if not has_results:
                if artifacts:
                    st.info("Previous analysis found. Click a module above to run new analysis.")
                else:
                    st.info("Click a module button above to run analysis on your selected files.")

            st.divider()
            st.subheader("Content & Actions")

            act_cols = st.columns(7)
            action_buttons = [
                ("Posts", "posts"),
                ("Blog Series", "blog"),
                ("Deck Builder", "deck"),
                ("Email Sequence", "email"),
                ("Video Pipeline", "video"),
                ("Export", "export"),
                ("Webhook", "webhook"),
            ]
            for i, (label, key) in enumerate(action_buttons):
                with act_cols[i]:
                    if st.button(label, key=f"act_{key}"):
                        st.session_state["show_action"] = key

            # === POSTS (Content Series) ===
            if st.session_state.get("show_action") == "posts":
                st.subheader("Social Media Posts")

                session_data_for_mods = api_get(f"/sessions/{session_id}")
                completed_artifacts = session_data_for_mods.get("artifacts", []) if isinstance(session_data_for_mods, dict) else []
                completed_module_names = list(set(a.get("module_name", "") for a in completed_artifacts if a.get("module_name") not in ("content_series", "blog_series", "deck_builder", "email_sequence", "video_pipeline", "")))

                if not completed_module_names:
                    st.warning("Run some analysis modules first (e.g. Claims, Canon, Signals), then come back here to generate posts based on those findings.")
                else:
                    module_label_map = {
                        "summary": "Summary", "signals": "Signals", "claims": "Claims",
                        "evidence": "Evidence", "relevance": "Relevance", "durability": "Durability",
                        "leverage": "Leverage", "canon": "Canon", "decision_memo": "Decision Memo",
                        "market_trends": "Market Trends",
                    }

                    st.markdown("**Step 1: Choose source modules**")
                    st.caption("Select which analysis findings to base your posts on")
                    mod_cols = st.columns(min(len(completed_module_names), 5))
                    selected_source_modules = []
                    for mi, mn in enumerate(completed_module_names):
                        with mod_cols[mi % len(mod_cols)]:
                            if st.checkbox(module_label_map.get(mn, mn.title()), value=True, key=f"src_mod_{mn}"):
                                selected_source_modules.append(mn)

                    st.markdown("**Step 2: Get thesis suggestions**")
                    if selected_source_modules:
                        if st.button("Suggest Thesis Ideas", key="suggest_thesis_btn"):
                            with st.spinner("Analyzing findings and suggesting thesis ideas..."):
                                suggestions_result = api_post(f"/sessions/{session_id}/suggest_thesis", {
                                    "source_modules": selected_source_modules,
                                })
                                st.session_state["thesis_suggestions"] = suggestions_result
                                st.rerun()

                        if "thesis_suggestions" in st.session_state:
                            suggestions = st.session_state["thesis_suggestions"].get("suggestions", [])
                            if suggestions:
                                thesis_options = [s.get("thesis", "") for s in suggestions]
                                thesis_options.append("Custom (write my own)")
                                selected_thesis_idx = st.radio(
                                    "Choose a thesis or write your own:",
                                    range(len(thesis_options)),
                                    format_func=lambda i: thesis_options[i],
                                    key="thesis_radio",
                                )

                                for si, s in enumerate(suggestions):
                                    if si == selected_thesis_idx:
                                        st.caption(f"Angle: {s.get('angle', '')}")
                                        st.caption(f"Source: {s.get('source_insight', '')}")
                                        st.caption(f"Recommended: {s.get('recommended_platform', '')}")

                                if selected_thesis_idx == len(suggestions):
                                    thesis_text = st.text_area("Your thesis:", key="custom_thesis_input")
                                else:
                                    thesis_text = thesis_options[selected_thesis_idx]
                            else:
                                st.info("No suggestions generated. Write your own thesis below.")
                                thesis_text = st.text_area("Series Thesis:", key="manual_thesis")
                        else:
                            st.caption("Click above to get AI-suggested thesis ideas, or write your own below.")
                            thesis_text = st.text_area("Or write your own thesis:", key="manual_thesis_2")

                        st.markdown("**Step 3: Choose platform & type**")
                        pcol1, pcol2 = st.columns(2)
                        with pcol1:
                            platform = st.selectbox("Platform", ["LinkedIn", "Facebook", "X/Twitter", "Instagram", "Website", "YouTube Shorts", "TikTok"])
                        with pcol2:
                            series_type = st.selectbox("Type", ["series", "one-time"])

                        st.markdown("**Step 4: Generate**")
                        if st.button("Generate Posts", type="primary", key="gen_posts_final"):
                            final_thesis = thesis_text if thesis_text else "Generate content based on the analysis findings"
                            with st.spinner("Generating content series..."):
                                post_payload = {
                                    "series_thesis": final_thesis,
                                    "platform": platform,
                                    "series_type": series_type,
                                    "source_modules": selected_source_modules,
                                    **_persona_payload(),
                                }
                                result = api_post(f"/sessions/{session_id}/generate_posts", post_payload)
                                st.session_state["content_result"] = result
                                st.rerun()
                    else:
                        st.warning("Select at least one source module above.")

                if "content_result" in st.session_state:
                    posts = st.session_state["content_result"].get("posts", [])

                    score_col1, score_col2 = st.columns([1, 3])
                    with score_col1:
                        if st.button("Score All Posts", key="score_all_btn", help="AI scores each post for engagement, authority, and audience fit"):
                            with st.spinner("Scoring posts..."):
                                score_result = api_post(f"/sessions/{session_id}/score_posts", {"posts": posts})
                                scores = score_result.get("scores", [])
                                if scores:
                                    st.session_state["post_scores"] = scores
                                    st.rerun()
                                else:
                                    st.warning("Scoring failed. Try again.")

                    if "post_scores" in st.session_state:
                        scores = st.session_state["post_scores"]
                        for sc in scores:
                            idx = sc.get("post_index", 0)
                            overall = sc.get("overall_score", 0)
                            eng = sc.get("engagement_score", 0)
                            auth = sc.get("authority_score", 0)
                            fit = sc.get("audience_fit", 0)
                            label = f"Post {idx+1}"
                            color = "#4CAF50" if overall >= 70 else "#FF9800" if overall >= 50 else "#f44336"
                            st.markdown(f'<div style="display:inline-block;background:#1a1d24;padding:6px 12px;border-radius:8px;margin:2px 4px;border-left:3px solid {color};">'
                                        f'<b style="color:{color}">{label}: {overall}/100</b> '
                                        f'<span style="color:#888;font-size:0.8em;">Engage:{eng} Authority:{auth} Fit:{fit}</span></div>',
                                        unsafe_allow_html=True)

                    if len(posts) > 1:
                        with st.expander("Schedule Entire Series", expanded=False):
                            st.write("Pick a date for the first post. The rest will be auto-spaced 2 days apart. You can adjust individual dates below.")
                            from datetime import timedelta as td_delta
                            sch_cols = st.columns(3)
                            with sch_cols[0]:
                                series_start = st.date_input("Series 1 start date", key="series_start_date")
                            with sch_cols[1]:
                                series_gap = st.number_input("Days between posts", min_value=1, max_value=14, value=2, key="series_gap")
                            with sch_cols[2]:
                                series_platform = st.selectbox("Platform", ["LinkedIn", "X/Twitter", "Blog", "Email"], key="series_platform")
                            if st.button("Schedule All Posts", key="sched_all_series"):
                                from datetime import datetime as dt_util
                                success_count = 0
                                for si, sp in enumerate(posts):
                                    post_date = series_start + td_delta(days=si * series_gap)
                                    sp_label = sp.get('series_label', f'Post {si+1}')
                                    sp_color = sp.get('color_tag', DEFAULT_COLORS[si % len(DEFAULT_COLORS)])
                                    sp_text = sp.get('text', '')
                                    sp_hashtags = sp.get('hashtags', [])
                                    if sp_hashtags:
                                        sp_text += "\n\n" + " ".join(sp_hashtags)
                                    cal_r = api_post("/calendar", {
                                        "title": sp_label,
                                        "content_type": "post",
                                        "scheduled_date": str(post_date),
                                        "scheduled_time": "09:00",
                                        "platform": series_platform,
                                        "content_preview": sp_text[:200],
                                        "color": sp_color,
                                        "session_id": str(session_id),
                                        "notes": f"Series post {si+1} of {len(posts)}",
                                        "meta": {"post_index": si, "post_number": si+1, "series_total": len(posts)},
                                    })
                                    if cal_r and cal_r.get("id"):
                                        success_count += 1
                                if success_count == len(posts):
                                    st.success(f"All {len(posts)} posts scheduled! First: {series_start}, Last: {series_start + td_delta(days=(len(posts)-1)*series_gap)}. View in Content Calendar.")
                                elif success_count > 0:
                                    st.warning(f"Scheduled {success_count}/{len(posts)} posts.")
                                else:
                                    st.error("Scheduling failed. Try again.")

                    for pi, p in enumerate(posts):
                        pnum = p.get('post_number', pi + 1)
                        ptype = p.get('post_type', 'post')
                        series_label = p.get('series_label', f'Post {pnum}')
                        color_tag = p.get('color_tag', DEFAULT_COLORS[pi % len(DEFAULT_COLORS)])
                        color_hex = COLOR_MAP.get(color_tag, "#2196F3")

                        st.markdown(f"""<div style="background: linear-gradient(135deg, {color_hex}11, {color_hex}22); border-left: 4px solid {color_hex}; padding: 16px; border-radius: 8px; margin: 12px 0;">
<span style="display:inline-block; background:{color_hex}33; padding:4px 14px; border-radius:20px; font-size:0.8em; color:{color_hex}; font-weight:600; margin-bottom:8px;">{series_label}</span>
<span style="display:inline-block; background:#ffffff10; padding:4px 10px; border-radius:20px; font-size:0.75em; color:#888; margin-left:8px;">{ptype.upper()}</span>
</div>""", unsafe_allow_html=True)

                        post_text = p.get("text", "")
                        hashtags = p.get("hashtags", [])
                        full_text = post_text
                        if hashtags:
                            full_text += "\n\n" + " ".join(hashtags)

                        st.text_area("Copy-paste ready text:", full_text, key=f"pt_{pnum}", height=180)

                        bcol1, bcol2, bcol3 = st.columns(3)
                        with bcol1:
                            if p.get("cta"):
                                st.caption(f"CTA: {p['cta']}")
                        with bcol2:
                            if p.get("best_time_to_post"):
                                st.caption(f"Best time: {p['best_time_to_post']}")
                        with bcol3:
                            if p.get("estimated_engagement"):
                                st.caption(f"Engagement: {p['estimated_engagement']}")

                        if p.get("compliance_note"):
                            st.caption(f"Compliance: {p['compliance_note']}")

                        st.markdown(f'<p style="font-size:0.85em; color:#aaa; margin:8px 0 4px;">AI Generate for {series_label}</p>', unsafe_allow_html=True)
                        ai_cols = st.columns(4)
                        with ai_cols[0]:
                            if st.button("Generate Image", key=f"ai_image_{pnum}"):
                                with st.spinner("Generating image..."):
                                    r = api_post(f"/sessions/{session_id}/ai_generate", {"tool": "image", "post_text": post_text[:300], "post_title": series_label})
                                    if r.get("status") == "success" and r.get("image_url"):
                                        st.session_state[f"ai_result_{pnum}"] = r
                                        st.rerun()
                                    else:
                                        st.warning(r.get("message", "Image generation failed."))
                        with ai_cols[1]:
                            if st.button("Gamma PPT", key=f"ai_gamma_{pnum}"):
                                with st.spinner("Generating presentation..."):
                                    r = api_post(f"/sessions/{session_id}/ai_generate", {"tool": "gamma", "post_text": full_text, "post_title": series_label})
                                    st.session_state[f"ai_result_{pnum}"] = r
                                    st.rerun()
                        with ai_cols[2]:
                            if st.button("HeyGen Video", key=f"ai_heygen_{pnum}"):
                                with st.spinner("Starting video generation..."):
                                    r = api_post(f"/sessions/{session_id}/ai_generate", {"tool": "heygen", "post_text": post_text, "post_title": series_label})
                                    st.session_state[f"ai_result_{pnum}"] = r
                                    st.rerun()
                        with ai_cols[3]:
                            if st.button("Runway Video", key=f"ai_runway_{pnum}"):
                                with st.spinner("Starting video generation..."):
                                    r = api_post(f"/sessions/{session_id}/ai_generate", {"tool": "runway", "post_text": post_text[:300], "post_title": series_label})
                                    st.session_state[f"ai_result_{pnum}"] = r
                                    st.rerun()

                        ai_result_key = f"ai_result_{pnum}"
                        if ai_result_key in st.session_state:
                            ai_r = st.session_state[ai_result_key]
                            ai_tool = ai_r.get("tool", "")
                            ai_status = ai_r.get("status", "")

                            if ai_tool == "image" and ai_status == "success":
                                st.image(f"{API_URL}{ai_r['image_url']}", caption=f"Visual card for {series_label}")

                            elif ai_tool == "gamma":
                                if ai_status == "success":
                                    url = ai_r.get("presentation_url", "")
                                    st.success(f"Presentation created! [Open in Gamma]({url})")
                                elif ai_status == "manual":
                                    st.info(ai_r.get("message", ""))
                                    st.code(ai_r.get("markdown", ""), language="markdown")
                                else:
                                    st.warning(ai_r.get("message", "Gamma generation issue."))

                            elif ai_tool in ("heygen", "runway"):
                                if ai_status == "processing":
                                    st.info(ai_r.get("message", "Video generation started..."))
                                    vid_id = ai_r.get("video_id", "") or ai_r.get("task_id", "")
                                    if vid_id:
                                        st.caption(f"Job ID: {vid_id}")
                                elif ai_status == "not_configured":
                                    st.warning(ai_r.get("message", "API key not configured."))
                                else:
                                    st.warning(ai_r.get("message", "Video generation issue."))

                        st.markdown(f'<p style="font-size:0.85em; color:#aaa; margin:12px 0 4px;">Share {series_label}</p>', unsafe_allow_html=True)
                        share_cols = st.columns(4)
                        with share_cols[0]:
                            linkedin_text = urllib.parse.quote(full_text[:1300])
                            st.markdown(f'''<a href="https://www.linkedin.com/shareArticle?mini=true&summary={linkedin_text}" target="_blank" style="display:inline-flex;align-items:center;gap:6px;background:#0077B5;color:white;padding:6px 14px;border-radius:6px;text-decoration:none;font-size:0.8em;">
<svg width="16" height="16" viewBox="0 0 24 24" fill="white"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
LinkedIn</a>''', unsafe_allow_html=True)
                        with share_cols[1]:
                            twitter_text = urllib.parse.quote(full_text[:280])
                            st.markdown(f'''<a href="https://twitter.com/intent/tweet?text={twitter_text}" target="_blank" style="display:inline-flex;align-items:center;gap:6px;background:#000;color:white;padding:6px 14px;border-radius:6px;text-decoration:none;font-size:0.8em;">
<svg width="16" height="16" viewBox="0 0 24 24" fill="white"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
X / Twitter</a>''', unsafe_allow_html=True)
                        with share_cols[2]:
                            st.download_button("Download Text", full_text, file_name=f"post_{pnum}.txt", key=f"dl_post_{pnum}")

                        action_cols = st.columns(5)
                        with action_cols[0]:
                            save_folder = st.session_state.get("save_folder", "General")
                            if st.button("Save to Archive", key=f"save_{pnum}", help="Save this post to your Archive"):
                                result = api_post("/archive", {
                                    "content_type": "post",
                                    "title": series_label,
                                    "body": full_text,
                                    "meta": {"platform": p.get("platform", ""), "post_number": pnum, "color": color_tag},
                                    "folder": save_folder,
                                    "session_id": str(session_id),
                                })
                                if result and result.get("id"):
                                    st.success("Saved to Archive!")
                                else:
                                    st.warning("Save failed.")
                        with action_cols[1]:
                            if st.button("Regenerate", key=f"regen_{pnum}", help="Generate a fresh version of this post"):
                                with st.spinner("Regenerating post..."):
                                    regen = api_post(f"/sessions/{session_id}/regenerate_post", {
                                        "post_index": pi, "posts": posts,
                                        "platform": p.get("platform", "LinkedIn"),
                                    })
                                    if regen and not regen.get("error"):
                                        regen["post_number"] = pnum
                                        regen["series_label"] = series_label
                                        regen["color_tag"] = color_tag
                                        posts[pi] = regen
                                        st.session_state["content_result"]["posts"] = posts
                                        if "post_scores" in st.session_state:
                                            del st.session_state["post_scores"]
                                        st.rerun()
                                    else:
                                        st.warning("Regeneration failed. Try again.")
                        with action_cols[2]:
                            if st.button("Repurpose", key=f"repurpose_{pnum}", help="Turn this post into blog + deck + email + video script"):
                                with st.spinner("Repurposing into multiple formats..."):
                                    rep = api_post(f"/sessions/{session_id}/repurpose_post", {
                                        "post_text": full_text, "post_title": series_label,
                                    })
                                    if rep and isinstance(rep, dict) and not rep.get("error"):
                                        st.session_state[f"repurpose_{pnum}"] = rep
                                        st.rerun()
                                    else:
                                        st.warning("Repurpose failed. Try again.")
                        with action_cols[3]:
                            sched_key = f"sched_date_{pnum}"
                            sched_date = st.date_input("Post date", key=sched_key, label_visibility="collapsed")
                        with action_cols[4]:
                            if st.button("Schedule", key=f"cal_{pnum}", help="Add this post to your Content Calendar"):
                                sched_d = st.session_state.get(f"sched_date_{pnum}")
                                cal_res = api_post("/calendar", {
                                    "title": series_label,
                                    "content_type": "post",
                                    "scheduled_date": str(sched_d) if sched_d else "",
                                    "scheduled_time": p.get("best_time_to_post", "09:00")[:5] if p.get("best_time_to_post") else "09:00",
                                    "platform": p.get("platform", "LinkedIn"),
                                    "content_preview": full_text[:200],
                                    "color": color_tag,
                                    "session_id": str(session_id),
                                    "notes": f"Series post {pnum} of {len(posts)}",
                                    "meta": {"post_index": pi, "post_number": pnum, "series_total": len(posts)},
                                })
                                if cal_res and cal_res.get("id"):
                                    st.success(f"Scheduled for {sched_d}!")
                                else:
                                    st.warning("Failed to schedule.")

                        repurpose_key = f"repurpose_{pnum}"
                        if repurpose_key in st.session_state:
                            rep = st.session_state[repurpose_key]
                            if not isinstance(rep, dict):
                                del st.session_state[repurpose_key]
                                continue
                            with st.expander(f"Repurposed Content for {series_label}", expanded=True):
                                blog = rep.get("blog", {})
                                if blog:
                                    st.markdown(f"**Blog: {blog.get('title', '')}**")
                                    st.markdown(blog.get("body", "")[:500] + "...")
                                    if blog.get("seo_keywords"):
                                        st.caption(f"SEO: {', '.join(blog['seo_keywords'])}")
                                    st.download_button("Download Blog", blog.get("body", ""), file_name=f"blog_{pnum}.md", key=f"dl_blog_rep_{pnum}")

                                email = rep.get("email", {})
                                if email:
                                    st.markdown(f"**Email: {email.get('subject', '')}**")
                                    st.text_area("Email body:", email.get("body", ""), height=100, key=f"email_rep_{pnum}")

                                script = rep.get("video_script", {})
                                if script:
                                    st.markdown(f"**Video Script** (~{script.get('duration_estimate', '60s')})")
                                    st.markdown(f"Hook: {script.get('hook', '')}")
                                    st.markdown(script.get("body", "")[:300])

                                deck_slides = rep.get("deck_slides", [])
                                if deck_slides:
                                    st.markdown(f"**Deck ({len(deck_slides)} slides)**")
                                    for s in deck_slides:
                                        st.markdown(f"- **{s.get('title', '')}**: {', '.join(s.get('bullets', []))}")

                                thread = rep.get("twitter_thread", [])
                                if thread:
                                    st.markdown("**X/Twitter Thread:**")
                                    for ti, t in enumerate(thread):
                                        st.markdown(f"{ti+1}/ {t}")

                        st.markdown("---")

            # === BLOG SERIES ===
            elif st.session_state.get("show_action") == "blog":
                st.subheader("Blog Series")

                session_data_blog = api_get(f"/sessions/{session_id}")
                blog_artifacts = session_data_blog.get("artifacts", []) if isinstance(session_data_blog, dict) else []
                blog_mod_names = list(set(a.get("module_name", "") for a in blog_artifacts if a.get("module_name") not in ("content_series", "blog_series", "deck_builder", "email_sequence", "video_pipeline", "")))

                if not blog_mod_names:
                    st.warning("Run some analysis modules first, then come back to generate blog posts.")
                else:
                    st.markdown("**Source modules for blog content:**")
                    blog_src_mods = []
                    bcols = st.columns(min(len(blog_mod_names), 5))
                    for bmi, bmn in enumerate(blog_mod_names):
                        with bcols[bmi % len(bcols)]:
                            if st.checkbox(bmn.replace("_", " ").title(), value=True, key=f"blog_src_{bmn}"):
                                blog_src_mods.append(bmn)

                    blog_thesis = st.text_area("Series Thesis", placeholder="What is the overarching theme? (Leave blank for auto-generated)")
                    bcol1, bcol2, bcol3 = st.columns(3)
                    with bcol1:
                        blog_count = st.selectbox("Number of Blog Posts", [2, 3, 4, 5], index=1)
                    with bcol2:
                        blog_audience = st.text_input("Target Audience", "professionals")
                    with bcol3:
                        blog_tone = st.selectbox("Tone", ["authoritative", "conversational", "educational", "persuasive"])

                    if not blog_src_mods:
                        st.warning("Select at least one source module above.")
                    elif st.button("Generate Blog Series", type="primary", key="gen_blog_final"):
                        with st.spinner("Generating blog series (this takes a moment)..."):
                            result = api_post(f"/sessions/{session_id}/generate_blogs", {
                                "series_thesis": blog_thesis or "Generate based on analysis findings",
                                "blog_count": blog_count,
                                "target_audience": blog_audience,
                                "tone": blog_tone,
                                "source_modules": blog_src_mods,
                                **_persona_payload(),
                            })
                            st.session_state["blog_result"] = result
                            st.rerun()

                if "blog_result" in st.session_state:
                    blogs = st.session_state["blog_result"].get("blogs", [])
                    for bi, b in enumerate(blogs):
                        bnum = b.get('blog_number', bi + 1)
                        series_label = b.get('series_label', f'Blog {bnum}')
                        color_tag = b.get('color_tag', DEFAULT_COLORS[bi % len(DEFAULT_COLORS)])
                        color_hex = COLOR_MAP.get(color_tag, "#2196F3")

                        st.markdown(f"""<div style="background: linear-gradient(135deg, {color_hex}11, {color_hex}22); border-left: 4px solid {color_hex}; padding: 16px; border-radius: 8px; margin: 12px 0;">
<span style="display:inline-block; background:{color_hex}33; padding:4px 14px; border-radius:20px; font-size:0.8em; color:{color_hex}; font-weight:600;">{series_label}</span>
<span style="display:inline-block; background:#ffffff10; padding:4px 10px; border-radius:20px; font-size:0.75em; color:#888; margin-left:8px;">{b.get('estimated_read_time', '')}</span>
</div>""", unsafe_allow_html=True)

                        st.markdown(f"### {b.get('title', '')}")
                        if b.get('subtitle'):
                            st.markdown(f"*{b['subtitle']}*")
                        if b.get('meta_description'):
                            st.caption(f"SEO: {b['meta_description']}")
                        if b.get('seo_keywords'):
                            st.caption(f"Keywords: {', '.join(b['seo_keywords'])}")

                        body = b.get('body', '')
                        st.markdown(body)

                        if b.get('key_takeaways'):
                            st.markdown("**Key Takeaways:**")
                            for kt in b['key_takeaways']:
                                st.markdown(f"- {kt}")

                        if b.get('cta'):
                            st.info(f"CTA: {b['cta']}")

                        bcol1, bcol2, bcol3 = st.columns(3)
                        with bcol1:
                            st.download_button(
                                f"Download Blog {bnum} (Markdown)",
                                f"# {b.get('title', '')}\n\n{body}",
                                file_name=f"blog_{bnum}.md",
                                mime="text/markdown",
                                key=f"dl_blog_{bnum}"
                            )
                        with bcol2:
                            full_blog = f"# {b.get('title', '')}\n\n*{b.get('subtitle', '')}*\n\n{body}"
                            st.text_area("Copy-paste ready:", full_blog, height=100, key=f"blog_copy_{bnum}")
                        with bcol3:
                            if st.button("Save to Archive", key=f"save_blog_{bnum}"):
                                api_post("/archive", {
                                    "content_type": "blog",
                                    "title": b.get("title", f"Blog {bnum}"),
                                    "body": full_blog,
                                    "meta": {"seo_keywords": b.get("seo_keywords", []), "subtitle": b.get("subtitle", "")},
                                    "folder": "General",
                                    "session_id": str(session_id),
                                })
                                st.success("Blog saved to Archive!")

                        st.markdown("---")

            # === DECK BUILDER ===
            elif st.session_state.get("show_action") == "deck":
                st.subheader("Deck Builder")

                session_data_deck = api_get(f"/sessions/{session_id}")
                deck_artifacts = session_data_deck.get("artifacts", []) if isinstance(session_data_deck, dict) else []
                deck_mod_names = list(set(a.get("module_name", "") for a in deck_artifacts if a.get("module_name") not in ("content_series", "blog_series", "deck_builder", "email_sequence", "video_pipeline", "")))

                deck_src_mods = []
                if deck_mod_names:
                    st.markdown("**Source modules for deck content:**")
                    dcols = st.columns(min(len(deck_mod_names), 5))
                    for dmi, dmn in enumerate(deck_mod_names):
                        with dcols[dmi % len(dcols)]:
                            if st.checkbox(dmn.replace("_", " ").title(), value=True, key=f"deck_src_{dmn}"):
                                deck_src_mods.append(dmn)

                dcol1, dcol2 = st.columns(2)
                with dcol1:
                    goal = st.selectbox("Deck Goal", ["Pitch", "Update", "Decision", "Trends", "Training"])
                    slide_count = st.selectbox("Slide Count", [5, 10, 15], index=1)
                with dcol2:
                    audience = st.selectbox("Audience", ["CEO", "Operators", "Investors", "Clients"])
                    style = st.selectbox("Narrative Style", ["analytical", "persuasive", "instructional"])

                if deck_mod_names and not deck_src_mods:
                    st.warning("Select at least one source module above.")
                elif st.button("Generate Deck", type="primary", key="gen_deck_final"):
                    with st.spinner("Generating deck..."):
                        payload = {
                            "deck_goal": goal, "audience": audience,
                            "slide_count": slide_count, "narrative_style": style,
                        }
                        if deck_src_mods:
                            payload["source_modules"] = deck_src_mods
                        result = api_post(f"/sessions/{session_id}/deck_builder", payload)
                        st.session_state["deck_result"] = result
                        st.rerun()

                if "deck_result" in st.session_state:
                    deck_file = st.session_state["deck_result"].get("deck_file", "")
                    slides = st.session_state["deck_result"].get("slides", [])
                    gamma_json = st.session_state["deck_result"].get("gamma_json", {})

                    if deck_file:
                        st.success("Deck generated!")
                        deck_url = f"{API_URL}/static/decks/{deck_file}"

                        dcol1, dcol2, dcol3 = st.columns(3)
                        with dcol1:
                            st.markdown(f"[Open Full Presentation]({deck_url})")
                        with dcol2:
                            try:
                                r = requests.get(deck_url, timeout=10)
                                if r.status_code == 200:
                                    st.download_button("Download Deck (HTML)", r.content, file_name=deck_file, mime="text/html")
                            except Exception:
                                pass
                        with dcol3:
                            if gamma_json and gamma_json.get("markdown"):
                                st.download_button("Download for Gamma/Canva (Markdown)", gamma_json["markdown"], file_name="deck_for_gamma.md", mime="text/markdown")

                        if st.button("Save Deck to Archive", key="save_deck_archive"):
                            slide_text = "\n\n".join([f"## {s.get('title', '')}\n" + "\n".join(f"- {b}" for b in s.get("bullets", [])) for s in slides])
                            api_post("/archive", {
                                "content_type": "deck",
                                "title": f"Deck - {len(slides)} slides",
                                "body": slide_text,
                                "meta": {"slide_count": len(slides), "deck_file": deck_file},
                                "folder": "General",
                                "session_id": str(session_id),
                            })
                            st.success("Deck saved to Archive!")

                        try:
                            r = requests.get(deck_url, timeout=10)
                            if r.status_code == 200:
                                import base64
                                b64 = base64.b64encode(r.content).decode()
                                st.markdown(f'<iframe src="data:text/html;base64,{b64}" width="100%" height="500" style="border:1px solid #333; border-radius:8px;"></iframe>', unsafe_allow_html=True)
                        except Exception:
                            pass

                    if gamma_json:
                        with st.expander("Gamma / Canva Export"):
                            st.info(gamma_json.get("paste_instructions", "Copy the markdown and paste into Gamma.app or Canva."))
                            st.text_area("Markdown for Gamma/Canva", gamma_json.get("markdown", ""), height=200, key="gamma_md")

                    st.markdown("---")
                    st.caption("Slide Details (editable)")
                    for s in slides:
                        with st.expander(f"Slide {s.get('slide_number', '')}: {s.get('title', '')}"):
                            st.text_area("Title", s.get("title", ""), key=f"slide_t_{s.get('slide_number')}")
                            st.text_area("Body", s.get("body", ""), key=f"slide_b_{s.get('slide_number')}")
                            if s.get("bullets"):
                                st.markdown("**Bullets:**")
                                for b in s["bullets"]:
                                    st.markdown(f"- {b}")
                            if s.get("speaker_notes"):
                                st.caption(f"Speaker Notes: {s['speaker_notes']}")

            # === EMAIL SEQUENCE ===
            elif st.session_state.get("show_action") == "email":
                st.subheader("Email Sequence")

                session_data_email = api_get(f"/sessions/{session_id}")
                email_artifacts = session_data_email.get("artifacts", []) if isinstance(session_data_email, dict) else []
                email_mod_names = list(set(a.get("module_name", "") for a in email_artifacts if a.get("module_name") not in ("content_series", "blog_series", "deck_builder", "email_sequence", "video_pipeline", "")))

                email_src_mods = []
                if email_mod_names:
                    st.markdown("**Source modules for email content:**")
                    ecols = st.columns(min(len(email_mod_names), 5))
                    for emi, emn in enumerate(email_mod_names):
                        with ecols[emi % len(ecols)]:
                            if st.checkbox(emn.replace("_", " ").title(), value=True, key=f"email_src_{emn}"):
                                email_src_mods.append(emn)

                count = st.selectbox("Number of Emails", [3, 4, 5])
                if email_mod_names and not email_src_mods:
                    st.warning("Select at least one source module above.")
                elif st.button("Generate Emails", type="primary", key="gen_email_final"):
                    with st.spinner("Generating emails..."):
                        payload = {"email_count": count, **_persona_payload()}
                        if email_src_mods:
                            payload["source_modules"] = email_src_mods
                        result = api_post(f"/sessions/{session_id}/generate_email", payload)
                        st.session_state["email_result"] = result
                        st.rerun()

                if "email_result" in st.session_state:
                    emails = st.session_state["email_result"].get("emails", [])
                    for e in emails:
                        with st.expander(f"Email {e.get('email_number', '')}: {e.get('subject', '')}"):
                            st.text_input("Subject", e.get("subject", ""), key=f"es_{e.get('email_number')}")
                            st.text_area("Body", e.get("body", ""), key=f"eb_{e.get('email_number')}", height=200)
                            if st.button("Save to Archive", key=f"save_email_{e.get('email_number')}"):
                                api_post("/archive", {
                                    "content_type": "email",
                                    "title": e.get("subject", f"Email {e.get('email_number', '')}"),
                                    "body": e.get("body", ""),
                                    "meta": {"subject": e.get("subject", ""), "email_number": e.get("email_number")},
                                    "folder": "General",
                                    "session_id": str(session_id),
                                })
                                st.success("Email saved to Archive!")

            # === VIDEO PIPELINE ===
            elif st.session_state.get("show_action") == "video":
                st.subheader("Video Pipeline")

                session_data_vid = api_get(f"/sessions/{session_id}")
                vid_artifacts = session_data_vid.get("artifacts", []) if isinstance(session_data_vid, dict) else []
                vid_mod_names = list(set(a.get("module_name", "") for a in vid_artifacts if a.get("module_name") not in ("content_series", "blog_series", "deck_builder", "email_sequence", "video_pipeline", "")))

                vid_src_mods = []
                if vid_mod_names:
                    st.markdown("**Source modules for video content:**")
                    vcols_src = st.columns(min(len(vid_mod_names), 5))
                    for vmi, vmn in enumerate(vid_mod_names):
                        with vcols_src[vmi % len(vcols_src)]:
                            if st.checkbox(vmn.replace("_", " ").title(), value=True, key=f"vid_src_{vmn}"):
                                vid_src_mods.append(vmn)

                st.markdown("**Generate video assets:**")
                vcols = st.columns(5)
                vid_payload_extra = {**_persona_payload()}
                if vid_mod_names:
                    vid_payload_extra["source_modules"] = vid_src_mods
                with vcols[0]:
                    if st.button("60s Script", key="vid_60s"):
                        with st.spinner("Generating..."):
                            r = api_post(f"/sessions/{session_id}/video_pipeline", {**{"action": "generate_script", "duration": "60s"}, **vid_payload_extra})
                            st.session_state["video_result"] = r
                            st.rerun()
                with vcols[1]:
                    if st.button("3min Script", key="vid_3min"):
                        with st.spinner("Generating..."):
                            r = api_post(f"/sessions/{session_id}/video_pipeline", {**{"action": "generate_script", "duration": "3min"}, **vid_payload_extra})
                            st.session_state["video_result"] = r
                            st.rerun()
                with vcols[2]:
                    if st.button("Scene List", key="vid_scenes"):
                        with st.spinner("Generating..."):
                            r = api_post(f"/sessions/{session_id}/video_pipeline", {**{"action": "generate_scenes"}, **vid_payload_extra})
                            st.session_state["video_result"] = r
                            st.rerun()
                with vcols[3]:
                    if st.button("Voiceover", key="vid_voice"):
                        with st.spinner("Generating..."):
                            r = api_post(f"/sessions/{session_id}/video_pipeline", {**{"action": "generate_voiceover"}, **vid_payload_extra})
                            st.session_state["video_result"] = r
                            st.rerun()
                with vcols[4]:
                    if st.button("SRT Captions", key="vid_srt"):
                        with st.spinner("Generating..."):
                            r = api_post(f"/sessions/{session_id}/video_pipeline", {**{"action": "generate_srt"}, **vid_payload_extra})
                            st.session_state["video_result"] = r
                            st.rerun()

                if "video_result" in st.session_state:
                    vr = st.session_state["video_result"].get("result", st.session_state["video_result"])
                    if isinstance(vr, dict):
                        vid_body_parts = []
                        for k, v in vr.items():
                            if k in ("artifact_id", "action"):
                                continue
                            if isinstance(v, str) and len(v) > 200:
                                st.text_area(k.replace("_", " ").title(), v, height=200, key=f"vr_{k}")
                                vid_body_parts.append(f"## {k.replace('_', ' ').title()}\n{v}")
                            elif isinstance(v, (dict, list)):
                                st.markdown(f"**{k.replace('_', ' ').title()}:**")
                                st.json(v)
                            else:
                                st.markdown(f"**{k.replace('_', ' ').title()}:** {v}")
                                vid_body_parts.append(f"**{k.replace('_', ' ').title()}:** {v}")
                        if st.button("Save to Archive", key="save_video_archive"):
                            api_post("/archive", {
                                "content_type": "video_script",
                                "title": "Video Script",
                                "body": "\n\n".join(vid_body_parts),
                                "meta": {},
                                "folder": "General",
                                "session_id": str(session_id),
                            })
                            st.success("Video script saved to Archive!")

            # === EXPORT ===
            elif st.session_state.get("show_action") == "export":
                st.subheader("Export")
                fmt = st.selectbox("Format", ["markdown", "json"])
                if st.button("Export Now", type="primary"):
                    result = api_post(f"/sessions/{session_id}/export", {"format": fmt, "include_pins": True})
                    content = result.get("content", "")
                    if isinstance(content, str):
                        st.download_button("Download", content, file_name=f"stackmind_export.{'md' if fmt == 'markdown' else 'json'}")
                        st.text_area("Preview", content, height=400)
                    else:
                        json_str = json.dumps(content, indent=2)
                        st.download_button("Download", json_str, file_name="stackmind_export.json")
                        st.json(content)

            # === WEBHOOK ===
            elif st.session_state.get("show_action") == "webhook":
                st.subheader("Send Webhook")
                sd = api_get(f"/sessions/{session_id}")
                art_list = sd.get("artifacts", []) if isinstance(sd, dict) else []
                art_opts = {f"{a['module_name']} ({a['id'][:8]})": a["id"] for a in art_list}
                sel_art = st.selectbox("Select Artifact", list(art_opts.keys()) if art_opts else ["No artifacts"])
                wh_url = st.text_input("Webhook URL", os.environ.get("WEBHOOK_DEFAULT_URL", ""))
                wh_channel = st.text_input("Channel", "")
                if st.button("Send", type="primary"):
                    if sel_art in art_opts:
                        result = api_post(f"/sessions/{session_id}/send_webhook", {
                            "artifact_id": art_opts[sel_art], "webhook_url": wh_url, "channel": wh_channel,
                        })
                        st.json(result)

        else:
            st.info("Set up a session using the left panel to begin analysis.")

    with col_pins:
        if "active_session" in st.session_state:
            st.subheader("Pinned Items")
            pins = api_get(f"/sessions/{st.session_state['active_session']}/pins")
            if pins:
                grouped = {}
                for p in pins:
                    t = p.get("item_type", "other")
                    grouped.setdefault(t, []).append(p)
                for gn, gi in grouped.items():
                    st.markdown(f"**{gn.replace('_', ' ').title()}**")
                    for item in gi:
                        content = item.get("content", {})
                        if isinstance(content, dict):
                            for k, v in list(content.items())[:3]:
                                if k != "citations":
                                    st.caption(f"{k}: {str(v)[:80]}")
                        if st.button("Unpin", key=f"unpin_{item['pin_id']}"):
                            api_post(f"/sessions/{st.session_state['active_session']}/unpin", {"artifact_item_id": item["artifact_item_id"]})
                            st.rerun()
                        st.markdown("---")
            else:
                st.caption("No pinned items yet.")

            st.divider()
            st.subheader("Approval Status")
            sd_ap = api_get(f"/sessions/{st.session_state['active_session']}")
            if isinstance(sd_ap, dict):
                for art in sd_ap.get("artifacts", []):
                    st.caption(f"{art['module_name']}")
                    opts = ["draft", "reviewed", "approved", "scheduled", "posted"]
                    cur = st.selectbox("Status", opts, key=f"ap_{art['id'][:8]}")
                    if st.button("Update", key=f"upd_{art['id'][:8]}"):
                        api_post(f"/sessions/{st.session_state['active_session']}/approval/update_status", {
                            "artifact_id": art["id"], "status": cur,
                        })
                        st.toast("Status updated!")

elif page == "Libraries & Upload":
    st.title("Libraries & File Management")

    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Create Library")
        with st.form("create_lib"):
            lib_name = st.text_input("Library Name")
            lib_desc = st.text_area("Description")
            if st.form_submit_button("Create Library", type="primary"):
                if lib_name:
                    result = api_post("/libraries", {"name": lib_name, "description": lib_desc})
                    if "id" in result:
                        st.success(f"Library '{lib_name}' created!")
                        st.rerun()

        st.divider()
        st.subheader("Upload Files")
        libraries = api_get("/libraries")
        if libraries:
            lib_opts = {l["name"]: l["id"] for l in libraries}
            upload_lib = st.selectbox("Target Library", list(lib_opts.keys()), key="upload_lib")
            uploaded_file = st.file_uploader(
                "Choose a file",
                type=["txt", "md", "csv", "json", "pdf", "docx", "doc", "xlsx", "xls",
                      "py", "js", "html", "xml", "yaml", "yml", "log", "rst", "tsv",
                      "wav", "mp3", "m4a", "ogg", "webm"],
                help="Supports text, Word docs, Excel, PDFs, code files, and audio"
            )
            tags_input = st.text_input("Tags (comma-separated)")
            if st.button("Upload & Process", type="primary") and uploaded_file:
                tags = [t.strip() for t in tags_input.split(",") if t.strip()] if tags_input else []
                with st.spinner("Uploading and processing..."):
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                    data = {"library_id": lib_opts[upload_lib], "tags": json.dumps(tags)}
                    result = api_post("/files/upload", data=data, files=files)
                    if result.get("status") == "embedded":
                        st.success(f"File '{uploaded_file.name}' processed successfully!")
                    elif result.get("error"):
                        st.warning(f"Uploaded with issues: {result.get('error', '')}")
                    else:
                        st.info(f"Status: {result.get('status', 'unknown')}")
                    st.rerun()

        st.divider()
        st.subheader("Paste Long Text")
        if libraries:
            paste_lib = st.selectbox("Target Library", list(lib_opts.keys()), key="paste_lib")
            paste_title = st.text_input("Title for this text", placeholder="e.g. Meeting Notes Jan 2025")
            paste_text = st.text_area("Paste your text here", height=200, placeholder="Paste long notes, articles, meeting transcripts...")
            paste_tags = st.text_input("Tags (comma-separated)", key="paste_tags")
            if st.button("Save Text to Library", type="primary") and paste_text:
                tags = [t.strip() for t in paste_tags.split(",") if t.strip()] if paste_tags else []
                with st.spinner("Processing text..."):
                    result = api_post("/files/paste", {
                        "library_id": lib_opts[paste_lib],
                        "title": paste_title or "Pasted Text",
                        "text": paste_text,
                        "tags": tags,
                    })
                    if result.get("status") == "embedded":
                        st.success("Text saved and processed!")
                    elif result.get("error"):
                        st.warning(f"Saved with issues: {result.get('error', '')}")
                    else:
                        st.info(f"Status: {result.get('status', 'unknown')}")
                    st.rerun()

        st.divider()
        st.subheader("Voice / Audio Upload")
        if libraries:
            audio_lib = st.selectbox("Target Library", list(lib_opts.keys()), key="audio_lib")
            audio_file = st.file_uploader("Upload Audio", type=["wav", "mp3", "m4a", "ogg", "webm"])
            if st.button("Upload Audio") and audio_file:
                with st.spinner("Uploading audio..."):
                    files = {"file": (audio_file.name, audio_file.getvalue())}
                    data = {"library_id": lib_opts[audio_lib], "tags": json.dumps(["audio", "transcription"])}
                    result = api_post("/files/upload", data=data, files=files)
                    if "error" in result and result["error"]:
                        st.warning(f"Upload issue: {result['error']}")
                    else:
                        st.success("Audio uploaded!")
                    st.rerun()

    with col2:
        st.subheader("Libraries")
        libraries = api_get("/libraries")
        for lib in libraries:
            with st.expander(f"{lib['name']}", expanded=True):
                st.caption(lib.get("description", ""))
                files = api_get(f"/files?library_id={lib['id']}")
                if files:
                    for f in files:
                        icons = {"embedded": "✅", "failed": "❌", "chunked": "🔄", "extracted": "📄", "uploaded": "⏳"}
                        icon = icons.get(f["status"], "❓")
                        st.markdown(f"{icon} **{f.get('display_name') or f['filename']}** — {f['status']}")
                        if f.get("tags"):
                            st.caption(f"Tags: {', '.join(f['tags'])}")
                        if f.get("error"):
                            st.error(f["error"])
                else:
                    st.caption("No files yet. Upload or paste text above.")

elif page == "Identities":
    st.title("Identity Management")

    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("Create Identity")
        with st.form("parse_identity"):
            st.markdown("**Quick Parse** -- describe a role in natural language")
            free_text = st.text_area("Describe the identity", placeholder="e.g., I'm a VP of Product at a fintech startup, focused on 90-day growth cycles...")
            if st.form_submit_button("Parse Identity"):
                with st.spinner("Parsing..."):
                    result = api_post("/identities/parse", {"free_text": free_text})
                    st.session_state["parsed_identity"] = result
                    st.rerun()

        if "parsed_identity" in st.session_state:
            st.json(st.session_state["parsed_identity"])

        st.divider()
        with st.form("create_identity"):
            st.markdown("**Manual Create**")
            id_name = st.text_input("Name")
            role_context = st.text_input("Role Context")
            time_horizon = st.selectbox("Time Horizon", ["30d", "90d", "12m", "24m", "3-5y"])
            risk_bias = st.selectbox("Risk Bias", ["low", "med", "high"])
            priority_values = st.multiselect("Priority Values", ["durability", "leverage", "clarity", "speed", "compliance"])
            tone = st.selectbox("Tone", ["direct", "analytical", "reflective", "persuasive"])
            target_audience = st.text_input("Target Audience (optional)")
            is_preset = st.checkbox("Save as Preset")

            if st.form_submit_button("Save Identity", type="primary"):
                if id_name:
                    result = api_post("/identities", {
                        "name": id_name,
                        "definition": {
                            "name": id_name, "role_context": role_context,
                            "time_horizon": time_horizon, "risk_bias": risk_bias,
                            "priority_values": priority_values, "tone": tone,
                            "target_audience": target_audience or None,
                        },
                        "is_preset": is_preset,
                    })
                    if "id" in result:
                        st.success(f"Identity '{id_name}' created!")
                        st.rerun()

    with col2:
        st.subheader("Existing Identities")
        identities = api_get("/identities")
        for i in identities:
            badge = " (Preset)" if i.get("is_preset") else ""
            with st.expander(f"{i['name']}{badge}"):
                defn = i.get("definition", {})
                st.markdown(f"**Role:** {defn.get('role_context', '')}")
                st.markdown(f"**Time Horizon:** {defn.get('time_horizon', '')}")
                st.markdown(f"**Risk Bias:** {defn.get('risk_bias', '')}")
                st.markdown(f"**Priorities:** {', '.join(defn.get('priority_values', []))}")
                st.markdown(f"**Tone:** {defn.get('tone', '')}")
                if defn.get("target_audience"):
                    st.markdown(f"**Audience:** {defn['target_audience']}")

elif page == "Audience Personas":
    st.title("Audience Personas")
    st.caption("Define your target audiences so AI tailors all content to them.")
    with st.expander("Create New Persona", expanded=False):
        p_name = st.text_input("Persona Name", placeholder="e.g., CTO at mid-stage startup")
        p_desc = st.text_area("Description", placeholder="Brief description of this audience persona")
        pcol1, pcol2 = st.columns(2)
        with pcol1:
            p_role = st.text_input("Role/Title", placeholder="e.g., CTO, VP Engineering")
            p_industry = st.text_input("Industry", placeholder="e.g., SaaS, Healthcare, Fintech")
        with pcol2:
            p_tone = st.selectbox("Preferred Tone", ["professional", "conversational", "authoritative", "casual", "technical", "inspirational"])
            p_cta = st.selectbox("CTA Style", ["direct", "soft", "question-based", "data-driven", "story-driven"])
        p_pains = st.text_input("Pain Points (comma separated)", placeholder="e.g., scaling challenges, hiring engineers, technical debt")

        if st.button("Create Persona", type="primary"):
            if p_name:
                pain_list = [x.strip() for x in p_pains.split(",") if x.strip()] if p_pains else []
                result = api_post("/personas", {
                    "name": p_name, "description": p_desc,
                    "role_title": p_role, "industry": p_industry,
                    "preferred_tone": p_tone, "preferred_cta_style": p_cta,
                    "pain_points": pain_list,
                })
                if "id" in result:
                    st.success(f"Persona '{p_name}' created!")
                    st.rerun()
                else:
                    st.error("Failed to create persona.")
            else:
                st.warning("Name is required.")

    personas = api_get("/personas")
    if personas:
        for per in personas:
            with st.container():
                st.markdown(f"""<div style="background:#1a1d24;padding:12px;border-radius:8px;margin:8px 0;border-left:3px solid #9C27B0;">
<b style="color:#9C27B0;">{per['name']}</b>
<span style="color:#888;font-size:0.85em;margin-left:12px;">{per.get('role_title', '')} | {per.get('industry', '')}</span>
<br/><span style="color:#aaa;font-size:0.85em;">{per.get('description', '')}</span>
<br/><span style="color:#666;font-size:0.8em;">Tone: {per.get('preferred_tone', '')} | CTA: {per.get('preferred_cta_style', '')}</span>
</div>""", unsafe_allow_html=True)
                pains = per.get("pain_points", [])
                if pains:
                    st.caption(f"Pain points: {', '.join(pains)}")
                if st.button("Delete", key=f"del_persona_{per['id']}"):
                    api_delete(f"/personas/{per['id']}")
                    st.rerun()
    else:
        st.info("No personas yet. Create one above to start tailoring content to specific audiences.")

elif page == "Actions & Exports":
    st.title("Actions & Approval Workflow")
    st.subheader("Approval Status Board")
    st.info("Use the Workbench to create sessions, run modules, and manage approvals from the right panel. Content moves through: Draft > Reviewed > Approved > Scheduled > Posted.")

elif page == "Content Calendar":
    st.title("Content Calendar")
    st.caption("Plan and schedule your content publishing across platforms.")

    import calendar as cal_mod
    from datetime import datetime as dt_now, timedelta

    cal_entries = api_get("/calendar") or []
    if isinstance(cal_entries, dict):
        cal_entries = []

    color_map = {
        "blue": "#4A90D9", "green": "#27AE60", "orange": "#E67E22",
        "purple": "#8E44AD", "red": "#E74C3C", "teal": "#1ABC9C",
    }
    status_icons = {"planned": "---", "scheduled": ">>>", "posted": "[OK]", "draft": "[D]"}
    platform_icons = {"LinkedIn": "in", "X/Twitter": "X", "Blog": "B", "Email": "E", "Other": "?"}

    total_entries = len(cal_entries)
    planned_count = sum(1 for e in cal_entries if e.get("status") == "planned")
    scheduled_count = sum(1 for e in cal_entries if e.get("status") == "scheduled")
    posted_count = sum(1 for e in cal_entries if e.get("status") == "posted")

    stat_cols = st.columns(4)
    stat_cols[0].metric("Total Entries", total_entries)
    stat_cols[1].metric("Planned", planned_count)
    stat_cols[2].metric("Scheduled", scheduled_count)
    stat_cols[3].metric("Posted", posted_count)

    with st.expander("Add New Entry / AI Suggestions", expanded=False):
        tab_add, tab_ai = st.tabs(["Manual Add", "AI Suggest"])
        with tab_add:
            cal_title = st.text_input("Title", key="cal_title")
            cal_cols = st.columns(4)
            with cal_cols[0]:
                cal_date = st.date_input("Date", key="cal_date")
            with cal_cols[1]:
                cal_time = st.time_input("Time", key="cal_time", value=None)
            with cal_cols[2]:
                cal_platform = st.selectbox("Platform", ["LinkedIn", "X/Twitter", "Blog", "Email", "Other"], key="cal_platform")
            with cal_cols[3]:
                cal_color = st.selectbox("Color", ["blue", "green", "orange", "purple", "red", "teal"], key="cal_color")
            cal_cols2 = st.columns(2)
            with cal_cols2[0]:
                cal_type = st.selectbox("Content Type", ["post", "blog", "deck", "email", "video_script", "twitter_thread"], key="cal_type")
            with cal_cols2[1]:
                cal_notes = st.text_input("Notes", key="cal_notes")
            if st.button("Add to Calendar"):
                if cal_title and cal_date:
                    time_str = cal_time.strftime("%H:%M") if cal_time else "09:00"
                    res = api_post("/calendar", {
                        "title": cal_title, "content_type": cal_type,
                        "scheduled_date": str(cal_date), "scheduled_time": time_str,
                        "platform": cal_platform, "notes": cal_notes, "color": cal_color,
                    })
                    if res and "id" in res:
                        st.success(f"Added: {cal_title}")
                        st.rerun()
                    else:
                        st.error("Failed to add entry")
                else:
                    st.warning("Title and date are required")

        with tab_ai:
            st.write("Get AI-powered scheduling recommendations.")
            ai_items = st.text_area("Content titles (one per line):", key="ai_sched_items", height=80)
            ai_platform = st.selectbox("Platform", ["LinkedIn", "X/Twitter", "Blog", "Mixed"], key="ai_sched_platform")
            if st.button("Get AI Suggestions", key="btn_ai_sched"):
                if ai_items.strip():
                    ai_posts = [{"title": line.strip(), "platform": ai_platform} for line in ai_items.strip().split("\n") if line.strip()]
                    with st.spinner("AI is analyzing optimal schedule..."):
                        suggestions = api_post("/calendar/ai_suggest", {"posts": ai_posts})
                    if suggestions and "suggestions" in suggestions:
                        for si, s in enumerate(suggestions["suggestions"]):
                            if isinstance(s, dict):
                                st.markdown(f"**{s.get('title', 'Item')}** - {s.get('scheduled_date', '')} at {s.get('scheduled_time', '')}")
                                if s.get("reason"):
                                    st.caption(s["reason"])
                                if st.button(f"Add", key=f"add_sug_{si}"):
                                    api_post("/calendar", {
                                        "title": s.get("title", "Suggested"),
                                        "scheduled_date": s.get("scheduled_date", ""),
                                        "scheduled_time": s.get("scheduled_time", "09:00"),
                                        "platform": ai_platform,
                                        "color": s.get("color", "blue"),
                                    })
                                    st.rerun()
                    else:
                        st.warning("No suggestions returned.")

    st.divider()

    today = dt_now.now()
    if "cal_month_offset" not in st.session_state:
        st.session_state["cal_month_offset"] = 0

    nav_cols = st.columns([1, 3, 1])
    with nav_cols[0]:
        if st.button("< Prev Month", key="cal_prev"):
            st.session_state["cal_month_offset"] -= 1
            st.rerun()
    with nav_cols[2]:
        if st.button("Next Month >", key="cal_next"):
            st.session_state["cal_month_offset"] += 1
            st.rerun()

    offset = st.session_state["cal_month_offset"]
    view_month = today.month + offset
    view_year = today.year
    while view_month > 12:
        view_month -= 12
        view_year += 1
    while view_month < 1:
        view_month += 12
        view_year -= 1

    month_str = f"{view_year}-{view_month:02d}"
    month_name = cal_mod.month_name[view_month]

    with nav_cols[1]:
        st.markdown(f"<h3 style='text-align:center;margin:0;'>{month_name} {view_year}</h3>", unsafe_allow_html=True)

    month_entries = [e for e in cal_entries if e.get("scheduled_date", "").startswith(month_str)]
    entries_by_day = {}
    for e in month_entries:
        try:
            day = int(e.get("scheduled_date", "")[-2:])
            entries_by_day.setdefault(day, []).append(e)
        except (ValueError, IndexError):
            pass

    header_cols = st.columns(7)
    for i, day_name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
        header_cols[i].markdown(f"<div style='text-align:center;font-weight:bold;color:#888;font-size:0.85em;'>{day_name}</div>", unsafe_allow_html=True)

    weeks = cal_mod.monthcalendar(view_year, view_month)
    for week in weeks:
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day == 0:
                    st.markdown("<div style='min-height:70px;'></div>", unsafe_allow_html=True)
                else:
                    day_entries = entries_by_day.get(day, [])
                    is_today = (day == today.day and view_month == today.month and view_year == today.year)
                    has_entries = len(day_entries) > 0

                    day_bg = "rgba(74,144,217,0.15)" if is_today else ("rgba(255,255,255,0.04)" if has_entries else "transparent")
                    day_border = "2px solid #4A90D9" if is_today else ("1px solid rgba(255,255,255,0.08)" if has_entries else "1px solid transparent")
                    day_label_color = "#4A90D9" if is_today else ("#fff" if has_entries else "#666")

                    entry_html = ""
                    for de in day_entries[:3]:
                        ec = color_map.get(de.get("color", "blue"), "#4A90D9")
                        plat = de.get("platform", "")[:2]
                        title_short = de.get("title", "")[:18]
                        time_short = de.get("scheduled_time", "")[:5]
                        meta = de.get("meta", {})
                        series_info = ""
                        if meta.get("series_total") and meta.get("post_number"):
                            series_info = f" ({meta['post_number']}/{meta['series_total']})"
                        entry_html += f'<div style="background:{ec}22;border-left:3px solid {ec};padding:1px 4px;border-radius:2px;font-size:0.65em;margin:1px 0;color:{ec};overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="{de.get("title","")}">{time_short} {plat} {title_short}{series_info}</div>'
                    if len(day_entries) > 3:
                        entry_html += f'<div style="font-size:0.6em;color:#888;text-align:center;">+{len(day_entries)-3} more</div>'

                    st.markdown(f"""<div style="min-height:70px;background:{day_bg};border:{day_border};border-radius:6px;padding:3px 4px;">
                        <div style="font-size:0.8em;font-weight:{'bold' if is_today else 'normal'};color:{day_label_color};margin-bottom:2px;">{day}</div>
                        {entry_html}
                    </div>""", unsafe_allow_html=True)

                    if has_entries:
                        if st.button(f"View {len(day_entries)}", key=f"cal_day_{view_year}_{view_month}_{day}", help=f"View details for {month_name} {day}"):
                            st.session_state["cal_selected_day"] = f"{view_year}-{view_month:02d}-{day:02d}"

    st.divider()

    selected_day = st.session_state.get("cal_selected_day")
    if selected_day:
        day_detail_entries = [e for e in cal_entries if e.get("scheduled_date") == selected_day]
        if day_detail_entries:
            st.subheader(f"Schedule for {selected_day}")
            for idx, entry in enumerate(day_detail_entries):
                ec = color_map.get(entry.get("color", "blue"), "#4A90D9")
                meta = entry.get("meta", {})
                series_info = ""
                if meta.get("series_total") and meta.get("post_number"):
                    series_info = f"Series {meta['post_number']} of {meta['series_total']}"

                st.markdown(f"""<div style="border-left:4px solid {ec};background:rgba(255,255,255,0.03);padding:10px 14px;border-radius:6px;margin:8px 0;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <strong style="color:{ec};font-size:1.1em;">{entry.get('title','Untitled')}</strong>
                        <span style="color:#888;font-size:0.85em;">{entry.get('scheduled_time','')}</span>
                    </div>
                    <div style="margin-top:6px;color:#aaa;font-size:0.85em;">
                        <span style="background:#ffffff10;padding:2px 8px;border-radius:12px;margin-right:8px;">{entry.get('platform','—')}</span>
                        <span style="background:#ffffff10;padding:2px 8px;border-radius:12px;margin-right:8px;">{entry.get('content_type','post')}</span>
                        <span style="background:#ffffff10;padding:2px 8px;border-radius:12px;">{entry.get('status','planned')}</span>
                        {f'<span style="margin-left:8px;color:#E67E22;">{series_info}</span>' if series_info else ''}
                    </div>
                    {f'<div style="margin-top:6px;color:#999;font-size:0.8em;">{entry.get("notes","")}</div>' if entry.get('notes') else ''}
                </div>""", unsafe_allow_html=True)
                preview_text = entry.get("content_preview", "")
                if preview_text:
                    st.caption(f"Preview: {preview_text[:150]}...")

                detail_cols = st.columns([2, 1, 1])
                with detail_cols[0]:
                    statuses = ["planned", "scheduled", "posted", "draft"]
                    cur_status = entry.get("status", "planned")
                    cur_idx = statuses.index(cur_status) if cur_status in statuses else 0
                    new_st = st.selectbox("Status", statuses, index=cur_idx, key=f"detail_st_{entry['id']}")
                    if new_st != cur_status:
                        api_patch(f"/calendar/{entry['id']}", {"status": new_st})
                        st.rerun()
                with detail_cols[2]:
                    if st.button("Delete", key=f"detail_del_{entry['id']}"):
                        api_delete(f"/calendar/{entry['id']}")
                        st.session_state.pop("cal_selected_day", None)
                        st.rerun()
        else:
            st.info(f"No entries for {selected_day}.")
    else:
        if month_entries:
            st.caption("Click 'View' on any day with entries to see full details below.")
        else:
            st.info("No entries this month. Schedule posts from the Workbench or add entries above.")

elif page == "Archive":
    st.title("Archive")
    st.caption("Everything you've saved, generated, and posted -- organized in one place.")

    stats = api_get("/archive/stats")
    if stats and isinstance(stats, dict) and stats.get("total", 0) > 0:
        stat_cols = st.columns(4)
        with stat_cols[0]:
            st.metric("Total Saved", stats.get("total", 0))
        by_type = stats.get("by_type", {})
        with stat_cols[1]:
            st.metric("Posts", by_type.get("post", 0))
        with stat_cols[2]:
            st.metric("Blogs", by_type.get("blog", 0))
        with stat_cols[3]:
            others = sum(v for k, v in by_type.items() if k not in ("post", "blog"))
            st.metric("Other", others)

    archive_tabs = st.tabs(["All", "Posts", "Blogs", "Decks", "Emails", "Video Scripts", "Exports"])

    type_filters = [None, "post", "blog", "deck", "email", "video_script", "export"]

    for tab_idx, tab in enumerate(archive_tabs):
        with tab:
            content_filter = type_filters[tab_idx]

            filter_cols = st.columns([2, 2, 1])
            with filter_cols[0]:
                folders = api_get("/archive/folders")
                folder_list = ["All Folders"] + (folders if isinstance(folders, list) else [])
                sel_folder = st.selectbox("Folder", folder_list, key=f"arch_folder_{tab_idx}")
            with filter_cols[1]:
                status_filter = st.selectbox("Status", ["All", "saved", "posted", "scheduled", "draft"], key=f"arch_status_{tab_idx}")

            params = []
            if content_filter:
                params.append(f"content_type={content_filter}")
            if sel_folder != "All Folders":
                params.append(f"folder={sel_folder}")
            if status_filter != "All":
                params.append(f"status={status_filter}")
            query_str = "?" + "&".join(params) if params else ""

            items = api_get(f"/archive{query_str}")

            if items and isinstance(items, list):
                for item in items:
                    ct = item.get("content_type", "")
                    type_icons = {"post": "📝", "blog": "📰", "deck": "📊", "email": "📧", "video_script": "🎬", "twitter_thread": "🐦", "export": "📦"}
                    icon = type_icons.get(ct, "📄")
                    status_badge = item.get("status", "saved")
                    status_colors = {"saved": "#2196F3", "posted": "#4CAF50", "scheduled": "#FF9800", "draft": "#666"}
                    badge_color = status_colors.get(status_badge, "#666")

                    with st.expander(f"{icon} {item['title']}  |  {item.get('folder', 'General')}  |  {item.get('created_at', '')[:10]}"):
                        st.markdown(f'<span style="background:{badge_color};color:white;padding:2px 8px;border-radius:10px;font-size:0.75em;">{status_badge}</span> <span style="color:#888;font-size:0.85em;">{ct.replace("_", " ").title()}</span>', unsafe_allow_html=True)
                        st.markdown("---")

                        body = item.get("body", "")
                        if len(body) > 500:
                            st.markdown(body[:500] + "...")
                            with st.expander("Show full content"):
                                st.markdown(body)
                        else:
                            st.markdown(body)

                        meta = item.get("meta", {})
                        if meta:
                            with st.expander("Details"):
                                st.json(meta)

                        act_cols = st.columns(4)
                        with act_cols[0]:
                            new_folder = st.text_input("Move to folder", value=item.get("folder", "General"), key=f"mv_{item['id']}")
                            if new_folder != item.get("folder", "General"):
                                if st.button("Move", key=f"mvbtn_{item['id']}"):
                                    api_patch(f"/archive/{item['id']}", {"folder": new_folder})
                                    st.rerun()
                        with act_cols[1]:
                            new_status = st.selectbox("Status", ["saved", "draft", "posted", "scheduled"], index=["saved", "draft", "posted", "scheduled"].index(status_badge) if status_badge in ["saved", "draft", "posted", "scheduled"] else 0, key=f"st_{item['id']}")
                            if new_status != status_badge:
                                if st.button("Update", key=f"stbtn_{item['id']}"):
                                    api_patch(f"/archive/{item['id']}", {"status": new_status})
                                    st.rerun()
                        with act_cols[2]:
                            st.download_button("Download", body, file_name=f"{item['title'][:30]}.txt", key=f"dl_{item['id']}")
                        with act_cols[3]:
                            if st.button("Delete", key=f"del_{item['id']}"):
                                api_delete(f"/archive/{item['id']}")
                                st.rerun()
            else:
                label = content_filter.replace("_", " ").title() if content_filter else "content"
                st.info(f"No {label} saved yet. Use the Workbench to generate content, then click 'Save to Archive' to store it here.")

elif page == "Diagnostics":
    st.title("Diagnostics")
    st.subheader("Recent Errors & Logs")

    diag = api_get("/diagnostics")
    if diag:
        for d in diag:
            with st.expander(f"[{d.get('level', 'error').upper()}] {d.get('module', '')} -- {d.get('created_at', '')}"):
                st.markdown(d.get("message", ""))
    else:
        st.success("No errors recorded. System is healthy.")

    st.divider()
    st.subheader("System Health")
    health = api_get("/health")
    if health:
        st.json(health)
