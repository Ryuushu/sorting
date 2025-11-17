// ========== SOCKET.IO SETUP ==========
const socket = io();
let cameraOnline = false;
let controllerOnline = false;

// Track last frame time
let lastFrameTime = Date.now();

socket.on("connect", () => {
  console.log("✓ Connected to server");
  updateStatusIndicators();
});

socket.on("disconnect", () => {
  console.log("✗ Disconnected from server");
  updateStatusIndicators();
});

// Track frame updates
socket.on("frame_update", () => {
  cameraOnline = true;
  lastFrameTime = Date.now();
  updateStatusIndicators();
});

// Track detections
socket.on("new_detection", (data) => {
  console.log("New detection:", data);
  
  cameraOnline = true;
  updateStatusIndicators();

  document.getElementById("latestDetection").classList.remove("hidden");
  document.getElementById("detectedText").textContent = data.text;
  document.getElementById("activatedServo").textContent = `Servo ${data.servo}`;
  
  updateServoPosition(data.servo, 180);
  highlightServo(data.servo);
  addLogEntry(data);
});

// ========== CAMERA SELECTION UI ==========
async function loadCameras() {
  const devices = await navigator.mediaDevices.enumerateDevices();
  const videoDevices = devices.filter(d => d.kind === "videoinput");

  const webcamList = document.getElementById("webcamList");
  webcamList.innerHTML = "";

  videoDevices.forEach((cam, i) => {
    let opt = document.createElement("option");
    opt.value = cam.deviceId;
    opt.textContent = cam.label || `Camera ${i + 1}`;
    webcamList.appendChild(opt);
  });
}

document.getElementById("cameraSelect").addEventListener("change", e => {
  const webcamSelect = document.getElementById("webcamList");
  const ipForm = document.getElementById("ipCamForm");

  webcamSelect.classList.add("hidden");
  ipForm.classList.add("hidden");

  if (e.target.value === "webcam_list") {
    loadCameras();
    webcamSelect.classList.remove("hidden");
  } else if (e.target.value === "ipcam") {
    ipForm.classList.remove("hidden");
  }
});

async function startWebcam(deviceId = null) {
  let stream = await navigator.mediaDevices.getUserMedia({
    video: deviceId ? { deviceId } : true
  });
  
  setVideoStream(stream);
  localStorage.setItem("cameraMode", "webcam");
  if (deviceId) localStorage.setItem("webcamDevice", deviceId);
}

function applyIPCamera() {
  let url = document.getElementById("ipCamUrl").value;
  if (!url) return alert("Masukkan URL IP Camera!");

  stopVideoStream();
  setVideoSrc(url);

  localStorage.setItem("cameraMode", "ipcam");
  localStorage.setItem("ipcamUrl", url);
}

// ========== REPLACE VIDEO WITH <IMG> FOR MJPEG ==========
const videoContainer = document.getElementById("videoStream");

function setVideoStream(stream) {
  if (videoContainer.tagName !== "VIDEO") resetVideoTag();

  videoContainer.srcObject = stream;
  videoContainer.play();
}

function setVideoSrc(url) {
  if (videoContainer.tagName !== "VIDEO") resetVideoTag();

  videoContainer.srcObject = null;
  videoContainer.src = url;
  videoContainer.play();
}

function resetVideoTag() {
  const video = document.createElement("video");
  video.id = "videoStream";
  video.className = "w-full h-full object-contain";
  video.autoplay = true;
  videoContainer.replaceWith(video);
}

function stopVideoStream() {
  if (videoContainer.srcObject) {
    videoContainer.srcObject.getTracks().forEach(t => t.stop());
  }
}

// ========== STATUS HANDLER ==========
function updateStatusIndicators() {
  document.getElementById("cameraStatus").className =
    "status-indicator " + (cameraOnline ? "status-online pulse" : "status-offline");

  document.getElementById("controllerStatus").className =
    "status-indicator " + (controllerOnline ? "status-online pulse" : "status-offline");
}

// ========== SERVO UI ==========
function updateServoPosition(id, angle) {
  document.getElementById(`angle${id}`).textContent = `${angle}°`;

  const rotation = angle - 90;
  document.getElementById(`needle${id}`).style.transform =
    `translateX(-50%) rotate(${rotation}deg)`;

  const progress = (angle / 180) * 157;
  document.getElementById(`progress${id}`).style.strokeDashoffset = 157 - progress;
}

function highlightServo(id) {
  const servoCard = document.getElementById(`servo${id}`);
  servoCard.classList.add("ring-4", "ring-green-400");
  
  setTimeout(() => {
    servoCard.classList.remove("ring-4", "ring-green-400");
  }, 2000);
}

// ========== MANUAL SERVO FUNCTIONS ==========
async function manualControl(servoId) {
  const res = await fetch(`/api/manual_servo/${servoId}?angle=180`);
  const data = await res.json();

  if (data.status !== "ok") {
    alert("Failed: " + data.message);
    return;
  }

  updateServoPosition(servoId, 180);
  highlightServo(servoId);

  setTimeout(async () => {
    await fetch(`/api/manual_servo/${servoId}?angle=0`);
    updateServoPosition(servoId, 0);
  }, 500);
}

// ========== LOGGING ==========
function addLogEntry(data) {
  addLogEntryToDOM({
    timestamp: data.timestamp,
    text: data.text,
    servo: data.servo,
    confidence: data.confidence,
  }, true);
}

function addLogEntryToDOM(log, prepend = false) {
  const logContainer = document.getElementById("activityLog");
  const entry = document.createElement("div");

  entry.className =
    "log-entry bg-gray-700 rounded-lg p-4 mb-3 flex items-center justify-between";

  const conf = (log.confidence * 100).toFixed(1);
  const color = log.confidence > 0.8 ? "text-green-400" : "text-yellow-400";

  entry.innerHTML = `
    <div class="flex items-center space-x-4">
      <div class="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-500 rounded-lg flex items-center justify-center">
        <i class="fas fa-robot text-white text-xl"></i>
      </div>
      <div>
        <p class="font-semibold text-lg">
          Detected: <span class="text-blue-400">${log.text}</span>
        </p>
        <p class="text-sm text-gray-400">${log.timestamp}</p>
      </div>
    </div>
    <div class="text-right">
      <p class="text-2xl font-bold text-purple-400">Servo ${log.servo}</p>
      <p class="text-sm ${color}">Confidence: ${conf}%</p>
    </div>
  `;

  if (prepend) logContainer.prepend(entry);
  else logContainer.appendChild(entry);
}

// ========== INITIALIZATION ==========
document.addEventListener("DOMContentLoaded", () => {
  console.log("🚀 Dashboard initialized");

  // Load logs
  loadLogs();

  // Check servo every 5s
  checkControllerStatus();
  setInterval(checkControllerStatus, 5000);

  // Camera timeout check
  setInterval(() => {
    if (Date.now() - lastFrameTime > 5000) {
      cameraOnline = false;
      updateStatusIndicators();
    }
  }, 1000);

  // Init servo UI
  for (let i = 1; i <= 6; i++) updateServoPosition(i, 90);

  // Restore camera state
  const mode = localStorage.getItem("cameraMode");
  if (mode === "ipcam") {
    setVideoSrc(localStorage.getItem("ipcamUrl"));
  } else {
    startWebcam(localStorage.getItem("webcamDevice"));
  }
});
