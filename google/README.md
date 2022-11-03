# Google Cloud
 Automated Transcription Service using the speech-to-text API in Google Cloud.

The sttparser.py script takes a JSON response file as an argument and prints out a formatted transcript. An optional "speakers" argument allows you to specify whether or not to use speaker diarization.

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
