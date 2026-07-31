import logging
from datetime import datetime
from enum import Enum

from odoo import http
from odoo.http import request


class SumState(Enum):
    FAULT = 0
    WARNING = 1


class Message:
    sent_at: datetime
    edge_id: str
    user_logins: list[str]

    def __init__(self, sent_at: datetime, edge_id: str, user_logins: list[str]) -> None:
        self.sent_at = sent_at
        self.edge_id = edge_id
        self.user_logins = user_logins


class SumStateMessage(Message):
    state: SumState

    def __init__(
        self, sent_at: datetime, edge_id: str, user_logins: list[str], state: SumState
    ) -> None:
        super().__init__(sent_at, edge_id, user_logins)
        self.state = state


class Alerting(http.Controller):
    __logger = logging.getLogger("Alerting")
    __datetime_format = "%Y-%m-%d %H:%M:%S"

    @http.route("/openems_backend/mail/alerting_sum_state", type="json", auth="user")
    def sum_state_alerting(self, sentAt: str, params: list[dict]) -> dict:
        msgs = self.__get_sum_state_params(sentAt, params)

        if len(msgs) == 0:
            self.__logger.error(
                "Scheduled SumState-Alerting-Mail without any recipients!!!"
            )
            return {
                "status": "error",
                "message": "No recipients for sum state alerting",
            }

        template = request.env.ref("openems.alerting_sum_state")
        mails_sent = 0
        for msg in msgs:
            mails_sent += self.__send_mails(
                template, msg, self.__mark_sum_state_notified
            )

        return {"status": "success", "mails_sent": mails_sent}

    @http.route("/openems_backend/mail/alerting_offline", type="json", auth="user")
    def offline_alerting(self, sentAt: str, params: list[dict]) -> dict:
        msgs = self.__get_offline_params(sentAt, params)

        if len(msgs) == 0:
            self.__logger.error(
                "Scheduled Offline-Alerting-Mail without any recipients!!!"
            )
            return {"status": "error", "message": "No recipients for offline alerting"}

        mails_sent = 0

        for msg in msgs:
            template = self.__get_template(msg.edge_id)
            mails_sent += self.__send_mails(template, msg, self.__mark_offline_notified)

        return {"status": "success", "mails_sent": mails_sent}

    @staticmethod
    def __mark_sum_state_notified(role, at) -> None:
        role.write({"sum_state_last_notification": at})

    @staticmethod
    def __mark_offline_notified(role, at) -> None:
        role.write({"offline_last_notification": at})

    def __get_offline_params(self, sentAt, params) -> list[Message]:
        msgs = list()
        sent = datetime.strptime(sentAt, self.__datetime_format)
        for param in params:
            edge_id = param["edgeId"]
            recipients = param["recipients"]
            msgs.append(Message(sent, edge_id, recipients))
        return msgs

    def __get_sum_state_params(self, sentAt, params) -> list[SumStateMessage]:
        msgs = list()
        sent = datetime.strptime(sentAt, self.__datetime_format)
        for param in params:
            edge_id = param["edgeId"]
            recipients = param["recipients"]
            state = param["state"]
            msgs.append(SumStateMessage(sent, edge_id, recipients, state))
        return msgs

    def __get_template(self, device_id):
        oem, producttype = self.__get_device_data_for(device_id)
        match (oem.casefold(), producttype.casefold()):
            case ("openems", _):
                return request.env.ref("openems.alerting_offline")

    def __get_device_data_for(self, device_id) -> tuple[str, str]:
        if device_id:
            found_devices = http.request.env["openems.device"].search_read(
                [("name", "=", device_id)], ["producttype", "oem"]
            )
            if len(found_devices) == 1:
                device = found_devices[0]
                oem = device.get("oem") or "openems"
                producttype = device.get("producttype") or "other"
                return oem, producttype

            self.__logger.warning(
                "no device with id '%s' found, "
                "using fallback [oem=openems, producttype=other]",
                device_id,
            )
        return "openems", "other"

    def __send_mails(self, template, msg: Message, update_func) -> int:
        roles = http.request.env["openems.alerting"].search(
            [("user_login", "in", msg.user_logins), ("device_id", "=", msg.edge_id)]
        )

        if not roles or len(roles) == 0:
            self.__logger.error(
                "No AlertingSettings found for edgeId[%s] and userLogins[%s]!!!",
                msg.edge_id,
                msg.user_logins,
            )
            return 0

        mails_sent = 0
        for role in roles:
            try:
                template.send_mail(res_id=role.id)
                update_func(role, msg.sent_at)
                mails_sent += 1
            except Exception as err:
                self.__logger.error(
                    "[%s] Unable to send template[%s] to edgeUser[user=%s, edge=%s]",
                    err,
                    template.name,
                    role.id,
                    msg.edge_id,
                )
        return mails_sent
