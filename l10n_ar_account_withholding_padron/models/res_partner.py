from odoo import models, fields


class ResPartnerInherit(models.Model):
    _inherit = 'res.partner'

    def update_alicuot(self):
        if self.vat:
            rec_arba = self.env['res.company.jurisdiction.padron'].search([], limit=1, order='id desc')
            rec_arba_ret = self.env['res.company.jurisdiction.padron.ret'].search([], limit=1, order='id desc')
            rec_agip = self.env['res.company.jurisdiction.padron.agip'].search([], limit=1, order='id desc')
            rec_arba.reescribirAlicuotaARBA(contact=self)
            rec_arba_ret.reescribirAlicuotaARBA(contact=self)
            rec_agip.reescribirAlicuotaAGIP(contact=self)
        else:
            raise ValueError('No se ha ingresado un número de CUIT')

class ResPartnerArbaAlicuotInherit(models.Model):
    _inherit = 'res.partner.arba_alicuot'
    
    date_last_update = fields.Datetime(readonly=True)