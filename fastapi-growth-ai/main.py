# main.py
import asyncio
import threading
from typing import Optional
from typing import List
from datetime import datetime, date, timedelta
from jose import JWTError, jwt
import os
# -
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import Body, FastAPI, Path, Query, UploadFile, Depends, Query, HTTPException, status, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
# -
from sqlalchemy import func, distinct, desc
from sqlalchemy.orm import Session, joinedload ,aliased  # Add this import
from pydantic import BaseModel

import uvicorn
# -
from models import Remarks, ResearchHub, SessionLocal, User, CapturedImage, ImagePrediction, ScheduleCapture
# -
from users import create_access_token, create_user, get_all_users, get_user_by_username, UserRoleEnum, hash_password, authenticate_user, get_current_user
from capture import capture_and_save_image
from predict import predict_and_store_predictions  # Add this import
# -
from threading import Thread


app = FastAPI()

# Assuming "img" is the folder where your images are stored
app.mount("/img", StaticFiles(directory="img"), name="img")



# Configure CORS
origins = ["*"]  # Update with the origin of your web page
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)






# Mount the 'img' directory to serve static files
app.mount("/img", StaticFiles(directory="img"), name="img")



# Import your models and SessionLocal here

@app.get("/captured_data")
async def get_captured_data():
    db = SessionLocal()
    # Group by timestamp and count the number of distinct plant names
    plants_per_day = (
        db.query(
            func.DATE(CapturedImage.timestamp).label('day'),
            func.count(distinct(ImagePrediction.plant_name)
                       ).label('plant_count')
        )
        # Adjust the join condition
        .join(ImagePrediction, CapturedImage.id == ImagePrediction.captured_images_id)
        .filter(ImagePrediction.plant_name.isnot(None))
        .group_by('day')
        .all()
    )

    # Get all distinct plant names
    all_plant_names = (
        db.query(ImagePrediction.plant_name.distinct())
        .filter(ImagePrediction.plant_name.isnot(None))
        .group_by('plant_name')
        .all()
    )

    db.close()

    # Return a combined response with captured images, captured plants, and plants per day
    return {
        "plants_per_day": [{"day": plant.day, "plant_count": plant.plant_count} for plant in plants_per_day],
        "all_plant_names": [plant[0] for plant in all_plant_names],
    }

# FastAPI route to get data for a specific plant by its id


@app.get("/plant_data/{plant}")
async def get_plant_data(plant):
    db = SessionLocal()

    # Query data for the specified plant_id
    plant_data = (
        db.query(CapturedImage, ImagePrediction)
        .join(ImagePrediction, CapturedImage.id == ImagePrediction.captured_images_id)
        .filter(ImagePrediction.plant_name.isnot(None), ImagePrediction.plant_name == plant)
        .group_by('timestamp')
        .all()
    )

    # Check if any data was found for the specified plant_id
    if not plant_data:
        raise HTTPException(status_code=404, detail="Plant data not found")

    # Return the data for the specified plant_id
    return {
        "idenfied_plants": [
            {
                "id": image.CapturedImage.id,
                "filename": image.CapturedImage.filename,
                "timestamp": image.CapturedImage.timestamp,
                "plant_name": image.ImagePrediction.plant_name,
                "disease": image.ImagePrediction.disease,
                "growth_stage": image.ImagePrediction.growth_stage,
            }
            for image in plant_data
        ],
    }


#  Route to get growth analysis data for a user

@app.get("/growth_analysis/{user_id}")
def get_growth_analysis(user_id: int):
    db = SessionLocal()
    # Check if the user exists
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Get growth analysis data for the user, focusing on counting unique stages for each plant name
    growth_analysis_data = (
        db.query(
            ImagePrediction.plant_name,
            func.count(func.distinct(ImagePrediction.growth_stage)).label("unique_stage_count")
        )
        .join(CapturedImage, CapturedImage.id == ImagePrediction.captured_images_id)
        .filter(CapturedImage.user_id == user_id)
        .group_by(ImagePrediction.plant_name)
        .all()
    )

    # Format the response to include the plant name and the count of unique growth stages for each plant
    response_data = [
        {
            "plant_name": row.plant_name,
            "unique_stage_count": row.unique_stage_count
        }
        for row in growth_analysis_data
    ]

    return {"user_id": user_id, "growth_analysis": response_data}


# ..

@app.get("/plant_stages/{plant_name}/{user_id}")
async def get_plant_stages(plant_name: str, user_id: int):
    db: Session = SessionLocal()
    
    stages_data = (
        db.query(
            ImagePrediction.growth_stage, 
            CapturedImage.timestamp,
            CapturedImage.filename
        )
        .join(CapturedImage, CapturedImage.id == ImagePrediction.captured_images_id)
        .filter(ImagePrediction.plant_name == plant_name, CapturedImage.user_id == user_id)
        .order_by(CapturedImage.timestamp.asc())
        .all()
    )
    
    if not stages_data:
        raise HTTPException(status_code=404, detail="No stages found for given plant name and user ID")

    # Process the results to filter out only the latest entry for each growth stage
    latest_stages = {}
    for stage, timestamp, filename in stages_data:
        if stage not in latest_stages or timestamp > latest_stages[stage]['timestamp']:
            latest_stages[stage] = {'timestamp': timestamp, 'filename': filename}
    
    response_data = [
        {
            "growth_stage": stage,
            "month": latest_stages[stage]['timestamp'].strftime("%Y-%m"),
            "image_url": f"/img/{latest_stages[stage]['filename']}",
        }
        for stage in latest_stages
    ]

    return {"plant_stages": response_data}


