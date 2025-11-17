import cv2
import matplotlib.pyplot as plt
import numpy as np
import ipywidgets as widgets
from IPython.display import display, clear_output
import os

# === GLOBAL VARIABEL ===
start_point = None      # bounding box (x1, y1)
end_point = None        # bounding box (x2, y2)
dragging = False        # sedang geser box atau tidak
offset = (0, 0)         # offset klik terhadap box
current_img = None
current_path = None
fig = None
ax = None

output_folder = "hasil_crop_realtime_colab"
os.makedirs(output_folder, exist_ok=True)


# === AUTO DETECT BOX ===
def auto_detect_box(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    _, thresh = cv2.threshold(
        blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )

    contours, _ = cv2.findContours(
        thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    boxes = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)

        if 300 < w < img.shape[1] and 40 < h < 300 and 150 < y < img.shape[0]//2:
            boxes.append((x, y, w, h))

    if len(boxes) == 0:
        return None

    boxes = sorted(boxes, key=lambda b: b[2] * b[3], reverse=True)
    x, y, w, h = boxes[0]

    x = max(0, x + 550)
    y = max(0, y + 0)
    w = min(img.shape[1] - x, w + 20)
    h = min(img.shape[0] - y, h + 25)

    return (x, y, x + w, y + h)


# === DRAW RECTANGLE ===
def draw_box():
    img_show = current_img.copy()

    if start_point and end_point:
        cv2.rectangle(img_show, start_point, end_point, (0, 255, 0), 3)

    ax.imshow(cv2.cvtColor(img_show, cv2.COLOR_BGR2RGB))
    fig.canvas.draw()


# === MOUSE EVENTS ===
def on_press(event):
    global dragging, offset

    if event.xdata is None or event.ydata is None:
        return

    x, y = int(event.xdata), int(event.ydata)
    x1, y1 = start_point
    x2, y2 = end_point

    # cek apakah klik berada dalam box
    if x1 <= x <= x2 and y1 <= y <= y2:
        dragging = True
        offset = (x - x1, y - y1)  # posisi klik relatif terhadap box


def on_move(event):
    global start_point, end_point

    if not dragging:
        return

    if event.xdata is None or event.ydata is None:
        return

    x, y = int(event.xdata), int(event.ydata)
    dx, dy = offset

    # Geser box tanpa mengubah ukuran
    w = end_point[0] - start_point[0]
    h = end_point[1] - start_point[1]

    new_x1 = x - dx
    new_y1 = y - dy
    new_x2 = new_x1 + w
    new_y2 = new_y1 + h

    # Batas agar tidak keluar gambar
    new_x1 = max(0, min(new_x1, current_img.shape[1] - w))
    new_y1 = max(0, min(new_y1, current_img.shape[0] - h))
    new_x2 = new_x1 + w
    new_y2 = new_y1 + h

    start_point = (new_x1, new_y1)
    end_point = (new_x2, new_y2)

    draw_box()


def on_release(event):
    global dragging
    dragging = False


# === SAVE ===
def save_crop(_):
    if start_point is None or end_point is None:
        print("❌ Kotak belum dipilih.")
        return

    x1, y1 = start_point
    x2, y2 = end_point

    crop = current_img[y1:y2, x1:x2]

    save_path = os.path.join(output_folder, os.path.basename(current_path))
    cv2.imwrite(save_path, crop)

    print(f"✅ Disimpan ke: {save_path}")
    next_image()    


# === RETRY ===
def retry(_):
    show_image(current_path)


# === SKIP ===
def skip(_):
    print("⏭️ Dilewati.")
    next_image()


# === BUTTONS ===
btn_save = widgets.Button(description="Save Crop", button_style='success')
btn_retry = widgets.Button(description="Retry", button_style='warning')
btn_skip = widgets.Button(description="Skip", button_style='danger')

btn_save.on_click(save_crop)
btn_retry.on_click(retry)
btn_skip.on_click(skip)


# === SHOW IMAGE ===
def show_image(path):
    global current_img, current_path, fig, ax
    global start_point, end_point

    current_img = cv2.imread(path)
    current_path = path

    clear_output(wait=True)
    display(widgets.HBox([btn_save, btn_retry, btn_skip]))

    auto_box = auto_detect_box(current_img)

    if auto_box:
        start_point = (auto_box[0], auto_box[1])
        end_point   = (auto_box[2], auto_box[3])
    else:
        start_point = None
        end_point = None

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.imshow(cv2.cvtColor(current_img, cv2.COLOR_BGR2RGB))
    ax.set_title("Klik & drag untuk menggeser bounding box")

    fig.canvas.mpl_connect("button_press_event", on_press)
    fig.canvas.mpl_connect("button_release_event", on_release)
    fig.canvas.mpl_connect("motion_notify_event", on_move)

    draw_box()

    plt.show()


# === LOAD IMAGE LIST ===
base_folder = r"C:\Users\Taufiqur Rahman\OneDrive\Documents\label_alamat_dataset\label_alamat_dataset\images"
image_list = []

for subset in ["train", "val"]:
    folder = os.path.join(base_folder, subset)
    print("Checking:", folder)

    for f in os.listdir(folder):
        if f.lower().endswith(('.jpg', '.png', '.jpeg')):
            image_list.append(os.path.join(folder, f))

index = 0


def next_image():
    global index
    if index >= len(image_list):
        print("✅ Semua gambar selesai.")
        return
    show_image(image_list[index])
    index += 1


# === START ===
next_image()
