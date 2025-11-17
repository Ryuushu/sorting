// Initialize Socket.IO connection
const socket = io();

// Connection status indicators
let cameraOnline = false;
let controllerOnline = false;

// Connect to WebSocket
socket.on("connect", () => {
  console.log("✓ Connected to server");
  updateStatusIndicators();
});

socket.on("disconnect", () => {
  console.log("✗ Disconnected from server");
  updateStatusIndicators();
});

// Listen for new detections
socket.on("new_detection", (data) => {
  console.log("New detection:", data);

  // Update latest detection display
  document.getElementById("latestDetection").classList.remove("hidden");
  document.getElementById("detectedText").textContent = data.text;
  document.getElementById("activatedServo").textContent = `Servo ${data.servo}`;

  // Highlight servo that was activated
  highlightServo(data.servo);

  // Add to activity log
  addLogEntry(data);

  // Update camera status
  cameraOnline = true;
  updateStatusIndicators();
});

// Listen for frame updates
socket.on("frame_update", (data) => {
  // Frame is being received, camera is online
  cameraOnline = true;
  updateStatusIndicators();
});

// Update servo position visualization
function updateServoPosition(servoId, angle) {
  // Update angle display
  document.getElementById(`angle${servoId}`).textContent = `${angle}°`;

  // Update needle rotation (0° = -90deg, 180° = 90deg)
  const rotation = angle - 90;
  document.getElementById(
    `needle${servoId}`
  ).style.transform = `translateX(-50%) rotate(${rotation}deg)`;

  // Update progress arc
  const progress = (angle / 180) * 157;
  document.getElementById(`progress${servoId}`).style.strokeDashoffset =
    157 - progress;
}

// Highlight servo when activated
function highlightServo(servoId) {
  const servoCard = document.getElementById(`servo${servoId}`);
  servoCard.classList.add("ring-4", "ring-green-400");

  setTimeout(() => {
    servoCard.classList.remove("ring-4", "ring-green-400");
  }, 2000);
}

// Manual servo control
async function manualControl(servoId) {
  try {
    // 1️⃣ Kirim perintah servo ke 180°
    const response = await fetch(`/api/manual_servo/${servoId}?angle=180`);
    const data = await response.json();

    if (data.status === "ok") {
      console.log(`✓ Servo ${servoId} activated manually`);

      // Animasi posisi servo di UI (opsional)
      updateServoPosition(servoId, 180);
      highlightServo(servoId);

      // 2️⃣ Setelah 500 ms, kembalikan ke 0° lewat endpoint juga
      setTimeout(async () => {
        try {
          const resetResponse = await fetch(`/api/manual_servo/${servoId}?angle=0`);
          const resetData = await resetResponse.json();

          if (resetData.status === "ok") {
            console.log(`↩ Servo ${servoId} returned to 0°`);
            updateServoPosition(servoId, 0); // animasi di UI
          } else {
            console.warn(`⚠ Gagal reset servo ${servoId}:`, resetData.message);
          }
        } catch (resetError) {
          console.error("Error resetting servo:", resetError);
        }
      }, 500);

    } else {
      console.error("Failed to activate servo:", data.message);
      alert("Failed to activate servo: " + data.message);
    }

  } catch (error) {
    console.error("Error:", error);
    alert("Error communicating with servo controller");
  }
}


// Load activity logs
async function loadLogs() {
  try {
    const response = await fetch("/api/logs?limit=50");
    const logs = await response.json();

    const logContainer = document.getElementById("activityLog");

    if (logs.length === 0) {
      logContainer.innerHTML =
        '<p class="text-gray-400 text-center py-8">No activity yet</p>';
      return;
    }

    logContainer.innerHTML = "";

    logs.forEach((log) => {
      addLogEntryToDOM(log);
    });
  } catch (error) {
    console.error("Error loading logs:", error);
  }
}

// Add log entry from WebSocket
function addLogEntry(data) {
  const log = {
    timestamp: data.timestamp,
    text: data.text,
    servo: data.servo,
    confidence: data.confidence,
  };

  addLogEntryToDOM(log, true);
}

