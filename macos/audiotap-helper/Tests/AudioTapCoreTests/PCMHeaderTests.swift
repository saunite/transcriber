import XCTest
@testable import AudioTapCore

final class PCMHeaderTests: XCTestCase {
    func testStereo48kHeaderLayout() {
        let header = makePCMHeader(sampleRate: 48_000, channelCount: 2)
        XCTAssertEqual(Array(header), [
            0x80, 0xBB, 0x00, 0x00, // 48_000 as little-endian uint32
            0x02, 0x00,             // 2 channels as little-endian uint16
            0x00, 0x00,             // reserved
        ])
    }

    func testMonoHeaderLayout() {
        let header = makePCMHeader(sampleRate: 44_100, channelCount: 1)
        XCTAssertEqual(Array(header), [
            0x44, 0xAC, 0x00, 0x00, // 44_100 as little-endian uint32
            0x01, 0x00,             // 1 channel as little-endian uint16
            0x00, 0x00,             // reserved
        ])
    }

    func testHeaderIsAlwaysEightBytes() {
        XCTAssertEqual(makePCMHeader(sampleRate: 0, channelCount: 0).count, 8)
        XCTAssertEqual(makePCMHeader(sampleRate: .max, channelCount: .max).count, 8)
    }
}
