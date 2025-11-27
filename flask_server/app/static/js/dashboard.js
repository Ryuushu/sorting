const socket = io("http://localhost:5000");
socket.on("connect", () => console.log("Socket connected!"));
socket.on("disconnect", () => console.log("Socket disconnected!"));
socket.on("trigger_ultrasonic", (data) => {
    // data: { sensor_id: "sensor1", distance: 23.5, timestamp: "..." }
    console.log("📏 Triggered from backend:", data);
const distance = data.distance ?? 0;

  // update label
  const label = document.getElementById("ultrasonicDistance");
  label.textContent = `${distance} cm`;

  // update progress bar
  const progress = document.getElementById("ultrasonicProgress");
  progress.style.width = `${Math.min(distance, 100)}%`;

  // optional: ubah warna progress berdasarkan jarak
  if (distance < 10) {
    progress.className = "bg-red-500 h-4 rounded-full";
  } else if (distance < 30) {
    progress.className = "bg-yellow-400 h-4 rounded-full";
  } else {
    progress.className = "bg-purple-400 h-4 rounded-full";
  }
});
socket.on("trigger_capture", () => {
  console.log("📸 AUTO CAPTURE triggered from backend!");

  const element = document.getElementById("videoStream");
  if (element.tagName === "IMG") captureIPCam(element);
  else captureWebcam(element);
});

/* ===========================
   CAMERA HANDLING
=========================== */
const video = document.getElementById("videoStream");
const cameraSelect = document.getElementById("cameraSelect");
const webcamList = document.getElementById("webcamList");
const ipCamForm = document.getElementById("ipCamForm");
const ipCamUrl = document.getElementById("ipCamUrl");

let currentStream = null;

/* ========== Show Options ========== */
cameraSelect.addEventListener("change", async () => {
  const mode = cameraSelect.value;

  if (mode === "webcam_default") {
    webcamList.classList.add("hidden");
    ipCamForm.classList.add("hidden");
    startDefaultWebcam();
  } else if (mode === "webcam_list") {
    ipCamForm.classList.add("hidden");
    webcamList.classList.remove("hidden");
    await loadWebcamList();
  } else if (mode === "ipcam") {
    webcamList.classList.add("hidden");
    ipCamForm.classList.remove("hidden");
    stopStream();
    video.srcObject = null;
    video.src = "";
  }
});

/* ========== Default Webcam ========== */
async function startDefaultWebcam() {
  stopStream();

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    video.srcObject = stream;
    currentStream = stream;
  } catch (err) {
    alert("Tidak bisa membuka webcam");
  }
}

/* ========== List Available Webcam ========== */
async function loadWebcamList() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
    alert("Browser tidak mendukung webcam atau halaman tidak pakai HTTPS!");
    return;
  }

  const devices = await navigator.mediaDevices.enumerateDevices();
  const cameras = devices.filter((d) => d.kind === "videoinput");

  webcamList.innerHTML = "";
  cameras.forEach((cam, i) => {
    const opt = document.createElement("option");
    opt.value = cam.deviceId;
    opt.textContent = cam.label || `Webcam ${i + 1}`;
    webcamList.appendChild(opt);
  });

  startSelectedWebcam();
}

webcamList.addEventListener("change", startSelectedWebcam);

async function startSelectedWebcam() {
  stopStream();
  const id = webcamList.value;

  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { deviceId: id },
    });
    video.srcObject = stream;
    currentStream = stream;
  } catch (err) {
    alert("Gagal membuka webcam tersebut.");
  }
}

/* ========== IP Camera (RTSP/HTTP MJPEG) ========== */
function applyIPCamera() {
  let url = ipCamUrl.value.trim();
  if (!url) return;

  stopStream();

  const old = document.getElementById("videoStream");

  const img = document.createElement("img");
  img.id = "videoStream";
  img.src = `/proxy_ipcam?url=${encodeURIComponent(url)}`;
  img.className = "w-full h-full object-contain";

  old.replaceWith(img);
}

/* ========== Stop Stream ========== */
function stopStream() {
  if (currentStream) {
    currentStream.getTracks().forEach((track) => track.stop());
    currentStream = null;
  }
}

/* ===========================
   CAPTURE & UPLOAD TO BACKEND
=========================== */
const captureBtn = document.getElementById("captureBtn");
const capturedImage = document.getElementById("capturedImage");
const captureResult = document.getElementById("captureResult");
const captureTime = document.getElementById("captureTime");
const detectedText = document.getElementById("detectedText");
const activatedServo = document.getElementById("activatedServo");
const captureCanvas = document.getElementById("captureCanvas");
// const ctx = captureCanvas.getContext("2d");

captureBtn.addEventListener("click", () => {
  const element = document.getElementById("videoStream");

  if (element.tagName === "IMG") {
    captureIPCam(element);
  } else {
    captureWebcam(element);
  }
});

function captureWebcam(video) {
  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;

  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0);

  const dataURL = canvas.toDataURL("image/jpeg");
  processCapturedImage(dataURL);
}

