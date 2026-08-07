import AppKit
import Foundation

let actionType = NSPasteboard.PasteboardType("com.apple.shortcuts.action")
guard let items = NSPasteboard.general.pasteboardItems, !items.isEmpty else {
    fputs("clipboard is empty\n", stderr)
    exit(1)
}
print("items=\(items.count)")
for (index, item) in items.enumerated() {
    guard let data = item.data(forType: actionType) else {
        print("item \(index): no Shortcuts action data")
        continue
    }
    let value = try PropertyListSerialization.propertyList(from: data, options: [], format: nil)
    let xml = try PropertyListSerialization.data(
        fromPropertyList: value,
        format: .xml,
        options: 0
    )
    print(String(decoding: xml, as: UTF8.self))
}
