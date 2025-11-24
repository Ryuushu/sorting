import cv2
import numpy as np

def crop_rotated(img, box):
    pts = np.float32(box)
    pts = pts[np.argsort(pts[:,1])]
    top = pts[:2]
    bottom = pts[2:]
    top = top[np.argsort(top[:,0])]
    bottom = bottom[np.argsort(bottom[:,0])]
    pts = np.float32([top[0], top[1], bottom[1], bottom[0]])

    w = int(np.linalg.norm(pts[0] - pts[1]))
    h = int(np.linalg.norm(pts[0] - pts[3]))
    dst = np.float32([[0,0],[w,0],[w,h],[0,h]])
    M  = cv2.getPerspectiveTransform(pts, dst)
    warped = cv2.warpPerspective(img, M, (w, h))
    return warped


def deteksi_roi(img):
    output = img.copy()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)

    # ---- Kontur kertas ----
    edges = cv2.Canny(blur, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        print("❌ Tidak ada kontur terdeteksi")
        return output, None, None

    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    paper_cnt = contours[0]
    rect = cv2.minAreaRect(paper_cnt)
    paper_box = cv2.boxPoints(rect).astype(np.int32)

    # ---- Crop kertas ----
    paper_crop = crop_rotated(gray, paper_box)
    _, text_bin = cv2.threshold(paper_crop, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours_text, _ = cv2.findContours(text_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    roi_box = paper_box.copy()  # default fallback

    kandidat = []
    for c in contours_text:
        r = cv2.minAreaRect(c)
        (cx, cy), (w, h), angle = r
        if 20 < w < paper_crop.shape[1] * 0.9 and 10 < h < paper_crop.shape[0] * 0.5:
            kandidat.append(r)

    if kandidat:
        kandidat = sorted(kandidat, key=lambda r: r[1][0]*r[1][1], reverse=True)
        (cx, cy), (w, h), angle = kandidat[0]
        text_box = cv2.boxPoints(kandidat[0]).astype(np.float32)

        # shrink supaya fokus tulisan
        shrink = 0.1
        center = np.array([cx, cy], dtype=np.float32)
        pts = text_box - center
        pts = pts * (1 - shrink)
        roi_box = (pts + center).astype(np.int32)

    # ---- Gambar kedua bounding box ----
    cv2.drawContours(output, [paper_box], -1, (255, 0, 0), 3)  # biru
    cv2.drawContours(output, [roi_box], -1, (0, 255, 255), 3)  # kuning

    return output, paper_box, roi_box

