import boto3
from urllib.parse import urlparse
from urllib.request import urlopen
from urllib.request import urlretrieve
import json
from datetime import timedelta
from datetime import datetime as dt
from io import BytesIO
import statistics
import os
from docx import Document
from docx.shared import Cm, Mm, Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.section import WD_SECTION
from docx.oxml.shared import qn
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml
import argparse
from pathlib import Path
from time import perf_counter

# Common formats and styles
CUSTOM_STYLE_HEADER = "CustomHeader"
TABLE_STYLE_STANDARD = "Light List"
ALTERNATE_ROW_COLOUR = "F0F0F0"
RED = "FF0000"
YELLOW = "FFFF00"
GREEN = "00FF00"

# Additional Constants
START_NEW_SEGMENT_DELAY = 2.0       # After n seconds pause by one speaker, put next speech in new segment

# Global variables
global_average_confidence = "0.0"
global_audio_duration = 0.0
global_languages = ""

class SpeechSegment:
    """ Class to hold information about a single speech segment """
    def __init__(self):
        self.segmentStartTime = 0.0
        self.segmentEndTime = 0.0
        self.segmentSpeaker = ""
        self.segmentText = ""
        self.segmentConfidence = []
        self.segmentSentimentScore = -1.0    # -1.0 => no sentiment calculated
        self.segmentPositive = 0.0
        self.segmentNegative = 0.0
        self.segmentIsPositive = False
        self.segmentIsNegative = False
        self.segmentAllSentiments = []
        self.segmentLoudnessScores = []
        self.segmentInterruption = False
        self.segmentIssuesDetected = []
        self.segmentActionItemsDetected = []
        self.segmentOutcomesDetected = []

# Get current date for S3 folder name:
today = dt.now().strftime("%Y%m%d")

# S3 client to read/write files
s3 = boto3.client('s3')

# Transcribe client to read job results
if __name__ != "__main__": ts_client = boto3.client('transcribe')

confidence_env = int(os.environ.get('CONFIDENCE', 90))

