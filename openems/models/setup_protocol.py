from odoo import fields, models


class SetupProtocol(models.Model):
    _name = "openems.setup_protocol"
    _description = "OpenEMS Edge Setup Protocols (IBN)"
    _order = "create_date desc"

    customer_id = fields.Many2one("res.partner", "Customer")
    different_location_id = fields.Many2one("res.partner", "Different Location")
    installer_id = fields.Many2one("res.partner", "Installer")
    device_id = fields.Many2one("openems.device", "OpenEMS Edge", required=True)
    productionlot_ids = fields.One2many(
        "openems.setup_protocol_production_lot", "setup_protocol_id", "Serial Numbers"
    )
    item_ids = fields.One2many(
        "openems.setup_protocol_item", "setup_protocol_id", "Entry Items"
    )
    type = fields.Selection(
        [
            ("setup-protocol", "Setup protocol"),
            ("ems-exchange", "EMS exchange"),
            ("capacity-extension", "Capacity extension"),
        ],
        "Type",
        default="setup-protocol",
    )

    def action_print_setup_protocol(self):
        # Resolved per record rather than bound in the view, so the printed
        # layout follows the device's OEM.
        self.ensure_one()
        report = self.__get_report(
            self.device_id.oem,
            self.device_id.producttype,
            "action_setup_protocol_report",
        )
        return report.report_action(self)

    def __get_report(self, brand, product_type: str, name: str):
        if not brand:
            brand = self.__get_config("edge_oem", default="openems")
        oem = self.__get_oem(brand)
        return oem.report(name, product_type)

    def __get_config(self, key, default=None):
        return self.env["ir.config_parameter"].sudo().get_param(key, default=default)

    def __get_oem(self, code):
        return self.env[f"openems.oem.{code}"]


class SetupProtocolProductionLot(models.Model):
    _name = "openems.setup_protocol_production_lot"
    _description = "OpenEMS Edge Setup Protocol Serial Number"
    _order = "setup_protocol_id, category, sequence asc"

    sequence = fields.Integer("Sort")
    category = fields.Char("Category")
    name = fields.Char("Name")
    lot_id = fields.Many2one("stock.production.lot", "Serial Number")
    setup_protocol_id = fields.Many2one(
        "openems.setup_protocol", "Setup Protocol", ondelete="cascade"
    )


class SetupProtocolItem(models.Model):
    _name = "openems.setup_protocol_item"
    _description = "OpenEMS Edge Setup Protocol Entry Item"
    _order = "setup_protocol_id, category, sequence asc"

    sequence = fields.Integer("Sort")
    category = fields.Char("Category")
    name = fields.Char("Name")
    value = fields.Char("Value")
    setup_protocol_id = fields.Many2one(
        "openems.setup_protocol", "Setup Protocol", ondelete="cascade"
    )
    view = fields.Char("View Identifier")
    field = fields.Char("Field Identifier")

