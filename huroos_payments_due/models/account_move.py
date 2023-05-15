# -*- coding: utf-8 -*-
# Powered by Federico Ranieri.
# Part of Huroos. See LICENSE file for full copyright and licensing details.
# © 2022 Huroos Srl. (<https://www.huroos.com>).

from odoo import models, fields, api
from odoo.tools import datetime
from odoo.tools.float_utils import float_compare, float_round


class AccountMove(models.Model):
    _inherit = 'account.move'

    payment_due_ids = fields.One2many('payment.due.item', 'move_id')
    payment_due_html = fields.Html(compute='compute_payment_due_ids')


    @api.onchange('invoice_payment_term_id', 'invoice_date', 'invoice_date_due', 'invoice_line_ids')
    @api.depends('line_ids')
    def compute_payment_due_ids(self):

        for move in self:
            if move.line_ids:
                due_data = [(5, )]
                payment_due_html = '<table style="width:320px; min-width: 320px; max-width: 320px;">'
                if move.invoice_payment_term_id:
                    payment_terms = move.invoice_payment_term_id.compute(value=move.amount_total, date_ref=move.invoice_date, currency=move.currency_id)
                else:
                    if move.invoice_date_due:
                        payment_terms = [(move.invoice_date_due.strftime('%Y-%m-%d'), move.amount_total)]
                    else:
                        payment_terms = []

                for payment_term in payment_terms:
                    amount = round(payment_term[1], 2)

                    try:
                        date = datetime.strptime(payment_term[0], '%Y-%m-%d').date().strftime('%d-%m-%Y')
                    except Exception as e:
                        date = ''

                    if move.invoice_payment_term_id:
                        method = move.invoice_payment_term_id.fatturapa_pm_id.name if move.invoice_payment_term_id.fatturapa_pm_id else ''
                    else:
                        method = ''
                    payment_due_html += '<tr>' \
                                        '<td  width="50%" style="padding: 2px; margin: 0px; font-size: 12px; border: solid 1px #e6e6e6;">'+method+'</td>' \
                                        '<td  width="30%" style="text-align:center; padding: 2px; margin: 0px; font-size: 12px; border: solid 1px #e6e6e6;">'+str(date) +'</td>' \
                                        '<td  width="20%" style="text-align:right; padding: 2px; margin: 0px; font-size: 12px; border: solid 1px #e6e6e6;">' + str(amount) + ' ' + str(move.currency_id.symbol) +'</td>' \
                                        '</tr>'

                    move_line_id = False
                    for line in move.line_ids:
                        if line.date_maturity == payment_terms[0] \
                                and float_compare(line.amount_currency, amount, precision_digits=2) \
                                and line.account_internal_type in ['debit', 'credit']:
                            move_line_id = line

                    due_data.append((0, 0, {
                        'amount': payment_term[1],
                        'due_date': payment_term[0],
                        'fatturapa_payment_method_id': move.invoice_payment_term_id.fatturapa_pm_id.id,
                        'move_line_id': move_line_id.id if move_line_id else False
                    }))
                payment_due_html += '</table>'
                move.write({
                    'payment_due_html': payment_due_html,
                    'payment_due_ids': due_data
                })
                move.payment_due_html = payment_due_html
            else:
                move.payment_due_html = '<div>'

class WizardImportFatturapa(models.TransientModel):
    _inherit = 'wizard.import.fatturapa'

    def importFatturaPA(self):
        vals = super(WizardImportFatturapa, self).importFatturaPA()
        invoices = vals['domain'][0][2]
        for inv in invoices:
            invoice_id = self.env['account.move'].browse(inv)
            # invoice_id._onchange_invoice_date()
            invoice_id.compute_payment_due_ids()
        return vals