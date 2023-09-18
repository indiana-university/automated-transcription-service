# automated-transcription-service

Social science researchers using qualitative methods, especially in-depth interviews and focus groups, typically need audio recordings transcribed into accurate text for analysis. Currently, many researchers use other automated transcription services, such as Temi, Trint, or Otter.ai, which are well-known to social science researchers and provide easy-to-use web interfaces for uploading multiple audio files, and then downloading multiple transcripts. These services are also more accessible to graduate students, who do not have internal departmental account numbers for billing and typically pay out-of-pocket for these external services. However, these services come with important data security concerns. Most of these services do not provide the kinds of security documentation required for data steward approval, and many will not have signed a Business Associate Agreement with the university, meaning that they are not approved for use with HIPAA-protected data.

We believe that cloud machine learning APIs provides a powerful alternative to researchers. Thus far, social scientists have not made full use of this option, in part, we believe, because using these services efficiently requires additional technical skills that many social scientists do not have, and/or do not have time to learn. Other social scientists, especially graduate students, have used these services, but do not have access to the same cloud environment as faculty—meaning that their data, when stored in a free or student account, do not receive the same security protections. 

Thus, we seek to provide a new service to researchers that will make audio transcription convenient, efficient, and accessible to them, even without technical skills. For researchers, this will provide an affordable and secure option for quickly producing automated transcripts of research-related recordings.

This project has folders:
* aws: To build a pipeline with terraform to accept audio files in an S3 input bucket and convert those to docx with the help of a Python script. Output files are placed in another S3 output bucket
* google: Python script to convert json to docx only
