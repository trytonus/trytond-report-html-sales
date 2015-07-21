# -*- coding: utf-8 -*-
from trytond.pool import Pool
from trytond.model import fields, ModelView
from trytond.transaction import Transaction
from trytond.wizard import Wizard, StateAction, StateView, Button

from openlabs_report_webkit import ReportWebkit

__all__ = ['SalesReport', 'SalesReportWizardStart', 'SalesReportWizard']


class ReportMixin(ReportWebkit):
    """
    Mixin Class to inherit from, for all HTML reports.
    """

    @classmethod
    def wkhtml_to_pdf(cls, data, options=None):
        """
        Call wkhtmltopdf to convert the html to pdf
        """
        Company = Pool().get('company.company')

        company = ''
        if Transaction().context.get('company'):
            company = Company(Transaction().context.get('company')).party.name
        options = {
            'margin-bottom': '0.50in',
            'margin-left': '0.50in',
            'margin-right': '0.50in',
            'margin-top': '0.50in',
            'footer-font-size': '8',
            'footer-left': company,
            'footer-line': '',
            'footer-right': '[page]/[toPage]',
            'footer-spacing': '5',
        }
        return super(ReportMixin, cls).wkhtml_to_pdf(
            data, options=options
        )


class SalesReport(ReportMixin):
    "Sales Report"
    __name__ = 'report.sales'

    @classmethod
    def parse(cls, report, records, data, localcontext):
        Sale = Pool().get('sale.sale')
        Party = Pool().get('party.party')
        Product = Pool().get('product.product')

        domain = [
            ('state', 'in', ['confirmed', 'processing', 'done']),
            ('sale_date', '>=', data['start_date']),
            ('sale_date', '<=', data['end_date'])
        ]

        customer_id = data.get('customer')
        product_id = data.get('product')

        if customer_id:
            domain.append(('party', '=', customer_id))
        if product_id:
            domain.append(('lines.product', '=', product_id))

        sales = Sale.search(domain)

        localcontext.update({
            'sales': sales,
            'customer': customer_id and Party(customer_id),
            'product': product_id and Product(product_id),
        })
        return super(SalesReport, cls).parse(
            report, records, data, localcontext
        )


class SalesReportWizardStart(ModelView):
    """
    Sales Report Wizard View
    """
    __name__ = 'report.sales.wizard.start'

    customer = fields.Many2One('party.party', 'Customer')
    product = fields.Many2One('product.product', 'Product')
    start_date = fields.Date('Start Date', required=True)
    end_date = fields.Date('End Date', required=True)

    @staticmethod
    def default_start_date():
        Date = Pool().get('ir.date')

        return Date.today()

    @staticmethod
    def default_end_date():
        Date = Pool().get('ir.date')

        return Date.today()


class SalesReportWizard(Wizard):
    """
    Wizard to generage Sales report
    """
    __name__ = 'report.sales.wizard'

    start = StateView(
        'report.sales.wizard.start',
        'sales_reports.report_sales_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Generate', 'generate', 'tryton-ok', default=True),
        ]
    )
    generate = StateAction('sales_reports.report_sales')

    def do_generate(self, action):
        """
        Sends the wizard data to report
        """
        data = {
            'customer': self.start.customer and self.start.customer.id,
            'product': self.start.product and self.start.product.id,
            'start_date': self.start.start_date,
            'end_date': self.start.end_date,
        }
        return action, data

    def transition_generate(self):
        return 'end'
