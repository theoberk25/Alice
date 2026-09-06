// Native camera producer. No image/file/URL input and no authentication authority.
import AppKit
import AVFoundation
import CoreImage
import Foundation
import Darwin

final class Camera: NSObject, AVCaptureVideoDataOutputSampleBufferDelegate {
    let session = AVCaptureSession()
    let context = CIContext(options: [.cacheIntermediates: false])
    let queue = DispatchQueue(label: "alice.camera.frames")
    let started = ProcessInfo.processInfo.systemUptime
    let parent = getppid()
    let binding: String
    let duration: Double
    var lastEvidence = 0.0
    var nextPreview = 0.0
    var previewSequence = 0
    var sequence = 0
    var received = 0
    var outputSize = CGSize(width: 640, height: 480)
    var timer: DispatchSourceTimer?
    var observers: [NSObjectProtocol] = []

    init(binding: String, duration: Double) {
        self.binding = binding
        self.duration = duration
    }

    func emit(_ payload: [String: Any]) {
        guard let data = try? JSONSerialization.data(withJSONObject: payload), data.count < 700_000 else {
            exit(3)
        }
        FileHandle.standardOutput.write(data)
        FileHandle.standardOutput.write(Data([10]))
    }

    func stop(_ reason: String) -> Never {
        session.stopRunning()
        emit(["kind": "stopped", "session_id": binding, "reason": reason,
              "received": received, "emitted": sequence])
        exit(0)
    }

    func start() {
        let status = AVCaptureDevice.authorizationStatus(for: .video)
        if status == .notDetermined {
            AVCaptureDevice.requestAccess(for: .video) { allowed in
                DispatchQueue.main.async {
                    if allowed { self.open() } else { self.stop("CAMERA_PERMISSION_DENIED") }
                }
            }
        } else if status == .authorized { open() }
        else { stop("CAMERA_PERMISSION_DENIED") }
    }

    func open() {
        let devices = AVCaptureDevice.DiscoverySession(
            deviceTypes: [.builtInWideAngleCamera], mediaType: .video, position: .unspecified
        ).devices
        guard let device = devices.first, device.isConnected,
              let input = try? AVCaptureDeviceInput(device: device) else {
            stop("SUPPORTED_BUILT_IN_CAMERA_UNAVAILABLE")
        }
        session.beginConfiguration()
        let output = AVCaptureVideoDataOutput()
        output.alwaysDiscardsLateVideoFrames = true
        output.videoSettings = [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA]
        output.setSampleBufferDelegate(self, queue: queue)
        guard session.canAddInput(input), session.canAddOutput(output) else {
            session.commitConfiguration()
            stop("CAMERA_CONFIGURATION_FAILED")
        }
        session.addInput(input)
        // Adapted from FaceGate-Mac CameraManager.swift (MIT, Dweep Desai),
        // be3fe1dde73cfc4a7f6a0f79cd1be7656dbca2eb. Select the preset only
        // after attaching the actual device. See third-party-notices.md.
        // Keep the sensor's wide view; inference output is still bounded below.
        if device.supportsSessionPreset(.hd1280x720) && session.canSetSessionPreset(.hd1280x720) {
            session.sessionPreset = .hd1280x720
        } else if session.canSetSessionPreset(.high) {
            session.sessionPreset = .high
        } else {
            session.sessionPreset = .medium
        }
        session.addOutput(output)
        if let connection = output.connection(with: .video), connection.isVideoMirroringSupported {
            connection.automaticallyAdjustsVideoMirroring = false
            connection.isVideoMirrored = false
        }
        session.commitConfiguration()
        let dimensions = CMVideoFormatDescriptionGetDimensions(device.activeFormat.formatDescription)
        if Double(dimensions.width) / Double(dimensions.height) > 1.6 {
            outputSize = CGSize(width: 640, height: 360)
        }
        if device.activeFormat.videoSupportedFrameRateRanges.contains(where: {
            $0.minFrameRate <= 30 && $0.maxFrameRate >= 30
        }) {
            do {
                try device.lockForConfiguration()
                device.activeVideoMinFrameDuration = CMTime(value: 1, timescale: 30)
                device.activeVideoMaxFrameDuration = CMTime(value: 1, timescale: 30)
                device.unlockForConfiguration()
            } catch { /* Keep the device's supported rate; evidence remains bounded. */ }
        }
        let center = NotificationCenter.default
        for name in [AVCaptureSession.runtimeErrorNotification, AVCaptureSession.wasInterruptedNotification,
                     AVCaptureDevice.wasDisconnectedNotification] {
            observers.append(center.addObserver(forName: name, object: nil, queue: .main) { _ in
                self.stop("CAMERA_DISCONNECTED_OR_INTERRUPTED")
            })
        }
        let workspace = NSWorkspace.shared.notificationCenter
        for name in [NSWorkspace.willSleepNotification, NSWorkspace.screensDidSleepNotification,
                     NSWorkspace.sessionDidResignActiveNotification] {
            observers.append(workspace.addObserver(forName: name, object: nil, queue: .main) { _ in
                self.stop("SYSTEM_LOCK_OR_SLEEP")
            })
        }
        observers.append(DistributedNotificationCenter.default().addObserver(
            forName: Notification.Name("com.apple.screenIsLocked"), object: nil, queue: .main
        ) { _ in self.stop("SYSTEM_LOCK_OR_SLEEP") })
        emit(["kind": "ready", "session_id": binding, "source": "AVFOUNDATION_BUILT_IN",
              "mirrored": false, "width": Int(outputSize.width), "height": Int(outputSize.height)])
        let watchdog = DispatchSource.makeTimerSource(queue: .main)
        watchdog.schedule(deadline: .now(), repeating: .milliseconds(100))
        watchdog.setEventHandler {
            if getppid() != self.parent { self.stop("PARENT_EXITED") }
            if ProcessInfo.processInfo.systemUptime - self.started >= self.duration { self.stop("EXPIRED") }
        }
        watchdog.resume()
        timer = watchdog
        DispatchQueue.global(qos: .userInitiated).async { self.session.startRunning() }
    }

