import importlib.util
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('reading_preferences', Path(__file__).resolve().parents[1] / 'scripts/reading_preferences.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ReadingPreferenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = MODULE.connect(Path(self.tmp.name) / 'private.sqlite')

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def add_record(self, i, paper=None):
        record = {'id':f'r{i}', 'paper_id':paper or f'doi:paper{i}', 'topic':f'topic{i % 3}', 'read_date':f'2026-11-{10+i:02d}', 'messages':[{'role':'user','text':'先解释目的再讲公式。'}, {'role':'assistant','text':'我建议先讲目的。'}]}
        MODULE.ingest(self.db, record)
        return record

    def hypothesis(self, indices, relation='support'):
        return {'id':'purpose-first', 'preference':'先解释目的', 'scope':'方法说明', 'alternative_explanations':'也许只是不熟悉该领域', 'evidence':[{'record_id':f'r{i}', 'message_index':0, 'quote':'先解释目的', 'relation':relation, 'rationale':'用户明确提出顺序要求'} for i in indices]}

    def test_assistant_words_are_not_user_evidence(self):
        self.add_record(0)
        h = self.hypothesis([0])
        h['evidence'][0].update(message_index=1, quote='先讲目的')
        with self.assertRaisesRegex(ValueError, 'actual user turn'):
            MODULE.observe(self.db, h)

    def test_repeated_exports_of_one_paper_cannot_establish_preference(self):
        for i in range(5):
            self.add_record(i, paper='doi:same-paper')
        MODULE.observe(self.db, self.hypothesis(range(4)))
        MODULE.observe(self.db, self.hypothesis([4], 'holdout'))
        with self.assertRaisesRegex(ValueError, 'Insufficient'):
            MODULE.decide(self.db, 'purpose-first', 'active', 'Repeated mentions')
        self.assertEqual(MODULE.profile(self.db), {'preferences':[]})

    def test_counts_do_not_auto_activate_and_counterevidence_suspends(self):
        for i in range(6):
            self.add_record(i)
        MODULE.observe(self.db, self.hypothesis(range(4)))
        MODULE.observe(self.db, self.hypothesis([4], 'holdout'))
        self.assertTrue(MODULE.inspect(self.db)[0]['gate_passed'])
        self.assertEqual(MODULE.profile(self.db), {'preferences':[]})
        MODULE.decide(self.db, 'purpose-first', 'active', 'Contexts and later paper support the narrow scope')
        self.assertEqual(len(MODULE.profile(self.db)['preferences']), 1)
        MODULE.observe(self.db, self.hypothesis([5], 'contradict'))
        self.assertEqual(MODULE.inspect(self.db)[0]['status'], 'suspended')
        self.assertEqual(MODULE.profile(self.db), {'preferences':[]})

    def test_duplicate_import_is_idempotent(self):
        record = self.add_record(0)
        record['id'] = 'another-export'
        self.assertEqual(MODULE.ingest(self.db, record), {'record_id':'r0','reused':True})


if __name__ == '__main__':
    unittest.main()
