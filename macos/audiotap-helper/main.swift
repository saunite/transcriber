// Native helper for macOS system-audio loopback capture via the Core Audio
// Process Tap API (macOS 14.4+). Spawned as a subprocess by
// macos_capture.py; writes a small self-describing header, then raw
// interleaved Float32LE PCM frames, to stdout until stdin is closed.
//
// UNVERIFIED DRAFT: written without access to macOS/Xcode to build or run
// against (see openspec/changes/add-macos-capture/design.md, "Open
// Questions" and "Risks"). The Core Audio Process Tap + aggregate-device
// + IOProc shape below matches Apple's documented pattern for this API as
// of authoring, but exact symbol availability, error codes, and the
// delivered stream format need confirmation on real hardware before this
// is trusted (see tasks.md section 5).

import Foundation
import CoreAudio
import AudioToolbox

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
    if status == kAudioHardwareNotAuthorizedError || status == kAudioHardwareIllegalOperationError {
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

// Header consumed by macos_capture.py: sample rate (uint32 LE), channel
// count (uint16 LE), reserved (uint16 LE, always 0). Frames follow as raw
// interleaved Float32LE PCM matching streamFormat.
let sampleRate = UInt32(streamFormat.mSampleRate)
let channelCount = UInt16(streamFormat.mChannelsPerFrame)

var header = Data()
withUnsafeBytes(of: sampleRate.littleEndian) { header.append(contentsOf: $0) }
withUnsafeBytes(of: channelCount.littleEndian) { header.append(contentsOf: $0) }
withUnsafeBytes(of: UInt16(0).littleEndian) { header.append(contentsOf: $0) }
FileHandle.standardOutput.write(header)

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

// Block until stdin hits EOF.
while FileHandle.standardInput.availableData.count > 0 {}
teardown()
exit(0)
