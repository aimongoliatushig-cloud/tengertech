{
    "name": "Municipal Procurement Workflow",
    "summary": "Project-linked procurement workflow with Mongolian mobile-first operations support",
    "version": "19.0.1.0.0",
    "category": "Project",
    "author": "OpenAI",
    "license": "LGPL-3",
    "depends": [
        "project",
        "purchase",
        "stock",
        "account",
        "mail",
        "hr",
    ],
    "data": [
        "security/municipal_procurement_groups.xml",
        "security/municipal_procurement_rules.xml",
        "security/ir.model.access.csv",
        "data/municipal_procurement_sequence.xml",
        "views/procurement_request_views.xml",
        "views/project_views.xml",
    ],
    "demo": [
        "demo/municipal_procurement_demo.xml",
    ],
    "installable": True,
    "application": True,
}
