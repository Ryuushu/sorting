import cv2
import numpy as np

def crop_rotated(img, box):
    """Crop area sesuai box miring (rotated rectangle)."""
    rect = cv2.minAreaRect(box)
    (cx, cy), (w, h), angle = rect

    M = cv2.getRotationMatrix2D((cx, cy), angle, 1.0)
    rotated = cv2.warpAffine(img, M, img.shape[1::-1])

    w, h = int(w), int(h)
    x, y = int(cx - w/2), int(cy - h/2)
    # pastikan crop masih valid
    y1, y2 = max(0, y), min(rotated.shape[0], y+h)
    x1, x2 = max(0, x), min(rotated.shape[1], x+w)
    return rotated[y1:y2, x1:x2]

def auto_detect_box(img):
    """Deteksi kotak terbesar di gambar."""
    if img is None or img.size == 0:
        return None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    edges = cv2.Canny(blur, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None

    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    paper_cnt = contours[0]
    rect = cv2.minAreaRect(paper_cnt)
    paper_box = cv2.boxPoints(rect)
    paper_box = np.intp(paper_box)
    return paper_box

# ========================== MAIN ==========================
ipcam_url = "http://192.168.100.44:4747/video"
cap = cv2.VideoCapture(ipcam_url)

while True:
    ret, frame = cap.read()
    if not ret:
        print("Gagal ambil frame...")
        break

    # --- ROI kanan optional (bisa dihapus kalau mau deteksi full frame) ---
    h, w = frame.shape[:2]
    x1, y1 = int(w * 0.56), 300
    x2, y2 = w - 210, h
    roi = frame[y1:y2, x1:x2]

    # Deteksi kotak otomatis di ROI
    box = auto_detect_box(roi)

    if box is not None:
        # Mapping koordinat ke frame asli
        box[:,0] += x1
        box[:,1] += y1

        # Gambar bounding box di frame
        cv2.drawContours(frame, [box], -1, (0,255,0), 2)

        # --- Auto crop sesuai box ---
        crop_auto = crop_rotated(frame, box)
        if crop_auto is not None and crop_auto.size > 0:
            cv2.imshow("Auto Crop", crop_auto)

    # Gambar ROI biru
    roi_box = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]])
    cv2.polylines(frame, [roi_box], True, (255,0,0), 2)

    cv2.imshow("IPCam Auto Detect Box", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
