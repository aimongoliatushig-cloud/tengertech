# -*- coding: utf-8 -*-
{
    "name": "Operations Stage Colors",
    "summary": "Adds custom kanban colors for municipal project stages",
    "version": "19.0.1.2.0",
    "category": "Project",
    "author": "OpenAI",
    "license": "LGPL-3",
    "depends": ["project", "web"],
    "assets": {
        "web.assets_backend": [
            "ops_stage_colors/static/src/js/kanban_stage_color_patch.js",
            "ops_stage_colors/static/src/js/project_task_state_patch.js",
            "ops_stage_colors/static/src/scss/kanban_stage_colors.scss",
            "ops_stage_colors/static/src/xml/project_task_state_patch.xml",
        ],
    },
    "installable": True,
    "application": False,
}
