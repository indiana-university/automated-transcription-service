import json
import csv
import argparse
import os

def flatten_json(input_file):
    output_file = os.path.splitext(input_file)[0] + '.csv'

    with open(input_file, 'r') as json_file:
        data = json.load(json_file)

    with open(output_file, 'w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(['Timestamp', 'TranscriptionJobName', 'Username', 'LanguageCode', 'DurationInSeconds'])

        for item in data:
            timestamp = item['Timestamp']
            job_name = item['TranscriptionJobName']
            username = job_name.split('_')[0].lower()
            for lang in item['LanguageCodes']:
                language_code = lang['LanguageCode']
                duration = lang['DurationInSeconds']
                writer.writerow([timestamp, job_name, username, language_code, duration])

    print(f'Data written to {output_file}.')

def main():
    parser = argparse.ArgumentParser(description='Flatten an ATS CloudWatch logs file.')
    parser.add_argument('input_file', help='The JSON file to flatten.')
    args = parser.parse_args()

    flatten_json(args.input_file)

if __name__ == '__main__':
    main()
