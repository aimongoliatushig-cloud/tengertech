from odoo import fields, models


class OpsPeopleSyncWizard(models.TransientModel):
    _name = "ops.people.sync.wizard"
    _description = "Ажилтан бүртгэл синк хийх wizard"

    create_missing_departments = fields.Boolean(
        string="Дутуу алба нэгж үүсгэх",
        default=True,
    )
    create_missing_jobs = fields.Boolean(
        string="Дутуу албан тушаал үүсгэх",
        default=True,
    )
    create_missing_users = fields.Boolean(
        string="Дутуу хэрэглэгч үүсгэх",
        default=False,
    )
    generate_missing_codes = fields.Boolean(
        string="Дутуу ажилтны код үүсгэх",
        default=True,
    )

    def action_run_sync(self):
        self.ensure_one()
        service = self.env["ops.people.registry.service"]
        run = service.run_registry_sync(
            rows=service._load_seed_rows(),
            source_label="Суурь утасны жагсаалт",
            create_missing_users=self.create_missing_users,
            create_missing_departments=self.create_missing_departments,
            create_missing_jobs=self.create_missing_jobs,
            generate_missing_codes=self.generate_missing_codes,
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "ops.people.audit.run",
            "res_id": run.id,
            "view_mode": "form",
        }
