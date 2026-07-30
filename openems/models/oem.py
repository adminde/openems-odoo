from odoo import models
from odoo.models import BaseModel
from typing import Optional


class Oem(models.AbstractModel):
    _name = "openems.oem"
    _description = "OEM"

    def _module(self, oem: str) -> str:
        if (oem or "").casefold() != "openems":
            return oem
        return "openems"

    def _ref(self, oem: str, name: str) -> Optional[BaseModel]:
        module = self._module(oem)
        if module != "openems":
            found = self.env.ref(f"{module}.{name}", raise_if_not_found=False)
            if found:
                return found
        return self.env.ref(f"openems.{name}")

    def mail_template(self, oem: str, name: str, product_type: Optional[str] = None) -> Optional[BaseModel]:
        """mail.template <name> as branded for <oem>."""
        return self._ref(oem, name)

    def report(self, oem: str, name: str, product_type: Optional[str] = None) -> Optional[BaseModel]:
        """ir.actions.report <name> as branded for <oem>."""
        return self._ref(oem, name)
