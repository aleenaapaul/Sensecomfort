# 🌸 SenseComfort — Menstruation Prediction Dashboard  
### Smart Early Detection for Autism Support  
Built by **Aleena Paul**

---

## 📌 Overview

**SenseComfort** is an IoT-based early menstruation prediction system designed for autistic individuals who may have difficulty communicating discomfort or physical symptoms.

The system uses:

- A **wet sensor** connected to an **ESP8266**
- A **Flask backend** running a trained ML model
- A **modern, responsive dashboard** for caregivers  

It predicts whether the user is **approaching menstruation in 4–5 days**, displays real-time sensor readings, and provides clear visual cues such as:

- Animated probability ring  
- Status indicators (Normal / Approaching / Detected)  
- Estimated countdown  
- Recent sensor readings  

---

## 🧠 Key Features

### ✔ Machine Learning Period Prediction  
Trained using real multi-user resistance datasets (Aleena, Mary, Farsana).

Model performance:
- **92% accuracy**
- **97% recall**
- **0.98 ROC-AUC**

### ✔ Real-time IoT Integration  
ESP8266 sends live sensor values to the backend:

```json
{ "resistance": 823 }
