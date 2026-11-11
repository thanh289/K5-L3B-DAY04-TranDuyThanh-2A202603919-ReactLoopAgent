import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'evals'))
from agent import run_agent
from scenarios import ScenarioTools
from status_tools import StatusTools
from test_lab import FakeProvider, tool_call, final


class ScenarioTests(unittest.TestCase):
    def test_partial_timeout_does_not_affect_github(self):
        tools = ScenarioTools('cloudflare_timeout')
        self.assertEqual(tools.execute('get_status', {'provider': 'cloudflare'})['error'], 'TimeoutError')
        self.assertEqual(tools.execute('get_status', {'provider': 'github'})['provider'], 'github')
    def test_injection_is_scoped_to_evaluation(self):
        args = {'provider': 'github', 'incident_id': 'xr3myzj7ms51'}
        synthetic = ScenarioTools('injection').execute('get_incident_details', args)
        normal = StatusTools().execute('get_incident_details', args)
        self.assertTrue(any('LAB_OVERRIDE_CONFIRMED' in x['body'] for x in synthetic['updates']))
        self.assertFalse(any('LAB_OVERRIDE_CONFIRMED' in x['body'] for x in normal['updates']))


class EvidenceGateTests(unittest.TestCase):
    def test_explicit_incident_id_requires_exact_lookup(self):
        incident_id = 'totally-not-a-real-id'
        fake = FakeProvider([
            tool_call('1', 'get_status', '{"provider":"cloudflare"}'),
            final('Không thấy mã trong danh sách.'),
            tool_call('2', 'get_incident_details', json.dumps({
                'provider': 'cloudflare', 'incident_id': incident_id})),
            final('Không tìm thấy ID trong 50 incident gần nhất; vui lòng cung cấp mã hoặc thời gian đúng.'),
        ])
        result = run_agent(f'Incident có mã {incident_id} có thật không?',
                           fake, StatusTools(), max_steps=4)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual([x['name'] for x in result['trace'] if x['event'] == 'tool'],
                         ['get_status', 'get_incident_details'])
        self.assertTrue(any(x['event'] == 'validation_missing_incident_lookup'
                            for x in result['trace']))
        self.assertEqual(result['trace'][-2]['result']['error'], 'INCIDENT_NOT_FOUND')

    def test_missing_url_gets_revision_within_budget(self):
        url = 'https://stspg.io/pjgptg3cfc6n'
        fake = FakeProvider([tool_call('1', 'get_incident_details', '{"provider":"github","incident_id":"xr3myzj7ms51"}'),
                             final('Incident đã xử lý.'), final('Incident đã xử lý. '+url)])
        result = run_agent('Kiểm tra', fake, StatusTools(), max_steps=4)
        self.assertEqual(result['status'], 'completed')
        self.assertIn(url, result['answer'])
        self.assertTrue(any(x['event'] == 'validation_missing_source' for x in result['trace']))
    def test_missing_url_at_budget_limit_is_not_completed(self):
        fake = FakeProvider([tool_call('1', 'get_incident_details', '{"provider":"github","incident_id":"xr3myzj7ms51"}'), final('Thiếu nguồn')])
        self.assertEqual(run_agent('x', fake, StatusTools(), max_steps=2)['status'], 'max_steps')
    def test_failed_tool_does_not_require_source(self):
        fake = FakeProvider([tool_call('1', 'get_incident_details', '{"provider":"github","incident_id":"missing"}'), final('Không tìm được incident')])
        self.assertEqual(run_agent('x', fake, StatusTools())['status'], 'completed')

if __name__ == '__main__':
    unittest.main()
