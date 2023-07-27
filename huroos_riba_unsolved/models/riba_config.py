
from odoo import fields, models


class RibaConfiguration(models.Model):

    _inherit = "riba.configuration"
    _description = "Configuration parameters for Cash Orders"

    bank_account_id = fields.Many2one(
        "account.account",
        "A/C Bank Account",
        domain=[("internal_type", "!=", "liquidity")],
    )