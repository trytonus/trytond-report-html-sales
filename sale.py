# -*- coding: utf-8 -*-
from itertools import groupby
from decimal import Decimal
from collections import defaultdict

from trytond.pool import Pool
from trytond.model import fields, ModelView
from trytond.transaction import Transaction
from trytond.wizard import Wizard, StateAction, StateView, Button
from trytond.exceptions import UserError

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
        Channel = Pool().get('sale.channel')
        Party = Pool().get('party.party')
        Product = Pool().get('product.product')

        domain = [
            ('state', 'in', ['confirmed', 'processing', 'done']),
            ('sale_date', '>=', data['start_date']),
            ('sale_date', '<=', data['end_date'])
        ]

        customer_id = data.get('customer')
        product_id = data.get('product')
        channel_id = data.get('channel')

        if customer_id:
            domain.append(('party', '=', customer_id))
        if product_id:
            domain.append(('lines.product', '=', product_id))
        if channel_id:
            domain.append(('channel', '=', channel_id))

        sales = Sale.search(domain, order=[('sale_date', 'desc')])

        if not sales:
            raise UserError(
                "There are no orders matching the filters."
            )

        sales_by_currency = defaultdict(dict)
        key = lambda sale: sale.currency
        for currency, cur_sales in groupby(sorted(sales, key=key), key):
            cur_sales = list(cur_sales)
            sales_by_currency[currency]['total'] = sum([
                sale.total_amount for sale in cur_sales
            ])
            sales_by_currency[currency]['tax'] = sum([
                sale.tax_amount for sale in cur_sales
            ])
            sales_by_currency[currency]['untaxed'] = sum([
                sale.untaxed_amount for sale in cur_sales
            ])
            sales_by_currency[currency]['payment_available'] = sum([
                sale.payment_available for sale in cur_sales
            ])

        # Payments by gateway and currency
        pbgc = defaultdict(lambda: defaultdict(lambda: Decimal('0')))
        pbc = defaultdict(lambda: Decimal('0'))
        for sale in sales:
            for payment in sale.payments:
                pbgc[payment.gateway][sale.currency] += payment.amount
                pbc[sale.currency] += payment.amount

        # Top 10 products
        top_10_products = []
        if not product_id:
            query = """
                SELECT
                    product,
                    SUM(quantity) AS quantity
                    FROM sale_line
                    WHERE sale IN %s
                    GROUP BY product
                    ORDER BY quantity DESC
                    LIMIT 10"""
            Transaction().cursor.execute(query, (tuple(map(int, sales)),))
            for top_product_id, quantity in Transaction().cursor.fetchall():
                top_10_products.append((Product(top_product_id), quantity))

        localcontext.update({
            'sales': sales,
            'pbgc': pbgc,
            'pbc': pbc,
            'top_10_products': top_10_products,
            'sales_by_currency': sales_by_currency,
            'customer': customer_id and Party(customer_id),
            'product': product_id and Product(product_id),
            'channel': channel_id and Channel(channel_id),
            'start_date': data['start_date'],
            'end_date': data['end_date'],
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
    channel = fields.Many2One('sale.channel', 'Channel')
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

    @classmethod
    def default_channel(cls):
        User = Pool().get('res.user')

        user = User(Transaction().user)
        channel_id = Transaction().context.get('current_channel')

        if channel_id:
            return channel_id
        return user.current_channel and \
            user.current_channel.id


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
            'channel': self.start.channel and self.start.channel.id,
            'customer': self.start.customer and self.start.customer.id,
            'product': self.start.product and self.start.product.id,
            'start_date': self.start.start_date,
            'end_date': self.start.end_date,
        }
        return action, data

    def transition_generate(self):
        return 'end'
