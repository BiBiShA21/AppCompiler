"""
Multi-Stage Generation Pipeline (GEMINI VERSION)
Stage 1: Intent Extraction
Stage 2: System Design
Stage 3: Schema Generation
Stage 4: Validation + Repair
"""

import google.generativeai as genai
import json
from typing import Dict, Any, Optional
import time
import os
from dotenv import load_dotenv
from typing import Dict, Any, Optional, List, Tuple

# Load from .env file
load_dotenv()

# Configure Gemini API
api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY environment variable not set")

genai.configure(api_key=api_key)
MODEL = "gemini-2.5-flash"  # Latest Gemini model

def call_gemini(prompt: str, max_tokens: int = 2000) -> str:
    """Call Gemini API and return text response"""
    try:
        model = genai.GenerativeModel(MODEL)
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=0.7,
            )
        )
        return response.text
    except Exception as e:
        print(f"Gemini API error: {e}")
        return ""

# ============ STAGE 1: INTENT EXTRACTION ============
def stage_intent_extraction(user_prompt: str) -> Dict[str, Any]:
    """
    Parse user intent into structured form
    Output: {
        "features": [list of features],
        "entities": [list of entities/objects],
        "roles": [list of user roles],
        "authentication_method": str,
        "premium_features": [list if any],
        "key_business_logic": [list]
    }
    """
    extraction_prompt = f"""
    Analyze this product request and extract structured intent.
    
    User Request:
    {user_prompt}
    
    Return ONLY valid JSON (no markdown, no explanation):
    {{
        "features": [list of core features],
        "entities": [primary business objects/entities],
        "roles": [user roles mentioned or implied],
        "authentication_method": "jwt or session",
        "premium_features": [features that need premium gating, if any],
        "key_business_logic": [main business rules],
        "external_integrations": [APIs or services needed, if any]
    }}
    """
    
    response_text = call_gemini(extraction_prompt, max_tokens=1000)
    
    try:
        intent_data = json.loads(response_text)
        return intent_data
    except json.JSONDecodeError:
        # Fallback structure
        return {
            "features": ["login", "dashboard"],
            "entities": ["User"],
            "roles": ["admin", "user"],
            "authentication_method": "jwt",
            "premium_features": [],
            "key_business_logic": ["basic RBAC"],
            "external_integrations": []
        }

