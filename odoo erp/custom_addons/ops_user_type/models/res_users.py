from odoo import api, fields, models


DEFAULT_INTERNAL_USER_LANG = "mn_MN"
DEFAULT_COMPANY_NAME = "Хот тохижилт"
DEFAULT_ADMIN_NAME = "Системийн админ"
DEFAULT_GENERAL_CHANNEL_NAME = "ерөнхий"
DEFAULT_GENERAL_CHANNEL_DESCRIPTION = "Бүх ажилтанд зориулсан ерөнхий зар, мэдээлэл."
DEFAULT_WELCOME_SUBJECT = "Системд тавтай морил!"
DEFAULT_WELCOME_BODY = (
    "<p>#ерөнхий сувагт тавтай морилно уу.</p>"
    "<p>Энэ сувгаар бүх хэрэглэгч байгууллагын мэдээллийг "
    "<b>хялбар хуваалцана</b>.</p>"
)


class ResUsers(models.Model):
    _inherit = "res.users"

    ops_user_type = fields.Selection(
        selection=[
            ("system_admin", "Системийн админ"),
            ("director", "Захирал"),
            ("general_manager", "Ерөнхий менежер"),
            ("project_manager", "Хэлтсийн дарга"),
            ("senior_master", "Ахлах мастер"),
            ("team_leader", "Мастер"),
            ("worker", "Ажилтан"),
        ],
        string="Хэрэглэгчийн төрөл",
        default="worker",
        help="Хотын ажиллагааны систем дээр хэрэглэгчийг аль түвшний үүрэгтэй ажиллахыг тодорхойлно.",
    )

    @staticmethod
    def _ops_prepare_internal_user_lang(vals):
        if vals.get("share") or vals.get("lang"):
            return vals
        prepared_vals = dict(vals)
        prepared_vals["lang"] = DEFAULT_INTERNAL_USER_LANG
        return prepared_vals

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [self._ops_prepare_internal_user_lang(vals) for vals in vals_list]
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("share") is False and not vals.get("lang"):
            vals = dict(vals)
            vals["lang"] = DEFAULT_INTERNAL_USER_LANG
        return super().write(vals)

    @api.model
    def _ops_apply_mongolian_defaults(self):
        internal_users = self.sudo().with_context(active_test=False).search(
            [("share", "=", False), ("lang", "!=", DEFAULT_INTERNAL_USER_LANG)]
        )
        if internal_users:
            internal_users.write({"lang": DEFAULT_INTERNAL_USER_LANG})

        admin_user = self.env.ref("base.user_admin", raise_if_not_found=False)
        if admin_user and admin_user.name == "Administrator":
            admin_user.sudo().write({"name": DEFAULT_ADMIN_NAME})

        default_companies = self.env["res.company"].sudo().search(
            [("name", "=", "My Company")]
        )
        if default_companies:
            default_companies.write({"name": DEFAULT_COMPANY_NAME})

        general_channel = False
        if "discuss.channel" in self.env or "mail.channel" in self.env:
            general_channel = self.env.ref(
                "mail.channel_all_employees", raise_if_not_found=False
            )
        if general_channel:
            channel_vals = {}
            if general_channel.name == "general":
                channel_vals["name"] = DEFAULT_GENERAL_CHANNEL_NAME
            if general_channel.description == "General announcements for all employees.":
                channel_vals["description"] = DEFAULT_GENERAL_CHANNEL_DESCRIPTION
            if channel_vals:
                general_channel.sudo().write(channel_vals)

        welcome_message = False
        if "mail.message" in self.env:
            welcome_message = self.env.ref(
                "mail.module_install_notification", raise_if_not_found=False
            )
        if welcome_message:
            message_vals = {}
            if welcome_message.subject == "Welcome to Odoo!":
                message_vals["subject"] = DEFAULT_WELCOME_SUBJECT
            if "Welcome to the #general channel." in (welcome_message.body or ""):
                message_vals["body"] = DEFAULT_WELCOME_BODY
            if message_vals:
                welcome_message.sudo().write(message_vals)

        return True
