import AppKit
let destination = CommandLine.arguments[1]
let size = NSSize(width: 1024, height: 1024)
let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: 1024, pixelsHigh: 1024, bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
bitmap.size = size
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: bitmap)
let outer = NSBezierPath(roundedRect: NSRect(x: 80, y: 80, width: 864, height: 864), xRadius: 190, yRadius: 190)
NSGradient(starting: NSColor(calibratedRed: 0.16, green: 0.20, blue: 0.27, alpha: 1), ending: NSColor(calibratedRed: 0.06, green: 0.08, blue: 0.12, alpha: 1))!.draw(in: outer, angle: 65)
let orange = NSColor(calibratedRed: 1, green: 0.44, blue: 0.035, alpha: 1)
let axis=NSBezierPath(); axis.move(to: NSPoint(x: 248,y: 728)); axis.line(to:NSPoint(x:248,y:290)); axis.line(to:NSPoint(x:772,y:290)); axis.lineWidth=30; axis.lineCapStyle = .round
NSColor(calibratedWhite:0.43,alpha:0.45).setStroke(); axis.stroke()
for (x,bottom,top) in [(350.0,365.0,480.0),(478.0,460.0,590.0),(606.0,510.0,690.0)] {
 let wick=NSBezierPath(); wick.move(to:NSPoint(x:x,y:bottom-33)); wick.line(to:NSPoint(x:x,y:top+33)); wick.lineWidth=13; wick.lineCapStyle = .round; orange.setStroke(); wick.stroke()
 orange.setFill(); NSBezierPath(roundedRect:NSRect(x:x-26,y:bottom,width:52,height:top-bottom),xRadius:8,yRadius:8).fill()
}
let line=NSBezierPath(); line.move(to:NSPoint(x:330,y:355)); line.line(to:NSPoint(x:458,y:428)); line.line(to:NSPoint(x:585,y:425)); line.line(to:NSPoint(x:743,y:605)); line.lineWidth=23; line.lineJoinStyle = .round; line.lineCapStyle = .round
NSColor(calibratedRed:0.84,green:0.94,blue:1,alpha:1).setStroke();line.stroke()
let arrow=NSBezierPath(); arrow.move(to:NSPoint(x:677,y:602)); arrow.line(to:NSPoint(x:748,y:618)); arrow.line(to:NSPoint(x:744,y:543)); arrow.lineWidth=23;arrow.lineJoinStyle = .round;arrow.lineCapStyle = .round;arrow.stroke()
NSGraphicsContext.restoreGraphicsState()
try bitmap.representation(using:.png,properties:[:])!.write(to:URL(fileURLWithPath:destination))
