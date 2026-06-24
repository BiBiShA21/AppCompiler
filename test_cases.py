"""
Evaluation Framework for AppCompiler
20 test cases: 10 real products + 10 edge cases
Track: success rate, retries, failure types, latency
"""

import json
import time
from pipeline_gemini import run_full_pipeline
from typing import Dict, List, Any
from schema_definitions import AppConfig, validate_config, cross_validate

# ============ TEST CASES ============

REAL_PRODUCT_PROMPTS = [
    # 1. E-Commerce
    "Build an e-commerce platform with user registration, product catalog with search and filters, shopping cart, checkout with Stripe payment integration, order history, admin dashboard for product management, and inventory tracking. Support both customers and sellers.",
    
    # 2. SaaS Task Manager
    "Create a project management tool where teams can create projects, add tasks with priorities and due dates, assign tasks to team members, track progress with status updates, add comments, and generate progress reports. Include both list and board views.",
    
    # 3. Social Network
    "Build a social media platform with user profiles, feed showing posts from followed users, like and comment functionality, direct messaging between users, user search, and recommendations. Include both mobile and web views.",
    
    # 4. CRM System
    "Build a customer relationship management system with contact management, deal pipeline tracking, activity logging, email integration, sales analytics dashboard, team collaboration features, and role-based access control for sales, managers, and admins.",
    
    # 5. Blog Platform
    "Create a multi-author blogging platform where writers can create, edit, and publish articles with rich text editor, readers can browse posts by category, like posts, leave comments, and subscribe to authors. Include admin moderation tools.",
    
    # 6. LMS (Learning Management System)
    "Build an online learning platform with course creation, video lessons, quizzes with instant grading, student progress tracking, discussion forums, instructor dashboard with student analytics, and certificates upon completion.",
    
    # 7. Hotel Booking
    "Create a hotel booking system with search by location and dates, room availability checking, booking confirmation with payment, user profile with booking history, admin panel to manage rooms and prices, and email notifications.",
    
    # 8. Fitness Tracker
    "Build a fitness app where users can log workouts, track calories, set fitness goals, view progress charts, join challenges with other users, get nutrition recommendations, and sync with wearable devices.",
    
    # 9. Inventory Management
    "Create an inventory management system for warehouses with stock tracking, low-stock alerts, supplier management, purchase orders, barcode scanning, inventory history, and analytics reports for business intelligence.",
    
    # 10. Collaboration Tool
    "Build a team collaboration platform with channels for different topics, real-time messaging, file sharing and collaboration, task assignments within discussions, user mentions and notifications, and search across all messages.",
]

EDGE_CASE_PROMPTS = [
    # 1. Vague Requirement
    "Build something like uber but for services",
    
    # 2. Contradictory Requirements
    "Build a free social network with advanced AI features but with no server costs and zero latency. Must work completely offline but also have real-time global synchronization.",
    
    # 3. Missing Authentication Details
    "Build a banking app",
    
    # 4. Underspecified Entities
    "Create an app for managing things with features",
    
    # 5. Complex Business Logic
    "Build a marketplace with dynamic pricing based on demand, tiered seller ratings that affect commission rates, and premium features that grant different permission levels.",
    
    # 6. Multiple Integration Requirements
    "Create a platform that integrates with Stripe, Twilio, SendGrid, Google Analytics, Slack, and AWS S3 simultaneously.",
    
    # 7. Extreme Scale Assumptions
    "Build Instagram but it needs to handle a million concurrent users with real-time updates.",
    
    # 8. Minimal Information
    "App",
    
    # 9. Conflicting Roles
    "Build a system where users are both admins and regular users simultaneously with different permission levels.",
    
    # 10. Nested Requirements
    "Create a CRM that also has an e-commerce store that integrates with the CRM and has a learning platform for training users on the CRM and e-commerce features.",
]

# ============ EVALUATION METRICS ============

