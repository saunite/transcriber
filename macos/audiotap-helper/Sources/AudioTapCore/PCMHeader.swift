import Foundation

/// Builds the fixed 8-byte header `macos_capture.py` reads before the raw
/// interleaved Float32LE PCM stream: sample rate (uint32 LE), channel count
/// (uint16 LE), reserved (uint16 LE, always 0). Pure/deterministic so it can
/// be unit-tested without a real Core Audio tap (see design.md's stream
/// format note and tasks.md 4.3).
public func makePCMHeader(sampleRate: UInt32, channelCount: UInt16) -> Data {
    var header = Data()
    withUnsafeBytes(of: sampleRate.littleEndian) { header.append(contentsOf: $0) }
    withUnsafeBytes(of: channelCount.littleEndian) { header.append(contentsOf: $0) }
    withUnsafeBytes(of: UInt16(0).littleEndian) { header.append(contentsOf: $0) }
    return header
}
