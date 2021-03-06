from datetime import datetime
import json

from flask import flash, url_for, request
from flask_admin import BaseView, expose
from flask_admin.contrib.sqla.filters import FilterEqual
from flask_admin.helpers import is_form_submitted
from flask_admin.model.template import macro

from flask_admin.contrib.sqla import ModelView
from invenio_db import db
from invenio_records import Record
from invenio_records.models import RecordMetadata
from jsonschema import ValidationError
from sqlalchemy import cast
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import SQLAlchemyError

from scoap3.modules.records.tasks import perform_article_check


class FilterByControlNumber(FilterEqual):
    def apply(self, query, value, alias=None):
        return query.filter(RecordMetadata.json['control_number'] == cast(value, JSONB))


class FilterByDoi(FilterEqual):
    def apply(self, query, value, alias=None):
        return query.filter(RecordMetadata.json['dois'][0]['value'] == cast(value, JSONB))


class RecordModelView(ModelView):
    """Records admin model view."""

    can_create = False
    can_edit = True
    can_delete = True
    can_view_details = False

    column_list = ('control_number', 'doi', 'active', 'title', 'id', 'created', 'updated', )
    column_formatters = {
        'control_number': macro('render_control_number'),
        'active': macro('render_active'),
        'title': macro('render_title'),
        'doi': macro('render_doi'),
    }
    column_filters = (
        FilterByControlNumber(column=None, name='Control number'),
        FilterByDoi(column=None, name='DOI')
    )

    page_size = 25

    edit_template = 'scoap3_records/admin/record_edit.html'
    list_template = 'scoap3_records/admin/record_list.html'

    def get_save_return_url(self, model, is_created=False):
        return url_for('record.edit_view', id=model.id)

    def validate_form(self, form):
        """Override base validation as the validation is done at a later step."""
        return is_form_submitted()

    def update_model(self, form, model):
        """Update the metadata for a record."""

        try:
            new_json_data = request.form.get('json')
            if new_json_data:
                record = Record(model.json, model=model)
                record.clear()
                record.update(json.loads(new_json_data))
                record.commit()
                self.session.commit()
        except ValidationError as ex:
            flash('Failed to update record, provided metadata is invalid: %s' % ex.message, 'error')
            return False
        except Exception as ex:
            if not self.handle_view_exception(ex):
                flash('Failed to update record. %s' % str(ex), 'error')

            self.session.rollback()
            return False
        else:
            self.after_model_change(form, model, False)

        return True

    def delete_model(self, model):
        """Delete a record."""
        try:
            if model.json is None:
                return True
            record = Record(model.json, model=model)
            record.delete()
            db.session.commit()

        except SQLAlchemyError as e:
            if not self.handle_view_exception(e):
                flash('Failed to delete record. %s' % str(e), category='error')
            db.session.rollback()
            return False

        return True


class RecordsDashboard(BaseView):
    @expose('/', methods=('GET',))
    def index(self):
        return self.render('scoap3_records/admin/dashboard.html')

    @staticmethod
    def run_article_check(from_date):
        if not from_date:
            flash("From date is required to run article check.", 'error')
            return False

        try:
            datetime.strptime(from_date, '%Y-%m-%d')
        except ValueError:
            flash('"%s" is invalid date parameter. It has to be in YYYY-mm-dd format.' % from_date, 'error')
            return False

        perform_article_check.apply_async((from_date,))
        flash("Article check started. The result will be sent out in an email.", 'success')
        return True

    @expose('/', methods=('POST',))
    def index_post(self):
        if 'run_article_check' in request.form:
            from_date = request.form.get('from_date')
            self.run_article_check(from_date)

        return self.index()


record_dashboard = {
    'view_class': RecordsDashboard,
    'kwargs': {'category': 'Records', 'name': 'Dashboard'},
}


record_adminview = {
    "modelview": RecordModelView,
    "model": RecordMetadata,
    "category": 'Records',
    "name": 'Edit records',
    "endpoint": 'record',
}


__all__ = (
    'record_adminview',
    'record_dashboard',
)
