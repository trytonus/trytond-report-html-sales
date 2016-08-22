# -*- coding: utf-8 -*-
import sys
import os
from decimal import Decimal

import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, USER, ModuleTestCase
from trytond.transaction import Transaction
from trytond.pyson import Eval

DIR = os.path.abspath(os.path.normpath(os.path.join(
    __file__, '..', '..', '..', '..', '..', 'trytond'
)))
if os.path.isdir(DIR):
    sys.path.insert(0, os.path.dirname(DIR))

ROOT_JSON_FOLDER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'json_data'
)


class BaseTestCase(ModuleTestCase):
    '''
    Base Test Case for report_html_sales module.
    '''
    module = 'sales_reports'

    def setUp(self):
        """
        Set up data used in the tests.
        this method is called before each test function execution.
        """
        trytond.tests.test_tryton.install_module('sales_reports')

        self.Currency = POOL.get('currency.currency')
        self.Company = POOL.get('company.company')
        self.Party = POOL.get('party.party')
        self.User = POOL.get('res.user')
        self.ProductTemplate = POOL.get('product.template')
        self.Uom = POOL.get('product.uom')
        self.ProductCategory = POOL.get('product.category')
        self.Product = POOL.get('product.product')
        self.Country = POOL.get('country.country')
        self.Subdivision = POOL.get('country.subdivision')
        self.Employee = POOL.get('company.employee')
        self.Location = POOL.get('stock.location')
        self.ShipmentOut = POOL.get('stock.shipment.out')
        self.StockLocation = POOL.get('stock.location')
        self.Address = POOL.get('party.address')
        self.Move = POOL.get('stock.move')
        self.Product = POOL.get('product.product')
        self.ShipmentIn = POOL.get('stock.shipment.in')
        self.ShipmentOutReturn = POOL.get('stock.shipment.out.return')
        self.Sale = POOL.get('sale.sale')
        self.SaleLine = POOL.get('sale.line')
        self.Channel = POOL.get('sale.channel')
        self.PriceList = POOL.get('product.price_list')
        self.PaymentTerm = POOL.get('account.invoice.payment_term')

    def _create_coa_minimal(self, company):
        """Create a minimal chart of accounts
        """
        AccountTemplate = POOL.get('account.account.template')
        Account = POOL.get('account.account')

        account_create_chart = POOL.get(
            'account.create_chart', type="wizard")

        account_template = AccountTemplate.search(
            [('parent', '=', None)]
        )[0]

        session_id, _, _ = account_create_chart.create()
        create_chart = account_create_chart(session_id)
        create_chart.account.account_template = account_template
        create_chart.account.company = company
        create_chart.transition_create_account()

        receivable, = Account.search([
            ('kind', '=', 'receivable'),
            ('company', '=', company),
        ])
        payable, = Account.search([
            ('kind', '=', 'payable'),
            ('company', '=', company),
        ])
        create_chart.properties.company = company
        create_chart.properties.account_receivable = receivable
        create_chart.properties.account_payable = payable
        create_chart.transition_create_properties()

    def _get_account_by_kind(self, kind, company=None, silent=True):
        """Returns an account with given spec
        :param kind: receivable/payable/expense/revenue
        :param silent: dont raise error if account is not found
        """
        Account = POOL.get('account.account')
        Company = POOL.get('company.company')

        if company is None:
            company, = Company.search([], limit=1)

        accounts = Account.search([
            ('kind', '=', kind),
            ('company', '=', company)
        ], limit=1)
        if not accounts and not silent:
            raise Exception("Account not found")

        if not accounts:
            return None
        account, = accounts

        return account

    def setup_defaults(self):
        """Creates default data for testing
        """

        self.currency, = self.Currency.create([{
            'name': 'US Dollar',
            'code': 'USD',
            'symbol': '$',
        }])

        with Transaction().set_context(company=None):
            self.company_party, = self.Party.create([{
                'name': 'openlabs',
            }])

            self.company, = self.Company.create([{
                'party': self.company_party,
                'currency': self.currency,
            }])

        self.User.write([self.User(USER)], {
            'company': self.company,
            'main_company': self.company,
        })

        Transaction().context.update(
            self.User.get_preferences(context_only=True))

        self.country, = self.Country.create([{
            'name': 'United States of America',
            'code': 'US',
        }])
        self.subdivision, = self.Subdivision.create([{
            'country': self.country.id,
            'name': 'California',
            'code': 'CA',
            'type': 'state',
        }])

        self._create_coa_minimal(self.company)

        self.party, = self.Party.create([{
            'name': 'Bruce Wayne',
            'addresses': [('create', [{
                'name': 'Bruce Wayne',
                'party': Eval('id'),
                'city': 'Gotham',
                'country': self.country.id,
                'subdivision': self.subdivision.id,
            }])],
            'contact_mechanisms': [('create', [
                {'type': 'mobile', 'value': '8888888888'},
            ])],
        }])
        self.Party.write([self.company.party], {
            'addresses': [('create', [{
                'name': 'Lie Nielsen',
                'city': 'Los Angeles',
                'country': self.country.id,
                'subdivision': self.subdivision.id,
            }])],
        })
        self.product_category, = self.ProductCategory.create([{
            'name': 'Automobile',
        }])

        self.uom, = self.Uom.search([('name', '=', 'Unit')])

        account_revenue = self._get_account_by_kind('revenue', self.company)
        self.product_template, = self.ProductTemplate.create([{
            'name': 'Bat Mobile',
            'type': 'goods',
            'categories': [('add', [self.product_category.id])],
            'list_price': Decimal('20000'),
            'cost_price': Decimal('15000'),
            'default_uom': self.uom.id,
            'salable': True,
            'sale_uom': self.uom.id,
            'account_revenue': account_revenue.id,
        }])
        self.product, = self.Product.create([{
            'template': self.product_template.id,
            'code': '123',
        }])

        self.price_list = self.PriceList(
            name='PL 1',
            company=self.company
        )
        self.price_list.save()

        self.payment_term, = self.PaymentTerm.create([{
            'name': 'Direct',
            'lines': [('create', [{'type': 'remainder'}])]
        }])

        self.warehouse, = self.Location.search([
            ('type', '=', 'warehouse')
        ], limit=1)

        with Transaction().set_context({'company': self.company.id}):
            self.channel, = self.Channel.create([{
                'name': 'Test Channel 1',
                'price_list': self.price_list,
                'invoice_method': 'order',
                'shipment_method': 'order',
                'source': 'manual',
                'create_users': [('add', [USER])],
                'warehouse': self.warehouse,
                'payment_term': self.payment_term,
            }])
