import csv
import os
from datetime import datetime, timezone
from io import StringIO

from azure.core.exceptions import ResourceNotFoundError
from azure.data.tables import TableClient
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobClient, BlobServiceClient


def credential():
    return DefaultAzureCredential(managed_identity_client_id=os.environ.get("AZURE_CLIENT_ID"))


def blob_service():
    return BlobServiceClient(os.environ["STORAGE_ACCOUNT_URL"], credential=credential())


def save_document(job_name, content):
    key = f"{datetime.now(timezone.utc):%Y%m%d}/{job_name}.docx"
    container = os.environ.get("DOWNLOAD_CONTAINER", "download")
    client = blob_service().get_blob_client(container, key)
    client.upload_blob(content, overwrite=True)
    return client.url


def delete_upload(blob_url):
    client = BlobClient.from_blob_url(blob_url, credential=credential())
    try:
        client.delete_blob()
    except ResourceNotFoundError:
        pass


def record_job(job_name, summary, document_url):
    table = TableClient(
        endpoint=os.environ["STORAGE_ACCOUNT_URL"].replace(".blob.", ".table."),
        table_name=os.environ.get("JOBS_TABLE", "jobs"),
        credential=credential(),
    )
    table.upsert_entity({
        "PartitionKey": "jobs",
        "RowKey": job_name,
        "Languages": summary["languages"],
        "TotalDuration": summary["duration"],
        "Confidence": summary["confidence"],
        "Created": datetime.now(timezone.utc).isoformat(),
        "DocumentUrl": document_url,
    })


def export_jobs():
    table = TableClient(
        endpoint=os.environ["STORAGE_ACCOUNT_URL"].replace(".blob.", ".table."),
        table_name=os.environ.get("JOBS_TABLE", "jobs"),
        credential=credential(),
    )
    rows = list(table.query_entities("PartitionKey eq 'jobs'"))
    output = StringIO()
    fields = ["Job", "Languages", "TotalDuration", "Confidence", "Created", "DocumentUrl"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        writer.writerow({"Job": row["RowKey"], **{name: row.get(name, "") for name in fields[1:]}})
    client = blob_service().get_blob_client(os.environ.get("DOWNLOAD_CONTAINER", "download"), "export/transcribe_jobs.csv")
    client.upload_blob(output.getvalue(), overwrite=True)
    return {"count": len(rows), "url": client.url}