# ..

@app.get("/plant_stages_data/{plant_name}/{user_id}")
async def get_plant_stages_data(plant_name: str, user_id: int):
    # Query to count the occurrences of each growth stage for the specified plant and user
    db: Session = SessionLocal()
    stage_counts = (
        db.query(
            ImagePrediction.growth_stage,
            func.count(ImagePrediction.growth_stage).label('stage_count')
        )
        .join(CapturedImage, CapturedImage.id == ImagePrediction.captured_images_id)
        .filter(ImagePrediction.plant_name == plant_name, CapturedImage.user_id == user_id)
        .group_by(ImagePrediction.growth_stage)
        .all()
    )

    if not stage_counts:
        raise HTTPException(status_code=404, detail="No data found for given plant name and user ID")

    # Constructing the response
    stage_data = [
        {
            "stage_name": stage.growth_stage,
            "stage_count": stage.stage_count
        }
        for stage in stage_counts
    ]

    return {
        "stage_data": stage_data
    }






# Endpoint to capture and save images
@app.post("/capture")
async def capture_image(
    user_id: int = Body(...),
    file: UploadFile = UploadFile(...),
):
    # Capture and save the image
    image_data = capture_and_save_image(file,user_id)
    image_id = image_data["id"]
    image_path = os.path.join("img", image_data["filename"])
  
    # Create a thread to handle the prediction
    prediction_thread = threading.Thread(target=predict_and_store_predictions, args=(image_id, image_path))
    prediction_thread.start()

    # Return the image ID immediately without waiting for the prediction
    return {"message": image_id}



# Pydantic model for scheduling captures
class ScheduleCaptureCreate(BaseModel):
    intervals: int
    times: int


@app.post("/schedule")
async def create_schedule(schedule_data: ScheduleCaptureCreate):
    db = SessionLocal()
    try:
        # Insert the schedule data into the database
        schedule = ScheduleCapture(**schedule_data.dict())
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        return schedule
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail="Failed to create schedule")
    finally:
        db.close()


