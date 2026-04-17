{
    "name": "Operations Field Reporting",
    "summary": "Task-level field reports with text, images, and audio.",
    "version": "19.0.1.6.0",
    "category": "Project",
    "author": "OpenAI",
    "license": "LGPL-3",
    "depends": ["project", "ops_role_security", "ops_team_assignment"],
    "data": [
        "security/ops_task_report_security.xml",
        "security/ir.model.access.csv",
        "views/project_task_views.xml",
    ],
    "installable": True,
    "application": False,
}
