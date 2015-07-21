# -*- coding: utf-8 -*-
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
