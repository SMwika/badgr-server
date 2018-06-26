# encoding: utf-8
from __future__ import unicode_literals

import io
import json

import responses
from django.urls import reverse
from openbadges.verifier.openbadges_context import OPENBADGES_CONTEXT_V1_URI, OPENBADGES_CONTEXT_V2_URI, \
    OPENBADGES_CONTEXT_V2_DICT
from openbadges_bakery import unbake

from backpack.tests import setup_resources, setup_basic_1_0
from issuer.models import Issuer, BadgeInstance
from issuer.utils import CURRENT_OBI_VERSION, OBI_VERSION_CONTEXT_IRIS, UNVERSIONED_BAKED_VERSION
from mainsite.models import BadgrApp
from mainsite.tests import BadgrTestCase, SetupIssuerHelper
from mainsite.utils import OriginSetting

class ImportedAssertionsIssuedOnTests(BadgrTestCase, SetupIssuerHelper):
    """
    Tests whether correct_issued_on_imported_assertions()
    in tasks.py correctly fixes any imported assertions
    whose 'issuedOn' date is not correct.
    """
    def test_single_imported_assertion():
        
