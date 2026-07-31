from odoo import http


class OpenemsBackend(http.Controller):
    # Sort keys the OpenEMS Backend may send, mapped onto device fields.
    __ORDER_FIELDS = {
        "id": "name_number",
        "comment": "comment",
        "sumState": "openems_sum_state_level",
    }

    @classmethod
    def __order_clause(cls, search_params) -> str:
        if not search_params or not search_params.get("orderState"):
            return ""
        parts = []
        for item in search_params.get("orderState"):
            field = cls.__ORDER_FIELDS.get(item["field"])
            if not field:
                raise ValueError(f"{item['field']} is not supported")
            parts.append(f"{field} {item['sortOrder']}")
        return ",".join(parts)

    @staticmethod
    def __filter_domains(search_params) -> list:
        domains = []
        if not search_params:
            return domains
        if search_params.get("producttype"):
            domains.append(("producttype", "in", search_params.get("producttype")))
        if search_params.get("sumState"):
            sum_states = [state.lower() for state in search_params.get("sumState")]
            domains.append(("openems_sum_state_level", "in", sum_states))
        if "isOnline" in search_params:
            domains.append(("openems_is_connected", "=", search_params.get("isOnline")))
        return domains

    def __search_domain(self, query, search_params) -> list:
        query_domains = []
        operators = []
        if query:
            operators.extend(["|", "|"])
            query_domains = [
                ("name", "ilike", query),
                ("comment", "ilike", query),
                ("producttype", "ilike", query),
            ]

        additional_domains = self.__filter_domains(search_params)
        if len(additional_domains) > 1:
            for _ in range(len(additional_domains) - 1):
                operators.insert(0, "&")

        # insert 'and' if both are not 'None'
        if query and search_params:
            operators.insert(0, "&")

        query_domains.extend(additional_domains)
        operators.extend(query_domains)
        return operators

    @http.route("/openems_backend/info", auth="user", type="json")
    def index(self, external_uid):
        # Get user
        res_users = http.request.env["res.users"].sudo()
        user_rec = res_users.search_read(
            [("oauth_uid", "=", external_uid)],
            [
                "login",
                "name",
                "groups_id",
                "global_role",
                "openems_language",
                "settings",
            ],
        )[0]

        # Get res group model
        res_groups_model = http.request.env["res.groups"].sudo()

        # Get Manager and Reader group
        manager_group = res_groups_model.env.ref("openems.group_openems_manager")
        reader_group = res_groups_model.env.ref("openems.group_openems_reader")

        manager_group_id = manager_group["id"]
        reader_group_id = reader_group["id"]

        settings = user_rec["settings"] if user_rec.get("settings") else {}

        # Get user attributes
        global_role = user_rec["global_role"]
        if manager_group_id in user_rec["groups_id"]:
            # Manager group
            global_role = "admin"

        has_multiple_edges = False
        if (
            manager_group_id in user_rec["groups_id"]
            or reader_group_id in user_rec["groups_id"]
        ):
            has_multiple_edges = True
        else:
            device_user_role_model = http.request.env["openems.device_user_role"]
            user_role_ids = device_user_role_model.search_read(
                [("user_id", "=", user_rec["id"])], ["id"], limit=2
            )
            has_multiple_edges = len(user_role_ids) > 1

        return {
            "user": {
                "id": user_rec["id"],
                "login": user_rec["login"],
                "name": user_rec["name"],
                "global_role": global_role,
                "language": user_rec["openems_language"],
                "has_multiple_edges": has_multiple_edges,
                "settings": settings,
            },
            "devices": [],
        }

    @http.route("/openems_backend/get_edge_with_role", auth="user", type="json")
    def get_edge_with_role(self, external_uid, edge_id: str):
        res_users = http.request.env["res.users"].sudo()
        user_rec = res_users.search_read(
            [("oauth_uid", "=", external_uid)],
            ["login", "name", "groups_id"],
        )[0]

        # Get res group model
        res_groups_model = http.request.env["res.groups"].sudo()

        # Get Manager and Reader group
        manager_group = res_groups_model.env.ref("openems.group_openems_manager")
        reader_group = res_groups_model.env.ref("openems.group_openems_reader")

        manager_group_id = manager_group["id"]
        reader_group_id = reader_group["id"]

        # get devices for which the user has permissions
        device_model = http.request.env["openems.device"]
        devices = device_model.with_user(user_rec["id"]).search_read(
            [("name", "=", edge_id)],
            [
                "id",
                "name",
                "comment",
                "producttype",
                "lastmessage",
                "first_setup_protocol_date",
                "openems_sum_state_level",
                "settings",
            ],
        )

        if len(devices) != 1:
            return {}

        device = devices[0]

        # Get specific Device roles
        device_user_role_model = http.request.env["openems.device_user_role"]
        device_user_roles = device_user_role_model.search_read(
            [("user_id", "=", user_rec["id"]), ("device_id", "=", device["id"])],
            ["id", "role"],
        )

        # Set user role per group
        role = "guest"
        if manager_group_id in user_rec["groups_id"]:
            # Manager group
            role = "admin"
        elif reader_group_id in user_rec["groups_id"]:
            # Reader group
            role = "guest"

        # Set specific user role
        if len(device_user_roles) > 0:
            role = device_user_roles[0]["role"]

        dev = {
            "id": device["id"],
            "name": device["name"],
            "comment": device["comment"],
            "producttype": device["producttype"],
            "role": role,
            "lastmessage": device["lastmessage"],
            "openems_sum_state_level": device["openems_sum_state_level"],
        }
        if device.get("settings"):
            dev["settings"] = device["settings"]

        if device["first_setup_protocol_date"]:
            dev["first_setup_protocol_date"] = device["first_setup_protocol_date"]

        return dev

    @http.route("/openems_backend/get_edges", auth="user", type="json")
    def get_edges(self, external_uid, limit, page, query=None, searchParams=None):
        # Get user
        res_users = http.request.env["res.users"].sudo()
        user_rec = res_users.search_read(
            [("oauth_uid", "=", external_uid)],
            ["login", "name", "groups_id", "global_role"],
        )[0]

        # Get res group model
        res_groups_model = http.request.env["res.groups"].sudo()

        # Get Manager and Reader group
        manager_group = res_groups_model.env.ref("openems.group_openems_manager")
        reader_group = res_groups_model.env.ref("openems.group_openems_reader")

        manager_group_id = manager_group["id"]
        reader_group_id = reader_group["id"]

        # Get specific Device roles
        device_user_role_model = http.request.env["openems.device_user_role"]
        user_role_ids = device_user_role_model.search_read(
            [("user_id", "=", user_rec["id"])], ["id", "role"]
        )

        logical_operators = self.__search_domain(query, searchParams)
        order = self.__order_clause(searchParams)

        # Get Devices
        device_model = http.request.env["openems.device"]
        devices = device_model.with_user(user_rec["id"]).search_read(
            logical_operators,
            [
                "id",
                "name",
                "user_role_ids",
                "comment",
                "producttype",
                "lastmessage",
                "first_setup_protocol_date",
                "openems_sum_state_level",
                "settings",
            ],
            order=order,
            limit=limit,
            offset=(page * limit),
        )
        devs = []
        for device_rec in devices:
            # Set user role per group
            role = "guest"
            if manager_group_id in user_rec["groups_id"]:
                # Manager group
                role = "admin"
            elif reader_group_id in user_rec["groups_id"]:
                # Reader group
                role = "guest"

            # Set specific user role
            for device_role_id in device_rec["user_role_ids"]:
                for user_role_id in user_role_ids:
                    if device_role_id == user_role_id["id"]:
                        role = user_role_id["role"]

            # Prepare result
            dev = {
                "id": device_rec["id"],
                "name": device_rec["name"],
                "comment": device_rec["comment"],
                "producttype": device_rec["producttype"],
                "role": role,
                "lastmessage": device_rec["lastmessage"],
                "openems_sum_state_level": device_rec["openems_sum_state_level"],
            }

            if device_rec.get("settings"):
                dev["settings"] = device_rec["settings"]

            if device_rec["first_setup_protocol_date"]:
                dev["first_setup_protocol_date"] = device_rec[
                    "first_setup_protocol_date"
                ]

            devs.append(dev)

        return {
            "devices": devs,
        }
