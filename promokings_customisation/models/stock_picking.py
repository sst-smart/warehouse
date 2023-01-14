# -*- coding: utf-8 -*-


from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    partner_id = fields.Many2one('res.partner', compute="_compute_partner_id_sale_order", string="Customer", store=True)
    sale_order_id = fields.Many2one('sale.order', compute="_compute_partner_id_sale_order", string="Sale order", store=True)
    is_mrp_picking = fields.Boolean('Mrp Picking', compute="_compute_partner_id_sale_order", store=True)
    mrp_sale_order_id = fields.Many2one('sale.order', string="Sale orders")

    def total_ordered_qty(self):
        total_ordered = 0.0
        for rec in self.move_ids_without_package:
            total_ordered += rec.product_uom_qty
        return total_ordered

    def total_done_qty(self):
        total_done = 0.0
        for rec in self.move_ids_without_package:
            total_done += rec.quantity_done
        return total_done


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

    def action_update_inventory_adjustment(self):
        for line in self.move_ids_without_package:
            stock_quant = self.env['stock.quant'].create({
                'location_id': line.location_id.id,
                'product_id': line.product_id.id,
                'inventory_quantity': line.quantity_done or line.product_uom_qty,
                'product_uom_id': line.product_id.uom_id.id
            })
            stock_quant.action_apply_inventory()

    def change_pre_production_location(self):
        if self.location_id.id == 17:
            self.location_id = 22
        elif self.location_dest_id.id == 17:
            self.location_dest_id = 22

    # def button_validate(self):
    #     for line in self.move_ids_without_package:
    #         if line.sale_line_id:
    #             # if line.sale_line_id.next_action == 'buy':
    #             purchase_line_id = self.env['purchase.order.line'].search(
    #                 [('sale_line_id', '=', line.sale_line_id.id),
    #                  ('product_id', '=', line.product_id.id)])
    #             if purchase_line_id:
    #                 # if purchase_line_id.qty_received < line.quantity_done:
    #                 if sum(purchase_line_id.mapped('qty_received')) < line.quantity_done:
    #                     raise UserError(_('Stock is not available for product %s') % line.product_id.name)
    #
    #             # if line.sale_line_id.next_action == 'manufacture':
    #             production_id = self.env['mrp.production'].search([('origin', '=', line.sale_line_id.order_id.name),
    #                                                                ('product_id', '=', line.product_id.id)],
    #                                                               limit=1)
    #             if production_id:
    #                 if production_id.qty_produced < line.quantity_done:
    #                     raise UserError(_('Stock is not available for product %s') % line.product_id.name)
    #     return super(StockPicking, self).button_validate()

    def _action_done(self):
        """
        Super the action done function for create the stock quant for finished goods,
        remove the same from ready goods location
        """
        res = super(StockPicking, self)._action_done()
        for record in self:
            if record.sale_id:
                next_action = record.sale_id.sudo().next_action_ids.next_action_line_ids
                picking_type = self.env['stock.picking.type'].search([('code', '=', 'internal')], limit=1)
                if record.picking_type_id == picking_type.id and record.move_line_ids_without_package:
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

    att_value = fields.Many2many('product.attribute.value', compute="_compute_attribute_value", string="Attribute")

    def _compute_attribute_value(self):

        if self.product_id and self.product_id.product_template_variant_value_ids:
            self.att_value = self.product_id.product_template_variant_value_ids.product_attribute_value_id
        else:
            self.att_value = False

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

    """!!!!! OVERRIDE FOR REMOVING THE CONFLICT BECAUSE OF ARCHIVED LOCATION !!!!!"""
    @api.model
    def _update_reserved_quantity(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None, strict=False):
        """ Increase the reserved quantity, i.e. increase `reserved_quantity` for the set of quants
        sharing the combination of `product_id, location_id` if `strict` is set to False or sharing
        the *exact same characteristics* otherwise. Typically, this method is called when reserving
        a move or updating a reserved move line. When reserving a chained move, the strict flag
        should be enabled (to reserve exactly what was brought). When the move is MTS,it could take
        anything from the stock, so we disable the flag. When editing a move line, we naturally
        enable the flag, to reflect the reservation according to the edition.

        :return: a list of tuples (quant, quantity_reserved) showing on which quant the reservation
            was done and how much the system was able to reserve on it
        """
        self = self.sudo()
        rounding = product_id.uom_id.rounding

        quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict)
        reserved_quants = []

        if float_compare(quantity, 0, precision_rounding=rounding) > 0:
            # if we want to reserve
            available_quantity = sum(quants.filtered(lambda q: float_compare(q.quantity, 0, precision_rounding=rounding) > 0).mapped('quantity')) - sum(quants.mapped('reserved_quantity'))
            if float_compare(quantity, available_quantity, precision_rounding=rounding) > 0:
                raise UserError(_('It is not possible to reserve more products of %s than you have in stock.', product_id.display_name))
        elif float_compare(quantity, 0, precision_rounding=rounding) < 0:
            # if we want to unreserve
            available_quantity = sum(quants.mapped('reserved_quantity'))
            # if float_compare(abs(quantity), available_quantity, precision_rounding=rounding) > 0:
            #     raise UserError(_('It is not possible to unreserve more products of %s than you have in stock.', product_id.display_name))
        else:
            return reserved_quants

        for quant in quants:
            if float_compare(quantity, 0, precision_rounding=rounding) > 0:
                max_quantity_on_quant = quant.quantity - quant.reserved_quantity
                if float_compare(max_quantity_on_quant, 0, precision_rounding=rounding) <= 0:
                    continue
                max_quantity_on_quant = min(max_quantity_on_quant, quantity)
                quant.reserved_quantity += max_quantity_on_quant
                reserved_quants.append((quant, max_quantity_on_quant))
                quantity -= max_quantity_on_quant
                available_quantity -= max_quantity_on_quant
            else:
                max_quantity_on_quant = min(quant.reserved_quantity, abs(quantity))
                quant.reserved_quantity -= max_quantity_on_quant
                reserved_quants.append((quant, -max_quantity_on_quant))
                quantity += max_quantity_on_quant
                available_quantity += max_quantity_on_quant

            if float_is_zero(quantity, precision_rounding=rounding) or float_is_zero(available_quantity, precision_rounding=rounding):
                break
        return reserved_quants


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
