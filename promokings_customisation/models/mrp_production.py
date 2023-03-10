# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import date
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    customisation_details = fields.Char(string="Customisation Details")
    customisation_type_ids = fields.Many2many('customisation.type', string='Customisation Type')

    branding_mo = fields.Boolean(string="Branding MO")
    partner_id = fields.Many2one('res.partner', string="Customer")
    sale_order_id = fields.Many2one('sale.order', string="Sale Order")

    # _sql_constraints = [
    #     ('name_uniq', 'unique(name, company_id)', 'Reference must be unique per Company!'),
    #     ('qty_positive', 'check (product_qty >= 0)', 'The quantity to produce must be positive!'),
    # ]

    @api.model
    def create(self, vals):
        res = super(MrpProduction, self).create(vals)
        if self._context.get('customisation_required'):
            mo_name = res.name.split("/")
            customisation_mo_name = mo_name[0] + "/" + mo_name[1]
            sequence = self.env['ir.sequence'].next_by_code('customisation.manufacturing.order')
            res.name = "B-" + customisation_mo_name + "/" + sequence
        return res

    def action_confirm(self):
        res = super(MrpProduction, self).action_confirm()
        for picking in self.picking_ids:
            if picking.picking_type_id.sequence_code == 'PC':
                for user in self.env['res.users'].sudo().search([]).filtered(
                        lambda u: u.has_group('promokings_customisation.group_manufacturing_pick_components_officer')):
                    self.env['mail.activity'].sudo().create({
                        'res_model_id': self.env['ir.model']._get_id('stock.picking'),
                        'res_id': picking.id,
                        'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                        'date_deadline': date.today(),
                        'user_id': user.id,
                        'summary': "Pick Components",
                        'note': "Pick Components",
                    })
            if self.branding_mo:
                if picking.location_id and picking.location_id.name == 'Post-Production':
                    finished_goods_location = self.env['stock.location'].search(
                        [('name', 'ilike', 'Finished Goods Store'), ('usage', '=', 'internal'), ('company_id', '=', self.env.company.id)], limit=1)
                    finished_goods_locations = self.env['stock.location'].search(
                        [('name', 'ilike', 'Finished Goods Stock'), ('usage', '=', 'internal'), ('company_id', '=', self.env.company.id)], limit=1)
                    picking.location_dest_id = finished_goods_location.id or finished_goods_locations.id
                picking.origin = self.name
            if self.sale_order_id:
                picking.mrp_sale_order_id = self.sale_order_id.id
        return res

    def button_mark_done(self):
        # produced = self.product_qty
        res = super(MrpProduction, self).button_mark_done()
        # self.product_qty = produced
        branding_mo = self.sudo().search([('branding_mo', '=', True), ('partner_id', '=', self.partner_id.id),
                                          ('sale_order_id', '=', self.sale_order_id.id)])
        if branding_mo:
            for user in self.env['res.users'].sudo().search([]).filtered(
                    lambda u: u.has_group('promokings_customisation.group_secondary_manufacturing_officer')):
                self.env['mail.activity'].sudo().create({
                    'res_model_id': self.env['ir.model']._get_id('mrp.production'),
                    'res_id': branding_mo[0].id,
                    'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                    'date_deadline': date.today() + relativedelta(days=1),
                    'user_id': user.id,
                    'summary': "Branding",
                    'note': "Branding",
                })
        return res

    # @api.model
    # def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
    #     res = super(MrpProduction, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
    #     return res

    def action_create_counterpart_transfer(self):
        for record in self:
            if record.picking_ids and record.delivery_count == 1:
                picking = record.picking_ids.filtered(lambda x: x.state not in ['cancel'])
                if picking:
                    location_id = self.env['stock.location'].search([('name', '=', 'Ready Goods Stock')], limit=1)
                    lines = [(5, 0, 0)]
                    if record.move_raw_ids:
                        for pick in record.move_raw_ids:
                            line = (0, 0, {
                                'name': '/',
                                'product_id': pick.product_id.id,
                                'product_uom': pick.product_uom.id,
                                'product_uom_qty': pick.product_uom_qty,
                                'location_id': location_id.id,
                                'location_dest_id': pick.location_id.id,
                            })
                            lines.append(line)
                        picking_type = self.env['stock.picking.type'].search([('code', '=', 'internal'), ('name', '=', 'Pick Components')])
                        pick_output = self.env['stock.picking'].create({
                            'name': '/',
                            'partner_id': False,
                            'scheduled_date': picking.scheduled_date,
                            'mrp_sale_order_id': record.sale_order_id.id or False,
                            'picking_type_id': picking_type.id,
                            'location_id': location_id.id,
                            'location_dest_id': record.location_src_id.id,
                            'origin': record.name,
                            'move_lines': lines,
                        })
                        pick_output.group_id = picking.group_id.id
                        pick_output.action_confirm()
                        record.picking_ids = [(4, pick_output.id)]
                    else:
                        raise ValidationError(_("Please add components to create counter part transfer"))
            else:
                raise ValidationError(_("It will only work if manufacturing order have one transfer."))


