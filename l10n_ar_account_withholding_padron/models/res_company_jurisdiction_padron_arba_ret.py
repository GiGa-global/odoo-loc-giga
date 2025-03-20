from odoo import models, api, fields
from odoo.exceptions import ValidationError
from datetime import datetime
import base64
import tempfile
import zipfile


class ResCompanyJurisdictionPadronArbaRet(models.Model):
    _name = 'res.company.jurisdiction.padron.ret'
    _inherit = 'res.company.jurisdiction.padron'

    log_content = fields.Text(readonly=True)
    log_no_process = fields.Text(readonly=True)
    log_process = fields.Text(readonly=True)
    l10n_ar_padron_from_date = fields.Date('From Date', required=False)
    l10n_ar_padron_to_date = fields.Date('To Date', required=False)

    def reescribirAlicuotaARBA(self,contact=False):
        for rec in self:
            if not rec.file_padron:
                raise ValidationError('No se encuentra subido el archivo del padron')

            lines = rec.open_file(rec)
            find_lines = rec.find_contacts_in_line(lines, contact)
            for line in find_lines:
                line = line.replace('\n', '')
                try:
                    split_line = line.split(';')
                    from_date = datetime.strptime(split_line[2], '%d%m%Y').date()
                    to_date = datetime.strptime(split_line[3], '%d%m%Y').date()
                    cuit = split_line[4]
                    alicuot = float(split_line[8].replace(',', '.'))
                except Exception as e:
                    rec.log_no_process += f'No se puede procesar la linea: {line}\n'
                    print(f'No se obtener los valores de la linea: {line}')
                    print(e)
                    continue
                contact = self.env['res.partner'].search([('vat', '=', cuit)], limit=1)
                rec.log_content += f'{line}\n'
                if contact:
                    find = False
                    if contact.arba_alicuot_ids:
                        for ali in contact.arba_alicuot_ids:
                            if ali.tag_id.id == rec.jurisdiction_id.id:
                                if ali.from_date == from_date:
                                    find = True
                                    ali.sudo().update(
                                        {
                                            'tag_id': rec.jurisdiction_id.id,
                                            'alicuota_retencion': alicuot,
                                            'from_date': from_date,
                                            'to_date': to_date,
                                            'date_last_update': datetime.now()
                                        }
                                    )
                                    rec.log_process += f'Linea procesada: {line}\n'

                    if not find:
                        new_line = {
                            'tag_id': rec.jurisdiction_id.id,
                            'from_date': from_date,
                            'to_date': to_date,
                            'alicuota_retencion': alicuot,
                            'withholding_amount_type': 'untaxed_amount',
                        }

                        try:
                            contact.sudo().write({'arba_alicuot_ids': [(0, 0, new_line)]})
                            rec.log_process += f'Linea procesada: {line}\n'
                        except Exception as e:
                            rec.log_no_process += f'No se puede procesar la linea: {line}\n'
                            print(e)

    @api.constrains('jurisdiction_id')
    def check_jurisdiction_id(self):
        pass

    def descompress_file(self, file_padron):
        ruta_extraccion = '/tmp'
        file = base64.decodebytes(file_padron)
        fobj = tempfile.NamedTemporaryFile(delete=False)
        fname = fobj.name
        fobj.write(file)
        fobj.close()
        f = open(fname, 'r+b')
        data = f.read()
        f.write(base64.b64decode(file_padron))
        with zipfile.ZipFile(f, 'r') as zip_file:
            zip_file.extractall(path=ruta_extraccion)
            zip_file.close()
            return zip_file.filelist[0].filename

    def open_file(self, rec):
        rec.log_content = ''
        rec.log_no_process = ''
        rec.log_process = ''
        try:
            txt_content = base64.b64decode(rec.file_padron).decode('utf-8')
            lines = txt_content.replace('\r', '').replace(' ', '').split('\n')
            lines = list(filter(None, lines))
            return lines
        except UnicodeDecodeError as e:
            print('Error decoding TXT')
            print('now decoding zip')
            file_name = rec.descompress_file(rec.file_padron)
            with open(f'/tmp/{file_name}', 'r', encoding='utf-8', errors='ignore') as fp:
                lines = fp.readlines()
                lines = list(filter(None, lines))
                lines = list(filter(lambda line: line.strip() != '', lines))
                return lines

    def find_contacts_in_line(self, lines, contact=False):
        if not contact:
            contacts = self.env['res.partner'].search([('vat', '!=', False)])
            cuit_array = [contact.vat for contact in contacts]
            cuits_datos = [line.split(';')[4] for line in lines]
            find_cuit = [cuit for cuit in cuit_array if cuit in cuits_datos]
            find_lines = [line for line in lines if line.split(';')[4] in find_cuit]
            return find_lines
        else:
            cuit_array = [c.vat for c in contact]
            cuits_datos = [line.split(';')[4] for line in lines]
            find_cuit = [cuit for cuit in cuit_array if cuit in cuits_datos]
            find_lines = [line for line in lines if line.split(';')[4] in find_cuit]
            return find_lines
