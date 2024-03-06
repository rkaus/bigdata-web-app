import unittest
from app import app

class TestAppIntegration(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def tearDown(self):
        pass

    def test_index_route(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)

    def test_search_route(self):
        response = self.app.post('/', data=dict(keyword='chicken'))
        self.assertEqual(response.status_code, 200)

    def test_health_check_route(self):
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
