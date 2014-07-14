# -*- coding: utf-8 -*-
from zope.component import getUtility
from zope.component.interfaces import ComponentLookupError

from Products.CMFPlone.utils import base_hasattr
from plone.dexterity.interfaces import IDexterityFTI

from . import logger


def add_fti_configuration(portal_type, configuration, force=False):
    """
        Add in fti a specific localroles configuration
    """
    try:
        fti = getUtility(IDexterityFTI, name=portal_type)
    except ComponentLookupError:
        logger.error("The portal type '%s' doesn't exist" % portal_type)
        return "The portal type '%s' doesn't exist" % portal_type
    if base_hasattr(fti, 'localroleconfig') and not force:
        logger.warn("The localroleconfig configuration on type '%s' is already set" % (portal_type))
        return "The localroleconfig configuration on type '%s' is already set" % (portal_type)
    setattr(fti, 'localroleconfig', configuration)