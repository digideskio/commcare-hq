from collections import OrderedDict
from datetime import datetime

from django.core.management import call_command
from django.test import TestCase, override_settings

from mock import patch

from casexml.apps.case.const import ARCHIVED_CASE_OWNER_ID
from casexml.apps.case.sharedmodels import CommCareCaseIndex

from corehq.form_processor.interfaces.dbaccessors import CaseAccessors
from custom.enikshay.private_sector_datamigration.models import (
    Adherence,
    Agency,
    Beneficiary,
    EpisodePrescription,
    LabTest,
    Episode,
    UserDetail,
)
from custom.enikshay.tests.utils import ENikshayLocationStructureMixin


@override_settings(TESTS_SHOULD_USE_SQL_BACKEND=True)
class TestCreateCasesByBeneficiary(ENikshayLocationStructureMixin, TestCase):

    @classmethod
    def setUpClass(cls):
        cls.domain = 'test_domain'
        super(TestCreateCasesByBeneficiary, cls).setUpClass()
        cls.beneficiary = Beneficiary.objects.create(
            addressLineOne='585 Mass Ave',
            addressLineTwo='Suite 4',
            age=25,
            caseId='3',
            caseStatus='patient',
            configureAlert='Yes',
            creationDate=datetime(2017, 1, 1),
            dateOfRegn=datetime(2017, 4, 17),
            dob=datetime(1992, 1, 2),
            emergencyContactNo='1234567890',
            fatherHusbandName='Nick Sr.',
            firstName='Nick',
            gender='4',
            identificationNumber='98765',
            identificationTypeId='16',
            isActive=True,
            languagePreferences='132',
            lastName='P',
            organisationId=2,
            phoneNumber='5432109876',
            referredQP='org123'
        )
        cls.case_accessor = CaseAccessors(cls.domain)

        cls.agency = Agency.objects.create(
            agencyId=1,
            creationDate=datetime(2017, 5, 1),
            dateOfRegn=datetime(2017, 5, 1),
            modificationDate=datetime(2017, 5, 1),
            nikshayId='123456',
            organisationId=2,
            parentAgencyId=3,
            subOrganisationId=4,
        )
        UserDetail.objects.create(
            id=0,
            agencyId=cls.agency.agencyId,
            isPrimary=True,
            motechUserName='org123',
            organisationId=2,
            passwordResetFlag=False,
            pincode=3,
            subOrganisationId=4,
            userId=5,
            valid=True,
        )

    def setUp(self):
        super(TestCreateCasesByBeneficiary, self).setUp()

        self.pcp.site_code = self.agency.nikshayId
        self.pcp.save()

    @patch('custom.enikshay.private_sector_datamigration.factory.datetime')
    def test_create_cases_for_beneficiary(self, mock_datetime):
        mock_datetime.utcnow.return_value = datetime(2016, 9, 8, 1, 2, 3, 4123)

        Episode.objects.create(
            adherenceScore=0.5,
            alertFrequencyId=2,
            basisOfDiagnosis='Clinical - Other',
            beneficiaryID=self.beneficiary,
            creationDate=datetime(2017, 4, 20),
            dateOfDiagnosis=datetime(2017, 4, 18),
            diabetes='Yes',
            dstStatus='Rifampicin sensitive',
            episodeDisplayID=3,
            episodeID=6,
            extraPulmonary='Abdomen',
            hiv='Negative',
            lastMonthAdherencePct=0.6,
            lastTwoWeeksAdherencePct=0.7,
            missedDosesPct=0.8,
            newOrRetreatment='New',
            nikshayID='02139-02215',
            patientWeight=50,
            rxStartDate=datetime(2017, 4, 19),
            rxOutcomeDate=datetime(2017, 5, 19),
            site='Extrapulmonary',
            unknownAdherencePct=0.9,
            unresolvedMissedDosesPct=0.1,
        )
        call_command('create_cases_by_beneficiary', self.domain)

        person_case_ids = self.case_accessor.get_case_ids_in_domain(type='person')
        self.assertEqual(len(person_case_ids), 1)
        person_case = self.case_accessor.get_case(person_case_ids[0])
        self.assertFalse(person_case.closed)
        self.assertIsNone(person_case.external_id)
        self.assertEqual(person_case.name, 'Nick P')
        self.assertEqual(person_case.owner_id, self.pcp.location_id)
        self.assertEqual(person_case.dynamic_case_properties(), OrderedDict([
            ('aadhaar_number', '98765'),
            ('age', '25'),
            ('age_entered', '25'),
            ('current_address', '585 Mass Ave, Suite 4'),
            ('current_episode_type', 'confirmed_tb'),
            ('dataset', 'real'),
            ('diabetes_status', 'diabetic'),
            ('dob', '1992-01-02'),
            ('dob_entered', '1992-01-02'),
            ('dob_known', 'yes'),
            ('enrolled_in_private', 'true'),
            ('facility_assigned_to', self.pcp.location_id),
            ('first_name', 'Nick'),
            ('hiv_status', 'non_reactive'),
            ('husband_father_name', 'Nick Sr.'),
            ('is_active', 'yes'),
            ('language_preference', 'hin'),
            ('last_name', 'P'),
            ('migration_created_case', 'true'),
            ('migration_created_from_record', '3'),
            ('person_occurrence_count', '1'),
            ('phone_number', '5432109876'),
            ('secondary_phone', '1234567890'),
            ('send_alerts', 'yes'),
            ('sex', 'male'),
        ]))
        self.assertEqual(len(person_case.xform_ids), 1)

        occurrence_case_ids = self.case_accessor.get_case_ids_in_domain(type='occurrence')
        self.assertEqual(len(occurrence_case_ids), 1)
        occurrence_case = self.case_accessor.get_case(occurrence_case_ids[0])
        self.assertFalse(occurrence_case.closed)
        self.assertIsNone(occurrence_case.external_id)
        self.assertEqual(occurrence_case.name, 'Occurrence #1')
        self.assertEqual(occurrence_case.owner_id, '-')
        self.assertEqual(occurrence_case.dynamic_case_properties(), OrderedDict([
            ('current_episode_type', 'confirmed_tb'),
            ('migration_created_case', 'true'),
            ('migration_created_from_record', '3'),
            ('occurrence_episode_count', '1'),
            ('occurrence_id', '20160908010203004'),
        ]))
        self.assertEqual(len(occurrence_case.indices), 1)
        self._assertIndexEqual(
            occurrence_case.indices[0],
            CommCareCaseIndex(
                identifier='host',
                referenced_type='person',
                referenced_id=person_case.get_id,
                relationship='extension',
            )
        )
        self.assertEqual(len(occurrence_case.xform_ids), 1)

        episode_case_ids = self.case_accessor.get_case_ids_in_domain(type='episode')
        self.assertEqual(len(episode_case_ids), 1)
        episode_case = self.case_accessor.get_case(episode_case_ids[0])
        self.assertFalse(episode_case.closed)
        self.assertEqual(episode_case.external_id, '02139-02215')
        self.assertEqual(episode_case.name, 'Episode #1: Confirmed TB (Patient)')
        self.assertEqual(episode_case.opened_on, datetime(2017, 4, 19))
        self.assertEqual(episode_case.owner_id, '-')
        self.assertEqual(episode_case.dynamic_case_properties(), OrderedDict([
            ('basis_of_diagnosis', 'clinical_other'),
            ('case_definition', 'clinical'),
            ('date_of_diagnosis', '2017-04-18'),
            ('date_of_mo_signature', '2017-04-17'),
            ('disease_classification', 'extrapulmonary'),
            ('dots_99_enabled', 'false'),
            ('dst_status', 'rif_sensitive'),
            ('enrolled_in_private', 'true'),
            ('episode_details_complete', 'true'),
            ('episode_id', '20160908010203004'),
            ('episode_pending_registration', 'no'),
            ('episode_type', 'confirmed_tb'),
            ('migration_created_case', 'true'),
            ('migration_created_from_record', '3'),
            ('new_retreatment', 'new'),
            ('nikshay_id', '02139-02215'),
            ('patient_type', 'new'),
            ('retreatment_reason', ''),
            ('rx_outcome_date', '2017-05-19'),
            ('site', 'extrapulmonary'),
            ('site_choice', 'abdominal'),
            ('transfer_in', ''),
            ('treatment_card_completed_date', '2017-04-20'),
            ('treatment_initiated', 'yes_private'),
            ('treatment_initiation_date', '2017-04-19'),
            ('weight', '50'),
        ]))
        self.assertEqual(len(episode_case.indices), 1)
        self._assertIndexEqual(
            episode_case.indices[0],
            CommCareCaseIndex(
                identifier='host',
                referenced_type='occurrence',
                referenced_id=occurrence_case.get_id,
                relationship='extension',
            )
        )
        self.assertEqual(len(episode_case.xform_ids), 1)

    def test_beneficiary_cured(self):
        Episode.objects.create(
            adherenceScore=0.5,
            alertFrequencyId=2,
            basisOfDiagnosis='Clinical - Other',
            beneficiaryID=self.beneficiary,
            creationDate=datetime(2017, 4, 20),
            dateOfDiagnosis=datetime(2017, 4, 18),
            dstStatus='Rifampicin sensitive',
            episodeDisplayID=3,
            episodeID=6,
            extraPulmonary='Abdomen',
            hiv='Negative',
            lastMonthAdherencePct=0.6,
            lastTwoWeeksAdherencePct=0.7,
            missedDosesPct=0.8,
            newOrRetreatment='New',
            nikshayID='02139-02215',
            patientWeight=50,
            rxStartDate=datetime(2017, 4, 19),
            site='Extrapulmonary',
            treatmentOutcomeId='Cured',
            unknownAdherencePct=0.9,
            unresolvedMissedDosesPct=0.1,
        )
        call_command('create_cases_by_beneficiary', self.domain)

        person_case_ids = self.case_accessor.get_case_ids_in_domain(type='person')
        self.assertEqual(len(person_case_ids), 1)
        person_case = self.case_accessor.get_case(person_case_ids[0])
        self.assertFalse(person_case.closed)
        self.assertEqual(person_case.owner_id, ARCHIVED_CASE_OWNER_ID)
        self.assertEqual(person_case.dynamic_case_properties()['archive_reason'], 'cured')
        self.assertEqual(person_case.dynamic_case_properties()['is_active'], 'no')
        self.assertEqual(person_case.dynamic_case_properties()['last_owner'], self.pcp.location_id)
        self.assertTrue('last_reason_to_close' not in person_case.dynamic_case_properties())

        occurrence_case_ids = self.case_accessor.get_case_ids_in_domain(type='occurrence')
        self.assertEqual(1, len(occurrence_case_ids))
        occurrence_case = self.case_accessor.get_case(occurrence_case_ids[0])
        self.assertTrue(occurrence_case.closed)

        episode_case_ids = self.case_accessor.get_case_ids_in_domain(type='episode')
        self.assertEqual(len(episode_case_ids), 1)
        episode_case = self.case_accessor.get_case(episode_case_ids[0])
        self.assertTrue(episode_case.closed)
        self.assertEqual(episode_case.dynamic_case_properties()['treatment_outcome'], 'cured')

    def test_beneficiary_died(self):
        Episode.objects.create(
            adherenceScore=0.5,
            alertFrequencyId=2,
            basisOfDiagnosis='Clinical - Other',
            beneficiaryID=self.beneficiary,
            creationDate=datetime(2017, 4, 20),
            dateOfDiagnosis=datetime(2017, 4, 18),
            dstStatus='Rifampicin sensitive',
            episodeDisplayID=3,
            episodeID=6,
            extraPulmonary='Abdomen',
            hiv='Negative',
            lastMonthAdherencePct=0.6,
            lastTwoWeeksAdherencePct=0.7,
            missedDosesPct=0.8,
            newOrRetreatment='New',
            nikshayID='02139-02215',
            patientWeight=50,
            rxStartDate=datetime(2017, 4, 19),
            site='Extrapulmonary',
            treatmentOutcomeId='Died',
            unknownAdherencePct=0.9,
            unresolvedMissedDosesPct=0.1,
        )
        call_command('create_cases_by_beneficiary', self.domain)

        person_case_ids = self.case_accessor.get_case_ids_in_domain(type='person')
        self.assertEqual(len(person_case_ids), 1)
        person_case = self.case_accessor.get_case(person_case_ids[0])
        self.assertTrue(person_case.closed)
        self.assertEqual(person_case.owner_id, ARCHIVED_CASE_OWNER_ID)
        self.assertEqual(person_case.dynamic_case_properties()['archive_reason'], 'died')
        self.assertEqual(person_case.dynamic_case_properties()['is_active'], 'no')
        self.assertEqual(person_case.dynamic_case_properties()['last_owner'], self.pcp.location_id)
        self.assertEqual(person_case.dynamic_case_properties()['last_reason_to_close'], 'died')

        occurrence_case_ids = self.case_accessor.get_case_ids_in_domain(type='occurrence')
        self.assertEqual(1, len(occurrence_case_ids))
        occurrence_case = self.case_accessor.get_case(occurrence_case_ids[0])
        self.assertTrue(occurrence_case.closed)

        episode_case_ids = self.case_accessor.get_case_ids_in_domain(type='episode')
        self.assertEqual(len(episode_case_ids), 1)
        episode_case = self.case_accessor.get_case(episode_case_ids[0])
        self.assertTrue(episode_case.closed)
        self.assertEqual(episode_case.dynamic_case_properties()['treatment_outcome'], 'died')

    def test_adherence(self):
        episode = Episode.objects.create(
            adherenceScore=0.5,
            alertFrequencyId=2,
            basisOfDiagnosis='Clinical - Other',
            beneficiaryID=self.beneficiary,
            creationDate=datetime(2017, 4, 20),
            dateOfDiagnosis=datetime(2017, 4, 18),
            dstStatus='Rifampicin sensitive',
            episodeDisplayID=3,
            episodeID=1,
            extraPulmonary='Abdomen',
            hiv='Negative',
            lastMonthAdherencePct=0.6,
            lastTwoWeeksAdherencePct=0.7,
            missedDosesPct=0.8,
            newOrRetreatment='New',
            nikshayID='02139-02215',
            patientWeight=50,
            rxStartDate=datetime(2017, 4, 19),
            site='Extrapulmonary',
            unknownAdherencePct=0.9,
            unresolvedMissedDosesPct=0.1,
        )
        Adherence.objects.create(
            adherenceId=5,
            creationDate=datetime(2017, 4, 21),
            dosageStatusId=0,
            doseDate=datetime(2017, 4, 22),
            doseReasonId=3,
            episodeId=episode,
            reportingMechanismId=4,
        )

        call_command('create_cases_by_beneficiary', self.domain)

        self.assertEqual(len(self.case_accessor.get_case_ids_in_domain(type='person')), 1)
        self.assertEqual(len(self.case_accessor.get_case_ids_in_domain(type='occurrence')), 1)
        episode_case_ids = self.case_accessor.get_case_ids_in_domain(type='episode')
        self.assertEqual(len(episode_case_ids), 1)
        episode_case = self.case_accessor.get_case(episode_case_ids[0])

        adherence_case_ids = self.case_accessor.get_case_ids_in_domain(type='adherence')
        self.assertEqual(len(adherence_case_ids), 1)
        adherence_case = self.case_accessor.get_case(adherence_case_ids[0])
        self.assertFalse(adherence_case.closed)  # TODO
        self.assertIsNone(adherence_case.external_id)
        self.assertEqual(adherence_case.name, '2017-04-22')
        self.assertEqual(adherence_case.opened_on, datetime(2017, 4, 21))
        self.assertEqual(adherence_case.owner_id, '-')
        self.assertEqual(adherence_case.dynamic_case_properties(), OrderedDict([
            ('adherence_date', '2017-04-22'),
            ('adherence_value', 'directly_observed_dose'),
            ('migration_created_case', 'true'),
            ('migration_created_from_record', '5'),
        ]))
        self.assertEqual(len(adherence_case.indices), 1)
        self._assertIndexEqual(
            adherence_case.indices[0],
            CommCareCaseIndex(
                identifier='host',
                referenced_type='episode',
                referenced_id=episode_case.get_id,
                relationship='extension',
            )
        )
        self.assertEqual(len(adherence_case.xform_ids), 1)

    def test_multiple_adherences(self):
        episode = Episode.objects.create(
            id=1,
            adherenceScore=0.5,
            alertFrequencyId=2,
            basisOfDiagnosis='Clinical - Other',
            beneficiaryID=self.beneficiary,
            creationDate=datetime(2017, 4, 20),
            dateOfDiagnosis=datetime(2017, 4, 18),
            dstStatus='Rifampicin sensitive',
            episodeDisplayID=3,
            extraPulmonary='Abdomen',
            hiv='Negative',
            lastMonthAdherencePct=0.6,
            lastTwoWeeksAdherencePct=0.7,
            missedDosesPct=0.8,
            newOrRetreatment='New',
            nikshayID='02139-02215',
            patientWeight=50,
            rxStartDate=datetime(2017, 4, 19),
            site='Extrapulmonary',
            unknownAdherencePct=0.9,
            unresolvedMissedDosesPct=0.1,
        )
        Adherence.objects.create(
            adherenceId=1,
            creationDate=datetime(2017, 4, 21),
            dosageStatusId=0,
            doseDate=datetime.utcnow(),
            doseReasonId=3,
            episodeId=episode,
            reportingMechanismId=4,
        )
        Adherence.objects.create(
            adherenceId=2,
            creationDate=datetime(2017, 4, 21),
            dosageStatusId=1,
            doseDate=datetime.utcnow(),
            doseReasonId=3,
            episodeId=episode,
            reportingMechanismId=4,
        )

        call_command('create_cases_by_beneficiary', self.domain)

        self.assertEqual(len(self.case_accessor.get_case_ids_in_domain(type='person')), 1)
        self.assertEqual(len(self.case_accessor.get_case_ids_in_domain(type='occurrence')), 1)
        self.assertEqual(len(self.case_accessor.get_case_ids_in_domain(type='episode')), 1)
        self.assertEqual(len(self.case_accessor.get_case_ids_in_domain(type='adherence')), 2)

    def test_prescription(self):
        EpisodePrescription.objects.create(
            id=1,
            beneficiaryId=self.beneficiary,
            numberOfDays=2,
            prescriptionID=3,
            pricePerUnit=0.5,
            productID=4,
            productName='drug name',
            refill_Index=5,
            voucherID=6,
        )

        call_command('create_cases_by_beneficiary', self.domain)

        self.assertEqual(len(self.case_accessor.get_case_ids_in_domain(type='person')), 1)
        self.assertEqual(len(self.case_accessor.get_case_ids_in_domain(type='occurrence')), 1)
        episode_case_ids = self.case_accessor.get_case_ids_in_domain(type='episode')
        self.assertEqual(len(episode_case_ids), 1)
        episode_case = self.case_accessor.get_case(episode_case_ids[0])

        prescription_case_ids = self.case_accessor.get_case_ids_in_domain(type='prescription')
        self.assertEqual(len(prescription_case_ids), 1)
        prescription_case = self.case_accessor.get_case(prescription_case_ids[0])
        self.assertFalse(prescription_case.closed)  # TODO
        self.assertIsNone(prescription_case.external_id)
        self.assertEqual(prescription_case.name, 'drug name')
        # self.assertEqual(adherence_case.opened_on, '')  # TODO
        self.assertEqual(prescription_case.owner_id, '-')
        self.assertEqual(prescription_case.dynamic_case_properties(), OrderedDict([
            ('migration_created_case', 'true'),
            ('migration_created_from_record', '3'),
        ]))
        self.assertEqual(len(prescription_case.indices), 1)
        self._assertIndexEqual(
            prescription_case.indices[0],
            CommCareCaseIndex(
                identifier='episode_of_prescription',
                referenced_type='episode',
                referenced_id=episode_case.get_id,
                relationship='extension',
            )
        )
        self.assertEqual(len(prescription_case.xform_ids), 1)

    def test_multiple_prescriptions(self):
        EpisodePrescription.objects.create(
            id=1,
            beneficiaryId=self.beneficiary,
            numberOfDays=2,
            prescriptionID=3,
            pricePerUnit=0.5,
            productID=4,
            refill_Index=5,
            voucherID=6,
        )
        EpisodePrescription.objects.create(
            id=2,
            beneficiaryId=self.beneficiary,
            numberOfDays=2,
            prescriptionID=3,
            pricePerUnit=0.5,
            productID=4,
            refill_Index=5,
            voucherID=6,
        )

        call_command('create_cases_by_beneficiary', self.domain)

        self.assertEqual(len(self.case_accessor.get_case_ids_in_domain(type='person')), 1)
        self.assertEqual(len(self.case_accessor.get_case_ids_in_domain(type='occurrence')), 1)
        self.assertEqual(len(self.case_accessor.get_case_ids_in_domain(type='episode')), 1)
        self.assertEqual(len(self.case_accessor.get_case_ids_in_domain(type='prescription')), 2)

    def test_labtest(self):
        episode = Episode.objects.create(
            id=1,
            adherenceScore=0.5,
            alertFrequencyId=2,
            basisOfDiagnosis='Clinical - Other',
            beneficiaryID=self.beneficiary,
            creationDate=datetime(2017, 4, 20),
            dateOfDiagnosis=datetime(2017, 4, 18),
            dstStatus='Rifampicin sensitive',
            episodeDisplayID=3,
            hiv='Negative',
            lastMonthAdherencePct=0.6,
            lastTwoWeeksAdherencePct=0.7,
            missedDosesPct=0.8,
            patientWeight=50,
            rxStartDate=datetime(2017, 4, 19),
            site='Extrapulmonary',
            unknownAdherencePct=0.9,
            unresolvedMissedDosesPct=0.1,
        )
        LabTest.objects.create(
            id=1,
            episodeId=episode,
            labId=2,
            tbStatusId=3,
            testId=4,
            testSiteId=5,
            testSiteSpecimenId=6,
            testSpecimenId=7,
            treatmentCardId=8,
            treatmentFileId=9,
            voucherNumber=10,
        )

        call_command('create_cases_by_beneficiary', self.domain)

        self.assertEqual(len(self.case_accessor.get_case_ids_in_domain(type='person')), 1)
        occurrence_case_ids = self.case_accessor.get_case_ids_in_domain(type='occurrence')
        self.assertEqual(len(occurrence_case_ids), 1)
        self.assertEqual(len(self.case_accessor.get_case_ids_in_domain(type='episode')), 1)

        test_case_ids = self.case_accessor.get_case_ids_in_domain(type='test')
        self.assertEqual(len(test_case_ids), 1)
        test_case = self.case_accessor.get_case(test_case_ids[0])
        self.assertFalse(test_case.closed)  # TODO
        self.assertIsNone(test_case.external_id)
        self.assertEqual(test_case.name, None)  # TODO
        # self.assertEqual(adherence_case.opened_on, '')  # TODO
        self.assertEqual(test_case.owner_id, '-')
        self.assertEqual(test_case.dynamic_case_properties(), OrderedDict([
            ('migration_created_case', 'true'),
        ]))
        self.assertEqual(len(test_case.indices), 1)
        self._assertIndexEqual(
            test_case.indices[0],
            CommCareCaseIndex(
                identifier='host',
                referenced_type='occurrence',
                referenced_id=occurrence_case_ids[0],
                relationship='extension',
            )
        )
        self.assertEqual(len(test_case.xform_ids), 1)

    def test_multiple_labtests(self):
        episode = Episode.objects.create(
            id=1,
            adherenceScore=0.5,
            alertFrequencyId=2,
            basisOfDiagnosis='Clinical - Other',
            beneficiaryID=self.beneficiary,
            creationDate=datetime(2017, 4, 20),
            dateOfDiagnosis=datetime(2017, 4, 18),
            dstStatus='Rifampicin sensitive',
            episodeDisplayID=3,
            hiv='Negative',
            lastMonthAdherencePct=0.6,
            lastTwoWeeksAdherencePct=0.7,
            missedDosesPct=0.8,
            patientWeight=50,
            rxStartDate=datetime(2017, 4, 19),
            site='Extrapulmonary',
            unknownAdherencePct=0.9,
            unresolvedMissedDosesPct=0.1,
        )
        LabTest.objects.create(
            id=1,
            episodeId=episode,
            labId=2,
            tbStatusId=3,
            testId=4,
            testSiteId=5,
            testSiteSpecimenId=6,
            testSpecimenId=7,
            treatmentCardId=8,
            treatmentFileId=9,
            voucherNumber=10,
        )
        LabTest.objects.create(
            id=2,
            episodeId=episode,
            labId=2,
            tbStatusId=3,
            testId=4,
            testSiteId=5,
            testSiteSpecimenId=6,
            testSpecimenId=7,
            treatmentCardId=8,
            treatmentFileId=9,
            voucherNumber=10,
        )

        call_command('create_cases_by_beneficiary', self.domain)

        self.assertEqual(len(self.case_accessor.get_case_ids_in_domain(type='person')), 1)
        self.assertEqual(len(self.case_accessor.get_case_ids_in_domain(type='occurrence')), 1)
        self.assertEqual(len(self.case_accessor.get_case_ids_in_domain(type='episode')), 1)
        self.assertEqual(len(self.case_accessor.get_case_ids_in_domain(type='test')), 2)

    def _assertIndexEqual(self, index_1, index_2):
        self.assertEqual(index_1.identifier, index_2.identifier)
        self.assertEqual(index_1.referenced_type, index_2.referenced_type)
        self.assertEqual(index_1.referenced_id, index_2.referenced_id)
        self.assertEqual(index_1.relationship, index_2.relationship)
