(() => {
    const video = document.getElementById("cameraVideo");
    const canvas = document.getElementById("cameraCanvas");
    const startButton = document.getElementById("startCamera");
    const captureButton = document.getElementById("captureImage");
    const form = document.getElementById("cameraForm");
    const imageInput = document.getElementById("imageData");

    if (!video || !canvas || !startButton || !captureButton || !form || !imageInput) {
        return;
    }

    let stream = null;

    async function startCamera() {
        try {
            if (stream) {
                stream.getTracks().forEach((track) => track.stop());
            }

            stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
                audio: false,
            });
            video.srcObject = stream;
            await video.play();
        } catch (error) {
            window.alert("Camera access failed. Allow camera permission and try again.");
            console.error(error);
        }
    }

    function captureAndSubmit() {
        if (!stream || video.videoWidth === 0) {
            window.alert("Start the camera before capturing an image.");
            return;
        }

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const context = canvas.getContext("2d");
        context.translate(canvas.width, 0);
        context.scale(-1, 1);
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        imageInput.value = canvas.toDataURL("image/jpeg", 0.9);
        captureButton.disabled = true;
        captureButton.textContent = "Processing...";
        form.submit();
    }

    startButton.addEventListener("click", startCamera);
    captureButton.addEventListener("click", captureAndSubmit);
    window.addEventListener("beforeunload", () => {
        if (stream) {
            stream.getTracks().forEach((track) => track.stop());
        }
    });
})();
