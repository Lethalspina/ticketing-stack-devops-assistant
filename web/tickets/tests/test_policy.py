import os
from django.test import SimpleTestCase
from tickets.policy import authorize
class PolicyTests(SimpleTestCase):
    def setUp(self):
        os.environ["ALLOWED_TARGETS_JSON"] = '{"lab":"127.0.0.1"}'
        os.environ["ALLOWED_SERVICES_JSON"] = '{"web":"nginx"}'
    def test_rejects_unknown_target(self):
        with self.assertRaises(ValueError): authorize("ping", "all")
    def test_restart_is_critical(self):
        self.assertTrue(authorize("restart_service", "lab", "web").critical)
