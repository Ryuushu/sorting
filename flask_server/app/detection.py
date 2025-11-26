import cv2
import numpy as np
import tensorflow as tf
import os
import matplotlib.pyplot as plt
import io
import base64
import difflib

IMG_SIZE = 64                  
MODEL_PATH = r"F:\project kampus smt 5\sort\sorting\flask_server\app\char_model_resnet.h5"
DATASET_DIR = r"F:\project kampus smt 5\train_sorting\label_alamat_dataset\train_ocr"      

# Load model CNN
print("[INFO] Loading model:", MODEL_PATH)
model = tf.keras.models.load_model(MODEL_PATH)
labels = sorted([
    d for d in os.listdir(DATASET_DIR)
    if os.path.isdir(os.path.join(DATASET_DIR, d))
])
print("[INFO] Loaded Labels:", labels)

def crop_rotated(img, box):
    rect = cv2.minAreaRect(box)
    (cx, cy), (w, h), angle = rect
    M = cv2.getRotationMatrix2D((cx, cy), angle, 1.0)
    rotated = cv2.warpAffine(img, M, (img.shape[1], img.shape[0]))
    box_points = cv2.boxPoints(rect).astype(np.int32)
    x, y, w, h = cv2.boundingRect(box_points)
    return rotated[y:y+h, x:x+w]

def roi_inside_area(roi_box):
    return True
def deteksi_roi2(img):
    """
    Deteksi kotak terbesar di gambar.
    Return:
        box -> koordinat kotak (4x2)
        crop -> crop area sesuai box
    """
    if img is None or img.size == 0:
        return None, None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    edges = cv2.Canny(blur, 50, 150)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, None

    # Ambil kontur terbesar
    paper_cnt = max(contours, key=cv2.contourArea)

    # Rotated rectangle
    rect = cv2.minAreaRect(paper_cnt)
    box = cv2.boxPoints(rect)
    box = np.intp(box)

    # Bounding rectangle axis-aligned tanpa rotasi
    x, y, w, h = cv2.boundingRect(paper_cnt)
    margin = 5

# Crop dengan margin dikurangi, tetap aman dari out-of-bounds
    x1 = max(x + margin, 0)
    y1 = max(y + margin, 0)
    x2 = min(x + w - margin, img.shape[1])
    y2 = min(y + h - margin, img.shape[0])

    crop_auto = img[y1:y2, x1:x2]

    return box, crop_auto
def deteksi_roi(img):

    output = img.copy()
    h, w = img.shape[:2]

    # ROI kuning
    roi_box = np.array([
        [int(w/1.9), 200],
        [w-100, 200],
        [w-100, int(h/1.1)],
        [int(w/1.9), int(h/1.1)]
    ], dtype=np.int32)
    cv2.drawContours(output, [roi_box], -1, (0, 255, 255), 3)

    # Crop ROI
    x_min = np.min(roi_box[:,0])
    y_min = np.min(roi_box[:,1])
    x_max = np.max(roi_box[:,0])
    y_max = np.max(roi_box[:,1])
    roi_crop = img[y_min:y_max, x_min:x_max]

    gray = cv2.cvtColor(roi_crop, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    edges = cv2.Canny(blur, 50, 50)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    target_w = 460 - 366  # 94
    target_h = 272 - 259  # 13
    red_boxes_coords = []

    for c in contours:
        x, y, w_c, h_c = cv2.boundingRect(c)
        if abs(w_c - target_w) < 20 and abs(h_c - target_h) < 10:
            x_global = int(x + x_min)
            y_global = int(y + y_min)
            red_boxes_coords.append((x_global, y_global, x_global + w_c, y_global + h_c))
            cv2.rectangle(output, (x_global, y_global), (x_global + w_c, y_global + h_c), (0,0,255), 2)
            cv2.putText(output, f"{x_global},{y_global}", (x_global, y_global-5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0,0,255), 1)

    # Pilih kotak terpilih
    kotak_terpilih = pilih_kotak(red_boxes_coords)
    roi_selected = None
    if kotak_terpilih:
        x1, y1, x2, y2 = kotak_terpilih
        cv2.rectangle(output, (x1,y1), (x2,y2), (255,0,0), 3)
        cv2.putText(output, f"Terpilih: ({x1},{y1},{x2},{y2})", (x1, y1-15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,0,0), 1)
        # Ambil crop dari kotak terpilih
        roi_selected = img[y1:y2, x1:x2]

    return output, roi_box, red_boxes_coords, kotak_terpilih, roi_selected
def segmentasi(thresh_img, target_size=(80,120)):

    save_dir = "hasil_crop_realtime_colab"
    os.makedirs(save_dir, exist_ok=True)

    # --- 0. Invert jika background putih ---
    if np.mean(thresh_img) > 127:
        thresh_img = cv2.bitwise_not(thresh_img)

    # --- 1. Bersihkan noise kecil (lebih lembut) ---
    kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (2,2))
    clean = cv2.morphologyEx(thresh_img, cv2.MORPH_OPEN, kernel_open, iterations=1)

    # --- 2. Tebalkan HURUF sedikit saja (tidak merusak) ---
    kernel_dil = cv2.getStructuringElement(cv2.MORPH_RECT, (2,2))
    thick = cv2.dilate(clean, kernel_dil, iterations=1)

    # --- 3. Closing untuk nutup celah huruf tipis ---
    kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
    thick = cv2.morphologyEx(thick, cv2.MORPH_CLOSE, kernel_close, iterations=1)

    cv2.imwrite(os.path.join(save_dir, "02_thick.png"), thick)

    # --- 4. Cari kontur ---
    contours, _ = cv2.findContours(thick, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h_img, w_img = thresh_img.shape

    char_boxes = []
    for cnt in contours:
        x,y,w,h = cv2.boundingRect(cnt)

        # Filter lebih aman supaya huruf tidak hilang
        if h < 10 or w < 5:
            continue
        if h > h_img * 0.95:
            continue

        char_boxes.append((x,y,w,h))

    if not char_boxes:
        return [], [], "Tidak ada karakter terdeteksi."

    # Urut kiri → kanan
    char_boxes = sorted(char_boxes, key=lambda b: b[0])

    # --- 5. Crop dan padding ---
    chars = []
    for i,(x,y,w,h) in enumerate(char_boxes):

        char_crop = thick[y:y+h, x:x+w]

        # Padding lebih lembut
        pad = int(max(w, h) * 0.20)
        char_pad = cv2.copyMakeBorder(
            char_crop, pad, pad, pad, pad,
            cv2.BORDER_CONSTANT, value=0
        )

        # Resize halus → tidak pecah
        resized = cv2.resize(char_pad, target_size, interpolation=cv2.INTER_AREA)

        chars.append(resized)
        cv2.imwrite(os.path.join(save_dir, f"char_{i+1}.png"), resized)

    return chars, char_boxes, f"{len(chars)} karakter tersegmentasi"


# Konfigurasi
IMG_SIZE = 64  # ukuran input model
# model dan labels sudah harus di-load sebelumnya:
# model = tf.keras.models.load_model(MODEL_PATH)
# labels = [...]  # list label karakter sesuai model

def preprocess_image(img):
    """
    Preprocess gambar karakter sebelum masuk model CNN ResNet.
    Input  : img (numpy array 2D grayscale atau 3D BGR)
    Output : img siap prediksi (shape: 1, IMG_SIZE, IMG_SIZE, 3)
    """

    # Pastikan grayscale
    if len(img.shape) == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Resize ke input model
    img = cv2.resize(img, (IMG_SIZE, IMG_SIZE))

    # Threshold invers sederhana (foreground putih, background hitam)
    img = cv2.inRange(img, 0, 170)

    # Normalisasi ke 0-1
    img = img.astype("float32") / 255.0

    # Ubah grayscale 1 channel menjadi 3 channel
    img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)

    # Tambahkan batch dimension
    img = np.expand_dims(img, axis=0)  # shape -> (1, IMG_SIZE, IMG_SIZE, 3)

    return img


