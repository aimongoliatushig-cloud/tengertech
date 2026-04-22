def post_init_hook(env):
    env["ops.work.unit"].sudo()._ops_run_legacy_unit_migration()
