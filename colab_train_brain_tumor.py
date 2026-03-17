# %% [markdown]
# # MediVision AI — Brain Tumor MRI Classification
# ## EfficientNetV2-S Fine-tuning on Kaggle Brain Tumor MRI Dataset
# **Classes:** glioma, meningioma, no_tumor, pituitary
# Run each cell in order. GPU runtime strongly recommended (Runtime → Change runtime type → T4 GPU).

# %% Install dependencies
# // turbo
import subprocess
subprocess.run(["pip", "install", "-q", "torch", "torchvision", "kaggle",
                "scikit-learn", "matplotlib", "seaborn", "tqdm"], check=True)

# %% [markdown]
# ## Step 1 — Set up Kaggle credentials
# Upload your `kaggle.json` from https://www.kaggle.com/account → API → Create Token

# %%
import os, shutil, json
from google.colab import files

print("Upload your kaggle.json ...")
uploaded = files.upload()

os.makedirs(os.path.expanduser("~/.kaggle"), exist_ok=True)
shutil.copy("kaggle.json", os.path.expanduser("~/.kaggle/kaggle.json"))
os.chmod(os.path.expanduser("~/.kaggle/kaggle.json"), 0o600)
print("kaggle.json installed.")

# %% [markdown]
# ## Step 2 — Download and extract dataset

# %%
import subprocess

# Dataset: sartajbhuvaji/brain-tumor-classification-mri
result = subprocess.run(
    ["kaggle", "datasets", "download", "-d", "sartajbhuvaji/brain-tumor-classification-mri",
     "--unzip", "-p", "/content/brain_tumor"],
    capture_output=True, text=True
)
print(result.stdout)
print(result.stderr)

# List structure
import os
for root, dirs, files_list in os.walk("/content/brain_tumor"):
    level = root.replace("/content/brain_tumor", "").count(os.sep)
    indent = " " * 2 * level
    print(f"{indent}{os.path.basename(root)}/")
    if level < 2:
        for f in files_list[:5]:
            print(f"{indent}  {f}")

# %% [markdown]
# ## Step 3 — Build Dataset & DataLoaders

# %%
import torch
import torchvision.transforms as T
from torchvision.datasets import ImageFolder
from torch.utils.data import DataLoader, random_split

DATA_DIR = "/content/brain_tumor/Training"   # adjust if extracted differently
IMG_SIZE = 224
BATCH_SIZE = 32
NUM_WORKERS = 2
SEED = 42

torch.manual_seed(SEED)

train_transforms = T.Compose([
    T.Resize((IMG_SIZE, IMG_SIZE)),
    T.RandomHorizontalFlip(),
    T.RandomRotation(15),
    T.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2),
    T.ToTensor(),
    T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

val_transforms = T.Compose([
    T.Resize((IMG_SIZE, IMG_SIZE)),
    T.ToTensor(),
    T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

# Load full dataset with train transforms first
full_dataset = ImageFolder(DATA_DIR, transform=train_transforms)
CLASS_NAMES = full_dataset.classes
NUM_CLASSES = len(CLASS_NAMES)
print(f"Classes ({NUM_CLASSES}): {CLASS_NAMES}")
print(f"Total samples: {len(full_dataset)}")

# Split 80/10/10
n_total = len(full_dataset)
n_val  = int(n_total * 0.10)
n_test = int(n_total * 0.10)
n_train = n_total - n_val - n_test

train_ds, val_ds, test_ds = random_split(
    full_dataset, [n_train, n_val, n_test],
    generator=torch.Generator().manual_seed(SEED)
)

# Override transforms for val/test subsets
val_ds.dataset.transform  = val_transforms
test_ds.dataset.transform = val_transforms

train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,  num_workers=NUM_WORKERS, pin_memory=True)
val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False, num_workers=NUM_WORKERS, pin_memory=True)
test_loader  = DataLoader(test_ds,  batch_size=BATCH_SIZE, shuffle=False, num_workers=NUM_WORKERS, pin_memory=True)

print(f"Train: {len(train_ds)} | Val: {len(val_ds)} | Test: {len(test_ds)}")

# %% [markdown]
# ## Step 4 — Build EfficientNetV2-S Model

# %%
import torchvision.models as models
import torch.nn as nn

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

model = models.efficientnet_v2_s(weights=models.EfficientNet_V2_S_Weights.IMAGENET1K_V1)

# Replace classifier head
in_features = model.classifier[1].in_features
model.classifier[1] = nn.Linear(in_features, NUM_CLASSES)
model = model.to(device)

print(f"Model: EfficientNetV2-S | Output classes: {NUM_CLASSES} | Classifier in_features: {in_features}")

# %% [markdown]
# ## Step 5 — Training Loop (30 epochs)

# %%
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR
from tqdm import tqdm
import copy

EPOCHS = 30
LR = 3e-4

criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=LR, weight_decay=1e-4)
scheduler = CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-6)

