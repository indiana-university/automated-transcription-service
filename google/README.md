# Google Cloud
 Automated Transcription Service using the speech-to-text API in Google Cloud.

The sttparser.py script takes a JSON response file as an argument and prints out a formatted text transcript. An optional "speakers" argument allows you to specify whether or not to use speaker diarization.
The JSON response file can be a local file or a file stored in a Google Cloud Storage bucket.

The sttparser_to_docx.py script outputs a docx file.

Without speakers:
```
$ /bin/python3 sttparser /tmp/transcript.json
```
```
Timestamp:      00:00:0.850
Confidence:     78%
Transcript:     Art party church-key affogato gastropub readymade brunch. Mumblecore listicle umami, activated charcoal four dollar toast kale chips freegan swag cornhole live-edge slow-carb next level jean shorts pop-up vegan.

Timestamp:      00:00:21.410
Confidence:     80%
Transcript:     Activated charcoal marfa cloud bread austin, fanny pack VHS poke echo park try-hard hammock asymmetrical keytar quinoa lo-fi heirloom.
```
With speakers:
```
$ /bin/python3 sttparser -s /tmp/transcript.json
```
## Installation
This is guide for using a Python script in this project to generate a text transcript from an Google Speech-to-text json output file. This is primarily written for use an a *nix machine but should similarly work on other Operating Systems. These steps will install required Python libraries in the Users' space.

Once this is complete it does not need to be repeated. Simply follow step #5 for executing the generation. If a developer changes the translate script step #6 may be used to update your local version.

1. Open a `Terminal`. Hint: By default Paste is done via Shift+Ctrl+V, if in doubt check the menu of your Terminal
2. Verify python3 is installed. This should return `Python 3.x.x`
```
python3 --version
```
2. Prepare Python's package manager for installing required Python libraries. Hint: Run this as two commands consecutively as shown, otherwise an error occurs
```
python3 -m pip install --user --upgrade pip
```
3. Install required libraries
```
python3 -m pip install --user google-cloud-storage urllib3
```
4. Checkout this project
```
git clone <REPO URL>
```
5. Execute the parser. The result will be dropped in the location of inputFile
```
python3 ~/automated-transcription-service/google/sttparser.py -s <JSON_FILE>
```
6. (Optional) If a developer makes changes they can be picked up with the following command
```
cd automated-transcription-service; git pull
cd ~/
```