import unittest

target = __import__("transcribe_to_docx")

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

    def test_format_speaker_label(self):
        self.assertEqual(target.format_speaker_label("spk_0"), 'Speaker 1')
        self.assertEqual(target.format_speaker_label("spk_1"), 'Speaker 2')
        self.assertEqual(target.format_speaker_label("Mr. Jones"), 'Mr. Jones')

    def test_convert_timestamp(self):
        self.assertEqual(target.convert_timestamp(0), '00:00:00')
        self.assertEqual(target.convert_timestamp(10000), '02:46:40')

    def test_create_turn_by_turn_segments_missing_speaker_labels(self):
        """Test that create_turn_by_turn_segments handles missing speaker_labels gracefully"""
        # Test case where speaker_labels is None
        data_missing_speaker_labels = {
            "results": {
                "speaker_labels": None
            }
        }
        result = target.create_turn_by_turn_segments(data_missing_speaker_labels, isSpeakerMode=True)
        self.assertEqual(result, [])
        
        # Test case where speaker_labels doesn't exist
        data_no_speaker_labels = {
            "results": {}
        }
        result = target.create_turn_by_turn_segments(data_no_speaker_labels, isSpeakerMode=True)
        self.assertEqual(result, [])
        
        # Test case where results is None
        data_no_results = {
            "results": None
        }
        result = target.create_turn_by_turn_segments(data_no_results, isSpeakerMode=True)
        self.assertEqual(result, [])

    def test_create_turn_by_turn_segments_missing_channel_labels(self):
        """Test that create_turn_by_turn_segments handles missing channel_labels gracefully"""
        # Test case where channel_labels is None
        data_missing_channel_labels = {
            "results": {
                "channel_labels": None
            }
        }
        result = target.create_turn_by_turn_segments(data_missing_channel_labels, isChannelMode=True)
        self.assertEqual(result, [])
        
        # Test case where channel_labels doesn't exist
        data_no_channel_labels = {
            "results": {}
        }
        result = target.create_turn_by_turn_segments(data_no_channel_labels, isChannelMode=True)
        self.assertEqual(result, [])

    def test_create_turn_by_turn_segments_missing_audio_segments(self):
        """Test that create_turn_by_turn_segments handles missing audio_segments gracefully"""
        # Test case where audio_segments is None
        data_missing_audio_segments = {
            "results": {
                "audio_segments": None
            }
        }
        result = target.create_turn_by_turn_segments(data_missing_audio_segments, isAudioSegmentsMode=True)
        self.assertEqual(result, [])
        
        # Test case where audio_segments doesn't exist
        data_no_audio_segments = {
            "results": {}
        }
        result = target.create_turn_by_turn_segments(data_no_audio_segments, isAudioSegmentsMode=True)
        self.assertEqual(result, [])

    def test_create_turn_by_turn_segments_valid_data(self):
        """Test that create_turn_by_turn_segments still works with valid data"""
        # Test with valid speaker mode data structure (minimal case)
        data_valid_speaker = {
            "results": {
                "speaker_labels": {
                    "segments": []
                },
                "items": []
            }
        }
        result = target.create_turn_by_turn_segments(data_valid_speaker, isSpeakerMode=True)
        self.assertEqual(result, [])
        
        # Test with valid channel mode data structure (minimal case)
        data_valid_channel = {
            "results": {
                "channel_labels": {
                    "channels": []
                }
            }
        }
        result = target.create_turn_by_turn_segments(data_valid_channel, isChannelMode=True)
        self.assertEqual(result, [])
        
        # Test with valid audio segments data structure (minimal case)
        data_valid_audio_segments = {
            "results": {
                "audio_segments": []
            }
        }
        result = target.create_turn_by_turn_segments(data_valid_audio_segments, isAudioSegmentsMode=True)
        self.assertEqual(result, [])

if __name__ == '__main__':
    unittest.main()
