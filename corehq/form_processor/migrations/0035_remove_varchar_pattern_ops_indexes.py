# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

from corehq.sql_db.operations import HqRunSQL


class Migration(migrations.Migration):

    dependencies = [
        ('form_processor', '0034_location_id_index'),
    ]

    NOOP_REVERSE = 'SELECT 1'
    operations = [
        HqRunSQL(
            'DROP INDEX IF EXISTS form_processor_caseattachmentsql_attachment_uuid_8d145664_like',
            NOOP_REVERSE
        ),
        HqRunSQL(
            'DROP INDEX IF EXISTS form_processor_xforminstancesql_form_uuid_12662b9ceadeeecc_like',
            NOOP_REVERSE
        ),
        HqRunSQL(
            'DROP INDEX IF EXISTS form_processor_xformattachmentsql_attachment_uuid_51177a7e_like',
            NOOP_REVERSE,
        ),
        HqRunSQL(
            'DROP INDEX IF EXISTS form_processor_xformattachmentsql_name_4b9f1b0d840a70bc_like',
            NOOP_REVERSE
        ),
        HqRunSQL(
            'DROP INDEX IF EXISTS form_processor_xformoperationsql_xform_id_14e64e95f71c3764_like',
            NOOP_REVERSE
        ),
    ]
