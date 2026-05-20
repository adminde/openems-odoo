import json
import logging
from odoo import http
from odoo.http import request


class User(http.Controller):
    __logger = logging.getLogger(__name__)

    @http.route("/openems_backend/sendRegistrationEmail", type="json", auth="user")
    def index(self, userId, password=None, oem: str = ''):
        user_model = request.env["res.users"]
        user_record = user_model.search_read([("id", "=", userId)], ["partner_id"])
        if len(user_record) != 1:
            raise ValueError("User not found for id [" + userId + "]")

        partner = user_record[0]
        partner_id = partner.get("partner_id")
        if partner_id is None:
            raise ValueError("User has no partner")

        if password is None:
            password = "*****"
        # load template
        template = self.getTemplate(oem)
        # set mail values
        email_values = {
            'password': password
        }
        # send mail
        template.with_context(email_values).send_mail(
            res_id=partner_id[0])
        return {}

    @http.route("/openems_backend/set_user_settings", type="json", auth="user")
    def set_user_settings(self, userId, settings):
        user = request.env["res.users"].search([("login", "=", userId)], limit=1)
        if not user:
            self.__logger.warning("Unable to set settings for userId=%s", userId)
            return {"status": "error", "message": f"Unable to set settings for userId={userId}"}

        _settings = {}
        if user.settings:
            try:
                _settings = json.loads(user.settings)
            except (json.JSONDecodeError, TypeError):
                self.__logger.warning("Invalid existing settings JSON for userId=%s, overwriting", userId)

        _settings.update(settings)
        user.write({"settings": json.dumps(_settings)})
        return {"status": "success", "settings": _settings}

    def getTemplate(self, oem: str):
        template = request.env.ref("openems.registration_email")
        return template
