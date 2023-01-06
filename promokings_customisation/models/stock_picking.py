# -*- coding: utf-8 -*-


from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    partner_id = fields.Many2one('res.partner', compute="_compute_partner_id_sale_order", string="Customer", store=True)
    sale_order_id = fields.Many2one('sale.order', compute="_compute_partner_id_sale_order", string="Sale order", store=True)
    is_mrp_picking = fields.Boolean('Mrp Picking', compute="_compute_partner_id_sale_order", store=True)
    mrp_sale_order_id = fields.Many2one('sale.order', string="Sale orders")

    def _compute_partner_id_sale_order(self):
        ctx = self.env.context
        for order in self:
            if ctx.get('active_model') == 'mrp.production':
                mrp_orders = self.env['mrp.production'].search([('picking_ids', '!=', False)])
                mrp_order = mrp_orders.filtered(lambda mrp: order.id in mrp.picking_ids.ids)
                if mrp_order and len(mrp_order) == 1:
                    self.is_mrp_picking = True
                    self.partner_id = mrp_order.partner_id.id or False
                    self.sale_order_id = mrp_order.sale_order_id.id or False
                elif len(mrp_order) > 1:
                    self.is_mrp_picking = True
                    self.partner_id = mrp_order[0].partner_id.id or False
                    self.sale_order_id = mrp_order[0].sale_order_id.id or False
            else:
                self.is_mrp_picking = False
                self.partner_id = False
                self.sale_order_id = False

    def button_validate(self):
        for line in self.move_ids_without_package:
            if line.sale_line_id:
                # if line.sale_line_id.next_action == 'buy':
                purchase_line_id = self.env['purchase.order.line'].search(
                    [('sale_line_id', '=', line.sale_line_id.id),
                     ('product_id', '=', line.product_id.id)])
                if purchase_line_id:
                    # if purchase_line_id.qty_received < line.quantity_done:
                    if sum(purchase_line_id.mapped('qty_received')) < line.quantity_done:
                        raise UserError(_('Stock is not available for product %s') % line.product_id.name)

                # if line.sale_line_id.next_action == 'manufacture':
                production_id = self.env['mrp.production'].search([('origin', '=', line.sale_line_id.order_id.name),
                                                                   ('product_id', '=', line.product_id.id)],
                                                                  limit=1)
                if production_id:
                    if production_id.qty_produced < line.quantity_done:
                        raise UserError(_('Stock is not available for product %s') % line.product_id.name)
        return super(StockPicking, self).button_validate()

    def _action_done(self):
        """
        Super the action done function for create the stock quant for finished goods,
        remove the same from ready goods location
        """
        res = super(StockPicking, self)._action_done()
        for record in self:
            if record.sale_id:
                next_action = record.sale_id.next_action_ids.next_action_line_ids
                if record.picking_type_code == 'internal' and record.move_line_ids_without_package:
                    for move_line in record.move_line_ids_without_package:
                        next_action_filter = next_action.filtered(lambda x: move_line.product_id.id in x.mapped('linked_product_id.id'))
                        if next_action_filter:
                            for action_line in next_action_filter:
                                if move_line.product_id == action_line.linked_product_id:
                                    stock_quant = self.env['stock.quant'].create({
                                        'location_id': record.location_dest_id.id,
                                        'product_id': action_line.product_id.id,
                                        'inventory_quantity': move_line.qty_done,
                                        'product_uom_id': action_line.product_id.uom_id.id
                                    })
                                    stock_quant.action_apply_inventory()
                                    current_quant = self.env['stock.quant'].search([('location_id', '=', record.location_dest_id.id),
                                                                                    ('product_id', '=', move_line.product_id.id),
                                                                                    ('quantity', '=', move_line.qty_done)], limit=1)
                                    current_quant.update({
                                        'inventory_quantity': 0
                                    })
                                    current_quant.action_apply_inventory()

        return res

    def action_confirm(self):
        res = super(StockPicking, self).action_confirm()
        if self.move_line_ids_without_package:
            for line in self.move_line_ids_without_package:
                for picking_type in self.picking_type_id:
                    if picking_type.code == 'outgoing':
                        values = {
                            'name': self.env['ir.sequence'].next_by_code('next.package.name')
                        }
                        package_id = self.env['stock.quant.package'].create(values)
                        line.result_package_id = package_id.id
        return res


class StockQuantPackageInherit(models.Model):
    _inherit = 'stock.quant.package'

    partner_id = fields.Many2one('res.partner', string="Customer")
    sale_order_id = fields.Many2one('sale.order', string="Sale Order")

    @api.model
    def create(self, vals):
        res = super(StockQuantPackageInherit, self).create(vals)
        ctx = self.env.context
        picking_id = self.env['stock.picking'].browse(ctx.get('picking_id'))
        sale_order = self.env['sale.order'].browse(ctx.get('active_id'))
        if picking_id:
            res.update({
                'partner_id': picking_id.purchase_id.partner_id or False,
            })
        if sale_order:
            res.update({
                'sale_order_id': sale_order or False
            })
        return res


class StockQuantInherit(models.Model):
    _inherit = 'stock.quant'

    value = fields.Many2many('product.attribute.value', compute="_compute_attribute_value", string="Attribute")

    def _compute_attribute_value(self):

        if self.product_id and self.product_id.product_template_variant_value_ids:
            self.value = self.product_id.product_template_variant_value_ids.product_attribute_value_id
        else:
            self.value = False

    @api.model
    def create(self, vals):
        res = super(StockQuantInherit, self).create(vals)
        ctx = self.env.context
        # picking_ids = ctx.get('button_validate_picking_ids')
        if ctx.get('active_model') == 'sale.order':
            active_id = self.env['sale.order'].browse(ctx.get('active_id'))
            if res.package_id:
                res.package_id.update({
                    'partner_id': active_id.partner_id.id
                })
        return res


class StockMoveLineInheritPromoKings(models.Model):
    _inherit = "stock.move.line"

    @api.onchange('product_id')
    def onchange_result_package_id(self):
        if not self.result_package_id:
            if self.picking_code == 'outgoing':
                values = {
                    'name': self.env['ir.sequence'].next_by_code('next.package.name')
                }
                package_id = self.env['stock.quant.package'].create(values)
                self.result_package_id = package_id.id
