import Foundation
import Vision
import AppKit
import CoreImage

func removeBG(input: URL, output: URL) throws {
    guard let src = CGImageSourceCreateWithURL(input as CFURL, nil),
          let cg = CGImageSourceCreateImageAtIndex(src, 0, nil) else {
        throw NSError(domain: "bgrm", code: 1, userInfo: [NSLocalizedDescriptionKey: "cannot read"])
    }

    let req = VNGenerateForegroundInstanceMaskRequest()
    let handler = VNImageRequestHandler(cgImage: cg)
    try handler.perform([req])

    guard let result = req.results?.first else {
        throw NSError(domain: "bgrm", code: 2, userInfo: [NSLocalizedDescriptionKey: "no foreground"])
    }

    let pixelBuffer = try result.generateMaskedImage(
        ofInstances: result.allInstances,
        from: handler,
        croppedToInstancesExtent: false
    )

    let ci = CIImage(cvPixelBuffer: pixelBuffer)
    let ctx = CIContext()
    guard let outCG = ctx.createCGImage(ci, from: ci.extent) else {
        throw NSError(domain: "bgrm", code: 3)
    }

    guard let dest = CGImageDestinationCreateWithURL(output as CFURL, "public.png" as CFString, 1, nil) else {
        throw NSError(domain: "bgrm", code: 4)
    }
    CGImageDestinationAddImage(dest, outCG, nil)
    guard CGImageDestinationFinalize(dest) else {
        throw NSError(domain: "bgrm", code: 5)
    }
}

let args = CommandLine.arguments
guard args.count == 3 else {
    FileHandle.standardError.write("usage: bgrm <in.png> <out.png>\n".data(using: .utf8)!)
    exit(1)
}
do {
    try removeBG(input: URL(fileURLWithPath: args[1]), output: URL(fileURLWithPath: args[2]))
} catch {
    FileHandle.standardError.write("error: \(error.localizedDescription)\n".data(using: .utf8)!)
    exit(2)
}
