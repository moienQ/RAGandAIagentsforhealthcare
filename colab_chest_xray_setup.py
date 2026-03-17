# %% [markdown]
# # MediVision AI — NIH ChestX-ray14 Data Pipeline
# ## Google Colab Setup Notebook
# Sets up the full training environment for chest X-ray classification.
# Downloads the first 5000 images from NIH ChestX-ray14, creates DataLoaders
# with train/val/test splits, applies augmentations, and displays sample batches.
# Run each cell in order. GPU runtime recommended.

# %% Install dependencies
import subprocess
deps = [
    "torch", "torchvision", "pydicom", "albumentations",
    "scikit-learn", "matplotlib", "kaggle", "opencv-python-headless", "tqdm"
]
subprocess.run(["pip", "install", "-q"] + deps, check=True)
print("All dependencies installed.")

# %% [markdown]
# ## Step 1 — Kaggle Authentication

# %%
import os, shutil
from google.colab import files

print("Upload your kaggle.json from https://www.kaggle.com/account")
uploaded = files.upload()
os.makedirs(os.path.expanduser("~/.kaggle"), exist_ok=True)
shutil.copy("kaggle.json", os.path.expanduser("~/.kaggle/kaggle.json"))
os.chmod(os.path.expanduser("~/.kaggle/kaggle.json"), 0o600)
print("Kaggle credentials configured.")

# %% [markdown]
# ## Step 2 — Download NIH ChestX-ray14 (first 5000 images)
# We download the full metadata CSV and the image archives, then take the first 5000.

# %%
import subprocess, zipfile, glob

# Download metadata and image batch 1 (~5000 images in images_001.zip)
print("Downloading metadata CSV...")
subprocess.run([
    "kaggle", "datasets", "download",
    "-d", "nih-chest-xrays/data",
    "--file", "Data_Entry_2017.csv",
    "-p", "/content/chest_xray_data"
], check=True)

print("Downloading image batch 001 (~5000 images, ~1.2 GB) ...")
subprocess.run([
    "kaggle", "datasets", "download",
    "-d", "nih-chest-xrays/data",
    "--file", "images_001.zip",
    "-p", "/content/chest_xray_data"
], check=True)

# Extract
zip_path = "/content/chest_xray_data/images_001.zip"
if os.path.exists(zip_path):
    print("Extracting images ...")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall("/content/chest_xray_data/images")
    print("Extraction complete.")

# Verify
img_files = sorted(glob.glob("/content/chest_xray_data/images/**/*.png", recursive=True))
print(f"Found {len(img_files)} images.")

# %% [markdown]
# ## Step 3 — Parse Metadata & Build Label Map

# %%
import pandas as pd
import numpy as np

meta_path = "/content/chest_xray_data/Data_Entry_2017.csv"
df = pd.read_csv(meta_path)
print(f"Metadata rows: {len(df)}")
print(df.head(3))

# Keep only images we actually downloaded
available_names = {os.path.basename(p) for p in img_files}
df = df[df["Image Index"].isin(available_names)].reset_index(drop=True)
print(f"Matched metadata rows: {len(df)}")

# Simplify: multi-label → pick first condition (or "No Finding")
df["primary_label"] = df["Finding Labels"].apply(lambda x: x.split("|")[0])
label_counts = df["primary_label"].value_counts()
print("\nTop 10 conditions:")
print(label_counts.head(10))

# Take only top-N classes for manageable classification
TOP_N = 8
top_labels = label_counts.head(TOP_N).index.tolist()
df = df[df["primary_label"].isin(top_labels)].reset_index(drop=True)
CLASS_NAMES = sorted(df["primary_label"].unique().tolist())
NUM_CLASSES = len(CLASS_NAMES)
label_to_idx = {c: i for i, c in enumerate(CLASS_NAMES)}
print(f"\nUsing {NUM_CLASSES} classes: {CLASS_NAMES}")
print(f"Dataset size after filtering: {len(df)}")

# Map image name → full path
name_to_path = {os.path.basename(p): p for p in img_files}
df["filepath"] = df["Image Index"].map(name_to_path)
df = df.dropna(subset=["filepath"]).reset_index(drop=True)
print(f"Final usable rows: {len(df)}")

# %% [markdown]
# ## Step 4 — Train/Val/Test Split (70/15/15)

# %%
from sklearn.model_selection import train_test_split

# First split: 70 train, 30 temp
train_df, temp_df = train_test_split(df, test_size=0.30, random_state=42,
                                      stratify=df["primary_label"])
# Second split: 15 val, 15 test from temp
val_df, test_df  = train_test_split(temp_df, test_size=0.50, random_state=42,
                                    stratify=temp_df["primary_label"])