function captureIPCam(img) {
  const canvas = document.createElement("canvas");
  canvas.width = img.naturalWidth;
  canvas.height = img.naturalHeight;

  const ctx = canvas.getContext("2d");
  ctx.drawImage(img, 0, 0);

  const dataURL = canvas.toDataURL("image/jpeg");
  processCapturedImage(dataURL);
}

function processCapturedImage(dataURL) {
  capturedImage.src = dataURL;
  captureResult.classList.remove("hidden");
  captureTime.textContent = new Date().toLocaleTimeString();

  uploadFrame(dataURL); // kirim ke backend
}
/* Upload to backend */
async function uploadFrame(base64data) {
  try {
    const res = await fetch("/upload_web", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: base64data }),
    });

    const data = await res.json();
    if (data.status !== "ok") return;

    // Update hasil captured frame
    updateCapturedFrame(data.final_vis, data.paper_box, data.roi_box);
    detectedText.textContent = data.hasil || "-";
    activatedServo.textContent = data.servo || "-";

    document.getElementById("latestDetection").classList.remove("hidden");

    // updateServoUI(data.servo, data.angle ?? 90);
  } catch (err) {
    console.log("Upload error:", err);
  }
}

/* ===========================
   SERVO UI UPDATE
=========================== */
function updateServoUI(id, angle) {
  if (!id || id < 1 || id > 6) return;

  document.getElementById(`angle${id}`).textContent = angle + "°";

  const needle = document.getElementById(`needle${id}`);
  const deg = ((angle - 0) / 180) * 180 - 90;
  needle.style.transform = `translateX(-50%) rotate(${deg}deg)`;

  const progress = document.getElementById(`progress${id}`);
  const dash = 157 - (157 * angle) / 180;
  progress.style.strokeDashoffset = dash;
}

/* ===========================
   MANUAL SERVO CONTROL
=========================== */
function manualControl(id) {
  fetch(`/api/manual_servo/${id}`);
}

/* ===========================
   ACTIVITY LOG
=========================== */
async function loadLogs() {
  const res = await fetch("/api/logs");
  const logs = await res.json();

  const logDiv = document.getElementById("activityLog");
  logDiv.innerHTML = "";
  const table = document.createElement("table");
  table.className = "min-w-full text-left text-gray-300";

  // Header tabel
  const thead = document.createElement("thead");
  thead.innerHTML = `
        <tr class="bg-gray-700 border-b border-gray-600">
            <th class="px-4 py-2">Timestamp</th>
            <th class="px-4 py-2">Detected Text</th>
            <th class="px-4 py-2">Servo ID</th>
            <th class="px-4 py-2">Image</th>
        </tr>
    `;
  table.appendChild(thead);

  // Body tabel
  const tbody = document.createElement("tbody");
  logs.forEach((log) => {
    const tr = document.createElement("tr");
    tr.className = "border-b border-gray-600";

    tr.innerHTML = `
            <td class="px-4 py-2">${log.timestamp}</td>
            <td class="px-4 py-2">${log.detected_text}</td>
            <td class="px-4 py-2">${log.servo_id}</td>
            <td class="px-4 py-2">
            ${
              log.img
                ? `<img src="${log.img.replace(
                    /\\/g,
                    "/"
                  )}" class="w-20 h-20 object-cover rounded" />`
                : "-"
            }
        </td>
        `;
    tbody.appendChild(tr);
  });

  table.appendChild(tbody);
  logDiv.appendChild(table);
}

function updateCapturedFrame(base64Image, paperBox, roiBox) {
  capturedImage.src = "data:image/jpeg;base64," + base64Image;

  capturedImage.onload = () => {
    // Sesuaikan canvas dengan ukuran image
    captureCanvas.width = capturedImage.width;
    captureCanvas.height = capturedImage.height;

    // Clear canvas sebelum menggambar ulang
    // ctx.clearRect(0, 0, captureCanvas.width, captureCanvas.height);

    // // Gambar bounding box
    // drawBox(ctx, paperBox, "blue");   // bounding box kertas
    // drawBox(ctx, roiBox, "yellow");   // bounding box tulisan
  };

  // Tampilkan waktu capture
  const now = new Date();
  captureTime.textContent = now.toLocaleTimeString();

  // Tampilkan div captureResult
  captureResult.classList.remove("hidden");
}
function drawBox(ctx, box, color, width = 3) {
  if (!box) return;
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.beginPath();
  ctx.moveTo(box[0][0], box[0][1]);
  ctx.lineTo(box[1][0], box[1][1]);
  ctx.lineTo(box[2][0], box[2][1]);
  ctx.lineTo(box[3][0], box[3][1]);
  ctx.closePath();
  ctx.stroke();
}
let capturedFlag = false;

function checkDistanceAndCapture() {
  if (
    latestDistance !== null &&
    latestDistance <= DISTANCE_THRESHOLD &&
    !capturedFlag
  ) {
    const element = document.getElementById("videoStream");

    if (element.tagName === "IMG") captureIPCam(element);
    else captureWebcam(element);

    capturedFlag = true; // mencegah capture terus-menerus
  } else if (latestDistance > DISTANCE_THRESHOLD) {
    capturedFlag = false; // reset flag saat jarak aman
  }
}
loadLogs();
