resource "aws_s3_bucket" "bucket_1" {
    bucket_prefix = "bl-ssrc-ats-input-"

}

resource "aws_s3_bucket" "bucket_2" {
    bucket_prefix = "bl-ssrc-ats-ts-output-"

}

resource "aws_s3_bucket" "bucket_3" {
    bucket_prefix = "bl-ssrc-ats-download-"
    
}