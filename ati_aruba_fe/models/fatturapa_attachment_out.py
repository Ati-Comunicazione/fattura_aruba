# -*- coding: utf-8 -*-
# Powered by Federico Ranieri.
# Part of Huroos. See LICENSE file for full copyright and licensing details.
# © 2022 Huroos Srl. (<https://www.huroos.com>).
import base64
import datetime
import json
import logging
import re
from time import sleep

import requests
from odoo import models, fields, api, _
import xml.etree.ElementTree as ET
from lxml import etree

from odoo.exceptions import UserError

WS_ENDPOINT_NOTIFICATION_FILENAME = '/services/invoice/out/getByFilename'
WS_ENDPOINT_NOTIFICATION_USERNAME = '/services/invoice/out/findByUsername'
WS_ENDPOINT_NOTIFICATION_FILENAME_CORRECT = '/services/notification/out/getByInvoiceFilename'
WS_ENDPOINT_UPLOAD_INVOICE = '/services/invoice/upload'

#Elenco degli Stati SDI che indicano che la fattura è in stato "Chiusa"
#Questi stati verranno saltati nelle successive richieste di Aggiornamento SDI
SDI_COMPLETED = [
    ('Consegnata', 'Consegnata'),
    ('Non Consegnata', 'Non Consegnata'),
    ('Non consegnata', 'Non Consegnata'), #Minuscolo anche per bug di Aruba
]

ERROR_CODE = [
    ('0000', 'OK'),
    ('0001', 'Errore Generico'),
    ('0002', 'Errore parametri in input mancanti o non validi'),
    ('0012', 'Errore Autenticazione'),
    ('0013', 'Si è verificato un errore in fase di registrazione della richiesta'),
    ('0018', 'Errore validazione firma fattura elettronica inviata, il file non risulta firmato'),
    ('0033', 'Il file fattura elettronica inviato supera la dimensione massima accettata'),
    ('0034', 'File già inviato di recente'),
    ('0071', 'Errore in fase di verifica nome file per utente'),
    ('0072', 'Errore in fase di caricamento lista fatture per utente'),
    ('0082', 'Si è verificato un errore in fase di recupero notifiche'),
    ('0092', 'Errore generico schema xsd'),
    ('0093', 'Errore deleghe non valide'),
    ('0094', 'La fattura che stai inviando contiene ID e/o contatti dei trasmittenti differenti dai dati dell’intermediario Aruba PEC.'),
    ('0095', 'Servizio momentaneamente non disponibile. Il controllo dei permessi è fallito. Si prega di riprovare più tardi.'),
    ('0096', 'Errore Non Mappato'),
    ('0097', 'Spazio esaurito o non sufficiente, è necessario effettuare un aumento di spazio.'),
]