    func captureOutput(_ output: AVCaptureOutput, didOutput sample: CMSampleBuffer,
                       from connection: AVCaptureConnection) {
        let now = ProcessInfo.processInfo.systemUptime
        received += 1
        // Display must not wait for identity inference. The native owner keeps
        // only the newest preview; independent evidence is sampled at <=4 Hz.
        guard now >= nextPreview - 0.002,
              let buffer = CMSampleBufferGetImageBuffer(sample) else { return }
        // Keep an accumulated deadline. Resetting it from each jittery callback
        // can skip the next genuine 30 Hz camera frame and make preview stutter.
        nextPreview = max(nextPreview + 1.0 / 30.0, now)
        let source = CIImage(cvPixelBuffer: buffer)
        // Fit every sensor pixel into the bounded evidence canvas. The old fill
        // transform cropped both sides of a wide image, losing faces on a turn.
        // Native wide frames stay 16:9, avoiding artificial letterbox edges in
        // the presentation model's contextual crop. 4:3 devices retain 640x480.
        let scale = min(outputSize.width / source.extent.width, outputSize.height / source.extent.height)
        let fitted = source.transformed(by: CGAffineTransform(
                translationX: -source.extent.minX, y: -source.extent.minY))
            .transformed(by: CGAffineTransform(scaleX: scale, y: scale))
            .transformed(by: CGAffineTransform(
                translationX: (outputSize.width - source.extent.width * scale) / 2,
                y: (outputSize.height - source.extent.height * scale) / 2))
        let canvas = CGRect(origin: .zero, size: outputSize)
        let background = CIImage(color: CIColor(red: 0, green: 0, blue: 0)).cropped(to: canvas)
        let picture = fitted.composited(over: background).cropped(to: canvas)
        guard let jpeg = context.jpegRepresentation(of: picture, colorSpace: CGColorSpaceCreateDeviceRGB(),
                  options: [kCGImageDestinationLossyCompressionQuality as CIImageRepresentationOption: 0.78]),
              jpeg.count < 500_000 else { return }
        let encoded = jpeg.base64EncodedString()
        let elapsed = Int((now - started) * 1000)
        previewSequence += 1
        emit(["kind": "preview", "session_id": binding, "sequence": previewSequence,
              "elapsed_ms": elapsed, "jpeg": encoded])
        if now - lastEvidence >= 0.25 {
            lastEvidence = now
            sequence += 1
            emit(["kind": "frame", "session_id": binding, "sequence": sequence,
                  "elapsed_ms": elapsed, "jpeg": encoded])
        }
    }
}

guard CommandLine.arguments.count == 3,
      UUID(uuidString: CommandLine.arguments[1]) != nil,
      let duration = Double(CommandLine.arguments[2]), duration >= 1, duration <= 90 else { exit(2) }
signal(SIGPIPE, SIG_DFL)
let camera = Camera(binding: CommandLine.arguments[1], duration: duration)
camera.start()
RunLoop.main.run()