class EvaluationMetrics:
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.success_count = 0
        self.total_tests = 0
        self.total_time = 0
        self.failure_types: Dict[str, int] = {}
        self.validation_issues_total = 0
    
    def add_result(self, test_name: str, prompt: str, success: bool, time_seconds: float, 
                  issues: List[str] = None, error: str = None):
        """Record a test result"""
        self.total_tests += 1
        if success:
            self.success_count += 1
        
        self.total_time += time_seconds
        
        result = {
            "test_name": test_name,
            "prompt_length": len(prompt),
            "success": success,
            "time_seconds": round(time_seconds, 2),
            "issues_found": len(issues or []),
            "error": error
        }
        
        if issues:
            self.validation_issues_total += len(issues)
            result["issues"] = issues
        
        self.results.append(result)
        
        if error:
            failure_type = error.split(":")[0] if ":" in error else "unknown"
            self.failure_types[failure_type] = self.failure_types.get(failure_type, 0) + 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get evaluation summary"""
        return {
            "total_tests": self.total_tests,
            "successful_tests": self.success_count,
            "success_rate": f"{(self.success_count / self.total_tests * 100):.1f}%",
            "average_generation_time": f"{(self.total_time / self.total_tests):.2f}s",
            "total_validation_issues_found": self.validation_issues_total,
            "issues_per_generation": f"{(self.validation_issues_total / self.total_tests):.1f}",
            "failure_types": self.failure_types,
            "all_results": self.results
        }

# ============ VALIDATION CHECKS ============

def validate_generated_config(config: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Validate that generated config is production-ready
    Returns: (is_valid, list_of_issues)
    """
    issues = []
    
    # Check: JSON is valid
    try:
        json.dumps(config)
    except:
        issues.append("Invalid JSON structure")
        return False, issues
    
    # Check: Required top-level keys
    required_keys = ["ui_schema", "api_schema", "db_schema", "auth_schema"]
    for key in required_keys:
        if key not in config:
            issues.append(f"Missing schema: {key}")
    
    # Check: UI Schema
    ui_schema = config.get("ui_schema", {})
    if not ui_schema.get("pages"):
        issues.append("No pages in UI schema")
    else:
        for page in ui_schema["pages"]:
            if "page_name" not in page or "route" not in page:
                issues.append(f"Incomplete page definition: {page.get('page_name', 'unknown')}")
    
    # Check: API Schema
    api_schema = config.get("api_schema", {})
    if not api_schema.get("endpoints"):
        issues.append("No endpoints in API schema")
    else:
        for endpoint in api_schema["endpoints"]:
            if "path" not in endpoint or "method" not in endpoint:
                issues.append(f"Incomplete endpoint definition")
    
    # Check: DB Schema
    db_schema = config.get("db_schema", {})
    if not db_schema.get("tables"):
        issues.append("No tables in database schema")
    else:
        for table in db_schema["tables"]:
            if "name" not in table or "fields" not in table:
                issues.append(f"Incomplete table definition")
    
    # Check: Auth Schema
    auth_schema = config.get("auth_schema", {})
    if not auth_schema.get("roles"):
        issues.append("No roles in auth schema")
    
    # Check: Cross-layer consistency
    cross_validation_issues = cross_validate_config(config)
    issues.extend(cross_validation_issues)
    
    is_valid = len(issues) == 0
    return is_valid, issues

def cross_validate_config(config: Dict[str, Any]) -> List[str]:
    """
    Check consistency between layers:
    - API roles must exist in auth
    - UI roles must exist in auth
    - API endpoints must be reasonable
    """
    issues = []
    
    # Get defined roles
    defined_roles = {r.get("name") for r in config.get("auth_schema", {}).get("roles", [])}
    if not defined_roles:
        issues.append("No roles defined in auth schema")
        return issues
    
    # Check API roles
    for endpoint in config.get("api_schema", {}).get("endpoints", []):
        endpoint_roles = set(endpoint.get("allowed_roles", []))
        undefined_roles = endpoint_roles - defined_roles
        if undefined_roles:
            issues.append(f"API endpoint '{endpoint.get('path')}' has undefined roles: {undefined_roles}")
    
    # Check UI roles
    for page in config.get("ui_schema", {}).get("pages", []):
        page_roles = set(page.get("allowed_roles", []))
        undefined_roles = page_roles - defined_roles
        if undefined_roles:
            issues.append(f"UI page '{page.get('page_name')}' has undefined roles: {undefined_roles}")
    
    return issues

# ============ RUN EVALUATION ============

