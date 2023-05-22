import numpy as np
from PIL import Image
from fastapi import FastAPI, File, UploadFile
import torch
from torchvision import transforms, models
from PIL import Image
from pathlib import Path
from io import BytesIO
import uvicorn
import cv2
from typing import List
from torchvision.models import resnet18

#모델 경로
MODEL_PATHS = [
    '/Users/joseongju/Desktop/dopic_fastapi/dopic_fastapi/fastapi/model/bd_model.pt',
    '/Users/joseongju/Desktop/dopic_fastapi/dopic_fastapi/fastapi/model/talmo_model.pt',
    '/Users/joseongju/Desktop/dopic_fastapi/dopic_fastapi/fastapi/model/mg_model.pt',
    '/Users/joseongju/Desktop/dopic_fastapi/dopic_fastapi/fastapi/model/pg_model.pt',
    '/Users/joseongju/Desktop/dopic_fastapi/dopic_fastapi/fastapi/model/mhn_model.pt'
]

device = torch.device("cpu")

models_list = []

for PATH in MODEL_PATHS:
    model = models.resnet18(pretrained=False)
    num_features = model.fc.in_features
    model.fc = torch.nn.Linear(num_features, 4)  # 출력 클래스 개수를 4로 설정

    state_dict = torch.load(PATH, map_location=device)
    model.load_state_dict(state_dict)
    model.eval()
    models_list.append(model)

severity_mapping = {
    0: '양호',
    1: '경증',
    2: '중등도',
    3: '중증',
}

app = FastAPI()

    
def predict(image: np.ndarray, model):
    transform = transforms.Compose([
        transforms.Resize([int(224), int(224)], interpolation=transforms.InterpolationMode.BICUBIC),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    image = transform(image)
    image = image.unsqueeze(0) 
    with torch.no_grad():
        predictions = model(image) 
        _, predicted_class = torch.max(predictions, 1)
        predicted_class_int = predicted_class.item()
        return severity_mapping[predicted_class_int], predicted_class_int

def load_image_into_numpy_array(data):
    npimg = np.frombuffer(data, np.uint8)
    frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(frame_rgb)
    return pil_image

#fastapi 파일 업로드 
@app.get("/")
def read_root():
    return {"message": "두피 이미지 인식 api"}

@app.post("/predict")
async def predict_api(files: list[UploadFile] = File(...)):
    predictions = []
    for file in files:
        contents = await file.read()
        contents = load_image_into_numpy_array(contents)
        file_predictions = {}
        for idx, model in enumerate(models_list):
            prediction, prediction_int = predict(contents, model)
            if idx == 0:
                file_predictions['비듬'] = {'description': prediction, 'value': prediction_int}
            elif idx == 1:
                file_predictions['탈모'] = {'description': prediction, 'value': prediction_int}
            elif idx == 2: 
                file_predictions['미세각질'] = {'description': prediction, 'value': prediction_int}
            elif idx == 3:
                file_predictions['피지'] = {'description': prediction, 'value': prediction_int}
            elif idx == 4:
                file_predictions['모낭홍반농포'] = {'description': prediction, 'value': prediction_int}
        predictions.append({"predictions": file_predictions})
    
    return {"predictions": predictions}
    
if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=8000)