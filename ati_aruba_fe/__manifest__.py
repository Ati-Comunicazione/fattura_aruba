# -*- coding: utf-8 -*-
# Powered by Federico Ranieri.
# Part of Huroos. See LICENSE file for full copyright and licensing details.
# © 2022 Huroos Srl. (<https://www.huroos.com>).

{
    'name': 'Aruba <> FE',
    'version': '14.0.0.0',
    'summary': '',
    'description': "Connettore Fatturazione Elettronica Aruba",
    'author': 'Huroos Srl',
    'website': 'https://www.huroos.com',
    'category': 'accounting',
    'depends': ['account', 'l10n_it_account', 'l10n_it_fatturapa', 'l10n_it_sdi_channel', 'l10n_it_fatturapa_in',
                'l10n_it_fatturapa_out', 'l10n_it_fatturapa_pec'],
    'data': [
        'data/ir_cron.xml',
        'security/ir.model.access.csv',
        'views/account_move.xml',
        'views/sdi_channel.xml',
        'views/fatturapa_attachment_out.xml',
        'views/fatturapa_attachment_in.xml',
        'wizard/send_to_aruba.xml'
    ],
}