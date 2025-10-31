"""
Route registration - combines all modular route files
"""
from routes.design_routes import register_design_routes
from routes.version_routes import register_version_routes
from routes.file_routes import register_file_routes
from routes.project_routes import register_project_routes
from routes.slicer_routes import register_slicer_routes


def register_routes(app, modifier_ref, llm, version_counter_ref):
    """Register all Flask routes from modular files
    
    Args:
        app: Flask app instance
        modifier_ref: Dict with 'current' key holding DesignModifier instance
        llm: LLMHandler instance
        version_counter_ref: Dict with 'current' key holding version counter (legacy, not used)
    """
    
    # Register each route module
    register_design_routes(app, modifier_ref, llm)
    register_version_routes(app, modifier_ref)
    register_file_routes(app, modifier_ref)
    register_project_routes(app, modifier_ref)
    register_slicer_routes(app, modifier_ref)
    
    print("✅ All routes registered successfully")
