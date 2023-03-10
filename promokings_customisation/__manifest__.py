# -*- coding: utf-8 -*-

{
    'name': "Promo Kings Customisation",
    'version': '15.0.1.1.87',
    'author': 'Pragmatic TechSoft Pvt Ltd.',
    'website': 'www.pragtech.co.in',
    'depends': ['base', 'sale_management', 'sale', 'purchase', 'stock', 'sale_stock', 'mrp', 'approvals', 'web', 'sales_team', 'stock_picking_invoice_link','web'],
    'summary': 'Promo Kings Customisation',
    'description': """
        Promo Kings Customisation
    """,
    'data': [
        'data/data.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/sale_order_view_inherit.xml',
        'views/purchase_order_view.xml',
        # 'views/res_partner_view_inherit.xml',
        'views/stock_picking_views.xml',
        'views/mrp_production_views.xml',
        'views/product_product_views.xml',
        'views/customisation_type_views.xml',
        'views/so_next_action_views.xml',
        'views/approval_request_view.xml',
        'views/res_config_settings_views.xml',
        'reports/mrp_production_template_inherit.xml',
        'reports/report_package_barcode_inherit.xml',
        'reports/job_card_report.xml',
        'reports/job_card_report_template.xml',
        'reports/sale_report_template.xml',
        'reports/delivery_slip_report_template.xml',
        'reports/invoice_report_template.xml',
        'reports/purchase_report_template.xml',
        'reports/product_label_layout_view_inherit.xml',
        # 'wizard/add_product_variants_wizard_views.xml',
        'wizard/multiple_so_creation_wizard_views.xml',
    ],
    'license': 'OPL-1',
    'installable': True,
    'application': True,
    'auto_install': False,
}
