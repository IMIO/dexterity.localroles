# encoding: utf-8

from plone import api

from . import logger
from .utility import runRelatedSearch
from .utils import add_related_roles, del_related_roles, fti_configuration, get_state


def update_security(context, event):
    context.reindexObjectSecurity()


def local_role_configuration_updated(context, event):
    """ Reindex security for objects """
    portal = api.portal.getSite()
    logger.info('Objects security update')
    for brain in portal.portal_catalog(portal_type=context.fti.__name__):
        obj = brain.getObject()
        obj.reindexObjectSecurity()


def related_role_removal(context, state, fti_config):
    if state in fti_config['static_config']:
        dic = fti_config['static_config'][state]
        uid = context.UID()
        for princ in dic:
            if dic[princ].get('rel', ''):
                related = eval(dic[princ]['rel'])
                for rel_dic in related:
                    for obj in runRelatedSearch(rel_dic['utility'], context):
                        if del_related_roles(obj, uid):
                            obj.reindexObjectSecurity()


def related_role_addition(context, state, fti_config):
    if state in fti_config['static_config']:
        dic = fti_config['static_config'][state]
        uid = context.UID()
        for princ in dic:
            if dic[princ].get('rel', ''):
                related = eval(dic[princ]['rel'])
                for rel_dic in related:
                    if not rel_dic['roles']:
                        continue
                    for obj in runRelatedSearch(rel_dic['utility'], context):
                        add_related_roles(obj, uid, princ, rel_dic['roles'])
                        obj.reindexObjectSecurity()


def related_change_on_transition(context, event):
    """ Set local roles on related objects after transition """
    fti_config = fti_configuration(context)
    if 'static_config' not in fti_config:
        return
    if event.old_state.id != event.new_state.id:  # escape creation
        # We have to remove the configuration linked to old state
        related_role_removal(context, event.old_state.id, fti_config)
        # We have to add the configuration linked to new state
        related_role_addition(context, event.new_state.id, fti_config)


def related_change_on_removal(context, event):
    """ Set local roles on related objects after removal """
    fti_config = fti_configuration(context)
    if 'static_config' not in fti_config:
        return
    # We have to remove the configuration linked to deleted object
    # There is a problem in Plone 4.3. The event is notified before the confirmation and after too.
    # The action could be cancelled: we can't know this !! Resolved in Plone 5...
    # We choose to update related objects anyway !!
    related_role_removal(context, get_state(context), fti_config)


def related_change_on_addition(context, event):
    """ Set local roles on related objects after addition """
    fti_config = fti_configuration(context)
    if 'static_config' not in fti_config:
        return
    related_role_addition(context, get_state(context), fti_config)
