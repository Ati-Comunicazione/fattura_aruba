from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    always_charge = fields.Boolean(
        string="Addebita sempre",
        config_parameter="huroos_riba_unsolved.always_charge",
        help="Metti la spunta se vuoi che le spese di incasso RiBa "
             "siano addebitate ad ogni fattura, altrimenti verranno addebitate una volta al mese."
    )