# Route to insert data into ResearchHub
@app.post("/research_hub")
async def insert_into_research_hub(
    user_id: int,
    topic: str,
    image_prediction_id: int
):
    db = SessionLocal()
    try:
        # Check if the user and image prediction exist
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        image_prediction = db.query(ImagePrediction).filter(ImagePrediction.id == image_prediction_id).first()
        if not image_prediction:
            raise HTTPException(status_code=404, detail="ImagePrediction not found")

        # Insert data into ResearchHub table
        research_hub = ResearchHub(user_id=user_id, topic=topic, image_prediction_id=image_prediction_id)
        db.add(research_hub)
        db.commit()

        return {"message": "Data inserted into ResearchHub successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# Endpoint to retrieve and group Research Hub data by user-submitted prediction topics.
# Data includes user details, image predictions, and remarks count.
# Executes a complex SQLAlchemy query, processes data, and structures the response.

@app.get("/research_hub")
async def get_research_hub():
    db = SessionLocal()

    UserAlias = aliased(User)
    ImagePredictionAlias = aliased(ImagePrediction)

    research_hub_data = (
        db.query(ResearchHub, User, ImagePrediction, CapturedImage, func.count(Remarks.id))
        .join(User, User.id == ResearchHub.user_id)
        .join(ImagePrediction, ImagePrediction.id == ResearchHub.image_prediction_id)
        .join(CapturedImage, CapturedImage.id == ImagePrediction.captured_images_id)
        .outerjoin(Remarks, Remarks.research_hub_id == ResearchHub.id)
        .group_by(ResearchHub.id)
        .all()
    )

    if not research_hub_data:
        raise HTTPException(status_code=404, detail="Research Hub not found")

    response_data = [
        {
            "research_hub_id": hub.id,
            "topic": hub.topic,
            "user_name": user.username,
            "image_url": f"/img/{captured_image.filename}",
            "remarks_count": remarks_count
        }
        for hub, user, prediction, captured_image, remarks_count in research_hub_data
    ]

    # Add print statements for debugging
    for entry in response_data:
        print("Complete image URL:", entry["image_url"])

    return {"research_hub": response_data}

# ...

@app.post("/research_hub_remarks")
async def insert_into_remarks(
    research_hub_id: int,
    remarks: str,
    user_id: int
):
    db = SessionLocal()

    # Check if the research hub exists
    research_hub = db.query(ResearchHub).filter(ResearchHub.id == research_hub_id).first()
    if not research_hub:
        raise HTTPException(status_code=404, detail="Research Hub not found")

    # Create a new remark with user_id
    remark = Remarks(replies=remarks, research_hub_id=research_hub_id, user_id=user_id)

    # Add and commit the remark to the database
    db.add(remark)
    db.commit()
    db.refresh(remark)

    return {"message": "Remark added successfully"}





# Endpoint to fetch and structure remarks for a specific research hub.
# Joins remarks with usernames for comprehensive information in the response.
# Essential for displaying and facilitating collaboration on Research Hub remarks.
# Includes usernames for user context, improving user experience and engagement.
@app.get("/research_hub_remarks/{research_hub_id}")
async def get_remarks_by_hub_id(research_hub_id: int):
    db = SessionLocal()
    # Fetch remarks based on research_hub_id, join with the User table
    remarks_with_usernames = (
        db.query(User.username, Remarks.replies)
        .outerjoin(Remarks, User.id == Remarks.user_id)
        .filter(Remarks.research_hub_id == research_hub_id)
        .all()
    )

    # Extract relevant information for the response
    result = {
        "remarks": [
            {"remark_number": i + 1, "username": username, "replies": remarks}
            for i, (username, remarks) in enumerate(remarks_with_usernames)
        ]
    }

    return result




@app.get("/capture-settings")
async def get_capture_settings():
    db = SessionLocal()
    settings = db.query(ScheduleCapture).order_by(
        desc(ScheduleCapture.id)).first()
    db.close()
    return {"intervals": settings.intervals, "times": settings.times}


@app.get("/items")
async def get_all_items():
    db = SessionLocal()
    items = db.query(ImagePrediction).order_by(
        desc(ImagePrediction.id)).limit(10).all()
    return items


@app.get("/item/{item_id}")
async def get_item_by_id(item_id: int):
    db = SessionLocal()
    item = db.query(ImagePrediction).filter(
        ImagePrediction.id == item_id).first()
    if item is not None:
        return item
    raise HTTPException(status_code=404, detail="Item not found.")


# Endpoint to fetch disease predictions for today's captured images, 
# presented as a daily notification dropdown in the frontend.
# Queries the database to identify diseases based on timestamp 
# conditions for images captured today.
@app.get("/diseases_today")
async def get_diseases_today():
    today = date.today()
    db = SessionLocal()
    # Query the database for predictions with diseases and timestamp for today
    predictions = db.query(ImagePrediction).join(CapturedImage).filter(
        ImagePrediction.disease.isnot(None),
        CapturedImage.timestamp >= today,
        CapturedImage.timestamp < today + timedelta(days=2)
    )
    # Get the results
    results = predictions.all()
    if not results:
        raise HTTPException(
            status_code=404, detail="No matching records found")
    return results


@app.get("/diseases")
async def get_diseases():
    db = SessionLocal()
    # Query the database for predictions with diseases and timestamp for today
    predictions = db.query(ImagePrediction).join(CapturedImage).filter(
        ImagePrediction.disease.isnot(None)
    )
    # Get the results
    results = predictions.all()
    if not results:
        raise HTTPException(
            status_code=404, detail="No matching records found")
    return results


# Registration endpoint
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: Optional[UserRoleEnum] = UserRoleEnum.user


# Registration endpoint
@app.post("/register")
async def register_user(user: UserCreate):
    # Check if the username or email already exists
    existing_user = get_user_by_username(user.username)
    if existing_user:
        raise HTTPException(
            status_code=400, detail="Username already taken")

    existing_email = get_user_by_username(user.email)
    if existing_email:
        raise HTTPException(
            status_code=400, detail="Email already in use")

    user_data = user.dict()

    # Hash the user's password before saving it
    user_data["hashed_password"] = hash_password(user.password)
    del user_data["password"]

    # Create the user
    created_user = create_user(user_data)
    return created_user


@app.post("/login")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user_token = await authenticate_user(form_data.username, form_data.password)
    if user_token is None:
        raise HTTPException(
            status_code=401, detail="Incorrect username or password")

    db = SessionLocal()
    user = db.query(User).filter(User.username == form_data.username).first()
    db.close()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    response_data = {
        "access_token": user_token,
        "token_type": "bearer",
        "user_role": user.role,
        "user_id": user.id,
        "user_name": user.username
    }

    return response_data


# Edit user role endpoint (Requires admin privileges)
@app.put("/user/{user_id}/edit-role")
async def edit_user_role(user_id: int, new_role: UserRoleEnum):
    db = SessionLocal()
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        db.close()
        raise HTTPException(status_code=404, detail="User not found")
    db_user.role = new_role
    db.commit()
    db.close()
    return {"message": "User role updated successfully"}


# Delete user endpoint (Requires admin privileges)
@app.delete("/user/{user_id}/delete")
async def delete_user(user_id: int):
    db = SessionLocal()
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        db.close()
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(db_user)
    db.commit()
    db.close()
    return {"message": "User deleted successfully"}


@app.get("/users")
async def list_users():
    users = get_all_users()
    return {"users": users}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
