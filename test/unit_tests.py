import unittest
from unittest.mock import patch, Mock
from app import app, search, analyze_results

class TestSearch(unittest.TestCase):
    def test_search_with_valid_response(self):
        with patch('your_main_module.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'hits': [
                    {'recipe': {
                        'label': 'Test Recipe 1',
                        'ingredientLines': ['Ingredient 1', 'Ingredient 2'],
                        'url': 'http://test1.com',
                        'calories': 100,
                        'cuisineType': ['Test Cuisine']
                    }},
                    {'recipe': {
                        'label': 'Test Recipe 2',
                        'ingredientLines': ['Ingredient 3', 'Ingredient 4'],
                        'url': 'http://test2.com',
                        'calories': 150,
                        'cuisineType': ['Test Cuisine', 'Another Cuisine']
                    }}
                ]
            }
            mock_get.return_value = mock_response

            recipes = search('test')
            self.assertEqual(len(recipes), 2)
            self.assertEqual(recipes[0]['name'], 'Test Recipe 1')
            self.assertEqual(recipes[1]['name'], 'Test Recipe 2')

    def test_search_with_invalid_response(self):
        with patch('your_main_module.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_get.return_value = mock_response

            response = search('test')
            self.assertEqual(response.status_code, 500)

    def test_analyze_results(self):
        recipes = [
            {'name': 'Test Recipe 1', 'calories': 100, 'cuisine_type': 'Test Cuisine'},
            {'name': 'Test Recipe 2', 'calories': 150, 'cuisine_type': 'Test Cuisine, Another Cuisine'}
        ]
        analysis_result = analyze_results(recipes)

        self.assertEqual(analysis_result['total_recipes'], 2)
        self.assertEqual(analysis_result['total_calories'], 250)
        self.assertEqual(analysis_result['average_calories'], 125)
        self.assertEqual(analysis_result['most_common_cuisine'], 'Test Cuisine')

if __name__ == '__main__':
    unittest.main()