def preprocess_image(img):
    """
    Preprocess gambar karakter sebelum masuk model CNN ResNet.
    Input  : img (numpy array 2D grayscale atau 3D BGR)
    Output : img siap prediksi (shape: 1, IMG_SIZE, IMG_SIZE, 3)
    """

    # Pastikan grayscale
    if len(img.shape) == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Resize ke input model
    img = cv2.resize(img, (IMG_SIZE, IMG_SIZE))

    # Threshold invers sederhana (foreground putih, background hitam)
    img = cv2.inRange(img, 0, 170)

    # Normalisasi ke 0-1
    img = img.astype("float32") / 255.0

    # Ubah grayscale 1 channel menjadi 3 channel
    img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)

    # Tambahkan batch dimension
    img = np.expand_dims(img, axis=0)  # shape -> (1, IMG_SIZE, IMG_SIZE, 3)

    return img


def prediksi(chars):
    """
    Menerima list array karakter hasil segmentasi.
    Mengembalikan string hasil OCR lengkap dan confidence tiap karakter.
    """
    hasil = ""
    confidences = []

    for ch in chars:
        # Preprocess setiap karakter
        processed = preprocess_image(ch)

        # Prediksi model
        pred = model.predict(processed, verbose=0)[0]
        idx = np.argmax(pred)
        confidence = float(pred[idx])
        char = labels[idx]

        hasil += char
        confidences.append(confidence)

    return hasil, confidences

def matching(input):
    kecamatan_list = [
            "Binakal", "Bondowoso", "Botolinggo", "Cermee", "Curahdami",
            "Grujugan", "Jambesari Darus Sholah", "Klabang", "Maesan",
            "Pakem", "Prajekan", "Pujer", "Sempol", "Sukosari",
            "Sumber Wringin", "Taman Krocok", "Tamanan", "Tapen",
            "Tegalampel", "Tenggarang", "Tlogosari", "Wonosari", "Wringin"
        ]
    hasil = difflib.get_close_matches(input, kecamatan_list, n=3, cutoff=0.5)

    return hasil 

def rule_grub(input_text):
    data = {
        "Utara": ["Tegal Ampel", "Wringin", "Taman Krocok"],
        "Selatan": ["Tenggarang", "Jambesari", "Pujer", "Tlogosari", "Sukosari", "SumberWringin", "Sempol"],
        "Timur": ["Wonosari", "Tapen", "Botolinggo", "Klabang", "Prajekan", "cerme"],
        "Barat": ["bondowoso", "curahdami", "grujugan", "maesan", "tamanan", "binakal", "pakem"]
    }

    # Normalize input supaya lebih fleksibel
    input_norm = input_text.strip().lower().replace(" ", "")
    
    for arah, kec_list in data.items():
        # normalisasi daftar kecamatan
        kec_norm = [k.lower().replace(" ", "") for k in kec_list]
        # gunakan difflib untuk kecocokan mirip
        hasil = difflib.get_close_matches(input_norm, kec_norm, n=1, cutoff=0.6)
        if hasil:
            return arah  # jika ketemu, kembalikan arah

    return None 
