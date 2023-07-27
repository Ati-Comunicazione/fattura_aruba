# -*- coding: utf-8 -*-
# Part of huroos srl. See LICENSE file for full copyright and licensing details.
# Copyright 2019 huroos srl (<http://www.addoons.it>)

{
    'name': 'Insoluti RIBA',
    'version': '14.0.1.2.7',
    'category': 'Localization/Italy',
    'summary': 'Gestione degli insoluti riba. Riapre la fattura se si registra un insoluto. Gestione spese incasso RiBa.',
    "author": "hello@huroos.com",
    'website': 'www.huroos.com',
    'license': 'LGPL-3',
    "depends": [
        'account',
        'l10n_it_ricevute_bancarie',
    ],
    "data": [
        #'views/riba_u.xml',
        'views/res_config_settings_view.xml'
    ],
    'installable': True,
}
