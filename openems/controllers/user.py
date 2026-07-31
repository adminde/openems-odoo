import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

ROUTE = "/openems_backend/send_registration_email"
ROUTE_DEPRECATED = "/openems_backend/sendRegistrationEmail"


class User(http.Controller):
    @http.route([ROUTE, ROUTE_DEPRECATED], type="json", auth="user")
    def index(self, userId, password=None, oem: str = ""):
        if request.httprequest.path == ROUTE_DEPRECATED:
            _logger.warning(
                "Deprecated route %s called, use %s instead", ROUTE_DEPRECATED, ROUTE
            )
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
        template = self.__get_template(oem)
        # Passed as kwargs, not as a dict: a positional dict replaces the whole
        # context instead of extending it, dropping lang/tz for the rendering.
        template.with_context(password=password).send_mail(res_id=partner_id[0])
        return {}

    def __get_template(self, oem: str):
        template = request.env.ref("openems.registration_email")
        return template