class FatturapaAttachmentOut(models.Model):
    _inherit = 'fatturapa.attachment.out'

    aruba_upload_filename = fields.Char()
    aruba_error_code = fields.Selection(selection=ERROR_CODE)
    aruba_sdi_state = fields.Char()
    aruba_error_description = fields.Text()
    aruba_sent = fields.Boolean()
    sdi_notification_ids = fields.One2many('sdi.notification', 'attachment_out_id')


    def unlink(self):
        for attachment_out in self:
            for invoice in attachment_out.out_invoice_ids:
                invoice.fatturapa_doc_attachments.filtered("is_pdf_invoice_print").unlink()
            #Notifica PEC
            if attachment_out.state != 'ready':
                attachment_out.state = 'ready'
        r = super(FatturapaAttachmentOut, self).unlink()
        #return r


    def send_to_aruba(self):
        """
        Invia il documento XML al ws di ARUBA
        """
        ws_ids = self.env['sdi.channel'].get_default_ws()
        if not ws_ids:
            raise UserWarning("Non e' stata trovata la configurazione Default di Aruba")
        for ws in ws_ids:
            xml_str = base64.b64decode(self.datas.decode('utf-8'))
            invoice_xml = etree.fromstring(xml_str)

            IdTrasmittente = invoice_xml.find('FatturaElettronicaHeader/DatiTrasmissione/IdTrasmittente')
            IdTrasmittente.find('IdPaese').text = "IT"
            IdTrasmittente.find('IdCodice').text = "01879020517"

            # ContattiTrasmittente = invoice_xml.find('FatturaElettronicaHeader/DatiTrasmissione/ContattiTrasmittente')
            # ContattiTrasmittente.find('Telefono').text = "05750505"
            # ContattiTrasmittente.find('Email').text = "info@arubapec.it"


            self.datas = base64.b64encode(etree.tostring(invoice_xml))

            print(etree.tostring(invoice_xml))


            ws.web_auth()
            header = {
                'Content-Type': 'application/json;charset=UTF-8',
                'Authorization': 'Bearer ' + ws.web_server_token,
            }
            data = {
                'dataFile': self.datas.decode('utf-8'),
                'credential': None,
                'domain': None,
            }
            try:
                r = requests.post(ws.web_server_method_address + WS_ENDPOINT_UPLOAD_INVOICE, headers=header, data=json.dumps(data))
                if r.status_code == 200:
                    r = r.json()
                    self.aruba_upload_filename = r['uploadFileName']
                    self.aruba_error_code = r['errorCode']
                    self.aruba_error_description = r['errorDescription']
                    if self.aruba_error_code == '0000':
                        self.aruba_sent = True
                        self.aruba_sdi_state = 'Inviata'
                        for invoice in self.out_invoice_ids:
                            invoice.fatturapa_state = 'sent'
                            self.state = 'sent'
                            self.env.cr.commit()
                else:
                    raise UserWarning(r)
            except Exception as e:
                raise UserWarning(e)


    def get_single_sdi_notification(self):
        ws_ids = self.env['sdi.channel'].get_default_ws()
        for ws in ws_ids:
            if ws.provider == 'aruba':
                # Ora gestiamo solo le notifiche di Aruba
                ws.web_auth()
                header = {
                    'Authorization': 'Bearer ' + ws.web_server_token,
                }
                data = {
                    'filename': str(self.aruba_upload_filename),
                    'includePdf': False,
                }
                r = requests.get(ws.web_server_method_address + WS_ENDPOINT_NOTIFICATION_FILENAME,
                                 headers=header, params=data)
                if r.status_code == 200:
                    r = r.json()
                    invoices = r['invoices']
                    for inv in invoices:
                        notification = [(5,)]
                        self.aruba_sdi_state = inv['status']
                        notification_date = re.sub(r'([-+]\d{2}):(\d{2})(?:(\d{2}))?$', r'\1\2\3', inv['invoiceDate'])
                        date = datetime.datetime.strptime(notification_date, '%Y-%m-%dT%H:%M:%S.%f%z')
                        notification.append((0, 0, {
                            'sdi_state': inv['status'],
                            'date': date.strftime('%Y-%m-%d %H:%M:%S'),
                            'sdi_description': inv['statusDescription']
                        }))
                        self.sdi_notification_ids = notification


    def get_sdi_notification(self):
        """
        Aggiorna lo stato notifica SDI
        """
        ws_ids = self.env['sdi.channel'].get_default_ws()
        for ws in ws_ids:
            if ws.provider == 'aruba':
                #Ora gestiamo solo le notifiche di Aruba
                ws.web_auth()
                #last_week = datetime.datetime.now() - datetime.timedelta(days=7)
                #12 è il limite massimo ogni 1 minuto ARUBA
                #for attachment in self.search([('aruba_sdi_state', 'not in', SDI_COMPLETED)], limit=12):
                #if attachment.aruba_upload_filename:

                cron_id = self.env.ref('ati_aruba_fe.aruba_fe_notify_import')
                if cron_id:
                    from_date = cron_id.nextcall - datetime.timedelta(days=31)
                    from_date = from_date.strftime("%Y-%m-%d")

                    to_date = cron_id.nextcall + datetime.timedelta(days=31)
                    to_date = to_date.strftime("%Y-%m-%d")

                    page_number = 1
                    header = {
                        'Authorization': 'Bearer ' + ws.web_server_token,
                    }
                    data = {
                        'username': ws.web_server_login,
                        'countrySender': 'IT',
                        'vatcodeSender': self.env.user.company_id.vat.replace('IT', ''),
                        'size': 2000,
                        'page': page_number,
                        'startDate': from_date,
                        'endDate': to_date
                    }
                    r = requests.get(ws.web_server_method_address + WS_ENDPOINT_NOTIFICATION_USERNAME, headers=header, params=data)

                    if r.status_code == 200:
                        r = r.json()
                        page_number = 1
                        if r['errorDescription']:
                            raise UserError(r['errorDescription'])
                        total_pages = r['totalPages']
                        while page_number <= total_pages:
                            sleep(5)
                            data['page'] = page_number
                            page_number += 1
                            r = requests.get(ws.web_server_method_address + WS_ENDPOINT_NOTIFICATION_USERNAME, headers=header, params=data)
                            if r.status_code == 200:
                                r = r.json()
                                contents = r['content']
                                for elem in contents:
                                    for inv in elem['invoices']:
                                        #Cerco l'XML
                                        invoice_id = self.env['account.move'].search([('name', '=', inv['number'])], limit=1)
                                        if invoice_id:
                                            attachment = invoice_id.fatturapa_attachment_out_id
                                            if attachment and attachment.aruba_sdi_state not in SDI_COMPLETED:


                                                #Ricerca Notifiche History
                                                data_notifications = {
                                                    'filename': str(elem['filename']),
                                                    'includePdf': False,
                                                }
                                                notification_response = requests.get(ws.web_server_method_address + WS_ENDPOINT_NOTIFICATION_FILENAME,headers=header, params=data_notifications)
                                                notification_response = notification_response.json()
                                                sleep(2)
                                                notification = [(5,)]

                                                for notify in notification_response['invoices']:
                                                    notification_date = re.sub(r'([-+]\d{2}):(\d{2})(?:(\d{2}))?$', r'\1\2\3', notify['invoiceDate'])
                                                    date = datetime.datetime.strptime(notification_date, '%Y-%m-%dT%H:%M:%S.%f%z')
                                                    notification.append((0, 0, {
                                                        'sdi_state': notify['status'],
                                                        'date': date.strftime('%Y-%m-%d %H:%M:%S'),
                                                        'sdi_description': notify['statusDescription']
                                                    }))
                                                    attachment.aruba_sdi_state = notify['status']

                                                attachment.sdi_notification_ids = notification
                                                logging.info('Aggiornata notifica SDI: ' + invoice_id.name)
                                        else:
                                            logging.info('NON TROVATA: ' + inv['number'])
