from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def month_check(self, invoice_date_due, all_date_due):
        check = self.env['ir.config_parameter'].sudo().get_param('huroos_riba_unsolved.always_charge')
        if check == 'True':
            return False
        else:
            return super(AccountMove, self).month_check(invoice_date_due, all_date_due)
