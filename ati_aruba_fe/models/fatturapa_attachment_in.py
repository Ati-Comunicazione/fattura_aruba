# -*- coding: utf-8 -*-
# Powered by Federico Ranieri.
# Part of Huroos. See LICENSE file for full copyright and licensing details.
# © 2022 Huroos Srl. (<https://www.huroos.com>).
import base64
import datetime
import logging
import re
from time import sleep

import requests
from odoo import models, fields, api


WS_ENDPOINT_IMPORT_INVOICE = '/services/invoice/in/findByUsername'
WS_ENDPOINT_IMPORT_INVOICE_XML = '/services/invoice/in/getByFilename'


class FatturapaAttachmentIn(models.Model):
    _inherit = 'fatturapa.attachment.in'


    aruba_filename = fields.Char()
    xml_error = fields.Boolean()
    ir_attachment_id_error = fields.Many2one('ir.attachment')
    import_error_message = fields.Text()
    e_invoice_invoice_date = fields.Date()
    aruba_pdf = fields.Binary()
    company_id = fields.Many2one('res.company', string='Azienda', change_default=True, required=True,
                                 default=lambda self: self.env['res.company']._company_default_get('fatturapa.attachment.in'))


    _sql_constraints = [
        (
            "ftpa_attachment_in_name_uniq",
            "unique(att_name,aruba_filename)",
            "The name of the e-bill file must be unique!",
        )
    ]

    def import_aruba_invoice(self):
        """
        Import Aruba Supplier Invoice
        """

        ws_ids = self.env['sdi.channel'].get_default_ws()
        for ws in ws_ids:
            ws.web_auth()
            nextcall = self.env.ref('ati_aruba_fe.aruba_fe_import').nextcall

            if nextcall:
                from_date = nextcall - datetime.timedelta(days=31)
                from_date = from_date.strftime("%Y-%m-%d")

                to_date = nextcall
                to_date = to_date.strftime("%Y-%m-%d")

                page_number = 1
                header = {
                    'Authorization': 'Bearer ' + ws.web_server_token,
                }
                data = {
                    'username': ws.web_server_login,
                    'countryReceiver': 'IT',
                    'vatcodeReceiver': ws.company_id.vat.replace('IT', ''),
                    'size': 500,
                    'page': page_number,
                    'startDate': from_date,
                    'endDate': to_date
                }
                r = requests.get(ws.web_server_method_address + WS_ENDPOINT_IMPORT_INVOICE,
                                 headers=header, params=data)

                if r.status_code == 200:
                    r = r.json()
                    page_number = 1
                    total_pages = r['totalPages']
                    while page_number <= total_pages:
                        sleep(5)
                        data['page'] = page_number
                        page_number += 1
                        r = requests.get(ws.web_server_method_address + WS_ENDPOINT_IMPORT_INVOICE,
                                         headers=header, params=data)
                        if r.status_code == 200:
                            r = r.json()
                            for invoice in r['content']:
                                filename = invoice['filename']
                                invoice_id = self.search([('aruba_filename', '=', filename)])
                                if not invoice_id:
                                    # LA FATTURA MANCA, IMPORTA
                                    invoice_data = {
                                        'filename': filename,
                                        'includePdf': True,
                                    }
                                    r = requests.get(ws.web_server_method_address + WS_ENDPOINT_IMPORT_INVOICE_XML,
                                                     headers=header,
                                                     params=invoice_data).json()
                                    sleep(6)
                                    if r:
                                        # CREA LA FATTURA
                                        vals = {}
                                        if r['file']:
                                            try:
                                                receive_date = re.sub(r'([-+]\d{2}):(\d{2})(?:(\d{2}))?$', r'\1\2\3', r['creationDate'])
                                                receive_date = datetime.datetime.strptime(receive_date,'%Y-%m-%dT%H:%M:%S.%f%z')
                                                invoice_date = re.sub(r'([-+]\d{2}):(\d{2})(?:(\d{2}))?$', r'\1\2\3',r['invoices'][0]['invoiceDate'])
                                                invoice_date = datetime.datetime.strptime(invoice_date,'%Y-%m-%dT%H:%M:%S.%f%z')
                                                # Fattura Importata Correttamente
                                                vals = {
                                                    'name': r['sender']['description'] if 'description' in r['sender'] else filename,
                                                    'company_id': ws.company_id.id if ws.company_id else 1,
                                                    'aruba_filename': filename,
                                                    'datas': r['file'],
                                                    'e_invoice_received_date': receive_date.strftime('%Y-%m-%d %H:%M:%S'),
                                                    'e_invoice_invoice_date': invoice_date.strftime('%Y-%m-%d %H:%M:%S'),
                                                }
                                                if 'pdfFile' in r:
                                                    vals['aruba_pdf'] = r['pdfFile']

                                                self.env.context.update({'company_id': ws.company_id.id})
                                                self.create(vals)
                                                self.env.cr.commit()
                                                logging.info("Importata fattura elettronica")
                                            except Exception as e:
                                                self.env.cr.rollback()
                                                attachment_error = self.env['ir.attachment'].sudo().create({
                                                    'datas': r['file'],
                                                    'mimetype': 'application/xml',
                                                    'name': 'fattura.xml',
                                                    'store_fname': 'fattura.xml'
                                                })
                                                xml_string = attachment_error.get_xml_string()
                                                attachment_error.unlink()
                                                attachment_error = self.env['ir.attachment'].sudo().create({
                                                    'datas': base64.encodestring(xml_string),
                                                    'name': 'fattura.xml',
                                                    'store_fname': 'fattura.xml'
                                                })
                                                vals['ir_attachment_id_error'] = attachment_error.id
                                                vals['xml_error'] = True
                                                vals['datas'] = False
                                                vals['e_invoice_received_date'] = receive_date.strftime('%Y-%m-%d %H:%M:%S')
                                                vals['import_error_message'] = e
                                                vals['mimetype'] = 'application/xml'
                                                self.create(vals)

                                        else:
                                            vals['xml_error'] = True
                                            self.create(vals)
