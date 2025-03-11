output "docx_lambda_name" {
  value = aws_lambda_function.docx.id
}

output "ts_lambda_name" {
  value = module.transcribe.lambda_function_name
}
