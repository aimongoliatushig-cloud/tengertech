# Odoo 19 Workspace

Odoo 19 was installed with the official Windows installer.

The installer keeps the real installation in:

`C:\Program Files\Odoo 19.0.20260415`

To make it easy to use from this folder, this workspace contains:

- `Odoo 19` -> junction to the installed Odoo directory
- `odoo_19.0.latest.exe` -> official installer that was downloaded
- `custom_addons\field-service` -> cloned from `https://github.com/OCA/field-service` branch `19.0`
- `Start Odoo 19.cmd` -> starts the Odoo service if needed and opens the browser
- `Stop Odoo 19.cmd` -> stops the Odoo service

Open Odoo in the browser:

`http://localhost:8069`

Windows services:

- `odoo-server-19.0`
- `PostgreSQL_For_Odoo`

OCA note:

- `base_territory` from the cloned `field-service` repository is linked into the Odoo user addons path.
- The `19.0` branch currently does not include the broader `fieldservice` addon set yet.

Important:

- The database manager master password is currently `admin`.
- Change that password after your first login/database setup.
