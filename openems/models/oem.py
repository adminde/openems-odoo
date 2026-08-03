from odoo import _, models
from odoo.models import BaseModel

OEM = "openems.oem"


class Oem(models.AbstractModel):
    """Prototype for OEM brands and aggregator over the installed ones.

    A brand is an AbstractModel named "openems.oem.<code>" that inherits this
    model and declares its own '_code'. Callers reach it with
    env[f"openems.oem.{device.oem}"] - this model carries no code and is
    therefore not a brand itself.
    """
    _name = "openems.oem"
    _code = None
    _label = None
    _description = "OEM"

    def name_prefixes(self) -> dict[str, str]:
        """Device name prefix per 'openems.device.producttype' of a brand.

        The prefix carries the number a device name is counted up with, so a
        brand keeps its own numbering sequence.
        """
        return {}

    def api_key_prefixes(self) -> dict[str, str]:
        """API key prefix per 'openems.device.producttype' of a brand.

        The prefix routes the edge to a backend, so it is part of the brand
        rather than of the key generation.
        """
        return {}

    def product_types(self) -> list[tuple[str, str]]:
        """Selection values a brand contributes to 'openems.device.producttype'.

        Codes are globally unique. A brand replaces this list; calling super()
        would hand it the base product types, which a white label does not sell.
        """
        return []

    def ems_hardware(self) -> list[tuple[str, str]]:
        """Selection values a brand contributes to 'openems.device.emshardware'."""
        return []

    def mail_template(self, name: str, product_type: str | None = None) -> BaseModel | None:
        """mail.template <name> as branded for this OEM."""
        return self._ref(name)

    def report(self, name: str, product_type: str | None = None) -> BaseModel | None:
        """ir.actions.report <name> as branded for this OEM."""
        return self._ref(name)

    def _ref(self, name: str) -> BaseModel | None:
        if self._module != "openems":
            found = self.env.ref(f"{self._module}.{name}", raise_if_not_found=False)
            if found:
                return found
        return self.env.ref(f"openems.{name}")


class OpenemsOem(models.AbstractModel):
    _code = "openems"
    _name = f"openems.oem.{_code}"
    _inherit = "openems.oem"
    _description = "OpenEMS OEM"
    _label = "OpenEMS"

    def name_prefixes(self) -> dict[str, str]:
        return {
            "openems-edge": "edge",
        }

    def api_key_prefixes(self) -> dict[str, str]:
        return {
            "openems-edge": "prod",
        }

    def product_types(self) -> list[tuple[str, str]]:
        return [
            ("openems-edge", _("OpenEMS Edge")),
        ]
