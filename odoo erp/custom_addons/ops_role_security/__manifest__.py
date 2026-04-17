{
    "name": "Operations Role Security",
    "summary": "Municipal operations roles, groups, and project/task permissions.",
    "version": "19.0.1.1.0",
    "category": "Tools",
    "author": "OpenAI",
    "license": "LGPL-3",
    "depends": ["project", "account", "analytic", "ops_user_type"],
    "data": [
        "security/ops_role_security.xml",
        "security/ir.model.access.csv",
        "views/project_menu_views.xml",
    ],
    "installable": True,
    "application": False,
}
