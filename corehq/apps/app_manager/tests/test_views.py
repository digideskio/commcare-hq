import os
import json

from django.core.urlresolvers import reverse
from django.test import TestCase
from corehq.apps.app_manager.tests import add_build
from corehq.apps.app_manager.views import AppSummaryView

from corehq import toggles
from corehq.apps.users.models import WebUser
from corehq.apps.domain.shortcuts import create_domain
from corehq.apps.app_manager.models import Application, APP_V1, APP_V2, import_app, Module


class TestViews(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.domain = 'app-manager-testviews-domain'
        cls.username = 'cornelius'
        cls.password = 'fudge'
        cls.user = WebUser.create(cls.domain, cls.username, cls.password, is_active=True)
        cls.user.is_superuser = True
        cls.user.save()
        toggles.CUSTOM_PROPERTIES.set("domain:{domain}".format(domain=cls.domain), True)

    @classmethod
    def tearDownClass(cls):
        cls.user.delete()

    def test_download_file_bad_xform_404(self):
        '''
        This tests that the `download_file` view returns
        HTTP code 404 for XML that cannot be generated...
        in some sense it does not exist.
        '''

        app = Application.new_app(self.domain, "TestApp", application_version=APP_V1)
        module = app.add_module(Module.new_module("Module0", "en"))

        # These builds are checked in to the repo for use in tests
        build1 = {'version': '1.2.dev', 'build_number': 7106}
        build2 = {'version': '2.7.0', 'build_number': 20655}

        add_build(**build1)
        add_build(**build2)

        with open(os.path.join(os.path.dirname(__file__), "data", "invalid_form.xml")) as f:
            xform_str = f.read()
        app.new_form(module.id, name="Form0-0", attachment=xform_str, lang="en")
        app.save()

        response = self.client.get(reverse('app_download_file', kwargs=dict(domain=self.domain,
                                                                            app_id=app.get_id,
                                                                            path='modules-0/forms-0.xml')))
        self.assertEqual(response.status_code, 404)

    def test_edit_commcare_profile(self):
        app = Application.new_app(self.domain, "TestApp", application_version=APP_V2)
        app.save()
        data = {
            "custom_properties": {
                "random": "value",
                "another": "value"
            }
        }
        self.client.login(username=self.username, password=self.password)

        response = self.client.post(reverse('edit_commcare_profile', args=[self.domain, app._id]),
                                    json.dumps(data),
                                    content_type='application/json')

        content = json.loads(response.content)
        custom_properties = content["changed"]["custom_properties"]

        self.assertEqual(custom_properties["random"], "value")
        self.assertEqual(custom_properties["another"], "value")

        data = {
            "custom_properties": {
                "random": "changed",
            }
        }

        response = self.client.post(reverse('edit_commcare_profile', args=[self.domain, app._id]),
                                    json.dumps(data),
                                    content_type='application/json')

        content = json.loads(response.content)
        custom_properties = content["changed"]["custom_properties"]

        self.assertEqual(custom_properties["random"], "changed")

    def _get_json(self, name):
        with open(os.path.join(os.path.dirname(__file__), 'data', name)) as f:
            return json.loads(f.read())

    def _test_urls(self, names, kwargs):
        for name in names:
            response = self.client.get(reverse(name, kwargs=kwargs))
            self.assertEqual(response.status_code, 200)

    def test_app_urls(self):
        self.client.login(username=self.username, password=self.password)
        app = import_app(self._get_json('basic_app.json'), self.domain)
        kwargs = { 'domain': self.domain, 'app_id': app.id }

        self._test_urls([
            'view_app',
            'release_manager',
            'current_app_version',
            AppSummaryView.urlname,
            'view_user_registration',
            'user_registration_source',
        ], kwargs)

        kwargs['module_id'] = 0
        self._test_urls(['view_module'], kwargs)

        kwargs['form_id'] = 0
        self._test_urls(['view_form', 'form_source'], kwargs)

        '''
    # GET: pass limit, get back list of builds (should have 1 item)
    url(r'^releases/json/$', 'paginate_releases', name='paginate_releases'), 

    # POST: pass ajax=1, check for json that has is_released set
    url(r'^releases/release/(?P<saved_app_id>[\w-]+)/$', 'release_build', name='release_build'),
    url(r'^releases/unrelease/(?P<saved_app_id>[\w-]+)/$', 'release_build', name='unrelease_build', kwargs={'is_released': False}),

    # POST: pass build_id, comment, check status='success' (and build comment is updated?)
    url(r'^update_build_comment/$', 'update_build_comment', name='update_build_comment'),
        '''
