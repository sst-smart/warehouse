# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import io
import time
from datetime import datetime
import tempfile
import binascii
from datetime import date, datetime
from odoo.exceptions import Warning, UserError
from odoo import models, fields, exceptions, api, _
import logging
_logger = logging.getLogger(__name__)
try:
    import xlrd
except ImportError:
    _logger.debug('Cannot `import xlrd`.')
try:
    import csv
except ImportError:
    _logger.debug('Cannot `import csv`.')
try:
    import xlwt
except ImportError:
    _logger.debug('Cannot `import xlwt`.')
try:
    import cStringIO
except ImportError:
    _logger.debug('Cannot `import cStringIO`.')
try:
    import base64
except ImportError:
    _logger.debug('Cannot `import base64`.')


class ImportChartAccount(models.TransientModel):
    _name = "import.chart.account"
    _description = "Chart of Account"

    File_slect = fields.Binary(string="Select Excel File")
    import_option = fields.Selection(
        [('csv', 'CSV File'), ('xls', 'XLS File')], string='Select', default='csv')

    def imoport_file(self):

        # -----------------------------
        if self.import_option == 'csv':

            keys = ['code', 'name', 'user_type_id']

            try:
                csv_data = base64.b64decode(self.File_slect)
                data_file = io.StringIO(csv_data.decode("utf-8"))
                data_file.seek(0)
                file_reader = []
                values = {}
                csv_reader = csv.reader(data_file, delimiter=',')
                file_reader.extend(csv_reader)

            except:

                raise UserError(_("Invalid file!"))

            for i in range(len(file_reader)):
                field = list(map(str, file_reader[i]))
                values = dict(zip(keys, field))
                if values:
                    if i == 0:
                        continue
                    else:
                        values.update({
                            'code': field[0],
                            'name': field[1],
                            'user': field[2],
                            'tax': field[3],
                            'tag': field[4],
                            'group': field[5],
                            'currency': field[6],
                            'reconcile': field[7],
                            'deprecat': field[8],

                        })
                        res = self.create_chart_accounts(values)

# ---------------------------------------
        elif self.import_option == 'xls':
            try:
                fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                fp.write(binascii.a2b_base64(self.File_slect))
                fp.seek(0)
                values = {}
                workbook = xlrd.open_workbook(fp.name)
                sheet = workbook.sheet_by_index(0)

            except:
                raise UserError(_("Invalid file!"))
            count = 0

            for row_no in range(sheet.nrows):
                count += 1
                val = {}
                if row_no <= 0:
                    fields = map(lambda row: row.value.encode(
                        'utf-8'), sheet.row(row_no))
                else:

                    line = list(map(lambda row: isinstance(row.value, bytes) and row.value.encode(
                        'utf-8') or str(row.value), sheet.row(row_no)))

                    values.update({'default_code': line[0],
                                   'name': line[1],
                                   'po_id': line[2],
                                   })

                    res = self.create_chart_accounts(values)
# ------------------------------------------------------------
        else:
            raise UserError(
                _("Please select any one from xls or csv formate!"))

        return res

    def create_chart_accounts(self, values):
        product_obj = self.env['product.product']
        product_search = product_obj.search([
            ('default_code', '=', values.get('default_code'))
        ], limit=1)
        product_search_po = product_obj.search([
            ('name', '=', values.get('po_id'))
        ], limit=1)
        if product_search:
            product_search.po_link_product_id = product_search_po.id
        else:
        	pass