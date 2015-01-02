# -*- coding: utf-8 -*-
"""
    __init__.py

    :copyright: (c) 2015 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.pool import Pool
from sale import SalesReport, SalesReportWizardStart, SalesReportWizard


def register():
    Pool.register(
        SalesReportWizardStart,
        module='sales_reports', type_='model'
    )
    Pool.register(
        SalesReport,
        module='sales_reports', type_='report'
    )
    Pool.register(
        SalesReportWizard,
        module='sales_reports', type_='wizard'
    )
