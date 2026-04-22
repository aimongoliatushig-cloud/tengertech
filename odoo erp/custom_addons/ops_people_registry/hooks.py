def post_init_hook(env):
    env["ops.people.registry.service"].action_initialize_registry()
