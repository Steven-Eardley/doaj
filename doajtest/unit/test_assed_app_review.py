from doajtest.helpers import DoajTestCase
from doajtest.fixtures import ApplicationFixtureFactory

import time
from copy import deepcopy

from portality import models
from portality.formcontext import formcontext
from portality import lcc

from werkzeug.datastructures import MultiDict

#####################################################################
# Mocks required to make some of the lookups work
#####################################################################

@classmethod
def editor_group_pull(cls, field, value):
    eg = models.EditorGroup()
    eg.set_editor("eddie")
    eg.set_associates(["associate", "assan"])
    eg.set_name("Test Editor Group")
    return eg

mock_lcc_choices = [
    (u'H', u'Social Sciences'),
    (u'HB1-3840', u'--Economic theory. Demography')
]

def mock_lookup_code(code):
    if code == "H": return "Social Sciences"
    if code == "HB1-3840": return "Economic theory. Demography"
    return None


APPLICATION_SOURCE = ApplicationFixtureFactory.make_application_source()
APPLICATION_FORM = ApplicationFixtureFactory.make_application_form()
del APPLICATION_FORM["editor_group"]

######################################################
# Main test class
######################################################

class TestAssedAppReview(DoajTestCase):

    def setUp(self):
        super(TestAssedAppReview, self).setUp()

        self.editor_group_pull = models.EditorGroup.pull_by_key
        models.EditorGroup.pull_by_key = editor_group_pull

        self.old_lcc_choices = lcc.lcc_choices
        lcc.lcc_choices = mock_lcc_choices

        self.old_lookup_code = lcc.lookup_code
        lcc.lookup_code = mock_lookup_code

    def tearDown(self):
        super(TestAssedAppReview, self).tearDown()

        models.EditorGroup.pull_by_key = self.editor_group_pull
        lcc.lcc_choices = self.old_lcc_choices

        lcc.lookup_code = self.old_lookup_code


    ###########################################################
    # Tests on the associate editor's reapplication form
    ###########################################################

    def test_01_editor_review_success(self):
        """Give the editor's reapplication form a full workout"""
        acc = models.Account()
        acc.set_id("richard")
        acc.add_role("associate_editor")
        ctx = self._make_and_push_test_context(acc=acc)

        # we start by constructing it from source
        fc = formcontext.ApplicationFormFactory.get_form_context(role="associate_editor", source=models.Suggestion(**APPLICATION_SOURCE))
        assert isinstance(fc, formcontext.AssEdApplicationReview)
        assert fc.form is not None
        assert fc.source is not None
        assert fc.form_data is None
        assert fc.template is not None

        # check that we can render the form
        # FIXME: we can't easily render the template - need to look into Flask-Testing for this
        # html = fc.render_template(edit_suggestion=True)
        html = fc.render_field_group("status")
        assert html is not None
        assert html != ""

        # now construct it from form data (with a known source)
        fc = formcontext.ApplicationFormFactory.get_form_context(
            role="associate_editor",
            form_data=MultiDict(APPLICATION_FORM) ,
            source=models.Suggestion(**APPLICATION_SOURCE))

        assert isinstance(fc, formcontext.AssEdApplicationReview)
        assert fc.form is not None
        assert fc.source is not None
        assert fc.form_data is not None

        # test each of the workflow components individually ...

        # pre-validate and check this doesn't cause errors
        fc.pre_validate()

        # run the validation itself
        fc.form.subject.choices = mock_lcc_choices # set the choices allowed for the subject manually (part of the test)
        assert fc.validate(), fc.form.errors

        # run the crosswalk (no need to look in detail, xwalks are tested elsewhere)
        fc.form2target()
        assert fc.target is not None

        # patch the target with data from the source
        fc.patch_target()
        assert fc.target.created_date == "2000-01-01T00:00:00Z"
        assert fc.target.id == "abcdefghijk"
        assert len(fc.target.notes) == 2
        assert fc.target.owner == "Owner"
        assert fc.target.editor_group == "editorgroup"
        assert fc.target.editor == "associate"
        assert fc.target.application_status == "pending", fc.target.application_status # is updated by the form
        assert fc.target.bibjson().replaces == ["1111-1111"]
        assert fc.target.bibjson().is_replaced_by == ["2222-2222"]
        assert fc.target.bibjson().discontinued_date == "2001-01-01"

        # now do finalise (which will also re-run all of the steps above)
        fc.finalise()

        time.sleep(2)

        # now check that a provenance record was recorded
        prov = models.Provenance.get_latest_by_resource_id(fc.target.id)
        assert prov is not None

        ctx.pop()

    def test_02_classification_required(self):
        # Check we can mark an application 'completed' with a subject classification present
        in_progress_application = models.Suggestion(**ApplicationFixtureFactory.make_application_source())
        in_progress_application.set_application_status("in progress")

        fc = formcontext.ApplicationFormFactory.get_form_context(role='associate_editor', source=in_progress_application)

        # Make changes to the application status via the form, check it validates
        fc.form.application_status.data = "completed"

        assert fc.validate()

        # Without a subject classification, we should not be able to set the status to 'completed'
        no_class_application = models.Suggestion(**ApplicationFixtureFactory.make_application_source())
        del no_class_application.data['bibjson']['subject']
        fc = formcontext.ApplicationFormFactory.get_form_context(role='associate_editor', source=no_class_application)
        # Make changes to the application status via the form
        assert fc.source.bibjson().subjects() == []
        fc.form.application_status.data = "completed"

        assert not fc.validate()

        # However, we should be able to set it to a different status rather than 'completed'
        fc.form.application_status.data = "pending"

        assert fc.validate()

    def test_03_associate_review_complete(self):
        """Give the editor's reapplication form a full workout"""
        acc = models.Account()
        acc.set_id("contextuser")
        acc.add_role("associate_editor")
        ctx = self._make_and_push_test_context(acc=acc)

        editor = models.Account()
        editor.set_id("editor")
        editor.set_email("email@example.com")
        editor.save()

        eg = models.EditorGroup()
        eg.set_name(APPLICATION_SOURCE["admin"]["editor_group"])
        eg.set_editor("editor")
        eg.add_associate("contextuser")
        eg.save()

        time.sleep(2)

        # construct a context from a form submission
        source = deepcopy(APPLICATION_FORM)
        source["application_status"] = "completed"
        fd = MultiDict(source)
        fc = formcontext.ApplicationFormFactory.get_form_context(
            role="associate_editor",
            form_data=fd,
            source=models.Suggestion(**APPLICATION_SOURCE))

        fc.finalise()
        time.sleep(2)

        # now check that a provenance record was recorded
        count = 0
        for prov in models.Provenance.iterall():
            if prov.action == "edit":
                count += 1
            if prov.action == "status:completed":
                count += 10
        assert count == 11

        ctx.pop()