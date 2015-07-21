# -*- coding: utf-8 -*-
import unittest
import datetime
from datetime import date
from decimal import Decimal
from dateutil.relativedelta import relativedelta

import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, DB_NAME, USER, CONTEXT
from trytond.transaction import Transaction
from trytond.pyson import Eval
from trytond.pool import Pool


class TestSale(unittest.TestCase):
    """
    Sale tests for Sales Report module
    """

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
        self.Journal = POOL.get('account.journal')
        self.Group = POOL.get('res.group')
        self.Country = POOL.get('country.country')
        self.Subdivision = POOL.get('country.subdivision')
        self.Sale = POOL.get('sale.sale')
        self.SaleLine = POOL.get('sale.line')

    def _create_fiscal_year(self, date=None, company=None):
        """
        Creates a fiscal year and requried sequences
        """
        FiscalYear = POOL.get('account.fiscalyear')
        Sequence = POOL.get('ir.sequence')
        SequenceStrict = POOL.get('ir.sequence.strict')
        Company = POOL.get('company.company')

        if date is None:
            date = datetime.date.today()

        if company is None:
            company, = Company.search([], limit=1)

        invoice_sequence, = SequenceStrict.create([{
            'name': '%s' % date.year,
            'code': 'account.invoice',
            'company': company,
        }])
        fiscal_year, = FiscalYear.create([{
            'name': '%s' % date.year,
            'start_date': date + relativedelta(month=1, day=1),
            'end_date': date + relativedelta(month=12, day=31),
            'company': company,
            'post_move_sequence': Sequence.create([{
                'name': '%s' % date.year,
                'code': 'account.move',
                'company': company,
            }])[0],
            'out_invoice_sequence': invoice_sequence,
            'in_invoice_sequence': invoice_sequence,
            'out_credit_note_sequence': invoice_sequence,
            'in_credit_note_sequence': invoice_sequence,
        }])
        FiscalYear.create_period([fiscal_year])
        return fiscal_year

    def _create_coa_minimal(self, company):
        """Create a minimal chart of accounts
        """
        AccountTemplate = POOL.get('account.account.template')
        Account = POOL.get('account.account')

        account_create_chart = POOL.get(
            'account.create_chart', type="wizard")

        account_template, = AccountTemplate.search([
            ('parent', '=', None),
            ('name', '=', 'Minimal Account Chart'),
        ])

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
        return accounts[0] if accounts else False

    def _create_payment_term(self):
        """Create a simple payment term with all advance
        """
        PaymentTerm = POOL.get('account.invoice.payment_term')

        return PaymentTerm.create([{
            'name': 'Direct',
            'lines': [('create', [{'type': 'remainder'}])]
        }])

    def setup_defaults(self):
        """Creates default data for testing
        """
        currency, = self.Currency.create([{
            'name': 'US Dollar',
            'code': 'USD',
            'symbol': '$',
        }])

        with Transaction().set_context(company=None):
            company_party, = self.Party.create([{
                'name': 'Openlabs'
            }])
            employee_party, = self.Party.create([{
                'name': 'Jim'
            }])

        self.company, = self.Company.create([{
            'party': company_party,
            'currency': currency,
        }])

        self.employee, = self.Employee.create([{
            'party': employee_party.id,
            'company': self.company.id,
        }])

        self.User.write([self.User(USER)], {
            'company': self.company,
            'main_company': self.company,
            'employees': [('add', [self.employee.id])],
        })
        # Write employee separately as employees needs to be saved first
        self.User.write([self.User(USER)], {
            'employee': self.employee.id,
        })

        CONTEXT.update(self.User.get_preferences(context_only=True))

        # Create Fiscal Year
        self._create_fiscal_year(company=self.company.id)
        # Create Chart of Accounts
        self._create_coa_minimal(company=self.company.id)
        # Create a payment term
        self.payment_term, = self._create_payment_term()

        self.cash_journal, = self.Journal.search(
            [('type', '=', 'cash')], limit=1
        )
        self.Journal.write([self.cash_journal], {
            'debit_account': self._get_account_by_kind('other').id
        })

        self.uom, = self.Uom.search([('symbol', '=', 'd')])

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

        # Add address to company's party record
        self.Party.write([self.company.party], {
            'addresses': [('create', [{
                'name': 'Openlabs',
                'party': Eval('id'),
                'city': 'Los Angeles',
                'invoice': True,
                'country': self.country.id,
                'subdivision': self.subdivision.id,
            }])],
        })

        # Create party
        self.party, = self.Party.create([{
            'name': 'Bruce Wayne',
            'addresses': [('create', [{
                'name': 'Bruce Wayne',
                'party': Eval('id'),
                'city': 'Gotham',
                'invoice': True,
                'country': self.country.id,
                'subdivision': self.subdivision.id,
            }])],
            'customer_payment_term': self.payment_term.id,
            'account_receivable': self._get_account_by_kind(
                'receivable').id,
            'contact_mechanisms': [('create', [
                {'type': 'mobile', 'value': '8888888888'},
            ])],
        }])

        self.journal, = self.Journal.search([('type', '=', 'revenue')], limit=1)

        self.product_category, = self.ProductCategory.create([{
            'name': 'Test Category',
            'account_revenue': self._get_account_by_kind(
                'revenue', company=self.company.id).id,
            'account_expense': self._get_account_by_kind(
                'expense', company=self.company.id).id,
        }])

        self.product_template, = self.ProductTemplate.create([{
            'name': 'Bat Mobile',
            'type': 'goods',
            'list_price': Decimal('2000'),
            'cost_price': Decimal('1500'),
            'category': self.product_category.id,
            'default_uom': self.uom,
            'account_revenue': self._get_account_by_kind(
                'revenue', company=self.company.id).id,
            'account_expense': self._get_account_by_kind(
                'expense', company=self.company.id).id,
            'salable': True,
            'sale_uom': self.uom,
        }])

        self.product, = self.Product.create([{
            'template': self.product_template.id,
            'code': '123',
        }])

    def test_0010_test_sales_report_wizard(self):
        """
        Test the sales report wizard
        """
        ActionReport = POOL.get('ir.action.report')
        ReportWizard = POOL.get('report.sales.wizard', type="wizard")

        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.setup_defaults()

            sales_report_action, = ActionReport.search([
                ('report_name', '=', 'report.sales'),
                ('name', '=', 'Sales Report')
            ])
            sales_report_action.extension = 'pdf'
            sales_report_action.save()

            with Transaction().set_context({'company': self.company.id}):
                sale, = self.Sale.create([{
                    'reference': 'Test Sale',
                    'payment_term': self.payment_term,
                    'currency': self.company.currency.id,
                    'party': self.party.id,
                    'invoice_address': self.party.addresses[0],
                    'sale_date': date.today(),
                }])
                sale_line, = self.SaleLine.create([{
                    'type': 'line',
                    'quantity': 2,
                    'unit': self.uom,
                    'unit_price': 10000,
                    'description': 'Test description',
                    'product': self.product.id,
                    'sale': sale.id
                }])

                session_id, start_state, end_state = ReportWizard.create()
                result = ReportWizard.execute(session_id, {}, start_state)
                self.assertEqual(result.keys(), ['view'])
                self.assertEqual(result['view']['buttons'], [
                    {
                        'state': 'end',
                        'states': '{}',
                        'icon': 'tryton-cancel',
                        'default': False,
                        'string': 'Cancel',
                    }, {
                        'state': 'generate',
                        'states': '{}',
                        'icon': 'tryton-ok',
                        'default': True,
                        'string': 'Generate',
                    }
                ])
                data = {
                    start_state: {
                        'customer': self.party,
                        'product': self.product,
                        'start_date': date.today(),
                        'end_date': date.today(),
                    },
                }
                result = ReportWizard.execute(
                    session_id, data, 'generate'
                )
                self.assertEqual(len(result['actions']), 1)

                report_name = result['actions'][0][0]['report_name']
                report_data = result['actions'][0][1]

                SalesReport = POOL.get(report_name, type="report")

                # Set Pool.test as False as we need the report to be generated
                # as PDF
                # This is specifically to cover the PDF coversion code
                Pool.test = False

                val = SalesReport.execute([], report_data)

                # Revert Pool.test back to True for other tests to run normally
                Pool.test = True

                self.assert_(val)
                # Assert report type
                self.assertEqual(val[0], 'pdf')
                # Assert report name
                self.assertEqual(val[3], 'Sales Report')


def suite():
    "Define suite"
    test_suite = trytond.tests.test_tryton.suite()
    test_suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestSale)
    )
    return test_suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
