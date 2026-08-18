import React, { useState, useRef, useEffect } from 'react';
import { Camera, Upload, X, RefreshCw, CheckCircle2, AlertCircle } from 'lucide-react';

export default function CameraOrUploadInput({
  onFileSelected,
  previewUrl = null,
  currentPreview = null,
  label = "Upload or Snap Produce Photo",
  accept = "image/*",
  id = "camera-or-upload-input",
  disabled = false
}) {
  const [showCameraModal, setShowCameraModal] = useState(false);
  const [stream, setStream] = useState(null);
  const [facingMode, setFacingMode] = useState('environment'); // 'user' or 'environment'
  const [cameraError, setCameraError] = useState(null);
  const [capturedPreview, setCapturedPreview] = useState(null);
  
  const videoRef = useRef(null);
  const fileInputRef = useRef(null);
  const directCameraInputRef = useRef(null);

  // Stop camera stream when modal closes
  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      setStream(null);
    }
  };

  const startCamera = async (mode = facingMode) => {
    stopCamera();
    setCameraError(null);

    if (!navigator?.mediaDevices?.getUserMedia) {
      setCameraError("Live browser camera stream is not supported in this browser. Use Direct Camera Snap instead.");
      return;
    }

    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: mode, width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false
      });
      setStream(mediaStream);
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
        videoRef.current.onloadedmetadata = () => {
          videoRef.current.play().catch(e => console.log('Camera video playback error:', e));
        };
      }
    } catch (err) {
      console.error("Camera access error:", err);
      setCameraError("Camera access denied or unavailable. Please click 'Open Device Camera' or use file upload.");
    }
  };

  useEffect(() => {
    if (showCameraModal) {
      startCamera(facingMode);
    } else {
      stopCamera();
    }
    return () => stopCamera();
  }, [showCameraModal, facingMode]);

  const toggleCameraFacing = () => {
    const nextMode = facingMode === 'environment' ? 'user' : 'environment';
    setFacingMode(nextMode);
  };

  const handleCapture = () => {
    if (!videoRef.current) return;
    const video = videoRef.current;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob((blob) => {
      if (blob) {
        const file = new File([blob], `camera_snap_${Date.now()}.jpg`, { type: 'image/jpeg' });
        const localUrl = URL.createObjectURL(blob);
        setCapturedPreview(localUrl);
        if (onFileSelected) {
          onFileSelected(file, localUrl);
        }
        setShowCameraModal(false);
        stopCamera();
      }
    }, 'image/jpeg', 0.92);
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      const localUrl = URL.createObjectURL(file);
      setCapturedPreview(localUrl);
      if (onFileSelected) {
        onFileSelected(file, localUrl);
      }
    }
  };

  const activeDisplayUrl = capturedPreview || currentPreview || previewUrl;

  return (
    <div className="space-y-3">
      {label && <label className="block text-sm font-semibold text-gray-700">{label}</label>}

      {/* Action Buttons */}
      <div className="flex flex-wrap gap-2.5">
        <button
          type="button"
          disabled={disabled}
          onClick={() => {
            if (navigator?.mediaDevices?.getUserMedia) {
              setShowCameraModal(true);
            } else {
              directCameraInputRef.current?.click();
            }
          }}
          className="flex-1 min-w-[140px] flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium rounded-xl shadow-sm transition-all disabled:opacity-50 text-xs sm:text-sm"
        >
          <Camera className="w-4 h-4" />
          <span>Snap Camera 📸</span>
        </button>

        <button
          type="button"
          disabled={disabled}
          onClick={() => fileInputRef.current?.click()}
          className="flex-1 min-w-[140px] flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-xl shadow-sm transition-all disabled:opacity-50 text-xs sm:text-sm"
        >
          <Upload className="w-4 h-4" />
          <span>Choose File 📁</span>
        </button>

        {/* Hidden Native Camera Input */}
        <input
          ref={directCameraInputRef}
          type="file"
          accept={accept}
          capture="environment"
          onChange={handleFileChange}
          className="hidden"
        />

        {/* Hidden File Picker */}
        <input
          ref={fileInputRef}
          id={id}
          type="file"
          accept={accept}
          onChange={handleFileChange}
          className="hidden"
        />
      </div>

      {/* Selected Image Preview Box */}
      {activeDisplayUrl && (
        <div className="relative mt-2 rounded-xl overflow-hidden border-2 border-emerald-500/30 bg-gray-900 shadow-md group max-h-64 flex justify-center">
          <img
            src={activeDisplayUrl}
            alt="Uploaded Preview"
            className="max-h-64 object-contain rounded-lg"
          />
          <div className="absolute top-2 right-2 bg-emerald-600/90 text-white text-xs font-semibold px-2.5 py-1 rounded-full flex items-center gap-1 shadow">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Photo Selected</span>
          </div>
        </div>
      )}

      {/* Camera Live Modal */}
      {showCameraModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl flex flex-col">
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800 bg-gray-900/90">
              <h3 className="text-white font-semibold flex items-center gap-2">
                <Camera className="w-5 h-5 text-emerald-400" />
                Live Camera Snap
              </h3>
              <button
                type="button"
                onClick={() => setShowCameraModal(false)}
                className="text-gray-400 hover:text-white p-1 rounded-lg hover:bg-gray-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="relative bg-black aspect-video flex items-center justify-center">
              {cameraError ? (
                <div className="text-center p-6 space-y-3">
                  <div className="text-red-400 text-xs font-semibold">{cameraError}</div>
                  <button
                    type="button"
                    onClick={() => {
                      setShowCameraModal(false);
                      directCameraInputRef.current?.click();
                    }}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-lg shadow inline-flex items-center gap-2"
                  >
                    <Camera className="w-4 h-4" /> Open Native Camera
                  </button>
                </div>
              ) : (
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className="w-full h-full object-cover"
                />
              )}
            </div>

            <div className="p-4 bg-gray-900 flex items-center justify-between gap-3">
              <button
                type="button"
                onClick={toggleCameraFacing}
                className="flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 text-sm font-medium rounded-lg transition"
              >
                <RefreshCw className="w-4 h-4" />
                Switch Camera
              </button>

              <button
                type="button"
                onClick={handleCapture}
                disabled={!!cameraError}
                className="flex items-center gap-2 px-6 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-xl shadow-lg transition disabled:opacity-50"
              >
                <Camera className="w-5 h-5" />
                Take Photo
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
