# # Speech-to-text
# Exploration and testing of the speech-to-text API

import json
import time
import argparse
from google.cloud import storage
from urllib.parse import urlparse

# Format output of timestamps
def timestamp(seconds):
    if (seconds.find(".") == -1):
        seconds = int(seconds[:-1])
        ts = time.gmtime(seconds)
        return time.strftime("%H:%M:%S",ts)
    else:
        x = seconds.split(".")
        seconds = int(x[0])
        ts = time.gmtime(seconds)
        return time.strftime("%H:%M:%S",ts) + "." + x[1][:3]    

def decode_gcs_url(url):
    p = urlparse(url)
    return p.netloc, p.path[1:]

def download_blob(url):
    if url:
        bucket, file_path = decode_gcs_url(url)
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket)
        blob = bucket.blob(file_path)
        contents = blob.download_as_text()
        return contents

# Next version parses the final transcription result in the response file, which includes speaker ID and timestamp for every word.
def print_transcript(response, speakers=False):
    if(speakers):
        last = len(response['results'])-1
        transcript = response['results'][last]

        #Grab first first speaker and start time for initial timestamp
        best_alternative = transcript['alternatives'][0]
        current_words = []
        try:
            current_speaker = best_alternative['words'][0]['speakerTag']
        except:
            print("Speaker diarization not enabled.")
            exit()
        current_ts = best_alternative['words'][0]['startTime']

        #Loop through words
        #When speaker changes: print line, timestamp, speaker, paragraph, add line break
        for word in best_alternative['words']:
            next_speaker = word['speakerTag']
            next_word = word['word']
            if (next_speaker == current_speaker):
                #Same speaker, so add word to list for paragraph
                current_words.append(next_word)
            else:
                #New speaker. Print everything and reset
                paragraph = ' '.join(current_words)
                print(f"Timestamp:\t{timestamp(current_ts)}")
                print(f"Speaker {current_speaker}:\t{paragraph}")
                print()
                current_words = [next_word]
                current_speaker = next_speaker
                current_ts = word['startTime']
    else:
        ts = "00:00:00"
        for result in response['results']:
            best_alternative = result['alternatives'][0]
            transcript = best_alternative.get('transcript','missing')
            if (transcript == 'missing'):
                continue
            confidence = best_alternative['confidence']
            print(f"Timestamp:\t{ts}")
            print(f"Confidence:\t{confidence:.0%}")
            print(f"Transcript:\t{transcript}")
            print()
            ts = timestamp(result['resultEndTime'])

def main():
    parser = argparse.ArgumentParser('Print formatted transcipts from a speech-to-text JSON response.')
    parser.add_argument('file', metavar='file', type=str, help='a JSON file to be parsed')
    parser.add_argument('-s', '--speakers', action='store_true', dest='speakers', help='Enable speaker diarization')
    args = parser.parse_args()
    
    # Open response file and load JSON results
    if (urlparse(args.file).scheme == 'gs'):
        response_file = download_blob(args.file)
        response = json.loads(response_file)
    else:
        with open(args.file) as f:
            response = json.load(f)
    print_transcript(response, args.speakers)

if __name__ == "__main__":
    main()