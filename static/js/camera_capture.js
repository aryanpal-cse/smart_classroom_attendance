(() => {
    const video = document.getElementById("cameraVideo");
    const canvas = document.getElementById("cameraCanvas");
    const startButton = document.getElementById("startCamera");
    const captureButton = document.getElementById("captureImage");
    const form = document.getElementById("cameraForm");
    const imageInput = document.getElementById("imageData");
    const statusBox = document.getElementById("cameraStatus");

    if (!video || !canvas || !startButton || !captureButton || !form || !imageInput) {
        console.error("Face capture controls could not be initialized.");
        return;
    }

    let stream = null;
    let cameraReady = false;
    let submitting = false;

    function setStatus(message, state = "info") {
        if (!statusBox) {
            return;
        }

        statusBox.textContent = message;
        statusBox.dataset.state = state;
    }

    function stopCamera() {
        if (!stream) {
            return;
        }

        stream.getTracks().forEach((track) => track.stop());
        stream = null;
        cameraReady = false;
    }

    async function startCamera() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            setStatus(
                "This browser does not support camera access. Open the page in the latest Google Chrome.",
                "error",
            );
            return;
        }

        startButton.disabled = true;
        captureButton.disabled = true;
        setStatus("Starting camera...", "working");

        try {
            stopCamera();

            stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: "user",
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                },
                audio: false,
            });

            video.srcObject = stream;

            await new Promise((resolve, reject) => {
                const timeout = window.setTimeout(() => {
                    reject(new Error("Camera preview did not become ready in time."));
                }, 8000);

                const onReady = () => {
                    window.clearTimeout(timeout);
                    video.removeEventListener("loadedmetadata", onReady);
                    resolve();
                };

                if (video.readyState >= 1 && video.videoWidth > 0) {
                    onReady();
                } else {
                    video.addEventListener("loadedmetadata", onReady, { once: true });
                }
            });

            await video.play();
            cameraReady = video.videoWidth > 0 && video.videoHeight > 0;

            if (!cameraReady) {
                throw new Error("The camera started but no video frame is available.");
            }

            captureButton.disabled = false;
            startButton.textContent = "Restart Camera";
            setStatus(
                "Camera ready. Center one face, look toward the camera, then click Capture Sample.",
                "success",
            );
        } catch (error) {
            stopCamera();
            captureButton.disabled = true;
            setStatus(
                `Camera access failed: ${error.name || "Error"}. Check Chrome camera permission and close other camera apps.`,
                "error",
            );
            console.error("CAMERA START ERROR:", error);
        } finally {
            startButton.disabled = false;
        }
    }

    function captureAndSubmit() {
        if (submitting) {
            return;
        }

        if (!stream || !cameraReady || video.videoWidth === 0 || video.videoHeight === 0) {
            setStatus("Start the camera and wait until the preview is ready.", "error");
            return;
        }

        try {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;

            const context = canvas.getContext("2d", { alpha: false });
            if (!context) {
                throw new Error("Canvas is unavailable in this browser.");
            }

            context.save();
            context.translate(canvas.width, 0);
            context.scale(-1, 1);
            context.drawImage(video, 0, 0, canvas.width, canvas.height);
            context.restore();

            const imageData = canvas.toDataURL("image/jpeg", 0.88);

            if (!imageData || imageData.length < 1000) {
                throw new Error("The captured frame is empty.");
            }

            // Set every image_data field defensively. Older templates may have
            // rendered the hidden field twice through hidden_tag().
            document.querySelectorAll('input[name="image_data"]').forEach((field) => {
                field.value = imageData;
            });
            imageInput.value = imageData;
            submitting = true;
            captureButton.disabled = true;
            startButton.disabled = true;
            captureButton.textContent = "Saving Sample...";
            setStatus("Captured. Detecting your face and saving the sample...", "working");

            // requestSubmit preserves CSRF/form validation and is safer than form.submit().
            if (typeof form.requestSubmit === "function") {
                form.requestSubmit();
            } else {
                HTMLFormElement.prototype.submit.call(form);
            }
        } catch (error) {
            submitting = false;
            captureButton.disabled = false;
            startButton.disabled = false;
            setStatus(`Capture failed: ${error.message}`, "error");
            console.error("CAMERA CAPTURE ERROR:", error);
        }
    }

    startButton.addEventListener("click", startCamera);
    captureButton.addEventListener("click", captureAndSubmit);

    window.addEventListener("beforeunload", stopCamera);
    document.addEventListener("visibilitychange", () => {
        if (document.hidden && submitting) {
            stopCamera();
        }
    });

    // Start automatically after the page is ready. The button remains available for retry.
    window.addEventListener("load", () => {
        startCamera();
    });
})();
