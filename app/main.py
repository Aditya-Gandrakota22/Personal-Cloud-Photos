from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
import boto3
import os

app = FastAPI()

# Load environment variables
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET = os.getenv("S3_BUCKET")

# Initialize S3 client
s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)

@app.get("/")
def home():
    return {"message": "Personal Cloud Photos API (S3 version) is running"}

# STEP 5 — Upload to S3 instead of local disk
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    s3.upload_fileobj(
        file.file,
        S3_BUCKET,
        file.filename,
        ExtraArgs={"ContentType": file.content_type}
    )

    return {"filename": file.filename, "status": "uploaded to S3 successfully"}

# STEP 6 — List files from S3
@app.get("/gallery", response_class=HTMLResponse)
def gallery():
    response = s3.list_objects_v2(Bucket=S3_BUCKET)

    files = []

    if "Contents" in response:
        for obj in response["Contents"]:
            files.append({
                "name": obj["Key"],
                "created": obj["LastModified"]
            })

    # Sort newest first
    files.sort(key=lambda x: x["created"], reverse=True)

    image_tags = ""

    for file in files:
        image_url = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{file['name']}"
        image_tags += f'<img src="{image_url}" />'

    html_content = f"""
    <html>
        <head>
            <title>My Personal Cloud Photos</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background: #f5f5f5;
                }}

                h1 {{
                    margin-left: 20px;
                }}

                .gallery {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                    gap: 15px;
                    padding: 20px;
                }}

                .gallery img {{
                    width: 100%;
                    border-radius: 12px;
                    object-fit: cover;
                    box-shadow: 0 4px 10px rgba(0,0,0,0.1);
                }}
            </style>
        </head>
        <body>
            <h1>My Gallery (S3)</h1>
            <form action="/upload" method="post" enctype="multipart/form-data" style="margin:20px;">
                <input type="file" name="file">
                <button type="submit">Upload</button>
            </form>
            <div class="gallery">
                {image_tags}
            </div>
        </body>
    </html>
    """

    return html_content