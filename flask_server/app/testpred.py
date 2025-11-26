import cv2
import numpy as np
import tensorflow as tf
import os
from detection import deteksi_roi, segmentasi, crop_rotated, prediksi
import matplotlib.pyplot as plt

def test_ocr(image_path):
    print("\n[TEST] Memulai OCR pada:", image_path)

    img = cv2.imread(image_path)
    if img is None:
        print("❌ ERROR: Gambar tidak ditemukan.")
        return

    # --------------------------
    # 1. DETEKSI ROI
    # --------------------------
    det_img, paper_box, roi_box = deteksi_roi(img)

    if roi_box is None:
        print("❌ ROI tidak ditemukan.")
        return
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    roi_crop = crop_rotated(gray, roi_box)
    
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    enhanced = clahe.apply(roi_crop)

    lower = 0
    upper = 200
    thresh = cv2.inRange(enhanced, lower, upper)
    

    plt.figure(figsize=(12, 4))

    # 1️⃣ Gray
    plt.subplot(1, 3, 1)
    plt.imshow(gray, cmap='gray')
    plt.title("Gray")
    plt.axis("off")

    # 2️⃣ CLAHE
    plt.subplot(1, 3, 2)
    plt.imshow(enhanced, cmap='gray')
    plt.title("CLAHE")
    plt.axis("off")

    # 3️⃣ Threshold
    plt.subplot(1, 3, 3)
    plt.imshow(thresh, cmap='gray')
    plt.title("Adaptive Threshold")
    plt.axis("off")

    plt.tight_layout()
    plt.show()



    # --------------------------
    # 3. SEGMENTASI KARAKTER
    # --------------------------
    chars, boxes, msg = segmentasi(thresh)
    print("[INFO]", msg)
    if len(chars) > 0:
        plt.figure(figsize=(12, 3))

        for i, ch in enumerate(chars):
            plt.subplot(1, len(chars), i+1)
            plt.imshow(ch, cmap='gray')
            plt.title(f"Char {i+1}")
            plt.axis("off")

        plt.tight_layout()
        plt.show()

    if len(chars) == 0:
        print("❌ Tidak ada karakter ditemukan.")
        return

    # --------------------------
    # 4. PREDIKSI CNN
    # --------------------------
    hasil, conf = prediksi(chars)

    print("\n===========================")
    print("        HASIL OCR")
    print("===========================")
    print("Teks:", hasil)
    print("Confidence:", conf)
    print("===========================\n")

    return hasil, conf


# =====================================
#  MENJALANKAN TEST
# =====================================
if __name__ == "__main__":
    test_ocr("3.jpg")  # ganti sesuai file gambar kamu
