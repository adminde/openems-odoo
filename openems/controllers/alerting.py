import logging
from datetime import  datetime
from enum import Enum

from odoo import http
from odoo.http import request
from typing import Optional, Tuple


class SumState(Enum):
    FAULT = 0
    WARNING = 1

class Message:
    sentAt: datetime
    edgeId: str
    userLogins: list[str]

    def __init__(self, sentAt: datetime, edgeId: str, userLogins : list[str]) -> None:
        self.sentAt = sentAt
        self.edgeId = edgeId
        self.userLogins = userLogins

class SumStateMessage(Message):
    state: SumState

    def __init__(self, sentAt: datetime, edgeId: str, userLogins: list[str], state: SumState) -> None:
        super().__init__(sentAt, edgeId, userLogins)
        self.state = state

class Alerting(http.Controller):
    __logger = logging.getLogger("Alerting")
    __datetime_format = "%Y-%m-%d %H:%M:%S"

    @http.route("/openems_backend/mail/alerting_sum_state", type="json", auth="user")
    def sum_state_alerting(self, sentAt: str, params: list[dict]) -> dict:
        msgs = self.__get_sum_state_params(sentAt, params)
        update_func = lambda role, at: { role.write({"sum_state_last_notification": at})}

        if len(msgs) == 0:
            self.__logger.error("Scheduled SumState-Alerting-Mail without any recipients!!!")
            return {"status": "error", "message": "No recipients for sum state alerting"}

        mails_sent = 0
        for msg in msgs:
            template = self.__get_template(msg.edgeId, "alerting_sum_state")
            mails_sent += self.__send_mails(template, msg, update_func)

        return {"status": "success", "mails_sent": mails_sent}

    @http.route("/openems_backend/mail/alerting_offline", type="json", auth="user")
    def offline_alerting(self, sentAt: str, params: list[dict]) -> dict:
        msgs = self.__get_offline_params(sentAt, params)
        update_func = lambda role, at: { role.write({"offline_last_notification": at})}

        if len(msgs) == 0:
            self.__logger.error("Scheduled Offline-Alerting-Mail without any recipients!!!")
            return {"status": "error", "message": "No recipients for offline alerting"}

        mails_sent = 0

        for msg in msgs:
            template = self.__get_template(msg.edgeId, "alerting_offline")
            mails_sent += self.__send_mails(template, msg, update_func)

        return {"status": "success", "mails_sent": mails_sent}

    def __get_offline_params(self, sentAt, params) -> list[Message]:
        msgs = list()
        sent = datetime.strptime(sentAt, self.__datetime_format)
        for param in params:
            edgeId = param["edgeId"]
            recipients = param["recipients"]
            msgs.append(Message(sent, edgeId, recipients));
        return msgs

    def __get_sum_state_params(self, sentAt, params) -> list[SumStateMessage]:
        msgs = list()
        sent = datetime.strptime(sentAt, self.__datetime_format)
        for param in params:
            edgeId = param["edgeId"]
            recipients = param["recipients"]
            state = param["state"]
            msgs.append(SumStateMessage(sent, edgeId, recipients, state));
        return msgs

    def __get_template(self, device_id, name: str):
        brand, product_type = self.__get_device_data(device_id)
        if not brand:
            brand = self.__get_config("edge_oem", default="openems")
        oem = self.__get_oem(brand)
        return oem.mail_template(name, product_type)

    @staticmethod
    def __get_config(key, default=None):
        return request.env["ir.config_parameter"].sudo().get_param(key, default=default)

    @staticmethod
    def __get_oem(code):
        return request.env[f"openems.oem.{code}"]

    def __get_device_data(self, device_id) -> Tuple[Optional[str], Optional[str]]:
        if device_id:
            device = http.request.env["openems.device"].search_read(
                [("name", "=", device_id)], ["oem", "producttype"]
            )
            if len(device) > 0:
                return device[0]["oem"], device[0].get("producttype") or None
            self.__logger.warning(
                f"No device with id '{device_id}' found, using fallback oem"
            )
        return None, None

    def __send_mails(self, template, msg: Message, update_func) -> int:
        roles = http.request.env['openems.alerting'].search(
            [('user_login','in', msg.userLogins),('device_id','=', msg.edgeId)]
        )

        if not roles or len(roles) == 0:
            self.__logger.error(f"No AlertingSettings found for edgeId[{msg.edgeId}] and userLogins[{msg.userLogins}]!!!")
            return 0

        mails_sent = 0
        for role in roles:
            try:
                template.send_mail(res_id=role.id)
                update_func(role, msg.sentAt)
                mails_sent += 1
            except Exception as err:
                template_name = getattr(template, 'name', template)
                self.__logger.error(f"[{err}] Unable to send template[{template_name}] to edgeUser[user={role.id}, edge={msg.edgeId}]")
        return mails_sent
