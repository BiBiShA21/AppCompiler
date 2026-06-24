"""
Strict Schema Definitions for App Generation
These define the contract that all stages must respect
"""

from typing import Any, List, Dict, Optional
from pydantic import BaseModel, Field, validator
import json

# ============ UI SCHEMA ============
class UIField(BaseModel):
    name: str
    type: str  # text, email, password, number, select, checkbox, etc.
    required: bool = True
    label: str
    placeholder: Optional[str] = None
    validation: Optional[str] = None

class UIComponent(BaseModel):
    id: str
    type: str  # form, card, button, table, list, etc.
    title: Optional[str] = None
    fields: List[UIField] = []
    actions: List[str] = []  # button actions, onClick handlers

class UIPage(BaseModel):
    page_name: str
    route: str
    components: List[UIComponent]
    auth_required: bool = False
    allowed_roles: List[str] = []

class UISchema(BaseModel):
    pages: List[UIPage]
    theme: str = "default"
    
    @validator("pages")
    def pages_not_empty(cls, v):
        if not v:
            raise ValueError("Must have at least one page")
        return v

# ============ API SCHEMA ============
class APIParameter(BaseModel):
    name: str
    type: str
    required: bool
    in_: str  # query, body, path, header

class APIResponse(BaseModel):
    status: int
    schema: Dict[str, Any]

class APIEndpoint(BaseModel):
    path: str
    method: str  # GET, POST, PUT, DELETE
    summary: str
    parameters: List[APIParameter] = []
    request_body: Optional[Dict[str, Any]] = None
    responses: Dict[int, APIResponse] = {}
    auth_required: bool = False
    allowed_roles: List[str] = []

class APISchema(BaseModel):
    endpoints: List[APIEndpoint]
    base_url: str = "/api"
    version: str = "1.0"
    
    @validator("endpoints")
    def endpoints_not_empty(cls, v):
        if not v:
            raise ValueError("Must have at least one endpoint")
        return v

# ============ DATABASE SCHEMA ============
class DBField(BaseModel):
    name: str
    type: str  # string, integer, boolean, datetime, email, enum, etc.
    required: bool = True
    unique: bool = False
    indexed: bool = False
    default: Optional[Any] = None
    enum_values: Optional[List[str]] = None

class DBTable(BaseModel):
    name: str
    fields: List[DBField]
    primary_key: str = "id"
    indexes: List[List[str]] = []

class DBSchema(BaseModel):
    tables: List[DBTable]
    relations: List[Dict[str, str]] = []  # foreign keys
    
    @validator("tables")
    def tables_not_empty(cls, v):
        if not v:
            raise ValueError("Must have at least one table")
        return v

# ============ AUTH SCHEMA ============
class Permission(BaseModel):
    resource: str
    action: str  # create, read, update, delete

class Role(BaseModel):
    name: str
    permissions: List[Permission]
    is_premium: bool = False

class AuthSchema(BaseModel):
    roles: List[Role]
    default_role: str = "user"
    auth_method: str = "jwt"  # jwt, session, oauth, etc.
    
    @validator("roles")
    def has_default_role(cls, v, values):
        role_names = [r.name for r in v]
        default = values.get("default_role", "user")
        if default not in role_names:
            raise ValueError(f"Default role '{default}' not defined in roles")
        return v

# ============ COMPLETE APP CONFIG ============
class AppConfig(BaseModel):
    app_name: str
    description: str
    ui_schema: UISchema
    api_schema: APISchema
    db_schema: DBSchema
    auth_schema: AuthSchema
    features: List[str] = []
    
    def to_dict(self):
        return json.loads(self.json())


# ============ VALIDATION UTILITIES ============
def validate_config(config_dict: Dict[str, Any]) -> tuple[bool, str, Optional[AppConfig]]:
    """
    Validate a complete app config.
    Returns: (is_valid, error_message, config_object)
    """
    try:
        config = AppConfig(**config_dict)
        return True, "", config
    except Exception as e:
        return False, str(e), None


def cross_validate(config: AppConfig) -> List[str]:
    """
    Check consistency across layers:
    - API endpoints should map to DB tables
    - UI fields should match API parameters
    - Auth roles should align with UI/API access control
    Returns: List of inconsistencies (empty = valid)
    """
    issues = []
    
    # Check: All API-required roles exist in AuthSchema
    api_roles = set()
    for endpoint in config.api_schema.endpoints:
        api_roles.update(endpoint.allowed_roles)
    
    auth_roles = {r.name for r in config.auth_schema.roles}
    missing_roles = api_roles - auth_roles
    if missing_roles:
        issues.append(f"API references undefined roles: {missing_roles}")
    
    # Check: All UI pages with auth have defined roles
    ui_roles = set()
    for page in config.ui_schema.pages:
        if page.auth_required:
            ui_roles.update(page.allowed_roles)
    
    missing_ui_roles = ui_roles - auth_roles
    if missing_ui_roles:
        issues.append(f"UI pages reference undefined roles: {missing_ui_roles}")
    
    # Check: DB tables are reasonable
    table_names = {t.name for t in config.db_schema.tables}
    if not table_names:
        issues.append("No database tables defined")
    
    return issues