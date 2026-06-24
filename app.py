"""
AppCompiler - AI-Powered App Generation System
Streamlit Web Interface
"""

import streamlit as st
import json
from pipeline_gemini import run_full_pipeline
import time

st.set_page_config(
    page_title="AppCompiler - AI App Generator",
    page_icon="🤖",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5em;
        color: #0066ff;
        font-weight: bold;
        margin-bottom: 0.5em;
    }
    .subtitle {
        font-size: 1.1em;
        color: #666;
        margin-bottom: 1.5em;
    }
    .success-box {
        background-color: #e8f5e9;
        padding: 1em;
        border-radius: 0.5em;
        border-left: 4px solid #4caf50;
    }
    .error-box {
        background-color: #ffebee;
        padding: 1em;
        border-radius: 0.5em;
        border-left: 4px solid #f44336;
    }
    .json-section {
        background-color: #f5f5f5;
        padding: 1em;
        border-radius: 0.5em;
        font-family: monospace;
        margin-top: 1em;
    }
</style>
""", unsafe_allow_html=True)

# Header
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown('<div class="main-header">🤖 AppCompiler</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Convert natural language → executable app configuration</div>', unsafe_allow_html=True)
with col2:
    st.info("⚡ Multi-stage pipeline with validation & repair")

# Sidebar
with st.sidebar:
    st.header("📚 About")
    st.markdown("""
    **AppCompiler** is a system that:
    1. Extracts intent from user prompts
    2. Designs the app architecture
    3. Generates UI, API, DB, Auth schemas
    4. Validates & repairs inconsistencies
    
    **Output:** Production-ready JSON config
    """)
    
    st.divider()
    st.header("💡 Example Prompts")
    examples = {
        "E-Commerce": "Build an e-commerce platform with user login, product catalog, shopping cart, checkout with Stripe payments, and admin dashboard to manage products and orders.",
        "Task Manager": "Create a task management app where users can create projects, add tasks with due dates, assign to team members, mark complete, and see analytics dashboard.",
        "Blog Platform": "Build a multi-author blog with user authentication, publish articles, comments, like system, and admin dashboard to moderate content."
    }
    
    selected_example = st.selectbox("Try an example:", ["---"] + list(examples.keys()))
    if selected_example != "---":
        example_prompt = examples[selected_example]
        if st.button("📋 Load Example", use_container_width=True):
            st.session_state.user_input = example_prompt

# Main Input
st.header("✍️ Describe Your App")
user_input = st.text_area(
    "What app do you want to build?",
    value=st.session_state.get("user_input", ""),
    placeholder="Example: Build a CRM with login, contacts, dashboard, role-based access, and payments...",
    height=150,
    key="user_input"
)

col1, col2, col3 = st.columns(3)
with col1:
    generate_btn = st.button("🚀 Generate Config", use_container_width=True, type="primary")
with col2:
    st.empty()
with col3:
    st.empty()

# Generation Logic
if generate_btn:
    if not user_input.strip():
        st.error("❌ Please describe your app first!")
    else:
        # Generate
        with st.spinner("⏳ Generating your app configuration..."):
            config, metadata = run_full_pipeline(user_input)
            
            # Store in session
            st.session_state.config = config
            st.session_state.metadata = metadata
            st.session_state.generated = True

# Results Display
if st.session_state.get("generated", False):
    config = st.session_state.config
    metadata = st.session_state.metadata
    
    # Metadata Section
    st.divider()
    st.header("📊 Generation Report")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Generation Time", f"{metadata.get('generation_time_seconds', 0)}s")
    with col2:
        st.metric("Stages", len(metadata.get("stages_completed", [])))
    with col3:
        issues_count = len(metadata.get("validation_issues", []))
        st.metric("Issues Found & Fixed", issues_count)
    with col4:
        stages = metadata.get("stages_completed", [])
        st.metric("Pipeline", "✅ Complete" if len(stages) == 4 else f"In Progress ({len(stages)}/4)")
    
    # Validation Issues (if any)
    if metadata.get("validation_issues"):
        st.warning("⚠️ Issues detected and auto-repaired:")
        for issue in metadata["validation_issues"]:
            st.markdown(f"- {issue}")
    
    # Schema Tabs
    st.divider()
    st.header("📋 Generated Schemas")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📱 UI", "🔌 API", "🗄️ Database", "🔐 Auth", "⚙️ Full Config"])
    
    # UI Schema
    with tab1:
        st.subheader("Pages & Components")
        ui_schema = config.get("ui_schema", {})
        if ui_schema.get("pages"):
            for page in ui_schema["pages"]:
                st.markdown(f"**Page:** `{page.get('page_name', 'Unknown')}`")
                st.markdown(f"- Route: `{page.get('route', '/')}`")
                st.markdown(f"- Auth Required: {page.get('auth_required', False)}")
                st.markdown(f"- Allowed Roles: {', '.join(page.get('allowed_roles', ['public']))}")
                st.json(page.get("components", []))
                st.divider()
        else:
            st.info("No pages generated yet")
    
    # API Schema
    with tab2:
        st.subheader("REST Endpoints")
        api_schema = config.get("api_schema", {})
        if api_schema.get("endpoints"):
            for endpoint in api_schema["endpoints"]:
                method_color = {
                    "GET": "🟢",
                    "POST": "🔵",
                    "PUT": "🟠",
                    "DELETE": "🔴"
                }
                method = endpoint.get("method", "GET")
                color = method_color.get(method, "⚫")
                
                st.markdown(f"**{color} {method}** `{endpoint.get('path', '/')}`")
                st.markdown(f"- Summary: {endpoint.get('summary', 'No description')}")
                st.markdown(f"- Auth Required: {endpoint.get('auth_required', False)}")
                
                if endpoint.get("parameters"):
                    st.markdown("- Parameters:")
                    for param in endpoint["parameters"]:
                        st.markdown(f"  - `{param.get('name')}` ({param.get('type')})")
                
                st.divider()
        else:
            st.info("No endpoints generated yet")
    
    # Database Schema
    with tab3:
        st.subheader("Database Tables")
        db_schema = config.get("db_schema", {})
        if db_schema.get("tables"):
            for table in db_schema["tables"]:
                st.markdown(f"**Table:** `{table.get('name', 'Unknown')}`")
                st.markdown(f"- Primary Key: `{table.get('primary_key', 'id')}`")
                
                if table.get("fields"):
                    st.markdown("- Fields:")
                    for field in table["fields"]:
                        required = "✓ required" if field.get("required") else "optional"
                        st.markdown(f"  - `{field.get('name')}` ({field.get('type')}) {required}")
                
                st.divider()
        else:
            st.info("No tables generated yet")
    
    # Auth Schema
    with tab4:
        st.subheader("Roles & Permissions")
        auth_schema = config.get("auth_schema", {})
        st.markdown(f"**Auth Method:** `{auth_schema.get('auth_method', 'jwt')}`")
        st.markdown(f"**Default Role:** `{auth_schema.get('default_role', 'user')}`")
        st.divider()
        
        if auth_schema.get("roles"):
            for role in auth_schema["roles"]:
                is_premium = "💎 Premium" if role.get("is_premium") else "🔓 Free"
                st.markdown(f"**{role.get('name')}** {is_premium}")
                
                if role.get("permissions"):
                    st.markdown("Permissions:")
                    for perm in role["permissions"]:
                        st.markdown(f"- {perm.get('action', 'unknown')} on `{perm.get('resource', 'unknown')}`")
                st.divider()
        else:
            st.info("No roles defined")
    
    # Full Config (JSON)
    with tab5:
        st.subheader("Complete Configuration (JSON)")
        st.json(config)
        
        # Download button
        config_json = json.dumps(config, indent=2)
        st.download_button(
            label="📥 Download Config (JSON)",
            data=config_json,
            file_name="app_config.json",
            mime="application/json",
            use_container_width=True
        )

# Footer
st.divider()
st.markdown("""
<div style="text-align: center; color: #999; font-size: 0.9em;">
💡 Built for AI Engineer Internship @ In2peta  
📧 System generates production-ready configs  
✨ Real-time validation & repair
</div>
""", unsafe_allow_html=True)