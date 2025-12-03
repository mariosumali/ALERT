"""
Training script for event detector model.
Loads labeled CSV data and trains a model to detect moments of interest.
"""

import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import os
from services.audio_features import extract_audio_features
from services.video_features import extract_video_features

class EventDataset(Dataset):
    """Dataset for event detection training."""
    
    def __init__(self, features, labels):
        self.features = torch.FloatTensor(features)
        self.labels = torch.FloatTensor(labels)
    
    def __len__(self):
        return len(self.features)
    
    def __getitem__(self, idx):
        return self.features[idx], self.labels[idx]

class EventDetectorModel(nn.Module):
    """Simple CNN-based event detector."""
    
    def __init__(self, input_dim=50, num_classes=5):
        super(EventDetectorModel, self).__init__()
        self.fc1 = nn.Linear(input_dim, 128)
        self.fc2 = nn.Linear(128, 64)
        self.fc3 = nn.Linear(64, num_classes)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.3)
    
    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.relu(self.fc2(x))
        x = self.dropout(x)
        x = self.fc3(x)
        return x

def load_labeled_data(csv_path: str):
    """
    Load labeled CSV with columns: file_id, start_time, end_time, event_type
    """
    df = pd.read_csv(csv_path)
    return df

def extract_features_from_files(df: pd.DataFrame, base_path: str = "./uploads"):
    """
    Extract features for each labeled moment.
    """
    features_list = []
    labels_list = []
    
    event_type_map = {
        "Gunshot": 0,
        "Silence": 1,
        "Motion": 2,
        "Occlusion": 3,
        "HighEnergy": 4
    }
    
    for _, row in df.iterrows():
        file_id = row["file_id"]
        file_path = os.path.join(base_path, f"{file_id}.mp4")
        
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            continue
        
        # Extract audio features
        audio_features = extract_audio_features(file_path)
        
        # Extract video features
        video_features = extract_video_features(file_path)
        
        # Combine features into feature vector
        feature_vector = []
        feature_vector.extend(audio_features.get("mfcc_mean", [0] * 13)[:13])
        feature_vector.append(audio_features.get("rms_mean", 0))
        feature_vector.append(audio_features.get("rms_max", 0))
        feature_vector.append(audio_features.get("silence_ratio", 0))
        feature_vector.append(audio_features.get("duration", 0))
        
        feature_vector.append(len(video_features.get("motion_spikes", [])))
        feature_vector.append(video_features.get("occlusion_detected", 0))
        feature_vector.append(video_features.get("duration", 0))
        
        # Pad or truncate to fixed size
        target_size = 50
        while len(feature_vector) < target_size:
            feature_vector.append(0.0)
        feature_vector = feature_vector[:target_size]
        
        features_list.append(feature_vector)
        
        # Create one-hot label
        event_type = row["event_type"]
        label = [0.0] * 5
        if event_type in event_type_map:
            label[event_type_map[event_type]] = 1.0
        labels_list.append(label)
    
    return np.array(features_list), np.array(labels_list)

def train_model(csv_path: str, model_save_path: str = "models/event_detector.pt"):
    """
    Main training function.
    """
    print("Loading labeled data...")
    df = load_labeled_data(csv_path)
    
    print("Extracting features...")
    features, labels = extract_features_from_files(df)
    
    if len(features) == 0:
        print("No features extracted. Please check file paths.")
        return
    
    # Normalize features
    scaler = StandardScaler()
    features = scaler.fit_transform(features)
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        features, labels, test_size=0.2, random_state=42
    )
    
    # Create datasets
    train_dataset = EventDataset(X_train, y_train)
    test_dataset = EventDataset(X_test, y_test)
    
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False)
    
    # Initialize model
    model = EventDetectorModel(input_dim=50, num_classes=5)
    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    # Training loop
    num_epochs = 50
    print(f"Training for {num_epochs} epochs...")
    
    for epoch in range(num_epochs):
        model.train()
        train_loss = 0.0
        
        for batch_features, batch_labels in train_loader:
            optimizer.zero_grad()
            outputs = model(batch_features)
            loss = criterion(outputs, batch_labels)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
        
        if (epoch + 1) % 10 == 0:
            print(f"Epoch [{epoch+1}/{num_epochs}], Loss: {train_loss/len(train_loader):.4f}")
    
    # Evaluate
    model.eval()
    test_loss = 0.0
    with torch.no_grad():
        for batch_features, batch_labels in test_loader:
            outputs = model(batch_features)
            loss = criterion(outputs, batch_labels)
            test_loss += loss.item()
    
    print(f"Test Loss: {test_loss/len(test_loader):.4f}")
    
    # Save model
    os.makedirs(os.path.dirname(model_save_path), exist_ok=True)
    torch.save({
        'model_state_dict': model.state_dict(),
        'scaler': scaler,
        'input_dim': 50,
        'num_classes': 5
    }, model_save_path)
    
    print(f"Model saved to {model_save_path}")

if __name__ == "__main__":
    import sys
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "labeled_data.csv"
    train_model(csv_path)

