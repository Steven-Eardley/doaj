import time
from flask import Response

from doajtest.helpers import DoajTestCase
from portality import models
from portality.core import app
from portality.app import load_account_for_login_manager
from portality.decorators import api_key_required

class TestClient(DoajTestCase):

    def setUp(self):
        super(TestClient, self).setUp()

    def tearDown(self):
        super(TestClient, self).tearDown()

    def test_01_api_role(self):
        """test the new roles added for the API"""
        a1 = models.Account.make_account(username="a1_user", name="a1_name", email="a1@example.com", roles=["user"], associated_journal_ids=[])
        a1.save()
        time.sleep(1)

        # Check an API key was generated on account creation
        a1_key = a1.api_key
        assert a1_key is not None

        # Check we can retrieve the account by its key
        a1_retrieved = models.Account.pull_by_api_key(a1_key)
        assert a1 == a1_retrieved

        # Check all roles gain the api role on creation
        a2 = models.Account.make_account(username="a2_user", name="a2_name", email="a2@example.com", roles=["admin"], associated_journal_ids=[])
        a3 = models.Account.make_account(username="a3_user", name="a3_name", email="a3@example.com", roles=["publisher"], associated_journal_ids=[])
        a4 = models.Account.make_account(username="a4_user", name="a4_name", email="a4@example.com", roles=["editor"], associated_journal_ids=[])
        a5 = models.Account.make_account(username="a5_user", name="a5_name", email="a5@example.com", roles=["associate_editor"], associated_journal_ids=[])
        assert a1.has_role("api")
        assert a2.has_role("api")
        assert a3.has_role("api")
        assert a4.has_role("api")
        assert a5.has_role("api")

        # Check that removing the API role means you don't get a key
        a1.remove_role('api')
        assert a1.api_key is None

    def test_02_api_decorator(self):
        """test the api_key_required decorator"""
        a1 = models.Account.make_account(username="a1_user", name="a1_name", email="a1@example.com", roles=["user"], associated_journal_ids=[])
        a1_key = a1.api_key
        a1.save()               # a1 has api access

        a2 = models.Account.make_account(username="a2_user", name="a2_name", email="a2@example.com", roles=["user"], associated_journal_ids=[])
        a2_key = a2.api_key     # user gets the key before access is removed
        a2.remove_role('api')
        a2.save()               # a2 does not have api access.

        time.sleep(1)

        app.testing = True
        # for some reason this wasn't being registered, so do so here
        app.login_manager.user_loader(load_account_for_login_manager)

        # Create a view to test the wrapper with
        @app.route('/hello')
        @api_key_required
        def hello_world():
            return Response("hello, world!")

        with app.test_client() as t_client:
            # Check the authorised user can access our function, but the unauthorised one can't.
            response_authorised = t_client.get('/hello?api_key=' + a1_key)
            assert response_authorised.data == "hello, world!"
            assert response_authorised.status_code == 200

            response_denied = t_client.get('/hello?api_key=' + a2_key)
            assert response_denied.status_code == 401