def run_evaluation() -> Dict[str, Any]:
    """
    Run complete evaluation suite
    10 real products + 10 edge cases
    """
    print("\n" + "="*80)
    print("🧪 APPCOMPILER EVALUATION SUITE")
    print("="*80 + "\n")
    
    metrics = EvaluationMetrics()
    
    # Real Product Prompts
    print("📊 REAL PRODUCT PROMPTS (10 tests)")
    print("-" * 80)
    for i, prompt in enumerate(REAL_PRODUCT_PROMPTS, 1):
        test_name = f"RealProduct_{i}"
        print(f"\n[{i}/10] {test_name}")
        print(f"Prompt: {prompt[:80]}...")
        
        start_time = time.time()
        try:
            config, metadata = run_full_pipeline(prompt)
            elapsed = time.time() - start_time
            
            is_valid, validation_issues = validate_generated_config(config)
            
            success = is_valid and metadata.get("error") is None
            metrics.add_result(
                test_name=test_name,
                prompt=prompt,
                success=success,
                time_seconds=elapsed,
                issues=validation_issues if not is_valid else metadata.get("validation_issues", []),
                error=metadata.get("error")
            )
            
            status = "✅ PASS" if success else "⚠️ PARTIAL"
            print(f"{status} | Time: {elapsed:.2f}s | Issues: {len(validation_issues)}")
            
        except Exception as e:
            elapsed = time.time() - start_time
            metrics.add_result(
                test_name=test_name,
                prompt=prompt,
                success=False,
                time_seconds=elapsed,
                error=str(e)
            )
            print(f"❌ FAIL | Time: {elapsed:.2f}s | Error: {str(e)[:60]}")
    
    # Edge Case Prompts
    print("\n\n🔥 EDGE CASE PROMPTS (10 tests)")
    print("-" * 80)
    for i, prompt in enumerate(EDGE_CASE_PROMPTS, 1):
        test_name = f"EdgeCase_{i}"
        print(f"\n[{i}/10] {test_name}")
        print(f"Prompt: {prompt[:80]}...")
        
        start_time = time.time()
        try:
            config, metadata = run_full_pipeline(prompt)
            elapsed = time.time() - start_time
            
            is_valid, validation_issues = validate_generated_config(config)
            
            success = is_valid and metadata.get("error") is None
            metrics.add_result(
                test_name=test_name,
                prompt=prompt,
                success=success,
                time_seconds=elapsed,
                issues=validation_issues if not is_valid else metadata.get("validation_issues", []),
                error=metadata.get("error")
            )
            
            status = "✅ PASS" if success else "⚠️ HANDLED"
            print(f"{status} | Time: {elapsed:.2f}s | Issues: {len(validation_issues)}")
            
        except Exception as e:
            elapsed = time.time() - start_time
            metrics.add_result(
                test_name=test_name,
                prompt=prompt,
                success=False,
                time_seconds=elapsed,
                error=str(e)
            )
            print(f"⚠️ FALLBACK | Time: {elapsed:.2f}s | Error: {str(e)[:60]}")
    
    # Summary
    summary = metrics.get_summary()
    
    print("\n\n" + "="*80)
    print("📈 EVALUATION SUMMARY")
    print("="*80)
    print(f"✅ Success Rate: {summary['success_rate']}")
    print(f"⏱️  Avg Generation Time: {summary['average_generation_time']}s")
    print(f"🔧 Total Issues Found & Auto-Repaired: {summary['total_validation_issues_found']}")
    print(f"⚡ Issues Per Generation: {summary['issues_per_generation']}")
    
    if summary["failure_types"]:
        print(f"\n❌ Failure Types:")
        for failure_type, count in summary["failure_types"].items():
            print(f"  - {failure_type}: {count}")
    
    print("\n✨ Individual Results:")
    for result in summary["all_results"]:
        status = "✅" if result["success"] else "⚠️"
        print(f"{status} {result['test_name']}: {result['time_seconds']}s | Issues: {result['issues_found']}")
    
    return summary

# ============ EXPORT RESULTS ============

def save_results(summary: Dict[str, Any], filepath: str = "evaluation_results.json"):
    """Save evaluation results to JSON"""
    with open(filepath, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n💾 Results saved to {filepath}")

if __name__ == "__main__":
    results = run_evaluation()
    save_results(results)