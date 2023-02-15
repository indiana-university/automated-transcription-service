import unittest

target = __import__("ats")

class TestSum(unittest.TestCase):
    def test_find_bucket_key_url(self):
        data = 'https://s3.region-code.amazonaws.com/bucket-name/key-name'
        bucket, key, qs = target.find_bucket_key(data)
        self.assertEqual(bucket, 'bucket-name')
        self.assertEqual(key, 'key-name')

        data = 'https://s3.us-east-1.amazonaws.com/aws-transcribe-us-east-1-prod/123456789012/my_job_name/g6574f2d-3g7a-4vwt-8q95-605d144c9288/asrOutput.json?X-Amz-Security-Token'
        bucket, key, qs = target.find_bucket_key(data)
        self.assertEqual(bucket, 'aws-transcribe-us-east-1-prod')
        self.assertEqual(key, '123456789012/my_job_name/g6574f2d-3g7a-4vwt-8q95-605d144c9288/asrOutput.json')
        self.assertEqual(qs, 'X-Amz-Security-Token')

    def test_find_bucket_key_uri(self):
        data = 's3://s3.region-code.amazonaws.com/key-name'
        bucket, key = target.find_bucket_key(data)
        self.assertEqual(bucket, 's3.region-code.amazonaws.com')
        self.assertEqual(key, 'key-name')

if __name__ == '__main__':
    unittest.main()
