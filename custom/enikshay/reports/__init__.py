from custom.enikshay.reports.case_finding import CaseFindingReport
from custom.enikshay.reports.historical_adherence import HistoricalAdherenceReport
from custom.enikshay.reports.treatment_outcome import TreatmentOutcomeReport
from custom.enikshay.reports.web_dashboard import WebDashboardReport
from custom.enikshay.reports.repeaters import ENikshayForwarderReport


CUSTOM_REPORTS = (
    ('Custom Reports', (
        WebDashboardReport,
        CaseFindingReport,
        TreatmentOutcomeReport,
        HistoricalAdherenceReport,
        ENikshayForwarderReport,
    )),
)
