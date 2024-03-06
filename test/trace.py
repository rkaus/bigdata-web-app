import unittest
from app import app
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor

class TestAppIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Configure Jaeger exporter
        jaeger_exporter = JaegerExporter(
            agent_host_name='localhost',
            agent_port=6831,
        )

        # Create a BatchSpanProcessor and attach the exporter
        span_processor = BatchSpanProcessor(jaeger_exporter)

        # Configure tracer
        tracer_provider = TracerProvider()
        tracer_provider.add_span_processor(span_processor)
        trace.set_tracer_provider(tracer_provider)

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def tearDown(self):
        pass

    def test_index_route(self):
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("test_index_route"):
            response = self.app.get('/')
        self.assertEqual(response.status_code, 200)

    def test_search_route(self):
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("test_search_route"):
            response = self.app.post('/', data=dict(keyword='chicken'))
        self.assertEqual(response.status_code, 200)

    def test_health_check_route(self):
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("test_health_check_route"):
            response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
