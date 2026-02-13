from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
import shutil
import os
from fastapi.responses import HTMLResponse

app = FastAPI()

# Create media folder if it doesn't exist
if not os.path.exists("media"):
    os.makedirs("media")

app.mount("/media", StaticFiles(directory="media"), name="media")

@app.get("/")
def home():
    return {"message": "Personal Cloud Photos API is running"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_path = f"media/{file.filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"filename": file.filename, "status": "uploaded successfully"}

@app.get("/files")
def list_files():
    files = os.listdir("media")
    file_urls = [f"http://127.0.0.1:8000/media/{file}" for file in files]
    return {"files": file_urls}




@app.get("/gallery", response_class=HTMLResponse)
def gallery():
    files = []
    for filename in os.listdir("media"):
        path = os.path.join("media", filename)
        created = os.path.getctime(path)
        files.append({
            "name": filename,
            "created": created
        })

    files.sort(key=lambda x: x["created"], reverse=True)

    image_tags = ""
    
    for file in files:
        image_url = f"/media/{file['name']}"
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
            <h1>My Gallery</h1>
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