train_df = train_df.reset_index(drop=True)
val_df   = val_df.reset_index(drop=True)
test_df  = test_df.reset_index(drop=True)

print(f"Train: {len(train_df)} | Val: {len(val_df)} | Test: {len(test_df)}")

# %% [markdown]
# ## Step 5 — Dataset Class with Albumentations Augmentation

# %%
import cv2
import torch
import albumentations as A
from albumentations.pytorch import ToTensorV2
from torch.utils.data import Dataset, DataLoader
from PIL import Image

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD  = (0.229, 0.224, 0.225)
IMG_SIZE = 224

train_aug = A.Compose([
    A.Resize(IMG_SIZE, IMG_SIZE),
    A.HorizontalFlip(p=0.5),
    A.Rotate(limit=10, p=0.5),
    A.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.1, hue=0.05, p=0.5),
    A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ToTensorV2(),
])

val_aug = A.Compose([
    A.Resize(IMG_SIZE, IMG_SIZE),
    A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ToTensorV2(),
])


class ChestXrayDataset(Dataset):
    def __init__(self, df, label_to_idx, transform=None):
        self.df = df
        self.label_to_idx = label_to_idx
        self.transform = transform

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        image = cv2.imread(row["filepath"])
        if image is None:
            # Fallback for unreadable images
            image = np.zeros((IMG_SIZE, IMG_SIZE, 3), dtype=np.uint8)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        label = self.label_to_idx[row["primary_label"]]

        if self.transform:
            image = self.transform(image=image)["image"]

        return image, label


BATCH_SIZE = 32
WIN = 2  # num_workers for Colab

train_ds = ChestXrayDataset(train_df, label_to_idx, transform=train_aug)
val_ds   = ChestXrayDataset(val_df,   label_to_idx, transform=val_aug)
test_ds  = ChestXrayDataset(test_df,  label_to_idx, transform=val_aug)

train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,  num_workers=WIN, pin_memory=True)
val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False, num_workers=WIN, pin_memory=True)
test_loader  = DataLoader(test_ds,  batch_size=BATCH_SIZE, shuffle=False, num_workers=WIN, pin_memory=True)

print(f"DataLoaders ready. Batches — Train: {len(train_loader)} | Val: {len(val_loader)} | Test: {len(test_loader)}")

# %% [markdown]
# ## Step 6 — Visualise Sample Grid

# %%
import matplotlib.pyplot as plt

INVMEAN = torch.tensor(IMAGENET_MEAN).view(3, 1, 1)
INVSTD  = torch.tensor(IMAGENET_STD).view(3, 1, 1)

def denormalize(tensor):
    """Undo ImageNet normalization for display."""
    return (tensor * INVSTD + INVMEAN).clamp(0, 1)

images, labels = next(iter(train_loader))
n_show = min(16, len(images))

fig, axes = plt.subplots(4, 4, figsize=(12, 12))
for i, ax in enumerate(axes.flatten()):
    if i >= n_show:
        ax.axis("off")
        continue
    img = denormalize(images[i]).permute(1, 2, 0).numpy()
    ax.imshow(img)
    ax.set_title(CLASS_NAMES[labels[i].item()], fontsize=9)
    ax.axis("off")

plt.suptitle("Sample Training Batch — NIH ChestX-ray14 (augmented)", fontsize=13, y=1.01)
plt.tight_layout()
plt.savefig("sample_batch.png", dpi=120, bbox_inches="tight")
plt.show()
print("Sample grid saved as sample_batch.png. Pipeline is working correctly!")

# %% [markdown]
# ## Step 7 — Label Distribution Check

# %%
fig, axes = plt.subplots(1, 3, figsize=(16, 5))
for ax, (split_df, title) in zip(axes, [
    (train_df, "Train"), (val_df, "Val"), (test_df, "Test")
]):
    split_df["primary_label"].value_counts().plot(kind="bar", ax=ax, color="steelblue")
    ax.set_title(f"{title} Split ({len(split_df)} samples)")
    ax.set_xlabel("Condition")
    ax.set_ylabel("Count")
    ax.tick_params(axis="x", rotation=35)

plt.tight_layout()
plt.savefig("label_distribution.png", dpi=120)
plt.show()
print("Label distribution verified. Ready for model training!")

# %% [markdown]
# ## Next Step
# Use the `train_loader`, `val_loader`, and `test_loader` defined above
# with an EfficientNetV2 or DenseNet model to train your chest pathology classifier.
# See `colab_train_brain_tumor.py` for the full training loop template.
