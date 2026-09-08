// Native helper for macOS system-audio loopback capture via the Core Audio
// Process Tap API (macOS 14.4+). Spawned as a subprocess by
// macos_capture.py; writes a small self-describing header, then raw
// interleaved Float32LE PCM frames, to stdout until stdin is closed.
//
// Builds and runs on real macOS 14.4+ hardware (see tasks.md section 5):
// creates the tap, wraps it in a private aggregate device, and streams a
// correctly-formatted header (confirmed 48kHz/stereo/float32) with no
// errors. Not yet verified against actual non-silent audio content or a
// permission-denied path — both need non-virtualized hardware (see
// tasks.md 5.3-5.6 for what's still outstanding and why).
//
// The pure header-construction logic lives in AudioTapCore (see
// ../AudioTapCore/PCMHeader.swift) so it's covered by `swift test` in CI
// without needing a real tap; everything below this point talks to actual
// Core Audio and can only be exercised on real hardware.

import Foundation
import CoreAudio
import AudioToolbox
import AudioTapCore

// MARK: - Exit codes (documented contract with macos_capture.py)

private enum HelperExitCode: Int32 {
    case unsupportedOSVersion = 10
    case permissionDenied = 11
    case tapCreationFailed = 12
}

private func fail(_ code: HelperExitCode, _ message: String) -> Never {
    FileHandle.standardError.write((message + "\n").data(using: .utf8)!)
    exit(code.rawValue)
}

private func checkStatus(_ status: OSStatus, _ context: String) {
    guard status != noErr else { return }
    if status == kAudioHardwareIllegalOperationError {
        fail(
            .permissionDenied,
            "Audio capture permission was not granted for \(context). Grant it in "
                + "System Settings > Privacy & Security > Audio Capture (or Screen "
                + "Recording, depending on macOS version), then try again."
        )
    }
    fail(.tapCreationFailed, "\(context) failed with OSStatus \(status).")
}

// MARK: - OS version gate (belt-and-suspenders; macos_capture.py checks first)

guard
    ProcessInfo.processInfo.isOperatingSystemAtLeast(
        OperatingSystemVersion(majorVersion: 14, minorVersion: 4, patchVersion: 0)
    )
else {
    fail(.unsupportedOSVersion, "macOS 14.4 or later is required for Core Audio Process Tap capture.")
}

// MARK: - Create the process tap (global system-output mix, no processes excluded)

let tapDescription = CATapDescription(stereoGlobalTapButExcludeProcesses: [])
tapDescription.name = "TranscriberSystemAudioTap"
tapDescription.isPrivate = true

var tapID: AudioObjectID = kAudioObjectUnknown
checkStatus(AudioHardwareCreateProcessTap(tapDescription, &tapID), "creating the process tap")

// MARK: - Wrap the tap in a private aggregate device (required to pull audio via an IOProc)

let aggregateDescription: [String: Any] = [
    kAudioAggregateDeviceNameKey as String: "TranscriberSystemAudioTapAggregate",
    kAudioAggregateDeviceUIDKey as String: UUID().uuidString,
    kAudioAggregateDeviceIsPrivateKey as String: true,
    kAudioAggregateDeviceTapAutoStartKey as String: true,
    kAudioAggregateDeviceTapListKey as String: [
        [
            kAudioSubTapUIDKey as String: tapDescription.uuid.uuidString,
            kAudioSubTapDriftCompensationKey as String: true,
        ]
    ],
]

var aggregateDeviceID: AudioObjectID = kAudioObjectUnknown
checkStatus(
    AudioHardwareCreateAggregateDevice(aggregateDescription as CFDictionary, &aggregateDeviceID),
    "creating the aggregate capture device"
)

// MARK: - Discover the stream format so macos_capture.py doesn't have to guess

var streamFormat = AudioStreamBasicDescription()
var formatPropertySize = UInt32(MemoryLayout<AudioStreamBasicDescription>.size)
var formatAddress = AudioObjectPropertyAddress(
    mSelector: kAudioDevicePropertyStreamFormat,
    mScope: kAudioObjectPropertyScopeInput,
    mElement: kAudioObjectPropertyElementMain
)
checkStatus(
    AudioObjectGetPropertyData(aggregateDeviceID, &formatAddress, 0, nil, &formatPropertySize, &streamFormat),
    "reading the capture stream format"
)

let sampleRate = UInt32(streamFormat.mSampleRate)
let channelCount = UInt16(streamFormat.mChannelsPerFrame)

FileHandle.standardOutput.write(makePCMHeader(sampleRate: sampleRate, channelCount: channelCount))

// MARK: - Stream captured audio to stdout via an IOProc

let stdoutHandle = FileHandle.standardOutput
var ioProcID: AudioDeviceIOProcID?

let ioBlock: AudioDeviceIOBlock = { _, inputData, _, _, _ in
    let bufferList = UnsafeMutableAudioBufferListPointer(UnsafeMutablePointer(mutating: inputData))
    for buffer in bufferList {
        guard let mData = buffer.mData, buffer.mDataByteSize > 0 else { continue }
        stdoutHandle.write(Data(bytes: mData, count: Int(buffer.mDataByteSize)))
    }
}

checkStatus(
    AudioDeviceCreateIOProcIDWithBlock(&ioProcID, aggregateDeviceID, nil, ioBlock),
    "creating the capture IO proc"
)
checkStatus(AudioDeviceStart(aggregateDeviceID, ioProcID), "starting capture")

// MARK: - Run until stdin closes (macos_capture.py closes/terminates this
// process to signal shutdown, mirroring how WASAPICapture relies on
// stream.close() to unblock its own background reader) or we're signaled.

func teardown() {
    if let ioProcID = ioProcID {
        AudioDeviceStop(aggregateDeviceID, ioProcID)
        AudioDeviceDestroyIOProcID(aggregateDeviceID, ioProcID)
    }
    AudioHardwareDestroyAggregateDevice(aggregateDeviceID)
    AudioHardwareDestroyProcessTap(tapID)
}

signal(SIGTERM) { _ in
    teardown()
    exit(0)
}
signal(SIGINT) { _ in
    teardown()
    exit(0)
}

// Watch for stdin EOF on a background thread so the main thread is free to
// run its run loop below -- several system frameworks (this tap's own async
// authorization check very plausibly among them) deliver completion
// callbacks via the main run loop/dispatch queue, and never fire at all if
// nothing ever pumps it (a bare top-level Swift executable doesn't start
// one automatically, unlike an app with a UIKit/AppKit lifecycle).
DispatchQueue.global(qos: .utility).async {
    while FileHandle.standardInput.availableData.count > 0 {}
    teardown()
    exit(0)
}

CFRunLoopRun()
