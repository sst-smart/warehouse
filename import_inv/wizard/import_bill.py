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
        # invoice = self.env['account.move'].browse(2)
        # invoice.picking_ids = [(4, 265)]
        # query = "select * from stock_quant"
        # self.env.cr.execute(query)
        # data = self.env.cr.fetchall()
        # print("data", data)
        # date = datetime.datetime(2022, 12, 31)
        # all_stock = self.env['stock.quant'].search([])
        # all_stock.inventory_date = date
        # if self.number:
        #     mrp = self.env['mrp.production'].browse(int(self.number))
        #     pick_output = self.env['stock.picking'].create({
        #         'name': '/',
        #         'partner_id': False,
        #         'scheduled_date': mrp.date_planned_start,
        #         'sale_id': mrp.sale_order_id.id,
        #         'picking_type_id': 7,
        #         'location_id': 8,
        #         'location_dest_id': 22,
        #         'origin': mrp.name,
        #         'move_lines': [(5, 0, 0), (0, 0, {
        #                     'name': '/',
        #                     'product_id': mrp.move_raw_ids[0].product_id.id,
        #                     'product_uom': mrp.move_raw_ids[0].product_id.uom_id.id,
        #                     'product_uom_qty': 100,
        #                     'location_id': 8,
        #                     'location_dest_id': 22,
        #                 })]
        #     })
        #     pick_output.action_confirm()
        #     pick_output.group_id = 109
        #     mrp.picking_ids = [(4, pick_output.id)]
        if self.number == 1:
            # sale_orders = self.env['sale.order'].search([('parent_so_id', '!=', False), ('state', '=', 'quotation_confirmed')])
            # sale_orders.state = 'sale'
            all_products = self.env['product.template'].search([('invoice_policy', '=', 'order')])
            all_products.invoice_policy = 'delivery'

        if self.number == 2:
            mrp = self.env['mrp.production'].search([('state', '=', 'draft')])
            for order in mrp:
                location = self.env['stock.location'].sudo().browse(22)
                if order.location_src_id == location:
                    order.location_src_id = 17
                if order.move_raw_ids:
                    for move_raw in order.move_raw_ids:
                        if move_raw.location_id == location:
                            move_raw.location_id = 17

        if self.number == 3:
            # mrp_id = self.env['mrp.production'].sudo().search([('state', '=', )])
            mrp = self.env['mrp.production'].browse(351)

            print("mrp", mrp.read())