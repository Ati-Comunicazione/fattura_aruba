# -*- coding: utf-8 -*-
# Copyright 2019 Federico Ranieri (<http://www.huroos.it>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, api


class SendAruba(models.TransientModel):
    _name = 'wizard.fatturapa.send.aruba'
    _description = "Wizard to send multiple e-invoice ARUBA"

    def send_aruba(self):
        if self.env.context.get('active_ids'):
            einvoice_ids = self.env['fatturapa.attachment.out'].browse(self.env.context.get('active_ids'))
            for einvoice in einvoice_ids:
                if not einvoice.aruba_sent:
                    einvoice.send_to_aruba()