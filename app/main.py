from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import boto3
import os

# Database and Models
from .database import engine, Base, SessionLocal
from .models import User, Photo
from .auth import hash_password, verify_password, create_access_token, get_current_user

# Pydantic Schemas
class UserRegister(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

# Initialize Database Tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

# --- Dependencies ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Environment Variables ---
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET = os.getenv("S3_BUCKET")

# --- S3 Client ---
s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)

# --- Routes ---

@app.get("/")
def home():
    return {"message": "Personal Cloud Photos API (S3 version) is running"}

# STEP 4: Register Endpoint
@app.post("/register")
def register(user: UserRegister, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=user.email,
        hashed_password=hash_password(user.password)
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User created successfully"}

# STEP 5: Login Endpoint
@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()

    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    access_token = create_access_token(data={"sub": db_user.email})

    return {"access_token": access_token, "token_type": "bearer"}

# Upload to S3 (Step 2 & 3: Protected with authentication and saves metadata)
@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Step 2: Create S3 key with user_id path (bucket/user_id/filename.jpg)
    s3_key = f"{current_user.id}/{file.filename}"
    
    # Upload to S3
    s3.upload_fileobj(
        file.file,
        S3_BUCKET,
        s3_key,
        ExtraArgs={"ContentType": file.content_type}
    )
    
    # Step 3: Save photo metadata to database
    new_photo = Photo(
        user_id=current_user.id,
        filename=file.filename,
        s3_key=s3_key
    )
    
    db.add(new_photo)
    db.commit()
    db.refresh(new_photo)

    return {"filename": file.filename, "status": "uploaded to S3 successfully"}

# List files from S3 (Gallery) - Step 4: Filter by authenticated user
@app.get("/gallery", response_class=HTMLResponse)
def gallery(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Step 4: Query photos from database filtered by current user
    photos = db.query(Photo).filter(Photo.user_id == current_user.id).all()

    image_tags = ""
    for photo in photos:
        # Generate pre-signed URL (expires in 1 hour for security)
        image_url = s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": S3_BUCKET,
                "Key": photo.s3_key
            },
            ExpiresIn=3600  # 1 hour
        )
        image_tags += f'<img src="{image_url}" />'

    html_content = f"""
    <html>
        <head>
            <title>My Personal Cloud Photos</title>
            <style>
                body {{ font-family: Arial, sans-serif; background: #f5f5f5; }}
                h1 {{ margin-left: 20px; }}
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
            <h1>My Gallery (S3) - {current_user.email}</h1>
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