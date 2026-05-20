from odoo import http


class AppCenter(http.Controller):

    @http.route("/openems_app_center/get_installed_apps", type="json", auth="user")
    def get_installed_apps(self, **kwargs):
        return {"installedApps": []}

    @http.route("/openems_app_center/get_possible_apps", type="json", auth="user")
    def get_possible_apps(self, **kwargs):
        return {"bundles": []}
