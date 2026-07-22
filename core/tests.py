from django.test import TestCase
from django.urls import reverse


class CoreTestCase(TestCase):
    def test_landing_page_renders(self):
        res = self.client.get(reverse("root"))
        self.assertEqual(res.status_code, 200)