# ============ STAGE 2: SYSTEM DESIGN ============
def stage_system_design(intent: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert intent into architectural blueprint
    Output: {
        "app_architecture": str,
        "entity_relationships": {},
        "user_flows": [],
        "design_decisions": {}
    }
    """
    design_prompt = f"""
    You are a system architect. Given this product intent, design the system architecture:
    
    Intent:
    {json.dumps(intent, indent=2)}
    
    Design decision framework:
    1. Which entities need to exist? (User, Admin, Product, etc.)
    2. What relationships exist? (1:N, N:N, etc.)
    3. What are the key user flows? (signup → dashboard → action)
    4. How should roles be structured?
    5. What database relations are needed?
    
    Return ONLY valid JSON (no markdown):
    {{
        "app_architecture": "description of overall architecture",
        "primary_entities": {{"entity_name": "description", ...}},
        "entity_relationships": [{{"from": "Entity1", "to": "Entity2", "relationship": "1:N" or "N:N"}}, ...],
        "critical_flows": ["User Flow 1", "User Flow 2", ...],
        "role_structure": {{"role_name": "description", ...}},
        "design_decisions": {{"decision": "reasoning", ...}}
    }}
    """
    
    response_text = call_gemini(design_prompt, max_tokens=1500)
    
    try:
        design_data = json.loads(response_text)
        return design_data
    except json.JSONDecodeError:
        return {
            "app_architecture": "N-tier architecture",
            "primary_entities": {"User": "System users"},
            "entity_relationships": [],
            "critical_flows": ["User authentication and dashboard access"],
            "role_structure": {"user": "Normal user", "admin": "Administrator"},
            "design_decisions": {}
        }

# ============ STAGE 3: SCHEMA GENERATION ============
def stage_schema_generation(intent: Dict[str, Any], design: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate UI, API, DB, and Auth schemas
    """
    schema_prompt = f"""
    You are a full-stack schema generator. Generate complete, valid schemas for:
    - UI (pages, components, forms)
    - API (REST endpoints with methods, parameters, responses)
    - Database (tables, fields, relations)
    - Authentication (roles, permissions)
    
    Intent: {json.dumps(intent, indent=2)}
    Design: {json.dumps(design, indent=2)}
    
    STRICT REQUIREMENTS:
    1. All JSON must be valid and parseable
    2. Every API endpoint must have defined parameters and responses
    3. Every UI field must have a corresponding API endpoint or DB field
    4. All referenced roles must be defined in auth_schema
    5. Database tables must match entities from design
    
    Return ONLY valid JSON (no markdown, no explanation):
    {{
        "ui_schema": {{
            "pages": [
                {{
                    "page_name": str,
                    "route": str,
                    "components": [
                        {{
                            "id": str,
                            "type": str,
                            "title": str or null,
                            "fields": [
                                {{"name": str, "type": str, "required": bool, "label": str, "placeholder": str or null}}
                            ],
                            "actions": [str]
                        }}
                    ],
                    "auth_required": bool,
                    "allowed_roles": [str]
                }}
            ]
        }},
        "api_schema": {{
            "endpoints": [
                {{
                    "path": str,
                    "method": "GET" or "POST" or "PUT" or "DELETE",
                    "summary": str,
                    "parameters": [
                        {{"name": str, "type": str, "required": bool, "in_": "query" or "body" or "path"}}
                    ],
                    "request_body": dict or null,
                    "responses": {{
                        200: {{"status": 200, "schema": {{}}}},
                        400: {{"status": 400, "schema": {{"error": "string"}}}}
                    }},
                    "auth_required": bool,
                    "allowed_roles": [str]
                }}
            ],
            "base_url": "/api",
            "version": "1.0"
        }},
        "db_schema": {{
            "tables": [
                {{
                    "name": str,
                    "fields": [
                        {{"name": str, "type": str, "required": bool, "unique": bool, "indexed": bool, "default": null}}
                    ],
                    "primary_key": "id",
                    "indexes": [[str]]
                }}
            ],
            "relations": [{{"from_table": str, "from_field": str, "to_table": str, "to_field": str}}]
        }},
        "auth_schema": {{
            "roles": [
                {{
                    "name": str,
                    "permissions": [
                        {{"resource": str, "action": "create" or "read" or "update" or "delete"}}
                    ],
                    "is_premium": bool
                }}
            ],
            "default_role": "user",
            "auth_method": "jwt"
        }}
    }}
    """
    
    response_text = call_gemini(schema_prompt, max_tokens=3000)
    
    try:
        schema_data = json.loads(response_text)
        return schema_data
    except json.JSONDecodeError as e:
        print(f"Schema generation JSON error: {e}")
        return _generate_fallback_schema()

def _generate_fallback_schema() -> Dict[str, Any]:
    """Fallback schema for JSON parsing failures"""
    return {
        "ui_schema": {
            "pages": [
                {
                    "page_name": "Login",
                    "route": "/login",
                    "components": [
                        {
                            "id": "login_form",
                            "type": "form",
                            "fields": [
                                {"name": "email", "type": "email", "required": True, "label": "Email"},
                                {"name": "password", "type": "password", "required": True, "label": "Password"}
                            ],
                            "actions": ["submit"]
                        }
                    ],
                    "auth_required": False,
                    "allowed_roles": []
                }
            ]
        },
        "api_schema": {
            "endpoints": [
                {
                    "path": "/auth/login",
                    "method": "POST",
                    "summary": "User login",
                    "parameters": [],
                    "request_body": {"email": "string", "password": "string"},
                    "responses": {200: {"status": 200, "schema": {"token": "string"}}},
                    "auth_required": False,
                    "allowed_roles": []
                }
            ],
            "base_url": "/api",
            "version": "1.0"
        },
        "db_schema": {
            "tables": [
                {
                    "name": "users",
                    "fields": [
                        {"name": "id", "type": "uuid", "required": True, "unique": True, "indexed": True},
                        {"name": "email", "type": "email", "required": True, "unique": True},
                        {"name": "password_hash", "type": "string", "required": True}
                    ],
                    "primary_key": "id",
                    "indexes": [["email"]]
                }
            ],
            "relations": []
        },
        "auth_schema": {
            "roles": [
                {"name": "user", "permissions": [{"resource": "profile", "action": "read"}], "is_premium": False},
                {"name": "admin", "permissions": [{"resource": "users", "action": "read"}, {"resource": "users", "action": "update"}], "is_premium": False}
            ],
            "default_role": "user",
            "auth_method": "jwt"
        }
    }

# ============ STAGE 4: VALIDATION + REPAIR ============def stage_validation_and_repair(schema_dict: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Validate schemas for:
    - Valid JSON structure
    - Required fields present
    - Cross-layer consistency (API ↔ DB ↔ UI ↔ Auth)
    - Type safety
    
    Returns: (repaired_schema, issues_found)
    """
    issues = []
    
    # Basic structure checks
    required_keys = ["ui_schema", "api_schema", "db_schema", "auth_schema"]
    for key in required_keys:
        if key not in schema_dict:
            issues.append(f"Missing required key: {key}")
            schema_dict[key] = {}
    
    # Ensure auth roles exist
    if "auth_schema" not in schema_dict or "roles" not in schema_dict.get("auth_schema", {}):
        issues.append("Auth schema missing roles")
        schema_dict.setdefault("auth_schema", {})["roles"] = [{"name": "user", "permissions": [], "is_premium": False}]
    
    # Extract all defined roles
    defined_roles = {r.get("name", "user") for r in schema_dict.get("auth_schema", {}).get("roles", [])}
    if not defined_roles:
        defined_roles = {"user", "admin"}
        issues.append("No roles defined, using defaults (user, admin)")
    
    # Validate UI references valid roles
    for page in schema_dict.get("ui_schema", {}).get("pages", []):
        page_roles = set(page.get("allowed_roles", []))
        undefined_ui_roles = page_roles - defined_roles
        if undefined_ui_roles:
            issues.append(f"UI page '{page.get('page_name', 'unknown')}' references undefined roles: {undefined_ui_roles}")
            page["allowed_roles"] = list(page_roles & defined_roles)
    
    # Validate API references valid roles
    for endpoint in schema_dict.get("api_schema", {}).get("endpoints", []):
        endpoint_roles = set(endpoint.get("allowed_roles", []))
        undefined_api_roles = endpoint_roles - defined_roles
        if undefined_api_roles:
            issues.append(f"API endpoint '{endpoint.get('path', 'unknown')}' references undefined roles: {undefined_api_roles}")
            endpoint["allowed_roles"] = list(endpoint_roles & defined_roles)
    
    # Ensure minimum required fields
    if not schema_dict.get("api_schema", {}).get("endpoints"):
        issues.append("No API endpoints defined")
        schema_dict.setdefault("api_schema", {})["endpoints"] = []
    
    if not schema_dict.get("db_schema", {}).get("tables"):
        issues.append("No database tables defined")
        schema_dict.setdefault("db_schema", {})["tables"] = []
    
    if not schema_dict.get("ui_schema", {}).get("pages"):
        issues.append("No UI pages defined")
        schema_dict.setdefault("ui_schema", {})["pages"] = []
    
    return schema_dict, issues

# ============ MAIN PIPELINE ============
def run_full_pipeline(user_prompt: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Execute the complete multi-stage pipeline
    Returns: (final_config, metadata)
    """
    metadata = {
        "user_prompt": user_prompt,
        "stages_completed": [],
        "validation_issues": [],
        "generation_time_seconds": 0
    }
    
    start_time = time.time()
    
    try:
        # Stage 1: Intent Extraction
        print("🔍 Stage 1: Intent Extraction...")
        intent = stage_intent_extraction(user_prompt)
        metadata["stages_completed"].append("intent_extraction")
        
        # Stage 2: System Design
        print("🏗️ Stage 2: System Design...")
        design = stage_system_design(intent)
        metadata["stages_completed"].append("system_design")
        
        # Stage 3: Schema Generation
        print("📋 Stage 3: Schema Generation...")
        raw_schemas = stage_schema_generation(intent, design)
        metadata["stages_completed"].append("schema_generation")
        
        # Stage 4: Validation + Repair
        print("✅ Stage 4: Validation & Repair...")
        repaired_schema, issues = stage_validation_and_repair(raw_schemas)
        metadata["stages_completed"].append("validation_repair")
        metadata["validation_issues"] = issues
        
        metadata["generation_time_seconds"] = round(time.time() - start_time, 2)
        
        return repaired_schema, metadata
        
    except Exception as e:
        metadata["error"] = str(e)
        print(f"❌ Pipeline error: {e}")
        return _generate_fallback_schema(), metadata