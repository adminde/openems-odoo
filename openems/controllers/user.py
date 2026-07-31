from odoo import http
from odoo.http import request

class User(http.Controller):
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
        template = self.__get_template(oem)
        # set mail values
        email_values = {
            'password': password
        }
        # send mail
        template.with_context(email_values).send_mail(
            res_id=partner_id[0])
        return {}

    @classmethod
    def __get_template(cls, brand: str):
        if not brand:
            brand = cls.__get_config("edge_oem", default="openems")
        return cls.__get_oem(brand).mail_template("registration_email")

    @classmethod
    def __get_config(cls, key, default=None):
        return request.env["ir.config_parameter"].sudo().get_param(key, default=default)

    @classmethod
    def __get_oem(cls, code):
        return request.env[f"openems.oem.{code}"]
