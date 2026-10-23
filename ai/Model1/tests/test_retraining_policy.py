import unittest
from src.retraining_policy import should_enqueue_retraining


class TestRetrainingPolicy(unittest.TestCase):
    def test_initial_training_waits_for_100_real_records(self):
        self.assertFalse(should_enqueue_retraining(
            total_eligible_records=99, new_records_since_last_attempt=99,
            last_attempt_exists=False, pending_or_running_job_exists=False,
            active_model_exists=False,
        ))
        self.assertTrue(should_enqueue_retraining(
            total_eligible_records=100, new_records_since_last_attempt=100,
            last_attempt_exists=False, pending_or_running_job_exists=False,
            active_model_exists=False,
        ))

    def test_retraining_waits_for_50_new_records(self):
        self.assertFalse(should_enqueue_retraining(
            total_eligible_records=180, new_records_since_last_attempt=49,
            last_attempt_exists=True, pending_or_running_job_exists=False,
            active_model_exists=True,
        ))
        self.assertTrue(should_enqueue_retraining(
            total_eligible_records=181, new_records_since_last_attempt=50,
            last_attempt_exists=True, pending_or_running_job_exists=False,
            active_model_exists=True,
        ))

    def test_no_duplicate_while_job_pending(self):
        self.assertFalse(should_enqueue_retraining(
            total_eligible_records=500, new_records_since_last_attempt=500,
            last_attempt_exists=True, pending_or_running_job_exists=True,
            active_model_exists=True,
        ))


if __name__ == "__main__":
    unittest.main()
