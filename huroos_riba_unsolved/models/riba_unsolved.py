from odoo import models, fields, api,_
from odoo.exceptions import ValidationError


class RibaUnsolved(models.TransientModel):
    _inherit = "riba.unsolved"

    def create_move(self):
        res = super(RibaUnsolved, self).create_move()
        # Riconcilia Crediti v/clienti e riapre la fattura
        active_id = self.env.context.get("active_id", False)
        distinta_line = self.env["riba.distinta.line"].browse(active_id)
        move = self.env['account.move'].browse(res['res_id'])
        move_line_model = self.env["account.move.line"]
        wizard = self
        to_be_unreconciled = []
        to_be_reconciled = []
        for move_line in move.line_ids:
            # Movimento di Insoluto
            if move_line.account_id.id == wizard.overdue_effects_account_id.id:
                to_be_reconciled.append(move_line.id)
        for acceptance_move_line in distinta_line.acceptance_move_id.line_ids:
            # Movimento di Accettazione
            if acceptance_move_line.account_id.id == wizard.overdue_effects_account_id.id:
                to_be_reconciled.append(acceptance_move_line.id)
                to_be_unreconciled.append(acceptance_move_line.id)
        for invoice_move_line in distinta_line.move_line_ids:
            if invoice_move_line.move_line_id.account_id.id == wizard.overdue_effects_account_id.id:
                to_be_unreconciled.append(invoice_move_line.move_line_id.id)

        # Deve rimuovere rincoliazione crediti v/clienti accettazione con fattura
        to_be_unreconciled_lines = move_line_model.with_context({"unsolved_reconciliation": True}).browse(
            to_be_unreconciled)
        to_be_unreconciled_lines.remove_move_reconcile()

        # Riconcilia crediti v/clienti accettazione con insoluto
        to_be_reconciled_lines = move_line_model.with_context({"unsolved_reconciliation": True}).browse(
            to_be_reconciled)
        to_be_reconciled_lines.reconcile()

        distinta_line.write(
            {
                "unsolved_move_id": move.id,
                "state": "unsolved",
            }
        )
        distinta_line.distinta_id.state = "unsolved"

        return res