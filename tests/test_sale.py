# -*- coding: utf-8 -*-
import unittest
import sys
import os
from datetime import date

import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, with_transaction
from trytond.transaction import Transaction
from trytond.pool import Pool
from test_base import BaseTestCase

DIR = os.path.abspath(os.path.normpath(os.path.join(
    __file__, '..', '..', '..', '..', '..', 'trytond'
)))
if os.path.isdir(DIR):
    sys.path.insert(0, os.path.dirname(DIR))


class TestSale(BaseTestCase):
    """
    Sale tests for Sales Report module
    """
    @with_transaction()
    @unittest.skipIf(sys.platform == 'darwin', 'wkhtmltopdf repo on OSX')
    def test_0010_test_sales_report_wizard(self):
        """
        Test the sales report wizard
        """
        ActionReport = POOL.get('ir.action.report')
        ReportWizard = POOL.get('report.sales.wizard', type="wizard")

        self.Sale = POOL.get('sale.sale')
        self.SaleLine = POOL.get('sale.line')
        self.setup_defaults()
        sales_report_action, = ActionReport.search([
            ('report_name', '=', 'report.sales'),
            ('name', '=', 'Sales Report')
        ])
        sales_report_action.extension = 'pdf'
        sales_report_action.save()

        with Transaction().set_context({
            'company': self.company.id,
            'channel': self.channel.id}
        ):
            sale, = self.Sale.create([{
                'reference': 'Test Sale',
                'payment_term': self.payment_term.id,
                'currency': self.company.currency.id,
                'party': self.party.id,
                'invoice_address': self.party.addresses[0],
                'sale_date': date.today(),
                'state': 'confirmed',
                'shipment_address': self.party.addresses[0],
                'channel': self.channel.id
            }])
            sale_line, = self.SaleLine.create([{
                'type': 'line',
                'quantity': 2,
                'product': self.product,
                'unit': self.uom,
                'unit_price': 10000,
                'description': 'Test description',
                'sale': sale.id,
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
                    'channel': self.channel,
                    'sale': sale.id,
                    'detailed_payments': False,
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