// Add log entry to DOM
function addLogEntryToDOM(log, prepend = false) {
  const logContainer = document.getElementById("activityLog");

  // Remove "no activity" message if present
  if (logContainer.querySelector("p")) {
    logContainer.innerHTML = "";
  }

  const entry = document.createElement("div");
  entry.className =
    "log-entry bg-gray-700 rounded-lg p-4 mb-3 flex items-center justify-between";

  const confidencePercent = (log.confidence * 100).toFixed(1);
  const confidenceColor =
    log.confidence > 0.8 ? "text-green-400" : "text-yellow-400";

  entry.innerHTML = `
        <div class="flex items-center space-x-4">
            <div class="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-500 rounded-lg flex items-center justify-center">
                <i class="fas fa-robot text-white text-xl"></i>
            </div>
            <div>
                <p class="font-semibold text-lg">Detected: <span class="text-blue-400">${log.text}</span></p>
                <p class="text-sm text-gray-400">${log.timestamp}</p>
            </div>
        </div>
        <div class="text-right">
            <p class="text-2xl font-bold text-purple-400">Servo ${log.servo}</p>
            <p class="text-sm ${confidenceColor}">Confidence: ${confidencePercent}%</p>
        </div>
    `;

  if (prepend) {
    logContainer.insertBefore(entry, logContainer.firstChild);
  } else {
    logContainer.appendChild(entry);
  }

  // Keep only last 50 entries
  const entries = logContainer.querySelectorAll(".log-entry");
  if (entries.length > 50) {
    entries[entries.length - 1].remove();
  }
}

// Update status indicators
function updateStatusIndicators() {
  const cameraStatus = document.getElementById("cameraStatus");
  const controllerStatus = document.getElementById("controllerStatus");

  cameraStatus.className =
    "status-indicator " +
    (cameraOnline ? "status-online pulse" : "status-offline");

  controllerStatus.className =
    "status-indicator " +
    (controllerOnline ? "status-online pulse" : "status-offline");
}

// Check servo controller status
async function checkControllerStatus() {
  try {
    const response = await fetch("/api/servo_status");
    const data = await response.json();
    if (response.status === 200) {
      controllerOnline = true;
      // Update servo positions
      data.servos.forEach((servo) => {
        updateServoPosition(servo.id, servo.position);
      });
    } else {
      controllerOnline = false;
    }
  } catch (error) {
    controllerOnline = false;
  }

  updateStatusIndicators();
}

// Initialize dashboard
document.addEventListener("DOMContentLoaded", () => {
  console.log("🚀 Dashboard initialized");

  // Load initial logs
  loadLogs();

  // Check controller status
  checkControllerStatus();

  // Set up periodic status checks
  setInterval(checkControllerStatus, 5000);

  // Set up periodic camera online check
  setInterval(() => {
    // If no frames received in last 5 seconds, mark as offline
    if (cameraOnline) {
      setTimeout(() => {
        cameraOnline = false;
        updateStatusIndicators();
      }, 5000);
    }
  }, 5000);

  // Initialize all servos to 90 degrees
  for (let i = 1; i <= 6; i++) {
    updateServoPosition(i, 90);
  }
});

// Handle video stream errors
document.getElementById("videoStream").addEventListener("error", () => {
  console.log("Video stream error");
  cameraOnline = false;
  updateStatusIndicators();
});

document.getElementById("videoStream").addEventListener("load", () => {
  console.log("Video stream loaded");
  cameraOnline = true;
  updateStatusIndicators();
});

// ====== SETUP STREAM VIDEO ======
document.addEventListener("DOMContentLoaded", () => {
  const video = document.getElementById("videoStream");

  // Ganti <video> jadi <img> karena /video_feed itu MJPEG, bukan media stream
  const img = document.createElement("img");
  img.src = "http://192.168.21.62:5000/video_feed";
  img.className = "w-full h-full object-contain";
  video.replaceWith(img);
  img.id = "videoStream";
});

// ====== CAPTURE & UPLOAD ======
document.getElementById("captureBtn").addEventListener("click", async () => {
  const videoElement = document.getElementById("videoStream");
  const canvas = document.createElement("canvas");
  canvas.width = videoElement.width || 640;
  canvas.height = videoElement.height || 480;

  const ctx = canvas.getContext("2d");
  ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);

  // Convert ke base64
  const imageBase64 = canvas.toDataURL("image/jpeg");

  // Tampilkan preview di dashboard
  document.getElementById("captureResult").classList.remove("hidden");
  document.getElementById("capturedImage").src = imageBase64;
  document.getElementById("captureTime").innerText =
    new Date().toLocaleString();

  try {
    const res = await fetch("/upload_web", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: imageBase64 }),
    });

    const data = await res.json();
    console.log("Upload response:", data);

    if (data.status === "ok") {
      // tampilkan hasil gambar yang sudah dideteksi
      if (data.detections_image) {
        document.getElementById("capturedImage").src =
          "data:image/jpeg;base64," + data.detections_image;
      }

      // tampilkan hasil deteksi text + servo
      if (data.detections && data.detections.length > 0) {
        const det = data.detections[0];
        document.getElementById("latestDetection").classList.remove("hidden");
        document.getElementById("detectedText").innerText = det.text;
        document.getElementById("activatedServo").innerText = det.servo;
      }
    } else {
      alert("Upload failed: " + data.message);
    }
  } catch (err) {
    console.error("Capture upload error:", err);
    alert("Error uploading image.");
  }
});
