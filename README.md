# automated-transcription-service

Social science researchers using qualitative methods, especially in-depth interviews and focus groups, typically need audio recordings transcribed into accurate text for analysis. Currently, many researchers use other automated transcription services, such as Temi, Trint, or Otter.ai, which are well-known to social science researchers and provide easy-to-use web interfaces for uploading multiple audio files, and then downloading multiple transcripts. These services are also more accessible to graduate students, who do not have internal departmental account numbers for billing and typically pay out-of-pocket for these external services. However, these services come with important data security concerns. Most of these services do not provide the kinds of security documentation required for IU data steward approval, and none have signed a Business Associate Agreement with IU, meaning that they are not approved for use with HIPAA-protected data.

We believe that cloud machine learning APIs provides a powerful alternative to IU researchers. Thus far, social scientists have not made full use of this option, in part, we believe, because using these services efficiently requires additional technical skills that many social scientists do not have, and/or do not have time to learn. Other social scientists, especially graduate students, have used these services, but do not have access to the same IU cloud environment as faculty—meaning that their data, when stored in a free or student account, do not receive the same security protections. 

Thus, we seek to provide a new service to IU researchers that will make audio transcription convenient, efficient, and accessible to them, even without technical skills. For researchers, this will provide an affordable and secure option for quickly producing automated transcripts of research-related recordings.

## Instructions for generating a Word document from an ATS json file via the command line on IUs RED

This is guide for using a Python script in this project to generate a Word document from an AWS ATS json files. A pre-requisite of this guide is access to IU RED (https://kb.iu.edu/d/apum). These steps will install required Python libraries in the Users' space.

Once this is complete it does not need to be repeated. Simply follow step #5 for executing the generation. If a developer changes the translate script step #6 may be used to update your local version.

1. Open a `Terminal`. Hint: By default Paste is done via Shift+Ctrl+V, if in doubt check the menu of your Terminal
2. Verify python3 is installed. This should return `Python 3.x.x`
```
python3 --version
```
2. Prepare Python's package manager for installing matplotlib. Hint: Run this as two commands consecutively as shown, otherwise an error occurs
```
python3 -m pip install --user --upgrade pip
python3 -m pip install --user --upgrade Pillow
```
3. Install required libraries 
```
python3 -m pip install --user python-docx matplotlib boto3
```
4. Checkout this project. This will challenge for IU authentication
```
git clone https://github.iu.edu/IUBSSRC/automated-transcription-service.git
```
5. Execute json to Word. The result will be dropped in the location of inputFile
```
python3 ~/automated-transcription-service/python/ts-to-word.py --confidence on --inputFile <JSON_FILE>
```
6. (Optional) If a developer makes changes they can be picked up with the following command
```
cd automated-transcription-service; git pull
<Challenge for IU authentication>
cd ~/
```
