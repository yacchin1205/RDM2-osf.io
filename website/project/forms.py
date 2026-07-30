# -*- coding: utf-8 -*-
from framework.forms import Form, BooleanField, validators
from wtforms import StringField

###############################################################################
# Forms
###############################################################################


class NewNodeForm(Form):
    title = StringField('Title', [
        validators.DataRequired(message=u'Title is required'),
        validators.Length(min=1, message=u'Title must contain at least 1 character.'),
        validators.Length(max=200, message=u'Title must contain fewer than 200 characters.')
    ])
    description = StringField('Description')
    category = StringField('Category')
    inherit_contributors = BooleanField('Inherit')
