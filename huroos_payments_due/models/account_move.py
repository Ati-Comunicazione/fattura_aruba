# -*- coding: utf-8 -*-
# Powered by Federico Ranieri.
# Part of Huroos. See LICENSE file for full copyright and licensing details.
# © 2022 Huroos Srl. (<https://www.huroos.com>).

from odoo import models, fields, api
from odoo.tools.float_utils import float_compare


class AccountMove(models.Model):
    _inherit = 'account.move'

    payment_due_ids = fields.One2many(
        comodel_name='payment.due.item',
        inverse_name='move_id'
    )
    payment_due_html = fields.Html(
        compute="_compute_payment_due_html"
    )

    def write(self, vals):
        res = super(AccountMove, self).write(vals)

        try:
            self._compute_payment_due_ids()

        except Exception as ex:
            odoobot = self.env.ref('base.partner_root')
            self.message_post(
                body=f"<b>⚠ ATTENZIONE:</b><br/>Non è stato possibile creare le "
                     f"scadenze di pagamento.<br/>"
                     f"<details><summary>Eccezione</summary><code>{ex}</code></details>",
                author_id=odoobot.id
            )

        return res

    def _compute_payment_due_ids(self):
        """Calcolo delle scadenze pagamento della fattura"""

        for move in self:
            if not move.line_ids:
                move.payment_due_ids.unlink()
                continue

            move.payment_due_ids.unlink()
            payment_due_data = list()

            if move.invoice_payment_term_id:
                payment_terms = move.invoice_payment_term_id.compute(
                    value=move.amount_total,
                    date_ref=move.invoice_date,
                    currency=move.currency_id
                )
            else:
                if move.invoice_date_due:
                    payment_terms = [(move.invoice_date_due.strftime('%Y-%m-%d'), move.amount_total)]
                else:
                    payment_terms = []

            for term in payment_terms:

                amount = round(term[1], 2)

                move_line_id = False
                for line in move.line_ids:
                    if line.date_maturity == payment_terms[0] \
                            and float_compare(line.amount_currency, amount, precision_digits=2) \
                            and line.account_internal_type in ['debit', 'credit']:
                        move_line_id = line

                due_vals = {
                    'move_id': move.id,
                    'amount': term[1],
                    'due_date': term[0],
                    'fatturapa_payment_method_id': move.invoice_payment_term_id.fatturapa_pm_id.id,
                    'move_line_id': move_line_id.id if move_line_id else False
                }
                payment_due_data.append(due_vals)

            self.env['payment.due.item'].create(payment_due_data)

    @api.depends('payment_due_ids')
    def _compute_payment_due_html(self):
        """Creazione della tabella html con le varie scadenze"""

        for move in self:
            payment_due_html = '<table style="width:320px; min-width: 320px; max-width: 320px;">'

            for due in move.payment_due_ids:

                try:
                    date = due.due_date.strftime('%d-%m-%Y')
                except Exception:
                    date = ''

                payment_due_html += f"""
                                    <tr>
                                        <td width="50%" style="padding: 2px; margin: 0px; font-size: 12px; border: solid 1px #e6e6e6;">
                                            {due.fatturapa_payment_method_id.name if due.fatturapa_payment_method_id else ''}
                                        </td>
                                        <td width="30%" style="text-align:center; padding: 2px; margin: 0px; font-size: 12px; border: solid 1px #e6e6e6;">
                                            {date}
                                        </td>
                                        <td  width="20%" style="text-align:right; padding: 2px; margin: 0px; font-size: 12px; border: solid 1px #e6e6e6;">
                                            {round(due.amount, 2):.2f} {move.currency_id.symbol}
                                        </td>
                                    </tr>
                                    """

            payment_due_html += '</table>'

            move.payment_due_html = payment_due_html


class WizardImportFatturapa(models.TransientModel):
    _inherit = 'wizard.import.fatturapa'

    def importFatturaPA(self):
        vals = super(WizardImportFatturapa, self).importFatturaPA()
        invoices = vals['domain'][0][2]
        for inv in invoices:
            invoice_id = self.env['account.move'].browse(inv)
            # invoice_id._onchange_invoice_date()
            invoice_id._compute_payment_due_ids()
        return vals
