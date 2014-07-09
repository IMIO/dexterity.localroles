# encoding: utf-8

from Products.CMFPlone.utils import base_hasattr
from collective.z3cform.datagridfield import DataGridFieldFactory
from collective.z3cform.datagridfield import DictRow
from copy import deepcopy
from five import grok
from plone import api
from plone.app.dexterity.browser.layout import TypeFormLayout
from plone.app.dexterity.interfaces import ITypeSchemaContext
from z3c.form import field
from z3c.form import form
from z3c.form.browser.checkbox import CheckBoxWidget
from z3c.form.interfaces import IFieldWidget
from z3c.form.interfaces import IFormLayer
from z3c.form.interfaces import ITerms
from z3c.form.interfaces import IWidget
from z3c.form.term import ChoiceTermsVocabulary
from z3c.form.widget import FieldWidget
from zope import schema
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import adapts
from zope.i18nmessageid import MessageFactory
from zope.interface import Interface
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import SimpleVocabulary

from dexterity.localroles import _

PMF = MessageFactory('plone')


def list_2_vocabulary(elements):
    terms = []
    for item in elements:
        term = SimpleVocabulary.createTerm(item[0],
                                           item[0],
                                           item[1])
        terms.append(term)
    return SimpleVocabulary(terms)


class IStateField(Interface):
    pass


class IRoleField(Interface):
    pass


class StateField(schema.Choice):
    grok.implements(IStateField)

    def __init__(self, *args, **kwargs):
        kwargs['vocabulary'] = u''
        super(StateField, self).__init__(*args, **kwargs)

    def bind(self, object):
        return super(schema.Choice, self).bind(object)


class RoleField(schema.List):
    grok.implements(IRoleField)


@grok.adapter(IRoleField, IFormLayer)
@grok.implementer(IFieldWidget)
def role_widget(field, request):
    return FieldWidget(field, CheckBoxWidget(request))


class StateTerms(ChoiceTermsVocabulary, grok.MultiAdapter):
    grok.implements(ITerms)
    grok.adapts(Interface,
                IFormLayer,
                Interface,
                IStateField,
                IWidget)

    def __init__(self, context, request, form, field, widget):
        self.context = context
        self.request = request
        self.form = form
        self.field = field
        self.widget = widget

        portal_type = self.form.parentForm.context
        portal_workflow = portal_type.portal_workflow
        workflow = portal_workflow.getWorkflowsFor(portal_type.__name__)[0]

        self.terms = list_2_vocabulary([(s, s) for s in workflow.states])
        field.vocabulary = self.terms


@grok.provider(IContextSourceBinder)
def plone_role_generator(context):
    portal = api.portal.getSite()
    roles = []
    filtered_roles = ['Anonymous', 'Authenticated', 'Manager', 'Member', 'Site Administrator']
    for role in portal.__ac_roles__:
        if role not in filtered_roles:
            roles.append((role, PMF(role)))
    return list_2_vocabulary(sorted(roles))


class IFieldRole(Interface):
    state = StateField(title=_(u'state'), required=True)

    value = schema.TextLine(title=_(u'value'))

    roles = RoleField(title=_(u'roles'),
                      value_type=schema.Choice(source=plone_role_generator),
                      required=True)


class RoleFieldConfigurationAdapter(object):
    adapts(ITypeSchemaContext)

    def __init__(self, context):
        self.__dict__['context'] = context
        self.__dict__['fti'] = self.context.fti

    def __getattr__(self, name):
        if not base_hasattr(self.context.fti, name) \
           or not isinstance(getattr(self.context.fti, name), dict):
            raise AttributeError
        value = getattr(self.context.fti, name)
        return self.convert_to_list(value)

    def __setattr__(self, name, value):
        old_value = getattr(self.context.fti, name, {})
        new_dict = self.convert_to_dict(value)
        if old_value == new_dict:
            return
        setattr(self.context.fti, name, new_dict)

    @staticmethod
    def convert_to_dict(value):
        value_dict = {}
        for row in value:
            state, roles, principal = row.values()
            if state not in value_dict:
                value_dict[state] = {'users': {}, 'groups': {}}
            if api.user.get(username=principal) is not None:
                value_dict[state]['users'][principal] = roles
            elif api.group.get(groupname=principal) is not None:
                value_dict[state]['groups'][principal] = roles
        return value_dict

    @staticmethod
    def convert_to_list(value):
        value_list = []
        for state_key, state in sorted(value.items()):
            for username, roles in sorted(state.get('users').items()):
                value_list.append({'state': state_key, 'roles': roles,
                                   'value': username})
            for groupname, roles in sorted(state.get('groups').items()):
                value_list.append({'state': state_key, 'roles': roles,
                                   'value': groupname})
        return value_list


class RoleFieldConfigurationForm(form.EditForm):
    template = ViewPageTemplateFile('templates/role-config.pt')
    label = _(u'Role field configuration')
    successMessage = _(u'Role fields configurations successfully updated.')
    noChangesMessage = _(u'No changes were made.')
    buttons = deepcopy(form.EditForm.buttons)
    buttons['apply'].title = PMF(u'Save')

    def update(self):
        super(RoleFieldConfigurationForm, self).update()

    def updateWidgets(self):
        super(RoleFieldConfigurationForm, self).updateWidgets()

    def getContent(self):
        return RoleFieldConfigurationAdapter(self.context)

    @property
    def fields(self):
        fields = [
            schema.List(
                __name__='localroleconfig',
                title=_(u'Local role configuration'),
                description=u'',
                value_type=DictRow(title=u"fieldconfig", schema=IFieldRole))
        ]
        fields = sorted(fields, key=lambda x: x.title)
        fields = field.Fields(*fields)

        for f in fields.values():
            f.widgetFactory = DataGridFieldFactory
        return fields


class RoleConfigurationPage(TypeFormLayout):
    form = RoleFieldConfigurationForm
    label = _(u'Role field configuration')