best_val_acc = 0.0
best_model_wts = copy.deepcopy(model.state_dict())
history = {"train_loss": [], "train_acc": [], "val_loss": [], "val_acc": []}


def run_epoch(model, loader, criterion, optimizer=None, device="cpu"):
    is_train = optimizer is not None
    model.train() if is_train else model.eval()
    total_loss, total_correct, total_samples = 0.0, 0, 0

    ctx = torch.enable_grad() if is_train else torch.no_grad()
    with ctx:
        for images, labels in tqdm(loader, leave=False):
            images, labels = images.to(device), labels.to(device)
            logits = model(images)
            loss = criterion(logits, labels)
            if is_train:
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
            total_loss    += loss.item() * images.size(0)
            total_correct += (logits.argmax(1) == labels).sum().item()
            total_samples += images.size(0)

    return total_loss / total_samples, total_correct / total_samples


for epoch in range(1, EPOCHS + 1):
    train_loss, train_acc = run_epoch(model, train_loader, criterion, optimizer, device)
    val_loss,   val_acc   = run_epoch(model, val_loader,   criterion, None,      device)
    scheduler.step()

    history["train_loss"].append(train_loss)
    history["train_acc"].append(train_acc)
    history["val_loss"].append(val_loss)
    history["val_acc"].append(val_acc)

    marker = " ← best" if val_acc > best_val_acc else ""
    print(f"Epoch {epoch:02d}/{EPOCHS} | "
          f"Train loss {train_loss:.4f} acc {train_acc:.4f} | "
          f"Val loss {val_loss:.4f} acc {val_acc:.4f}{marker}")

    if val_acc > best_val_acc:
        best_val_acc = val_acc
        best_model_wts = copy.deepcopy(model.state_dict())

print(f"\nBest Val Accuracy: {best_val_acc:.4f}")

# Save best checkpoint
torch.save(best_model_wts, "best_model.pt")
print("Saved best_model.pt")

# %% [markdown]
# ## Step 6 — Evaluation (Accuracy, AUC-ROC, Confusion Matrix)

# %%
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    accuracy_score, roc_auc_score, confusion_matrix, classification_report
)

# Reload best weights
model.load_state_dict(best_model_wts)
model.eval()

all_preds, all_probs, all_labels = [], [], []
with torch.no_grad():
    for images, labels in tqdm(test_loader):
        images = images.to(device)
        logits = model(images)
        probs  = torch.softmax(logits, dim=1).cpu().numpy()
        preds  = logits.argmax(1).cpu().numpy()
        all_probs.append(probs)
        all_preds.extend(preds)
        all_labels.extend(labels.numpy())

all_probs  = np.vstack(all_probs)
all_preds  = np.array(all_preds)
all_labels = np.array(all_labels)

# Accuracy
acc = accuracy_score(all_labels, all_preds)
print(f"Test Accuracy: {acc:.4f} ({acc*100:.2f}%)")

# AUC-ROC (One-vs-Rest)
auc = roc_auc_score(all_labels, all_probs, multi_class="ovr", average="macro")
print(f"Test AUC-ROC (macro OvR): {auc:.4f}")

# Classification report
print("\nClassification Report:")
print(classification_report(all_labels, all_preds, target_names=CLASS_NAMES))

# Confusion matrix
cm = confusion_matrix(all_labels, all_preds)
plt.figure(figsize=(7, 6))
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
            xticklabels=CLASS_NAMES, yticklabels=CLASS_NAMES)
plt.title("Confusion Matrix — Brain Tumor Classification")
plt.ylabel("True Label")
plt.xlabel("Predicted Label")
plt.tight_layout()
plt.savefig("confusion_matrix.png", dpi=150)
plt.show()

# Training curves
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
epochs_range = range(1, EPOCHS + 1)

axes[0].plot(epochs_range, history["train_loss"], label="Train")
axes[0].plot(epochs_range, history["val_loss"],   label="Val")
axes[0].set_title("Loss")
axes[0].set_xlabel("Epoch")
axes[0].legend()

axes[1].plot(epochs_range, history["train_acc"], label="Train")
axes[1].plot(epochs_range, history["val_acc"],   label="Val")
axes[1].set_title("Accuracy")
axes[1].set_xlabel("Epoch")
axes[1].legend()

plt.tight_layout()
plt.savefig("training_curves.png", dpi=150)
plt.show()

# %% [markdown]
# ## Step 7 — Download best_model.pt to your computer

# %%
from google.colab import files
files.download("best_model.pt")
print("Download started. Place best_model.pt in your MediVision backend/ folder.")
