# -*- coding: utf-8 -*-
# Powered by Federico Ranieri.
# Part of Huroos. See LICENSE file for full copyright and licensing details.
# © 2022 Huroos Srl. (<https://www.huroos.com>).

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools import datetime
from odoo.tools.float_utils import float_compare, float_round


class AccountMove(models.Model):
    _inherit = 'account.move'

    fatturapa_aruba_state_sdi = fields.Char(related='fatturapa_attachment_out_id.aruba_sdi_state')
    xml_generated = fields.Boolean(compute='compute_xml_generated')

    def compute_xml_generated(self):
        for x in self:
            if x.fatturapa_attachment_out_id:
                x.xml_generated = True
            else:
                x.xml_generated = False

    def get_aruba_pdf(self):
        if self.fatturapa_attachment_in_id:
            att_id = self.env['ir.attachment'].create({
                'name': str(self.id),
                'type': 'binary',
                'datas': self.fatturapa_attachment_in_id.aruba_pdf,
                #'name': '{}.pdf'.format(self.partner_id.name),
                #'datas_fname': '{}.pdf'.format(self.partner_id.name),
                'res_model': 'account.move',
                'res_id': self.id,
                'mimetype': 'application/pdf'
            })
            self.env['account.move'].browse(self.id).message_post(attachment_ids=[att_id.id])
        else:
            raise UserError("Fattura Elettronica fornitore non agganciata")

