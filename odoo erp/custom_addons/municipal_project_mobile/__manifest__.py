{
    "name": "Талбайн төслийн мобайл удирдлага",
    "summary": "Хотын талбайн төсөл, тайланг мобайлаар хурдан удирдах энгийн модуль.",
    "version": "19.0.1.1.0",
    "category": "Project",
    "author": "OpenAI",
    "license": "LGPL-3",
    "depends": ["mail", "project", "web"],
    "data": [
        "security/municipal_project_mobile_groups.xml",
        "security/ir.model.access.csv",
        "security/municipal_project_mobile_rules.xml",
        "views/dashboard_views.xml",
        "views/project_project_views.xml",
        "views/project_task_views.xml",
        "views/menu_views.xml",
    ],
    "demo": [
        "demo/municipal_project_mobile_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "municipal_project_mobile/static/src/css/mobile_backend.css",
        ],
    },
    "installable": True,
    "application": True,
}
