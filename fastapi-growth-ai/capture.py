# capture.py
import os
import uuid
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from models import SessionLocal, CapturedImage

upload_directory = "img"
# Mount the 'img' directory to serve static files


def capture_and_save_image(file: UploadFile, user_id:int):
    try:
        unique_filename = str(uuid.uuid4()) + file.filename
        filename = os.path.join(upload_directory, unique_filename)
        os.makedirs(upload_directory, exist_ok=True)
        with open(filename, "wb") as image_file:
            image_file.write(file.file.read())
        db = SessionLocal()
        db_image = CapturedImage(
            filename=unique_filename ,
            user_id=user_id
        )
        db.add(db_image)
        db.commit()
        db.refresh(db_image)
        image_id = db_image.id  # Get the image ID from the database after it's created
        db.close()

        return {"id": image_id, "filename": unique_filename, 
                "text": "image data is here", "user":user_id }
    except Exception as e:
        print("Error:", str(e))
        raise HTTPException(status_code=500, detail="Image capture error")
