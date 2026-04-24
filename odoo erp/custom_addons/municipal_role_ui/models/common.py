MUNICIPAL_ROLE_SELECTION = [
    ("director", "Захирал"),
    ("general_manager", "Ерөнхий менежер"),
    ("department_head", "Хэлтсийн дарга"),
    ("project_leader", "Төслийн удирдагч"),
    ("senior_master", "Ахлах мастер"),
    ("master", "Мастер"),
    ("employee", "Энгийн ажилтан"),
    ("hr", "Хүний нөөц"),
    ("accountant", "Нягтлан бодогч"),
    ("finance_officer", "Санхүүгийн ажилтан"),
    ("storekeeper", "Нярав"),
    ("office_clerk", "Бичиг хэргийн ажилтан"),
    ("contract_officer", "Гэрээний ажилтан"),
    ("garage_mechanic", "Гаражийн механик"),
    ("driver", "Жолооч"),
    ("loader", "Ачигч"),
    ("inspector", "Хяналтын ажилтан"),
    ("system_admin", "Системийн админ"),
]

ROLE_NAME_BY_CODE = dict(MUNICIPAL_ROLE_SELECTION)
ROLE_PROFILE_CODE_BY_ROLE = {
    role_code: f"municipal_role_ui.{role_code}"
    for role_code, _role_name in MUNICIPAL_ROLE_SELECTION
}

LEGACY_USER_TYPE_BY_ROLE = {
    "director": "director",
    "general_manager": "general_manager",
    "department_head": "project_manager",
    "project_leader": "project_manager",
    "senior_master": "senior_master",
    "master": "team_leader",
    "employee": "worker",
    "driver": "worker",
    "loader": "worker",
    "inspector": "worker",
    "garage_mechanic": "worker",
    "system_admin": "system_admin",
}
