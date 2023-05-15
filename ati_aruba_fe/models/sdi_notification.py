# -*- coding: utf-8 -*-
# Powered by Federico Ranieri.
# Part of Huroos. See LICENSE file for full copyright and licensing details.
# © 2022 Huroos Srl. (<https://www.huroos.com>).
import requests
from odoo import models, fields, api


class SdiNotification(models.Model):
    _name = 'sdi.notification'

    attachment_out_id = fields.Many2one('fatturapa.attachment.out')
    date = fields.Datetime()
    sdi_state = fields.Char()
    sdi_description = fields.Text()