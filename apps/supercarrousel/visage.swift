// Trouve les visages d'une image (Vision, intégré à macOS). Sortie : x y largeur hauteur, en fractions, origine en haut à gauche.
import Foundation
import Vision
let url = URL(fileURLWithPath: CommandLine.arguments[1])
let req = VNDetectFaceRectanglesRequest()
try VNImageRequestHandler(url: url, options: [:]).perform([req])
for f in req.results ?? [] {   // un visage par ligne
    let b = f.boundingBox
    print(String(format: "%.4f %.4f %.4f %.4f", b.minX, 1 - b.maxY, b.width, b.height))
}
