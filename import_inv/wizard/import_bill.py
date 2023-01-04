# -*- coding: utf-8 -*-


import time
import tempfile
import binascii
import xlrd
import io
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import datetime
from odoo.exceptions import Warning
from collections import Counter
from odoo import models, fields, exceptions, api, _


class DynamicField(models.TransientModel):
    _name = 'import.inv.new'
    _description = 'Import'

    file = fields.Binary('File')
    number = fields.Float('Number')

    def import_inv(self):
        buffer = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        buffer.write(binascii.a2b_base64(self.file))
        buffer.seek(0)
        book = xlrd.open_workbook(buffer.name)
        sheet = book.sheet_by_index(0)
        invoice_name = 'new'
        count = 0
        product_template = False
        int_ref = False
        prod_id = False
        for row_no in range(sheet.nrows):
            if row_no <= 0:
                fields = map(lambda row: row.value.encode('utf-8'), sheet.row(row_no))
            else:
                line = list(
                    map(lambda row: isinstance(row.value, bytes) and row.value.encode('utf-8') or str(row.value),
                        sheet.row(row_no)))
                if line:
                    count += 1
                    print("Line No", count)
                    if line[0]:
                        location_id = self.env['stock.location'].search([('name', 'ilike', line[0])])
                        if location_id:
                            product_id = self.env['product.product'].search([('ext_id_map', '=', int(line[1]))])
                            uom_id = self.env['uom.uom'].search([('name', '=', line[4])])
                            print("Uom", uom_id.name)
                            stock_quant = self.env['stock.quant'].create({
                                'location_id': location_id.id,
                                'product_id': product_id.id,
                                'inventory_quantity': float(line[3]),
                                'product_uom_id': uom_id.id
                            })
                            stock_quant.action_apply_inventory()

    def run_the_code(self):
        if self.number:
            # product = self.env['product.product'].browse(self.number)
            query = "delete from stock_quant"
            self.env.cr.execute(query)
            # att = self.env['ir.attachment'].search([('res_model', '=', 'mrp.production'), ('res_id', '=', mrp.id)])
            # print("\n Attachment: ", att)
