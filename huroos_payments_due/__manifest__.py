# -*- coding: utf-8 -*-
# Powered by Federico Ranieri.
# Part of Huroos. See LICENSE file for full copyright and licensing details.
# © 2022 Huroos Srl. (<https://www.huroos.com>).

{
    'name': 'Scadenziario Pagamenti',
    'version': '14.0.0.0',
    'summary': '',
    'description': "Gestione Scadenziario Pagamenti",
    'author': 'Huroos Srl',
    'website': 'https://www.huroos.com',
    'category': 'accounting',
    'depends': ['account', 'l10n_it_fiscal_payment_term', 'l10n_it_fatturapa_in'],
    'data': [
        'security/ir.model.access.csv',
        'report/account_move.xml',
        'views/account_move.xml'
    ],
}
