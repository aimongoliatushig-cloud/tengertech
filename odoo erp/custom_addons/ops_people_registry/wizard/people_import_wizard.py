from odoo import fields, models
from odoo.exceptions import UserError


class OpsPeopleImportWizard(models.TransientModel):
    _name = "ops.people.import.wizard"
    _description = "Ажилтан бүртгэл импортлох wizard"

    data_file = fields.Binary(string="CSV файл", required=True)
    filename = fields.Char(string="Файлын нэр")
    create_missing_departments = fields.Boolean(
        string="Дутуу алба нэгж үүсгэх",
        default=True,
    )
    create_missing_jobs = fields.Boolean(
        string="Дутуу албан тушаал үүсгэх",
        default=False,
    )
    create_missing_users = fields.Boolean(
        string="Дутуу хэрэглэгч үүсгэх",
        default=False,
    )
    generate_missing_codes = fields.Boolean(
        string="Дутуу ажилтны код үүсгэх",
        default=True,
    )

    def action_import(self):
        self.ensure_one()
        if not self.data_file:
            raise UserError("Импортлох CSV файлаа оруулна уу.")
        service = self.env["ops.people.registry.service"]
        rows = service.parse_import_file(self.data_file)
        run = service.run_registry_sync(
            rows=rows,
            source_label="CSV импорт",
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
