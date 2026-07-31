from odoo import _, models
from odoo.models import BaseModel
from typing import List, Optional, Tuple

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


    def product_types(self) -> List[Tuple[str, str]]:
        """Selection values a brand contributes to 'openems.device.producttype'.

        Codes are globally unique. A brand replaces this list; calling super()
        would hand it the base product types, which a white label does not sell.
        """
        return []

    def ems_hardware(self) -> List[Tuple[str, str]]:
        """Selection values a brand contributes to 'openems.device.emshardware'."""
        return []

    def mail_template(self, name: str, product_type: Optional[str] = None) -> Optional[BaseModel]:
        """mail.template <name> as branded for this OEM."""
        return self._ref(name)

    def report(self, name: str, product_type: Optional[str] = None) -> Optional[BaseModel]:
        """ir.actions.report <name> as branded for this OEM."""
        return self._ref(name)

    def _ref(self, name: str) -> Optional[BaseModel]:
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

    def product_types(self) -> List[Tuple[str, str]]:
        return [
            ("openems-edge", _("OpenEMS Edge")),
        ]