def convert_timestamp(time_in_seconds):
    """
    Function to help convert timestamps from s to hh:mm:ss

    :param time_in_seconds: Time in seconds to be displayed
    :return: Formatted string for this timestamp value
    """
    timeDelta = timedelta(seconds=float(time_in_seconds))
    tsFront = timeDelta - timedelta(microseconds=timeDelta.microseconds)
    hours, remainder = divmod(tsFront.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return '{:02d}:{:02d}:{:02d}'.format(int(hours), int(minutes), int(seconds))

def set_transcript_text_style(run, force_highlight, confidence=0.0, rgb_color=None):
    """
    Sets the colour and potentially the style of a given run of text in a transcript.  You can either
    supply the hex-code, or base it upon the confidence score in the transcript.

    :param run: DOCX paragraph run to be modified
    :param force_highlight: Indicates that we're going to forcibly set the background colour
    :param confidence: Confidence score for this word, used to dynamically set the colour
    :param rgb_color: Specific colour for the text
    """

    # If we have an RGB colour then use it
    if rgb_color is not None:
        run.font.color.rgb = rgb_color
    else:
        # Set the colour based upon the supplied confidence score
        if confidence >= (confidence_env / 100):
            run.font.color.rgb = RGBColor(0, 0, 0)
        else:
            run.font.highlight_color = WD_COLOR_INDEX.YELLOW

    # Apply any other styles wanted
    if confidence == 0.0:
        # Call out any total disasters in bold
        run.font.bold = True

    # Force the background colour if required
    if force_highlight:
        run.font.highlight_color = WD_COLOR_INDEX.YELLOW

def write_transcribe_text(document, speech_segments):
    """
    Writes out each line of the transcript in the Word document
    :param document: Document to write the text to
    :param speech_segments: Turn-by-turn speech list
    """
    for segment in speech_segments:
        startTime = convert_timestamp(segment.segmentStartTime)
        speaker = format_speaker_label(segment.segmentSpeaker)

        paragraph = document.add_paragraph()
        run = paragraph.add_run()
        run.add_text("[" + startTime + "] " + speaker + ": ")

        # Then do each word with confidence-level colouring
        text_index = 1
        for eachWord in segment.segmentConfidence:
            run = paragraph.add_run()

            # Output the next word, with the correct confidence styling and forced background
            run.add_text(eachWord["text"])
            text_index += len(eachWord["text"])
            confLevel = eachWord["confidence"]
            set_transcript_text_style(run, False, confidence=confLevel)

def format_speaker_label(label):
    """
    :param label: Label to format. It only formats labels of style "spk_0", "spk_1" etc.
    :return: Formatted Label. Example: "spk_0" -> "Speaker 1"
    """
    if 'spk_' in label:
        parts = label.split('_')
        return parts[0].replace('spk', 'Speaker ') + str(int(parts[1])+1)
    return label

def load_image(url):
    """
    Loads binary image data from a URL for later embedding into a docx document
    :param url: URL of image to be downloaded
    :return: BytesIO object that can be added as a docx image
    """
    image_url = urlopen(url)
    io_url = BytesIO()
    io_url.write(image_url.read())
    io_url.seek(0)
    return io_url

def write_small_header_text(document, text, confidence):
    """
    Helper function to write out small header entries, where the text colour matches the
    colour of the transcript text for a given confidence value

    :param document: Document to write the text to
    :param text: Text to be output
    :param confidence: Confidence score, which changes the text colour
    """
    run = document.paragraphs[-1].add_run(text)
    set_transcript_text_style(run, False, confidence=confidence)
    run.font.size = Pt(10)
    run.font.italic = True

def generate_confidence_stats(speech_segments):
    """
    Creates a map of timestamps and confidence scores to allow for both summarising and graphing in the document.
    We also need to bucket the stats for summarising into bucket ranges that feel important (but are easily changed)

    :param speech_segments: List of call speech segments
    :return: Confidence and timestamp structures for graphing
    """""

    # Stats dictionary
    stats = {
        "timestamps": [],
        "accuracy": [],
        "9.8": 0, "9": 0, "8": 0, "7": 0, "6": 0, "5": 0, "4": 0, "3": 0, "2": 0, "1": 0, "0": 0,
        "parsedWords": 0}

    # Confidence count - we need the average confidence score regardless
    for line in speech_segments:
        for word in line.segmentConfidence:
            stats["timestamps"].append(word["start_time"])
            conf_value = word["confidence"]
            stats["accuracy"].append(int(conf_value * 100))
            if conf_value >= 0.98:
                stats["9.8"] += 1
            elif conf_value >= 0.9:
                stats["9"] += 1
            elif conf_value >= 0.8:
                stats["8"] += 1
            elif conf_value >= 0.7:
                stats["7"] += 1
            elif conf_value >= 0.6:
                stats["6"] += 1
            elif conf_value >= 0.5:
                stats["5"] += 1
            elif conf_value >= 0.4:
                stats["4"] += 1
            elif conf_value >= 0.3:
                stats["3"] += 1
            elif conf_value >= 0.2:
                stats["2"] += 1
            elif conf_value >= 0.1:
                stats["1"] += 1
            else:
                stats["0"] += 1
            stats["parsedWords"] += 1
    return stats

def write_custom_text_header(document, text_label, level=3):
    """
    Adds a run of text to the document with the given text label, but using our customer text-header style

    :param document: Document to write the text to
    :param text_label: Header text to write out
    :return:
    """
    paragraph = document.add_heading(text_label, level)

def write_confidence_scores(document, stats, temp_files):
    """
    Using the pre-build confidence stats list, create a summary table of confidence score
    spreads, as well as a scatter-plot showing each word against the overall mean

    :param document: Document to write the text to
    :param stats: Statistics for the confidence scores in the conversation
    :param temp_files: List of temporary files for later deletion
    :return:
    """
    document.add_section(WD_SECTION.CONTINUOUS)
    section_ptr = document.sections[-1]._sectPr
    cols = section_ptr.xpath('./w:cols')[0]
    cols.set(qn('w:num'), '1')
    write_custom_text_header(document, "Word Confidence Scores")
    # Start with the fixed headers
    table = document.add_table(rows=1, cols=3)
    table.style = document.styles[TABLE_STYLE_STANDARD]
    table.alignment = WD_ALIGN_PARAGRAPH.LEFT
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Confidence"
    hdr_cells[1].text = "Count"
    hdr_cells[2].text = "Percentage"
    parsedWords = stats["parsedWords"]
    confidenceRanges = ["98% - 100%", "90% - 97%", "80% - 89%", "70% - 79%", "60% - 69%", "50% - 59%", "40% - 49%",
                        "30% - 39%", "20% - 29%", "10% - 19%", "0% - 9%"]
    confidenceRangeStats = ["9.8", "9", "8", "7", "6", "5", "4", "3", "2", "1", "0"]
    # Add on each row
    shading_reqd = False
    for confRange, rangeStats in zip(confidenceRanges, confidenceRangeStats):
        row_cells = table.add_row().cells
        row_cells[0].text = confRange
        row_cells[1].text = str(stats[rangeStats])
        row_cells[2].text = str(round(stats[rangeStats] / parsedWords * 100, 2)) + "%"

        # Add highlighting to the row if required
        if shading_reqd:
            for column in range(0, 3):
                set_table_cell_background_colour(row_cells[column], ALTERNATE_ROW_COLOUR)
        shading_reqd = not shading_reqd

    # Formatting transcript table widths, then move to the next column
    widths = (Inches(1.2), Inches(0.8), Inches(0.8))
    for row in table.rows:
        for idx, width in enumerate(widths):
            row.cells[idx].width = width


def set_table_cell_background_colour(cell, rgb_hex):
    """
    Modifies the background color of the given table cell to the given RGB hex value.  This currently isn't
    supporting by the DOCX module, and the only option is to modify the underlying Word document XML

    :param cell: Table cell to be changed
    :param rgb_hex: RBG hex string for the background color
    """
    parsed_xml = parse_xml(r'<w:shd {0} w:fill="{1}"/>'.format(nsdecls('w'), rgb_hex))
    cell._tc.get_or_add_tcPr().append(parsed_xml)

def write(data, speech_segments, job_info, output_file):
    """
    Write a transcript from the .json transcription file and other data generated
    by the results parser, putting it all into a human-readable Word document

    :param data: JSON output from the transcription job
    :param speech_segments: List of call speech segments
    :param job_info: Status of the Transcribe job
    :param summaries_detected: Flag to indicate presence of call summary data
    """

    # Global variable to hold the average confidence score
    global global_average_confidence
    global global_audio_duration
    global global_languages

    tempFiles = []

    # Initiate Document, orientation and margins
    document = Document()
    document.sections[0].left_margin = Mm(19.1)
    document.sections[0].right_margin = Mm(19.1)
    document.sections[0].top_margin = Mm(19.1)
    document.sections[0].bottom_margin = Mm(19.1)
    document.sections[0].page_width = Mm(210)
    document.sections[0].page_height = Mm(297)

    # Set the base font and document title
    font = document.styles["Normal"].font
    font.name = "Calibri"
    font.size = Pt(10)

    # Create our custom text header style
    custom_style = document.styles.add_style(CUSTOM_STYLE_HEADER, WD_STYLE_TYPE.PARAGRAPH)
    custom_style.paragraph_format.widow_control = True
    custom_style.paragraph_format.keep_with_next = True
    custom_style.paragraph_format.space_after = Pt(0)
    custom_style.font.size = font.size
    custom_style.font.name = font.name
    custom_style.font.bold = True
    custom_style.font.italic = True

    # Intro header
    DOCUMENT_TITLE = os.environ.get("DOCUMENT_TITLE", "Transcription Results")
    write_custom_text_header(document, DOCUMENT_TITLE, 2)

    # Write put the call summary table - depending on the mode that Transcribe was used in, and
    # if the request is being run on a JSON results file rather than reading the job info from Transcribe,
    # not all of the information is available.
    # -- Media information
    # -- Amazon Transcribe job information
    # -- Average transcript word-confidence scores
    write_custom_text_header(document, "Amazon Transcribe Audio Source")
    table = document.add_table(rows=1, cols=2)
    table.style = document.styles[TABLE_STYLE_STANDARD]
    table.alignment = WD_ALIGN_PARAGRAPH.LEFT
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Job Name"
    hdr_cells[1].text = data["jobName"]
    job_data = []
    # Audio duration is the end-time of the final voice segment, which might be shorter than the actual file duration
    if len(speech_segments) > 0:
        global_audio_duration = speech_segments[-1].segmentEndTime
        dur_text = str(int(global_audio_duration / 60)) + "m " + str(round(global_audio_duration % 60, 2)) + "s"
        job_data.append({"name": "Audio Duration", "value": dur_text})
    # We can infer diarization mode from the JSON results data structure
    if "speaker_labels" in data["results"]:
        job_data.append({"name": "Audio Identification", "value": "Speaker-separated"})
    elif "channel_labels" in data["results"]:
        job_data.append({"name": "Audio Identification", "value": "Channel-separated"})
    elif "audio_segments" in data["results"]:
         job_data.append({"name": "Audio Identification", "value": "Audio-segments"})

    # Some information is only in the job info
    if job_info is not None:
        if "LanguageCode" in job_info: # AWS sample job_info
            global_languages = job_info["LanguageCode"]
            job_data.append({"name": "Language", "value": job_info["LanguageCode"]})
        elif "LanguageCodes" in job_info: # AWS job_info
            languages = []
            for language in job_info["LanguageCodes"]: languages.append(language["LanguageCode"])
            global_languages = ', '.join(languages)
            job_data.append({"name": "Language(s)", "value": global_languages})
        elif "language_codes" in job_info: # json job_info
            languages = []
            for language in job_info["language_codes"]: languages.append(language["language_code"])
            global_languages = ', '.join(languages)
            job_data.append({"name": "Language(s)", "value": global_languages})
        if "MediaFormat" in job_info:
            job_data.append({"name": "File Format", "value": job_info["MediaFormat"]})
        if "MediaSampleRateHertz" in job_info:
            job_data.append({"name": "Sample Rate", "value": str(job_info["MediaSampleRateHertz"]) + " Hz"})
        if "CreationTime" in job_info:
            job_data.append({"name": "Job Created", "value": job_info["CreationTime"].strftime("%a %d %b '%y at %X")})
        if "Settings" in job_info:
            if "ContentRedaction" in job_info["Settings"]:
                redact_type = job_info["Settings"]["ContentRedaction"]["RedactionType"]
                redact_output = job_info["Settings"]["ContentRedaction"]["RedactionOutput"]
                job_data.append({"name": "Redaction Mode", "value": redact_type + " [" + redact_output + "]"})
            if "VocabularyFilterName" in job_info["Settings"]:
                vocab_filter = job_info["Settings"]["VocabularyFilterName"]
                vocab_method = job_info["Settings"]["VocabularyFilterMethod"]
                job_data.append({"name": "Vocabulary Filter", "value": vocab_filter + " [" + vocab_method + "]"})
            if "VocabularyName" in job_info["Settings"]:
                job_data.append({"name": "Custom Vocabulary", "value": job_info["Settings"]["VocabularyName"]})

    # Finish with the confidence scores (if we have any)
    stats = generate_confidence_stats(speech_segments)
    if len(stats["accuracy"]) > 0:
        global_average_confidence = str(round(statistics.mean(stats["accuracy"]), 2))
        job_data.append({"name": "Average Confidence", "value": global_average_confidence + "%"})

    # Place all of our job-summary fields into the Table, one row at a time
    for next_row in job_data:
        row_cells = table.add_row().cells
        row_cells[0].text = next_row["name"]
        row_cells[1].text = next_row["value"]

    # Formatting transcript table widths
    widths = (Cm(3.44), Cm(4.89))
    for row in table.rows:
        for idx, width in enumerate(widths):
            row.cells[idx].width = width

    # Spacer paragraph
    document.add_paragraph()

    # At this point, if we have no transcript then we need to quickly exit
    if len(speech_segments) == 0:
        document.add_section(WD_SECTION.CONTINUOUS)
        section_ptr = document.sections[-1]._sectPr
        write_custom_text_header(document, "This file had no audible speech to transcribe.")
    else:
        # Process and display transcript by speaker segments (new section)
        # -- Conversation "turn" start time and duration
        # -- Speaker identification
        document.add_section(WD_SECTION.CONTINUOUS)
        section_ptr = document.sections[-1]._sectPr
        write_custom_text_header(document, "Audio Transcription")
        document.add_paragraph()  # Spacing
        write_small_header_text(document, "WORD CONFIDENCE: >= " + str(confidence_env) + "% in black, ", (confidence_env / 100))
        write_small_header_text(document, "< " + str(confidence_env) + "% in yellow highlight", ((confidence_env - 1) / 100))

        # Based upon our segment list, write out the transcription
        write_transcribe_text(document, speech_segments)
        document.add_paragraph()

        # Display confidence count table (new section)
        # -- Summary table of confidence scores into "bins"
        # -- Scatter plot of confidence scores over the whole transcript
        write_confidence_scores(document, stats, tempFiles)
        document.add_section(WD_SECTION.CONTINUOUS)

    # Save the whole document and then upload to S3
    document.save(output_file)

    # Now delete any local images that we created
    for filename in tempFiles:
        os.remove(filename)

def find_bucket_key(s3_url_or_uri):
    """
    This is a helper function that given an s3 path such that the path is of
    the form:
        1) https://s3.region-code.amazonaws.com/bucket-name/key-name
        2) https://s3.us-east-1.amazonaws.com/aws-transcribe-us-east-1-prod/123456789012/my_job_name/g6574f2d-3g7a-4vwt-8q95-605d144c9288/asrOutput.json?X-Amz-Security-Token...
        3) s3://s3.region-code.amazonaws.com/key-name
    It will return the bucket and the key represented by the s3 path, as well as the query string (if one exists)
    """
    if 's3://' in s3_url_or_uri:
        path_parts=s3_url_or_uri.replace("s3://","").split("/")
        bucket=path_parts.pop(0)
        key="/".join(path_parts)
        return bucket, key
    else:
        s3_path = urlparse(s3_url_or_uri)
        s3_qs = s3_path.query
        s3_components = s3_path.path.split('/')
        s3_bucket = s3_components[1]
        s3_key = ""
        if len(s3_components) > 1:
            s3_key = '/'.join(s3_components[2:])
        return s3_bucket, s3_key, s3_qs

def get_json(download_url):
    bucket, key, qs = find_bucket_key(download_url)
    if len(qs) > 0:
        # Transcription is available via signed URL
        try:
            with urlopen(download_url) as f:
                file_content = f.read().decode('utf-8')
                transcript = json.loads(file_content)
        except:
            print(f"Error downloading from: {download_url}")
    else:
        # Transcription stored in a bucket
        try:
            transcription = s3.get_object(Bucket=bucket, Key=key)
            file_content = transcription['Body'].read().decode('utf-8')
            transcript = json.loads(file_content)
        except Exception as e:
            print(e)
            print(f"Error retrieving file from bucket={bucket}, key={key}.")
            raise
    return transcript

def merge_speaker_segments(input_segment_list):
    """
    Merges together consecutive speaker segments unless:
    a) There is a speaker change, or
    b) The gap between segments is greater than our acceptable level of delay

    :param input_segment_list: Full time-sorted list of speaker segments
    :return: An updated segment list
    """
    outputSegmentList = []
    lastSpeaker = ""
    lastSegment = None

    # Step through each of our defined speaker segments
    for segment in input_segment_list:
        if (segment.segmentSpeaker != lastSpeaker) or \
                ((segment.segmentStartTime - lastSegment.segmentEndTime) >= START_NEW_SEGMENT_DELAY):
            # Simple case - speaker change or > n-second gap means new output segment
            outputSegmentList.append(segment)

            # This is now our base segment moving forward
            lastSpeaker = segment.segmentSpeaker
            lastSegment = segment
        else:
            # Same speaker, short time, need to copy this info to the last one
            lastSegment.segmentEndTime = segment.segmentEndTime
            lastSegment.segmentText += " " + segment.segmentText
            segment.segmentConfidence[0]["text"] = " " + segment.segmentConfidence[0]["text"]
            for wordConfidence in segment.segmentConfidence:
                lastSegment.segmentConfidence.append(wordConfidence)

    return outputSegmentList

def create_turn_by_turn_segments(data, isSpeakerMode=False, isChannelMode=False, isAudioSegmentsMode=False):
    """
    This creates a list of per-turn speech segments based upon the transcript data.  It has to work in three modes:
        a) Speaker-separated audio
        b) Channel-separated audio
        c) Audio Segments

    :param data: JSON result data from Transcribe
    :param isSpeakerMode: (optional) Boolean indicating whether the audio was speaker-separated
    :param isChannelMode: (optional) Boolean indicating whether the audio was channel-separated
    :param isAudioSegmentsMode: (optional) Boolean indicating whether the audio was segments-separated
    :return: List of transcription speech segments
    """
    speechSegmentList = []

    lastSpeaker = ""
    lastEndTime = 0.0
    skipLeadingSpace = False
    confidenceList = []
    nextSpeechSegment = None

    # Process a Speaker-separated non-analytics file
    if isSpeakerMode:
        # A segment is a blob of pronunciation and punctuation by an individual speaker
        for segment in data["results"]["speaker_labels"]["segments"]:

            # If there is content in the segment then pick out the time and speaker
            if len(segment["items"]) > 0:
                # Pick out our next data
                nextStartTime = float(segment["start_time"])
                nextEndTime = float(segment["end_time"])
                nextSpeaker = str(segment["speaker_label"])

                # If we've changed speaker, or there's a gap, create a new row
                if (nextSpeaker != lastSpeaker) or ((nextStartTime - lastEndTime) >= START_NEW_SEGMENT_DELAY):
                    nextSpeechSegment = SpeechSegment()
                    speechSegmentList.append(nextSpeechSegment)
                    nextSpeechSegment.segmentStartTime = nextStartTime
                    nextSpeechSegment.segmentSpeaker = nextSpeaker
                    skipLeadingSpace = True
                    confidenceList = []
                    nextSpeechSegment.segmentConfidence = confidenceList
                nextSpeechSegment.segmentEndTime = nextEndTime

                # Note the speaker and end time of this segment for the next iteration
                lastSpeaker = nextSpeaker
                lastEndTime = nextEndTime

                # For each word in the segment...
                for word in segment["items"]:

                    # Get the word with the highest confidence
                    pronunciations = list(filter(lambda x: x["type"] == "pronunciation", data["results"]["items"]))
                    word_result = list(filter(lambda x: x["start_time"] == word["start_time"] and x["end_time"] == word["end_time"], pronunciations))
                    try:
                        result = sorted(word_result[-1]["alternatives"], key=lambda x: x["confidence"])[-1]
                        confidence = float(result["confidence"])
                    except:
                        result = word_result[-1]["alternatives"][0]
                        confidence = float(result["redactions"][0]["confidence"])

                    # Write the word, and a leading space if this isn't the start of the segment
                    if skipLeadingSpace:
                        skipLeadingSpace = False
                        wordToAdd = result["content"]
                    else:
                        wordToAdd = " " + result["content"]

                    # If the next item is punctuation, add it to the current word
                    try:
                        word_result_index = data["results"]["items"].index(word_result[0])
                        next_item = data["results"]["items"][word_result_index + 1]
                        if next_item["type"] == "punctuation":
                            wordToAdd += next_item["alternatives"][0]["content"]
                    except IndexError:
                        pass

                    nextSpeechSegment.segmentText += wordToAdd
                    confidenceList.append({"text": wordToAdd,
                                           "confidence": confidence,
                                           "start_time": float(word["start_time"]),
                                           "end_time": float(word["end_time"])})

    # Process a Channel-separated non-analytics file
    elif isChannelMode:

        # A channel contains all pronunciation and punctuation from a single speaker
        for channel in data["results"]["channel_labels"]["channels"]:

            # If there is content in the channel then start processing it
            if len(channel["items"]) > 0:

                # We have the same speaker all the way through this channel
                nextSpeaker = str(channel["channel_label"])
                for word in channel["items"]:
                    # Pick out our next data from a 'pronunciation'
                    if word["type"] == "pronunciation":
                        nextStartTime = float(word["start_time"])
                        nextEndTime = float(word["end_time"])

                        # If we've changed speaker, or we haven't and the
                        # pause is very small, then start a new text segment
                        if (nextSpeaker != lastSpeaker) or\
                                ((nextSpeaker == lastSpeaker) and ((nextStartTime - lastEndTime) > 0.1)):
                            nextSpeechSegment = SpeechSegment()
                            speechSegmentList.append(nextSpeechSegment)
                            nextSpeechSegment.segmentStartTime = nextStartTime
                            nextSpeechSegment.segmentSpeaker = nextSpeaker
                            skipLeadingSpace = True
                            confidenceList = []
                            nextSpeechSegment.segmentConfidence = confidenceList
                        nextSpeechSegment.segmentEndTime = nextEndTime

                        # Note the speaker and end time of this segment for the next iteration
                        lastSpeaker = nextSpeaker
                        lastEndTime = nextEndTime

                        # Get the word with the highest confidence
                        pronunciations = list(filter(lambda x: x["type"] == "pronunciation", channel["items"]))
                        word_result = list(filter(lambda x: x["start_time"] == word["start_time"] and x["end_time"] == word["end_time"], pronunciations))
                        try:
                            result = sorted(word_result[-1]["alternatives"], key=lambda x: x["confidence"])[-1]
                            confidence = float(result["confidence"])
                        except:
                            result = word_result[-1]["alternatives"][0]
                            confidence = float(result["redactions"][0]["confidence"])
                        # result = sorted(word_result[-1]["alternatives"], key=lambda x: x["confidence"])[-1]

                        # Write the word, and a leading space if this isn't the start of the segment
                        if (skipLeadingSpace):
                            skipLeadingSpace = False
                            wordToAdd = result["content"]
                        else:
                            wordToAdd = " " + result["content"]

                        # If the next item is punctuation, add it to the current word
                        try:
                            word_result_index = channel["items"].index(word_result[0])
                            next_item = channel["items"][word_result_index + 1]
                            if next_item["type"] == "punctuation":
                                wordToAdd += next_item["alternatives"][0]["content"]
                        except IndexError:
                            pass

                        # Finally, add the word and confidence to this segment's list
                        nextSpeechSegment.segmentText += wordToAdd
                        confidenceList.append({"text": wordToAdd,
                                               "confidence": confidence,
                                               "start_time": float(word["start_time"]),
                                               "end_time": float(word["end_time"])})

        # Sort the segments, as they are in channel-order and not speaker-order, then
        # merge together turns from the same speaker that are very close together
        speechSegmentList = sorted(speechSegmentList, key=lambda segment: segment.segmentStartTime)
        speechSegmentList = merge_speaker_segments(speechSegmentList)

    # Process an Audio-segment non-analytics file
    elif isAudioSegmentsMode:
        for segment in data["results"]["audio_segments"]:
            nextSpeechSegment = SpeechSegment()
            nextSpeechSegment.segmentStartTime = float(segment["start_time"])
            nextSpeechSegment.segmentEndTime = float(segment["end_time"])
            nextSpeechSegment.segmentText = segment["transcript"]
            nextSpeechSegment.segmentSpeaker = ""  # Default speaker label for audio segments
            confidenceList = []
 
            for item_id in segment["items"]:
                item = data["results"]["items"][item_id]
                if item["type"] == "pronunciation":
                    word_result = item["alternatives"][0]
                    confidence = float(word_result["confidence"])
                    wordToAdd = word_result["content"]
                    if confidenceList:
                        wordToAdd = " " + wordToAdd  # Add space before each word except the first one
                    confidenceList.append({
                        "text": wordToAdd,
                        "confidence": confidence,
                        "start_time": float(item["start_time"]),
                        "end_time": float(item["end_time"])
                    })
                elif item["type"] == "punctuation":
                    word_result = item["alternatives"][0]
                    wordToAdd = word_result["content"]
                    if confidenceList:
                        confidenceList[-1]["text"] += wordToAdd  # Last word
 
            nextSpeechSegment.segmentConfidence = confidenceList
 
             # Check if new segment based on the delay. There are no speaker or channels like the previous two modes so we can't check that
            if speechSegmentList and (nextSpeechSegment.segmentStartTime - speechSegmentList[-1].segmentEndTime) >= START_NEW_SEGMENT_DELAY:
                speechSegmentList.append(nextSpeechSegment)
            else:
                if speechSegmentList:
                    speechSegmentList[-1].segmentEndTime = nextSpeechSegment.segmentEndTime
                    speechSegmentList[-1].segmentText += " " + nextSpeechSegment.segmentText
                    for wordConfidence in confidenceList:
                        speechSegmentList[-1].segmentConfidence.append(wordConfidence)
                else:
                    speechSegmentList.append(nextSpeechSegment)
 
    # Return our full turn-by-turn speaker segment list
    return speechSegmentList

def lambda_handler(event, context):
    """
    Entrypoint for the Lambda function.
    """
    print("transcribe_to_docx.lambda_handler started")

    # Get environment variables
    BUCKET = os.environ["BUCKET"]               # S3 output bucket name
    DOCX_MAX_DURATION = float(os.environ['DOCX_MAX_DURATION'])   # Max transcription duration to process

    # Attempt to retrieve job details
    job_status = event["detail"]["TranscriptionJobStatus"]
    job_name = event["detail"]["TranscriptionJobName"]
    try:
        job_info = ts_client.get_transcription_job(TranscriptionJobName=job_name)["TranscriptionJob"]
        print(f"Job info: {job_info}")
    except Exception as e:
        # Can't retrieve job details, so we can't do anything
        print(e)
        title = "Transcription job failed"
        default_message = f"Failed to retrieve job details for {job_name}"
        return {
            'statusCode': 500,
            'body': {
                'subject': title,
                'lambda': default_message,
                'default': default_message,
            }
        }

    # Check duration and error if exceeded
    if global_audio_duration > DOCX_MAX_DURATION:
        default_message = f"Job name: {job_name}. Total transcription duration ({global_audio_duration:.1f}s) exceeded DOCX_MAX_DURATION ({DOCX_MAX_DURATION}s), download and finish command line using the available JSON."
        lambda_message = f"Job name:<br><pre>{job_name}</pre><br>Total transcription duration ({global_audio_duration:.1f}s) exceeded DOCX_MAX_DURATION ({DOCX_MAX_DURATION}s), download and finish command line using the available JSON."
        print(default_message)
        title = "Transcription job stopped"
        deleteUploadFileHelper(job_status, job_info)
        return {
            'statusCode': 500,
            'body': {
                'subject': title,
                'lambda': lambda_message,
                'default': default_message,
            }
        }

    # Try and download the transcript JSON
    if "RedactedTranscriptFileUri" in job_info["Transcript"]:
        download_url = job_info["Transcript"]["RedactedTranscriptFileUri"]
    else:
        download_url = job_info["Transcript"]["TranscriptFileUri"]
    try:
        transcript = get_json(download_url)
    except Exception as e:
        print(e)
        title = "Transcription job failed"
        default_message = f"Failed to download transcript for {job_name}"
        print(default_message)
        return {
            'statusCode': 500,
            'body': {
                'subject': title,
                'lambda': default_message,
                'default': default_message,
            }
        }

    # Check the job settings for speaker/channel/audio ID
    if "ChannelIdentification" in job_info["Settings"] and job_info["Settings"]["ChannelIdentification"] == True:
        speech_segments = create_turn_by_turn_segments(transcript, isChannelMode = True)
    elif "ShowSpeakerLabels" in job_info["Settings"] and job_info["Settings"]["ShowSpeakerLabels"] == True:
        speech_segments = create_turn_by_turn_segments(transcript, isSpeakerMode = True)
    elif "ChannelIdentification" in job_info["Settings"] and job_info["Settings"]["ChannelIdentification"] == False:
        speech_segments = create_turn_by_turn_segments(transcript, isAudioSegmentsMode = True)
    else:
        # We do not support non-speaker mode in this version
        title = "Transcription job failed"
        default_message = f"Transcribe job name: {job_name}. Channel/speaker/audio mode must be used in this version."
        print(default_message)
        return {
            'statusCode': 500,
            'body': {
                'subject': title,
                'lambda': default_message,
                'default': default_message,
            }
        }

    # Write out the file
    os.chdir("/tmp")
    output_file = job_info["TranscriptionJobName"] + ".docx"
    write(transcript, speech_segments, job_info, output_file)

    # Upload file to S3
    # Use bucket provided in the environment variable, plus today's date
    key = today + "/" + output_file
    try:
        s3.upload_file(output_file, BUCKET, key)
    except Exception as e:
        print(e)
        title = "Transcription job failed"
        default_message = f"Failed to upload file {output_file} to S3 bucket {BUCKET}"
        print(default_message)
        return {
            'statusCode': 500,
            'body': {
                'subject': title,
                'lambda': default_message,
                'default': default_message,
            }
        }

    deleteUploadFileHelper(job_status, job_info)

    title = "Transcription job completed"
    s3uri = f"s3://{BUCKET}/{key}"
    print(f"{title}: Job Name: {job_name} Transcript available at: {s3uri}")
    lambda_message = f"Job Name:<br><pre>{job_name}</pre><br>Transcript available at:<br><pre>{s3uri}</pre>"
    default_message = f"Transcription job {job_name} completed. Transcript available at {s3uri}"
    creation_time = job_info["CreationTime"].strftime("%Y-%m-%d")
    total_duration = str(round(global_audio_duration, 2))
    return {
        'statusCode': 200,
        'body': {
            'job': job_name,
            'duration': total_duration,
            'languages': global_languages,
            'confidence': global_average_confidence,
            'created': creation_time,
            'subject': title,
            's3uri': s3uri,
        }
    }

def deleteUploadFileHelper(job_status, job_info):
    """
    Helper to delete the upload file

    :param job_status: event_message TranscriptionJobStatus
    :param job_info: get_transcription_job TranscriptionJob
    :param WEBHOOK: webhook for teams notification
    """
    if job_status == "COMPLETED":
        upload_uri = job_info["Media"]["MediaFileUri"]
        upload_bucket, upload_key = find_bucket_key(upload_uri)
        print(f"Deleting from bucket {upload_bucket} key {upload_key}")
        try:
            s3.delete_object(Bucket=upload_bucket, Key=upload_key)
        except Exception as e:
            print(e)

def load_transcribe_job_status(cli_args):
    """
    Loads in the job status for the job named in cli_args.inputJob.  This will try both the standard Transcribe API
    as well as the Analytics API, as the customer may not know which one their job relates to

    :param cli_args: CLI arguments used for this processing run
    :return: The job status structure (different between standard/analytics), and a 'job-completed' flag
    """
    transcribe_client = boto3.client("transcribe")

    try:
        # Extract the standard Transcribe job status
        job_status = transcribe_client.get_transcription_job(TranscriptionJobName=cli_args.inputJob)["TranscriptionJob"]
        cli_args.analyticsMode = False
        completed = job_status["TranscriptionJobStatus"]
    except:
        # That job doesn't exist, but it may have been an analytics job
        job_status = transcribe_client.get_call_analytics_job(CallAnalyticsJobName=cli_args.inputJob)["CallAnalyticsJob"]
        cli_args.analyticsMode = True
        completed = job_status["CallAnalyticsJobStatus"]

    return job_status, completed

def generate_document():
    """
    Entrypoint for the command-line interface.
    """
    # Parameter extraction
    cli_parser = argparse.ArgumentParser(prog='transcribe_to_docx',
                                         description='Turn an Amazon Transcribe job output into an MS Word document')
    source_group = cli_parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument('--inputFile', metavar='filename', type=str, help='File containing Transcribe JSON output')
    source_group.add_argument('--inputJob', metavar='job-id', type=str, help='Transcribe job identifier')
    cli_parser.add_argument('--outputFile', metavar='filename', type=str, help='Output file to hold MS Word document')
    cli_parser.add_argument('--confidence', choices=['on', 'off'], default='off', help='Displays information on word confidence scores throughout the transcript')
    cli_parser.add_argument('--keep', action='store_true', help='Keeps any downloaded job transcript JSON file')
    cli_args = cli_parser.parse_args()

    # If we're downloading a job transcript then validate that we have a job, then download it
    if cli_args.inputJob is not None:
        try:
            job_info, job_status = load_transcribe_job_status(cli_args)
        except:
            # Exception, most-likely due to the job not existing
            print("NOT FOUND: Requested job-id '{0}' does not exist.".format(cli_args.inputJob))
            exit(-1)

        # If the job hasn't completed then there is no transcript available
        if job_status == "FAILED":
            print("{0}: Requested job-id '{1}' has failed to complete".format(job_status, cli_args.inputJob))
            exit(-1)
        elif job_status != "COMPLETED":
            print("{0}: Requested job-id '{1}' has not yet completed.".format(job_status, cli_args.inputJob))
            exit(-1)

        # The transcript is available from a signed URL - get the redacted if it exists, otherwise the non-redacted
        if "RedactedTranscriptFileUri" in job_info["Transcript"]:
            # Get the redacted transcript
            download_url = job_info["Transcript"]["RedactedTranscriptFileUri"]
        else:
            # Gen the non-redacted transcript
            download_url = job_info["Transcript"]["TranscriptFileUri"]
        cli_args.inputFile = cli_args.inputJob + "-asrOutput.json"

        # Try and download the JSON - this will fail if the job delivered it to
        # an S3 bucket, as in that case the service no longer has the results
        try:
            urlretrieve(download_url, cli_args.inputFile)
        except:
            print("UNAVAILABLE: Transcript for job-id '{0}' is not available for download.".format(cli_args.inputJob))
            exit(-1)

        # Set our output filename if one wasn't supplied
        if cli_args.outputFile is None:
            cli_args.outputFile = cli_args.inputJob + ".docx"

    # Load in the JSON file for processing
    json_filepath = Path(cli_args.inputFile)
    if json_filepath.is_file():
        json_data = json.load(open(json_filepath.absolute(), "r", encoding="utf-8"))
    else:
        print("FAIL: Specified JSON file '{0}' does not exists.".format(cli_args.inputFile))
        exit(-1)

    # If this is a file-input run then try and load the job status (which may no longer exist)
    if cli_args.inputJob is None:
        try:
            # Ensure we don't delete our JSON later, reset our output file to match the job-name if it's currently blank
            cli_args.keep = True
            if cli_args.outputFile is None:
                if "results" in json_data:
                    cli_args.outputFile = json_data["jobName"] + ".docx"
                    cli_args.inputJob = json_data["jobName"]
                else:
                    cli_args.outputFile = json_data["JobName"] + ".docx"
                    cli_args.inputJob = json_data["JobName"]
            job_info, job_status = load_transcribe_job_status(cli_args)
        except:
            # No job status - need to quickly work out what mode we're in,
            # as standard job results look different from analytical ones
            cli_args.inputJob = None
            cli_args.outputFile = cli_args.inputFile + ".docx"
            cli_args.analyticsMode = "results" not in json_data
            if "language_codes" in json_data["results"]:
                job_info = {'language_codes': json_data["results"]["language_codes"]}
            else:
                job_info = None

    # Confirm that we have speaker or channel information then generate the core transcript
    start = perf_counter()
    if "channel_labels" in json_data["results"]:
        speech_segments = create_turn_by_turn_segments(json_data, isChannelMode = True)
    elif "speaker_labels" in json_data["results"]:
        speech_segments = create_turn_by_turn_segments(json_data, isSpeakerMode = True)
    elif "audio_segments" in json_data["results"]:
        speech_segments = create_turn_by_turn_segments(json_data, isAudioSegmentsMode = True)
    else:
        print("FAIL: No speaker or channel information found in JSON file.")
        exit(-1)

    # Write out our file and the performance statistics
    write(json_data, speech_segments, job_info, cli_args.outputFile)
    finish = perf_counter()
    duration = round(finish - start, 2)
    print(f"> Transcript {cli_args.outputFile} writen in {duration} seconds.")

    # Finally, remove any temporary downloaded JSON results file
    if (cli_args.inputJob is not None) and (not cli_args.keep):
        os.remove(cli_args.inputFile)

# Main entrypoint
if __name__ == "__main__":
    generate_document()
