# predict.py
import cv2
import tensorflow as tf
import numpy as np
from PIL import Image
from models import  SessionLocal, ImagePrediction 


class PlantPredictor:
    def __init__(self, plant_model, disease_model, growth_stage_model):
        self.plant_name_model = plant_model
        self.disease_model = disease_model
        self.growth_stage_model = growth_stage_model
        # make it null if not identified
        self.plant_names = ["Banana_plant", "Tomato_plant", "none"]
        self.growth_stage_labels = [
            "seedling", "vegetative", "flowering","fruiting", "haverst", "none"]
        self.disease_labels = ["spider_mites","singatoka","fusarium_wilt","late_blight",
            "mosaic_virus", "bunch_top","panama","none"]
               

    # ...
    def predict(self, image_path):
        # Preprocess the image using OpenCV
        image = cv2.imread(image_path)
        image = cv2.resize(image, (224, 224))
        image = image / 255.0
        image = np.reshape(image, (1, 224, 224, 3))

        # Make predictions with each model
        plant_name_prediction = self.plant_name_model.predict(image)
        disease_prediction = self.disease_model.predict(image)
        growth_stage_prediction = self.growth_stage_model.predict(image)

        return plant_name_prediction, disease_prediction, growth_stage_prediction


# This function takes an image, runs it through pre-trained models for 
# plant name, disease, and growth stage predictions,
# and stores the resulting predictions for further analysis.

def predict_and_store_predictions(image_id, image_path):
    # Load pre-trained models for Plant Name, Disease, and Growth Stage
    plant_name_model = tf.keras.models.load_model('plant_name_model.h5')
    disease_model = tf.keras.models.load_model('disease_model.h5')
    growth_stage_model = tf.keras.models.load_model('growth_stage_model.h5')

    # Initialize the PlantPredictor class with the loaded models
    plant_predictor = PlantPredictor(
        plant_name_model, disease_model, growth_stage_model)

    # Use the PlantPredictor instance to make predictions
    plant_name_prediction, disease_prediction, growth_stage_prediction = plant_predictor.predict(
        image_path)

    # Extract the predicted class indices
    predicted_plant_index = np.argmax(plant_name_prediction[0])
    predicted_disease_index = np.argmax(disease_prediction[0])
    predicted_growth_stage_index = np.argmax(growth_stage_prediction[0])

    # Map the indices to class labels
    predicted_plant_name = plant_predictor.plant_names[predicted_plant_index]
    predicted_disease = plant_predictor.disease_labels[predicted_disease_index]
    predicted_growth_stage = plant_predictor.growth_stage_labels[predicted_growth_stage_index]


    # Create an ImagePrediction record and associate it with the captured image
    db = SessionLocal()
    db_image = ImagePrediction(
        plant_name = predicted_plant_name,
        disease = predicted_disease,
        growth_stage = predicted_growth_stage,
        captured_images_id = image_id 
    )
    db.add(db_image)
    db.commit()
    db.refresh(db_image)
    image_id = db_image.id  # Get the image ID from the database after it's created
    db.close()

    return {"plant": image_id}
